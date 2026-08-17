"""
Bragi Dependency Graph Service (Plan 03 Phase B)

One graph, many consumers: builds the import graph ONCE per scan and serves
cycles (SCC condensation), centrality (Ca/Ce/instability/pagerank/percentile),
and weighted break suggestions to every other Bragi consumer — replacing the
three-full-scans-per-report pattern (DEEPTHINK_09, RESEARCH_15, RESEARCH_02).

Caching (RESEARCH_15 / CH-0039):
    - Per-file entries under `.asgard_cache/bragi_dep_graph.json` keyed by
      CONTENT hash (skip re-parsing unchanged files) and carrying an
      INTERFACE hash (sorted export names + import targets).
    - Derived results (SCCs, centrality) are keyed by the combined interface
      hash of all files: a body-only edit re-parses one file but leaves every
      interface hash unchanged, so dependents' cached edges and the derived
      results survive; changing an export list invalidates them.
    - The file is HMAC-SHA256 signed (`ASGARD_DEP_GRAPH_HMAC_KEY` or a
      sibling ``.key``), schema-validated, size-capped, and written via
      atomic replace. Unsigned, corrupt, or schema-invalid records are a
      miss. Derived payloads are never reused unless the envelope verifies.

All outputs are deterministic: modules and results are sorted, and pagerank
uses networkx's deterministic power iteration.
"""

import ast
import hashlib
import hmac
import json
import os
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

import networkx as nx

from Asgard.Bragi.Dependencies.models.dependency_models import (
    SCC,
    CentralityInfo,
    DependencyConfig,
    DependencySeverity,
    EdgeBreak,
    ModuleDependencies,
)
from Asgard.Bragi.Dependencies.services.import_analyzer import ImportAnalyzer

CACHE_RELATIVE_PATH = Path(".asgard_cache") / "bragi_dep_graph.json"
CACHE_VERSION = "1.0.0"
HMAC_ENV = "ASGARD_DEP_GRAPH_HMAC_KEY"

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_CACHE_BYTES = 8 * 1024 * 1024
_MAX_FILES = 20_000
_MAX_PATH_LEN = 4096
_MAX_MODULE_LEN = 512
_MAX_NAME_LEN = 256
_MAX_NAMES_PER_FILE = 2_000
_MAX_SCCS = 10_000
_MAX_SCC_MEMBERS = 10_000
_MAX_CENTRALITY = 20_000
_SEVERITY_VALUES = frozenset(item.value for item in DependencySeverity)

#: SCCs at or below this size get their simple cycles enumerated for display;
#: larger SCCs are reported as one component with break suggestions instead
#: (DEEPTHINK_09: never run simple_cycles on a dense component).
MAX_SCC_FOR_CYCLE_ENUMERATION = 12

#: Cap on enumerated simple cycles per SCC (display budget).
MAX_CYCLES_PER_SCC = 50

#: Number of minimum-weight feedback edges suggested per large SCC.
TOP_BREAK_SUGGESTIONS = 3


def no_cache_env() -> bool:
    """True when ASGARD_NO_CACHE requests that scans write nothing into
    the scanned path (read-only target safety)."""
    return os.environ.get("ASGARD_NO_CACHE", "").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_limited(path: Path, max_bytes: int) -> Optional[bytes]:
    if path.is_symlink():
        return None
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return None
    try:
        data = os.read(fd, max_bytes + 1)
    finally:
        os.close(fd)
    if not data or len(data) > max_bytes:
        return None
    return data


