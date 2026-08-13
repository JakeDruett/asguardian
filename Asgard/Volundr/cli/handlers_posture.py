"""
CLI handler for `volundr posture` — portfolio Graph-Weighted Posture Index.

`volundr posture <path>` validates every infrastructure artifact under a
directory (or a single file) through the Validation engine, builds a
declared-reference graph (kustomization `resources:`/`bases:` entries,
plus optional user-supplied edges), and rolls the surviving findings up
into the GWPI: PageRank centrality weights over the reference graph and
an L3-norm system risk so the weakest link dominates
(`Validation/services/posture_index.py`, DEEPTHINK_01).

Honesty notes:
- Files that fail to validate are listed as UNVALIDATED — they still
  carry the epistemic-floor risk (never confidently clean).
- The result's invalidating assumptions are always printed.
- Zero network calls; everything is computed from local artifacts.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

ARTIFACT_SUFFIXES = (".yaml", ".yml", ".tf")


def _collect_artifact_files(path: Path) -> List[Path]:
    """Deterministically enumerate artifact files under ``path``."""
    if path.is_file():
        return [path]
    return sorted(
        p for p in path.rglob("*")
        if p.is_file() and p.suffix.lower() in ARTIFACT_SUFFIXES
    )


def _resource_name(file_path: Path, root: Path) -> str:
    """Stable resource id: POSIX-style path relative to the scan root."""
    try:
        return file_path.relative_to(root).as_posix()
    except ValueError:
        return file_path.as_posix()


def _kustomize_edges(
    files: List[Path], root: Path
) -> List[Tuple[str, str]]:
    """Edges from kustomization ``resources:``/``bases:`` file references."""
    names = {_resource_name(f, root) for f in files}
    edges: List[Tuple[str, str]] = []
    for f in files:
        if f.name not in ("kustomization.yaml", "kustomization.yml"):
            continue
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8", errors="ignore"))
        except yaml.YAMLError:
            continue
        if not isinstance(doc, dict):
            continue
        src = _resource_name(f, root)
        for key in ("resources", "bases"):
            for ref in doc.get(key) or []:
                if not isinstance(ref, str):
                    continue
                target = _resource_name((f.parent / ref).resolve(), root.resolve())
                if target in names:
                    edges.append((src, target))
    return sorted(set(edges))


def _load_user_edges(edges_path: str) -> List[Tuple[str, str]]:
    """User-declared edges: JSON list of [from, to] resource-name pairs."""
    data = json.loads(Path(edges_path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("edges file must be a JSON list of [from, to] pairs")
    edges: List[Tuple[str, str]] = []
    for pair in data:
        if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                or not all(isinstance(x, str) for x in pair)):
            raise ValueError(f"invalid edge entry: {pair!r}")
        edges.append((pair[0], pair[1]))
    return edges


def run_posture(args: argparse.Namespace) -> int:
    """`volundr posture <path>`."""
    from Asgard.Volundr.Validation.services.posture_index import (
        compute_posture_index,
    )
    from Asgard.Volundr.cli.handlers_score_gitops import _validate_artifact

    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path does not exist: {path}")
        return 2

    root = path if path.is_dir() else path.parent
    files = _collect_artifact_files(path)
    if not files:
        print(f"Error: No infrastructure artifacts found under: {path}")
        return 2

    findings_by_resource: Dict[str, list] = {}
    unvalidated: List[str] = []
    for f in files:
        name = _resource_name(f, root)
        try:
            report = _validate_artifact(f)
            findings_by_resource[name] = list(report.results)
        except Exception as e:  # unresolved over-approximates, never clean
            findings_by_resource[name] = []
            unvalidated.append(f"{name}: {e}")

    edges = _kustomize_edges(files, root)
    edges_path = getattr(args, "edges", None)
    if edges_path:
        try:
            edges = sorted(set(edges) | set(_load_user_edges(edges_path)))
        except (OSError, ValueError, json.JSONDecodeError) as e:
            print(f"Error: Could not load edges file: {e}")
            return 2

    posture = compute_posture_index(
        findings_by_resource,
        edges=edges or None,
        external_tools_ran=bool(getattr(args, "external_tools_ran", False)),
    )

    output_format = getattr(args, "format", "text")
    if output_format == "json":
        payload = (posture.model_dump(mode="json")
                   if hasattr(posture, "model_dump") else posture.dict())
        payload["resources"] = sorted(findings_by_resource)
        payload["edges"] = [list(e) for e in edges]
        payload["unvalidated"] = unvalidated
        print(json.dumps(payload, indent=2, default=str))
    else:
        lines = ["", "VOLUNDR POSTURE INDEX (GWPI)", "=" * 60,
                 f"  Path:          {path}",
                 f"  Posture:       {posture.posture:.2f}/100",
                 f"  System risk:   {posture.system_risk:.4f} (L3-norm)",
                 f"  Resources:     {len(findings_by_resource)}  "
                 f"Edges: {len(edges)}",
                 f"  Epistemic floor: {posture.epistemic_floor}"]
        if not edges:
            lines.append(
                "  (no declared cross-references known — uniform weights)"
            )
        lines.append("")
        lines.append("  Per-resource risk (weight):")
        for name in sorted(findings_by_resource):
            risk = posture.resource_risks.get(name, posture.epistemic_floor)
            weight = posture.resource_weights.get(name, 0.0)
            lines.append(f"    {name:40} {risk:.4f}  (w={weight:.4f})")
        if unvalidated:
            lines.append("")
            lines.append("  UNVALIDATED (risk held at the epistemic floor,"
                         " never confidently clean):")
            for entry in unvalidated:
                lines.append(f"    ! {entry}")
        lines.append("")
        lines.append("  Invalidating assumptions (read before trusting):")
        for assumption in posture.assumptions:
            lines.append(f"    - {assumption}")
        lines.append("")
        print("\n".join(lines))

    threshold = float(getattr(args, "threshold", 0.0))
    return 1 if posture.posture < threshold else 0
