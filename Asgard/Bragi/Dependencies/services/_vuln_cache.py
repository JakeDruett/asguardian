"""
On-disk TTL cache for live vulnerability-database lookups (OSV/NVD).

Purely a performance/politeness layer for the opt-in network path (Plan
03 Phase E / Plan 07.10): repeat runs against the same dependency set do
not need to re-hit api.osv.dev or NVD within the TTL window. This module
is never imported or touched by the default (no-network) path -- it is
only exercised from inside `VulnerabilityChecker._check_network` /
`_check_nvd`, which themselves require `enable_network=True`.

Cache location: `<cwd>/.asgard_cache/vulnerability/<sha256>.json` by
default, overridable via `cache_dir`. The cache directory is created
mode `0o700`. Entries are HMAC-SHA256 signed (`ASGARD_VULN_HMAC_KEY` or
a sibling `.key` at `0o600`). Unsigned, HMAC-mismatched, schema-invalid,
or TTL-expired records are treated as a miss and never as a clean scan.

Set `ASGARD_NO_CACHE=1` in CI gates to bypass the cache entirely (always
re-fetch, never write) so a committed or poisoned workspace cache cannot
hide or inject CVEs.

The cache stores a schema-validated OSV querybatch object or a list of
NVD-normalised vuln dicts, plus a timestamp. It never stores secrets or
credentials. The cache key is a hash of the query content, not a raw
file path, so it cannot be used for path traversal.
"""

import hashlib
import hmac
import json
import os
import re
import stat
import time
from pathlib import Path
from typing import Any, Optional

_CACHE_KEY_RE = re.compile(r"^[a-z0-9_]+$")

DEFAULT_TTL_SECONDS = 24 * 60 * 60  # 24h
NO_CACHE_ENV_VAR = "ASGARD_NO_CACHE"
HMAC_ENV = "ASGARD_VULN_HMAC_KEY"
CACHE_VERSION = "2"
_KEY_FILENAME = ".key"

_MAX_CACHE_BYTES = 2 * 1024 * 1024
_MAX_RESULTS = 1000
_MAX_VULNS_PER = 512
_MAX_NVD_ITEMS = 64
_MAX_ID_LEN = 128
_MAX_SUMMARY_LEN = 8192
_MAX_SEVERITY_ITEMS = 16
_MAX_SEV_TYPE_LEN = 64
_MAX_SEV_SCORE_LEN = 128


def _cache_disabled() -> bool:
    return os.environ.get(NO_CACHE_ENV_VAR, "").strip().lower() in (
        "1", "true", "yes", "on",
    )


def cache_key(namespace: str, payload: str) -> str:
    """Deterministic cache key: namespace-prefixed sha256 of the payload."""
    if not _CACHE_KEY_RE.fullmatch(namespace or ""):
        raise ValueError("cache namespace must match ^[a-z0-9_]+$")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{namespace}_{digest}"


def _safe_cache_filename(key: str) -> Optional[str]:
    """Hash an allowlisted key; reject path-like keys."""
    if not _CACHE_KEY_RE.fullmatch(key or ""):
        return None
    return hashlib.sha256(key.encode("utf-8")).hexdigest() + ".json"


def _key_namespace(key: str) -> Optional[str]:
    if not _CACHE_KEY_RE.fullmatch(key or ""):
        return None
    if key.startswith("osv_"):
        return "osv"
    if key.startswith("nvd_"):
        return "nvd"
    return None


def _sanitize_severity(raw: Any) -> Optional[list]:
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > _MAX_SEVERITY_ITEMS:
        return None
    clean: list = []
    for item in raw:
        if not isinstance(item, dict):
            return None
        typ = item.get("type", "")
        if not isinstance(typ, str) or len(typ) > _MAX_SEV_TYPE_LEN:
            return None
        score = item.get("score")
        if score is not None and not isinstance(score, (str, int, float)):
            return None
        if isinstance(score, str) and len(score) > _MAX_SEV_SCORE_LEN:
            return None
        if isinstance(score, bool):
            return None
        entry = {"type": typ}
        if score is not None:
            entry["score"] = score
        clean.append(entry)
    return clean


def _sanitize_vuln_dict(vuln: Any) -> Optional[dict]:
    if not isinstance(vuln, dict):
        return None
    vid = vuln.get("id", "")
    if not isinstance(vid, str) or len(vid) > _MAX_ID_LEN:
        return None
    summary = vuln.get("summary", "")
    if summary is None:
        summary = ""
    if not isinstance(summary, str) or len(summary) > _MAX_SUMMARY_LEN:
        return None
    severity = _sanitize_severity(vuln.get("severity"))
    if severity is None:
        return None
    return {"id": vid, "summary": summary, "severity": severity}