def _sign_cache(payload: dict, key: bytes) -> str:
    body = {
        "version": payload.get("version"),
        "files": payload.get("files"),
        "derived": payload.get("derived"),
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def _nonneg_int(value: object) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _finite_float(value: object) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _str_list(value: object, *, max_items: int, max_len: int) -> Optional[List[str]]:
    if not isinstance(value, list) or len(value) > max_items:
        return None
    out: List[str] = []
    for item in value:
        if not isinstance(item, str) or len(item) > max_len:
            return None
        out.append(item)
    return out


def _sanitize_file_entry(entry: object) -> Optional[dict]:
    if not isinstance(entry, dict):
        return None
    content_hash = entry.get("content_hash")
    interface_hash_value = entry.get("interface_hash")
    module = entry.get("module")
    if not isinstance(content_hash, str) or not _HASH_RE.fullmatch(content_hash):
        return None
    if not isinstance(interface_hash_value, str) or not _HASH_RE.fullmatch(
        interface_hash_value
    ):
        return None
    if not isinstance(module, str) or not module or len(module) > _MAX_MODULE_LEN:
        return None
    imports = _str_list(
        entry.get("imports"), max_items=_MAX_NAMES_PER_FILE, max_len=_MAX_NAME_LEN,
    )
    exports = _str_list(
        entry.get("exports"), max_items=_MAX_NAMES_PER_FILE, max_len=_MAX_NAME_LEN,
    )
    if imports is None or exports is None:
        return None
    return {
        "content_hash": content_hash,
        "interface_hash": interface_hash_value,
        "module": module,
        "imports": imports,
        "exports": exports,
    }


def _sanitize_files(raw: object) -> Dict[str, dict]:
    if not isinstance(raw, dict) or len(raw) > _MAX_FILES:
        return {}
    out: Dict[str, dict] = {}
    for rel, entry in raw.items():
        if not isinstance(rel, str) or not rel or len(rel) > _MAX_PATH_LEN:
            continue
        clean = _sanitize_file_entry(entry)
        if clean is None:
            continue
        out[rel] = clean
    return out


def _sanitize_scc(raw: object) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    members = _str_list(
        raw.get("members"), max_items=_MAX_SCC_MEMBERS, max_len=_MAX_MODULE_LEN,
    )
    member_loc = _nonneg_int(raw.get("member_loc"))
    external_afferent = _nonneg_int(raw.get("external_afferent"))
    internal_edges = _nonneg_int(raw.get("internal_edges"))
    severity = raw.get("severity")
    if members is None or member_loc is None or external_afferent is None:
        return None
    if internal_edges is None or not isinstance(severity, str):
        return None
    if severity not in _SEVERITY_VALUES:
        return None
    return {
        "members": members,
        "member_loc": member_loc,
        "external_afferent": external_afferent,
        "internal_edges": internal_edges,
        "severity": severity,
    }


def _sanitize_centrality_entry(raw: object) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    module = raw.get("module")
    if not isinstance(module, str) or not module or len(module) > _MAX_MODULE_LEN:
        return None
    afferent = _nonneg_int(raw.get("afferent"))
    efferent = _nonneg_int(raw.get("efferent"))
    instability = _finite_float(raw.get("instability"))
    pagerank = _finite_float(raw.get("pagerank"))
    percentile = _finite_float(raw.get("afferent_percentile"))
    if None in (afferent, efferent, instability, pagerank, percentile):
        return None
    return {
        "module": module,
        "afferent": afferent,
        "efferent": efferent,
        "instability": instability,
        "pagerank": pagerank,
        "afferent_percentile": percentile,
    }


def _sanitize_derived(raw: object) -> dict:
    if not isinstance(raw, dict):
        return {}
    graph_key = raw.get("graph_key")
    if not isinstance(graph_key, str) or not _HASH_RE.fullmatch(graph_key):
        return {}
    sccs_raw = raw.get("sccs")
    centrality_raw = raw.get("centrality")
    if not isinstance(sccs_raw, list) or len(sccs_raw) > _MAX_SCCS:
        return {}
    if not isinstance(centrality_raw, dict) or len(centrality_raw) > _MAX_CENTRALITY:
        return {}
    sccs: List[dict] = []
    for item in sccs_raw:
        clean = _sanitize_scc(item)
        if clean is None:
            return {}
        sccs.append(clean)
    centrality: Dict[str, dict] = {}
    for name, entry in centrality_raw.items():
        if not isinstance(name, str) or not name or len(name) > _MAX_MODULE_LEN:
            return {}
        clean_entry = _sanitize_centrality_entry(entry)
        if clean_entry is None:
            return {}
        centrality[name] = clean_entry
    return {"graph_key": graph_key, "sccs": sccs, "centrality": centrality}


def _extract_exports(source: str) -> List[str]:
    """Top-level exported names: def/class/assignment targets (sorted)."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    names: Set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return sorted(names)


def interface_hash(exports: List[str], import_targets: List[str]) -> str:
    """Hash of the file's exported interface + import list (not its body)."""
    payload = "\x00".join(sorted(exports)) + "\x01" + "\x00".join(sorted(import_targets))
    return _sha256(payload)


class DependencyGraph:
    """The single built import graph and its derived indices."""

    def __init__(
        self,
        modules: List[ModuleDependencies],
        scan_path: Path,
    ):
        self.scan_path = scan_path
        self.modules = sorted(modules, key=lambda m: m.module_name)
        self.by_name: Dict[str, ModuleDependencies] = {
            m.module_name: m for m in self.modules
        }
        # Internal edges only (both endpoints are scanned modules).
        self.graph: Dict[str, Set[str]] = {
            m.module_name: {d for d in m.all_dependencies if d in self.by_name}
            for m in self.modules
        }
        self.reverse: Dict[str, Set[str]] = {name: set() for name in self.graph}
        for src, deps in self.graph.items():
            for dst in deps:
                self.reverse[dst].add(src)
        # Edge weight basis: number of imported symbols per (src, dst).
        self.edge_symbols: Dict[Tuple[str, str], int] = {}
        for m in self.modules:
            for dep in m.dependency_list:
                if dep.target in self.by_name:
                    key = (m.module_name, dep.target)
                    self.edge_symbols[key] = self.edge_symbols.get(key, 0) + 1
        self.module_loc: Dict[str, int] = {}
        for m in self.modules:
            try:
                self.module_loc[m.module_name] = sum(
                    1 for _ in open(m.file_path, "r", encoding="utf-8", errors="ignore")
                )
            except OSError:
                self.module_loc[m.module_name] = 0

    def nx_graph(self) -> "nx.DiGraph":
        g = nx.DiGraph()
        g.add_nodes_from(sorted(self.graph))
        for src in sorted(self.graph):
            for dst in sorted(self.graph[src]):
                g.add_edge(src, dst)
        return g

    def edge_weight(self, source: str, target: str) -> float:
        """Break cost of an edge: imported symbols x (1 + source afferent).

        Removing an edge out of a heavily-depended-on module ripples to all
        its dependents, so the same symbol count costs more there.
        """
        symbols = self.edge_symbols.get((source, target), 1)
        return float(symbols) * (1.0 + len(self.reverse.get(source, set())))


class DependencyGraphService:
    """
    Builds the import graph once and serves cycles/centrality/breaks.

    Usage:
        service = DependencyGraphService(config)
        graph = service.build(scan_path)
        sccs = service.sccs(scan_path)
        centrality = service.centrality(scan_path)
        provider = service.centrality_provider(scan_path)   # Plan 02 exposure
    """

    def __init__(self, config: Optional[DependencyConfig] = None,
                 use_disk_cache: bool = True):
        self.config = config or DependencyConfig()
        # ASGARD_NO_CACHE=1 forces the disk cache off (read-only targets).
        self.use_disk_cache = use_disk_cache and not no_cache_env()
        self.import_analyzer = ImportAnalyzer(self.config)
        self._graphs: Dict[str, DependencyGraph] = {}
        self._derived: Dict[str, dict] = {}
        # Cache observability (tested properties, RESEARCH_15):
        self.last_parse_count = 0          # files parsed on the last build
        self.last_file_cache_hits = 0      # files served from content cache
        self.derived_cache_hit = False     # SCC/centrality reused via interface hash

    # ------------------------------------------------------------------ build

    def build(self, scan_path: Optional[Path] = None) -> DependencyGraph:
        """Build (or return the memoized) dependency graph for a path."""
        path = Path(scan_path or self.config.scan_path).resolve()
        key = str(path)
        if key in self._graphs:
            return self._graphs[key]

        try:
            cache = self._load_cache(path)
            cached_files = cache.get("files", {})
            if not isinstance(cached_files, dict):
                raise TypeError("files")
        except (TypeError, AttributeError, KeyError, ValueError):
            cache = {}
            cached_files = {}

        modules = self.import_analyzer.analyze(path)
        self.last_parse_count = len(modules)
        self.last_file_cache_hits = 0

        new_files: Dict[str, dict] = {}
        for m in sorted(modules, key=lambda m: m.relative_path):
            try:
                source = Path(m.file_path).read_text(
                    encoding="utf-8", errors="ignore")
            except OSError:
                source = ""
            content_hash = _sha256(source)
            try:
                entry = cached_files.get(m.relative_path)
                if isinstance(entry, dict) and entry.get("content_hash") == content_hash:
                    self.last_file_cache_hits += 1
                    new_files[m.relative_path] = entry
                    continue
            except (TypeError, AttributeError):
                pass
            exports = _extract_exports(source)
            targets = sorted({d.target for d in m.dependency_list})
            new_files[m.relative_path] = {
                "content_hash": content_hash,
                "interface_hash": interface_hash(exports, targets),
                "module": m.module_name,
                "imports": targets,
                "exports": exports,
            }

        graph = DependencyGraph(modules, path)
        self._graphs[key] = graph

        graph_key = self._graph_key(new_files)
        try:
            derived = cache.get("derived", {})
            if not isinstance(derived, dict):
                raise TypeError("derived")
            self.derived_cache_hit = (
                bool(derived) and derived.get("graph_key") == graph_key
            )
            if self.derived_cache_hit and not _sanitize_derived(derived):
                raise ValueError("derived")
        except (TypeError, AttributeError, KeyError, ValueError):
            self.derived_cache_hit = False
            derived = {}
        if not self.derived_cache_hit:
            derived = {
                "graph_key": graph_key,
                "sccs": [self._scc_payload(s) for s in self._compute_sccs(graph)],
                "centrality": {
                    name: info.__dict__
                    for name, info in self._compute_centrality(graph).items()
                },
            }
        self._derived[key] = derived

        if self.use_disk_cache:
            self._save_cache(path, {"version": CACHE_VERSION,
                                    "files": new_files,
                                    "derived": derived})
        return graph

    def invalidate(self, scan_path: Optional[Path] = None) -> None:
        """Drop the in-memory memo for a path (or all paths)."""
        if scan_path is None:
            self._graphs.clear()
            self._derived.clear()
        else:
            key = str(Path(scan_path).resolve())
            self._graphs.pop(key, None)
            self._derived.pop(key, None)

    @staticmethod
    def _graph_key(files: Dict[str, dict]) -> str:
        """Combined interface hash: unchanged under body-only edits."""
        payload = "\x00".join(
            f"{rel}={entry.get('interface_hash', '')}"
            for rel, entry in sorted(files.items())
        )
        return _sha256(payload)

    def _cache_path(self, scan_path: Path) -> Path:
        return scan_path / CACHE_RELATIVE_PATH

    def _key_path(self, scan_path: Path) -> Path:
        cache_file = self._cache_path(scan_path)
        return cache_file.with_name(cache_file.name + ".key")

    def _hmac_key(self, scan_path: Path, *, create: bool = False) -> Optional[bytes]:
        from Asgard.common._hmac_env import hmac_key_from_env

        env = hmac_key_from_env(HMAC_ENV)
        if env is not None:
            return env
        if create:
            if getattr(self, "_ephemeral_hmac", None) is None:
                self._ephemeral_hmac = os.urandom(32)
            return self._ephemeral_hmac
        return getattr(self, "_ephemeral_hmac", None)

    def _sign(self, payload: dict, key: bytes) -> str:
        return _sign_cache(payload, key)

    def _load_cache(self, scan_path: Path) -> dict:
        if not self.use_disk_cache:
            return {}
        cache_file = self._cache_path(scan_path)
        if not cache_file.exists() or cache_file.is_symlink():
            return {}
        raw = _read_limited(cache_file, _MAX_CACHE_BYTES)
        if raw is None:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict) or data.get("version") != CACHE_VERSION:
                return {}
            expected = data.get("hmac")
            unsigned = {
                "version": data.get("version"),
                "files": data.get("files"),
                "derived": data.get("derived"),
            }
            key = self._hmac_key(scan_path, create=False)
            if key is not None:
                if not isinstance(expected, str) or not hmac.compare_digest(
                    expected, self._sign(unsigned, key)
                ):
                    return {}
            files = _sanitize_files(unsigned["files"])
            derived = _sanitize_derived(unsigned["derived"])
            return {"version": CACHE_VERSION, "files": files, "derived": derived}
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
            return {}

    def _save_cache(self, scan_path: Path, payload: dict) -> None:
        cache_file = self._cache_path(scan_path)
        tmp_path = cache_file.with_name(cache_file.name + ".tmp")
        try:
            if cache_file.is_symlink() or tmp_path.is_symlink():
                return
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            key = self._hmac_key(scan_path, create=True)
            if key is None:
                return
            body = {
                "version": payload.get("version", CACHE_VERSION),
                "files": payload.get("files", {}),
                "derived": payload.get("derived", {}),
            }
            envelope = dict(body)
            envelope["hmac"] = self._sign(body, key)
            raw = json.dumps(envelope, indent=1, sort_keys=True).encode("utf-8")
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(tmp_path, flags, 0o600)
            try:
                os.write(fd, raw)
            finally:
                os.close(fd)
            os.chmod(tmp_path, 0o600)
            if cache_file.is_symlink():
                tmp_path.unlink(missing_ok=True)
                return
            os.replace(tmp_path, cache_file)
        except OSError:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass

    # ------------------------------------------------------------------- SCCs

    def sccs(self, scan_path: Optional[Path] = None) -> List[SCC]:
        """Strongly connected components of size >= 2, reach-ranked."""
        graph = self.build(scan_path)
        return self._compute_sccs(graph)

    def _compute_sccs(self, graph: DependencyGraph) -> List[SCC]:
        g = graph.nx_graph()
        result: List[SCC] = []
        for component in nx.strongly_connected_components(g):
            if len(component) < 2:
                continue
            members = sorted(component)
            member_loc = sum(graph.module_loc.get(m, 0) for m in members)
            external_afferent = sum(
                1
                for m in members
                for src in graph.reverse.get(m, set())
                if src not in component
            )
            internal_edges = sum(
                1
                for m in members
                for dst in graph.graph.get(m, set())
                if dst in component
            )
            scc = SCC(
                members=members,
                member_loc=member_loc,
                external_afferent=external_afferent,
                internal_edges=internal_edges,
            )
            scc.severity = self._scc_severity(scc)
            result.append(scc)
        # Deterministic: biggest reach first, then members.
        result.sort(key=lambda s: (-s.reach, s.members))
        return result

    @staticmethod
    def _scc_severity(scc: SCC) -> DependencySeverity:
        """Severity = f(reach), not f(length) (RESEARCH_02/15).

        A 2-cycle between two 1000-line, heavily-imported modules is CRITICAL;
        a 5-cycle between five 30-line leaf helpers is MODERATE.
        """
        if scc.reach >= 1000 or scc.external_afferent >= 10 or scc.size >= 8:
            return DependencySeverity.CRITICAL
        if scc.reach >= 300 or scc.external_afferent >= 3:
            return DependencySeverity.HIGH
        return DependencySeverity.MODERATE

    @staticmethod
    def _scc_payload(scc: SCC) -> dict:
        return {
            "members": scc.members,
            "member_loc": scc.member_loc,
            "external_afferent": scc.external_afferent,
            "internal_edges": scc.internal_edges,
            "severity": scc.severity.value,
        }

    def enumerate_cycles(self, graph: DependencyGraph, scc: SCC) -> List[List[str]]:
        """Simple cycles for display — only inside a small SCC (bounded)."""
        if scc.size > MAX_SCC_FOR_CYCLE_ENUMERATION:
            return []
        sub = graph.nx_graph().subgraph(scc.members)
        cycles: List[List[str]] = []
        for cycle in nx.simple_cycles(sub):
            min_idx = cycle.index(min(cycle))
            cycles.append(cycle[min_idx:] + cycle[:min_idx])
            if len(cycles) >= MAX_CYCLES_PER_SCC:
                break
        cycles.sort(key=lambda c: (len(c), c))
        return cycles

    # ------------------------------------------------------------ break edges

    def break_suggestions(
        self, scc: SCC, scan_path: Optional[Path] = None
    ) -> List[EdgeBreak]:
        """Minimum-weight feedback edges that would break the SCC.

        Greedy: repeatedly remove the cheapest intra-SCC edge (weight =
        imported symbols x (1 + source afferent)) until the component is
        acyclic; report the removals (top TOP_BREAK_SUGGESTIONS).
        """
        graph = self.build(scan_path)
        sub = nx.DiGraph()
        member_set = set(scc.members)
        for m in scc.members:
            for dst in graph.graph.get(m, set()):
                if dst in member_set:
                    sub.add_edge(m, dst, weight=graph.edge_weight(m, dst))
        suggestions: List[EdgeBreak] = []
        working = sub.copy()
        while True:
            cyclic_nodes = [
                c for c in nx.strongly_connected_components(working) if len(c) > 1
            ]
            if not cyclic_nodes:
                break
            candidates = sorted(
                (
                    (data["weight"], src, dst)
                    for src, dst, data in working.edges(data=True)
                    if any(src in c and dst in c for c in cyclic_nodes)
                ),
            )
            if not candidates:
                break
            weight, src, dst = candidates[0]
            working.remove_edge(src, dst)
            suggestions.append(EdgeBreak(
                source=src,
                target=dst,
                weight=weight,
                symbol_count=graph.edge_symbols.get((src, dst), 1),
                reason=(
                    f"Minimum-weight feedback edge: {graph.edge_symbols.get((src, dst), 1)} "
                    f"imported symbol(s), source has "
                    f"{len(graph.reverse.get(src, set()))} dependent(s)"
                ),
            ))
        return suggestions[:TOP_BREAK_SUGGESTIONS]

    # ------------------------------------------------------------- centrality

    def centrality(
        self, scan_path: Optional[Path] = None
    ) -> Dict[str, CentralityInfo]:
        """Ca/Ce/instability/pagerank + afferent percentile per module."""
        graph = self.build(scan_path)
        return self._compute_centrality(graph)

    def _compute_centrality(
        self, graph: DependencyGraph
    ) -> Dict[str, CentralityInfo]:
        names = sorted(graph.graph)
        if not names:
            return {}
        afferents = {n: len(graph.reverse.get(n, set())) for n in names}
        efferents = {n: len(graph.graph.get(n, set())) for n in names}
        g = graph.nx_graph()
        try:
            pagerank = nx.pagerank(g, alpha=0.85)
        except Exception:
            pagerank = {n: 0.0 for n in names}
        total = len(names)
        result: Dict[str, CentralityInfo] = {}
        for name in names:
            ca, ce = afferents[name], efferents[name]
            below = sum(1 for other in names if afferents[other] < ca)
            result[name] = CentralityInfo(
                module=name,
                afferent=ca,
                efferent=ce,
                instability=(ce / (ca + ce)) if (ca + ce) else 0.0,
                pagerank=round(float(pagerank.get(name, 0.0)), 10),
                afferent_percentile=below / total if total > 1 else 0.0,
            )
        return result

    def centrality_provider(
        self, scan_path: Optional[Path] = None
    ) -> Callable[[str], Optional[float]]:
        """
        A `CentralityProvider` for Plan 02's Exposure Factor: maps a module
        name, absolute file path, or relative path to its afferent-coupling
        percentile in [0, 1]. Returns None for unknown paths.
        """
        graph = self.build(scan_path)
        centrality = self._compute_centrality(graph)
        by_key: Dict[str, float] = {}
        for m in graph.modules:
            info = centrality.get(m.module_name)
            if info is None:
                continue
            by_key[m.module_name] = info.afferent_percentile
            by_key[str(Path(m.file_path))] = info.afferent_percentile
            by_key[m.relative_path] = info.afferent_percentile

        def provider(path_or_module: str) -> Optional[float]:
            key = str(path_or_module)
            if key in by_key:
                return by_key[key]
            try:
                resolved = str(Path(key).resolve())
            except (OSError, ValueError):
                return None
            return by_key.get(resolved)

        return provider

    # ------------------------------------------------------- import frequency

    def import_frequencies(
        self, scan_path: Optional[Path] = None
    ) -> Dict[str, int]:
        """
        Import-site count per imported module across the codebase (Plan 03
        §3.4): the fact feed for Quality's lazy-import scanner, which needs
        RESEARCH_18's dual heuristic (import cost x call-site frequency)
        instead of import cost alone.
        """
        graph = self.build(scan_path)
        frequencies: Dict[str, int] = {}
        for m in graph.modules:
            for dep in m.dependency_list:
                frequencies[dep.target] = frequencies.get(dep.target, 0) + 1
        return dict(sorted(frequencies.items()))