def sanitize_osv_body(value: Any) -> Optional[dict]:
    """Return a cleaned OSV querybatch body, or None if it is not trusted."""
    if not isinstance(value, dict):
        return None
    results = value.get("results")
    if not isinstance(results, list) or len(results) > _MAX_RESULTS:
        return None
    clean_results: list = []
    for entry in results:
        if entry is None:
            clean_results.append({})
            continue
        if not isinstance(entry, dict):
            return None
        if "vulns" not in entry:
            clean_results.append({})
            continue
        vulns = entry.get("vulns")
        if vulns is None:
            clean_results.append({"vulns": []})
            continue
        if not isinstance(vulns, list) or len(vulns) > _MAX_VULNS_PER:
            return None
        clean_vulns = []
        for vuln in vulns:
            cleaned = _sanitize_vuln_dict(vuln)
            if cleaned is None:
                return None
            clean_vulns.append(cleaned)
        clean_results.append({"vulns": clean_vulns})
    return {"results": clean_results}


def sanitize_nvd_body(value: Any) -> Optional[list]:
    """Return a cleaned NVD-normalised vuln list, or None if untrusted."""
    if not isinstance(value, list) or len(value) > _MAX_NVD_ITEMS:
        return None
    clean: list = []
    for item in value:
        cleaned = _sanitize_vuln_dict(item)
        if cleaned is None:
            return None
        clean.append(cleaned)
    return clean


def sanitize_cached_body(key: str, value: Any) -> Any:
    """Schema-validate a cached body for the key's namespace."""
    namespace = _key_namespace(key)
    if namespace == "osv":
        return sanitize_osv_body(value)
    if namespace == "nvd":
        return sanitize_nvd_body(value)
    return None


class VulnCache:
    """On-disk TTL cache. One HMAC-signed JSON file per cache key."""

    def __init__(self, cache_dir: Optional[Path] = None,
                 ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(".asgard_cache") / "vulnerability"
        self.ttl_seconds = ttl_seconds

    def _confined_path(self, key: str) -> Optional[Path]:
        name = _safe_cache_filename(key)
        if name is None:
            return None
        try:
            root = self.cache_dir.resolve()
            dest = (root / name).resolve()
        except OSError:
            return None
        if not dest.is_relative_to(root):
            return None
        return dest

    def _key_path(self) -> Path:
        return self.cache_dir / _KEY_FILENAME

    def _dir_is_private(self) -> bool:
        try:
            if self.cache_dir.is_symlink():
                return False
            mode = stat.S_IMODE(self.cache_dir.stat().st_mode)
            return (mode & 0o077) == 0
        except OSError:
            return False

    def _ensure_cache_dir(self) -> bool:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            if self.cache_dir.is_symlink():
                return False
            os.chmod(self.cache_dir, 0o700)
        except OSError:
            return False
        return self._dir_is_private()

    def _hmac_key(self, *, create: bool = False) -> Optional[bytes]:
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
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str,
        )
        return hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Return the cached value for `key`, or None on miss/untrusted/disabled."""
        if _cache_disabled():
            return None
        if not self._dir_is_private():
            return None
        path = self._confined_path(key)
        if path is None or path.is_symlink():
            return None
        raw = _read_limited(path, max_bytes=_MAX_CACHE_BYTES)
        if raw is None:
            return None
        try:
            envelope = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(envelope, dict):
            return None
        mac_key = self._hmac_key(create=False)
        if mac_key is None:
            return None
        expected = envelope.get("hmac")
        unsigned = {
            "version": envelope.get("version"),
            "key": envelope.get("key"),
            "cached_at": envelope.get("cached_at"),
            "value": envelope.get("value"),
        }
        if not isinstance(expected, str) or not hmac.compare_digest(
            expected, self._sign(unsigned, mac_key)
        ):
            return None
        if unsigned["version"] != CACHE_VERSION or unsigned["key"] != key:
            return None
        cached_at = unsigned["cached_at"]
        if not isinstance(cached_at, (int, float)) or isinstance(cached_at, bool):
            return None
        if time.time() - cached_at > self.ttl_seconds:
            return None
        return sanitize_cached_body(key, unsigned["value"])

    def set(self, key: str, value: Any) -> None:
        """Write a signed, schema-validated `value`. Best-effort only."""
        if _cache_disabled():
            return
        clean = sanitize_cached_body(key, value)
        if clean is None:
            return
        if not self._ensure_cache_dir():
            return
        path = self._confined_path(key)
        if path is None:
            return
        mac_key = self._hmac_key(create=True)
        if mac_key is None:
            return
        unsigned = {
            "version": CACHE_VERSION,
            "key": key,
            "cached_at": time.time(),
            "value": clean,
        }
        envelope = dict(unsigned)
        envelope["hmac"] = self._sign(unsigned, mac_key)
        tmp_path = path.with_suffix(".json.tmp")
        payload = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(tmp_path, flags, 0o600)
            try:
                os.write(fd, payload)
            finally:
                os.close(fd)
            os.chmod(tmp_path, 0o600)
            os.replace(tmp_path, path)
        except OSError:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass


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
