"""
Bragi License Disk Cache (Plan 03 Phase D)

Implements the cache the config always promised: `LicenseConfig.use_cache`
and `cache_expiry_days` were previously backed by an in-memory dict that died
with the process, so every run re-hit `pip show` per package and then
pypi.org serially.

Storage: `.asgard_cache/bragi_license_cache.json` under the scan path.
Entries are keyed by ``name@version``. The file is HMAC-SHA256 signed
(`ASGARD_LICENSE_HMAC_KEY` or a sibling ``.key``). Unsigned, corrupt,
schema-invalid, or version-mismatched records are treated as a miss.
CI defaults `use_cache=False` so a committed cache cannot steer policy.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

CACHE_RELATIVE_PATH = Path(".asgard_cache") / "bragi_license_cache.json"
CACHE_VERSION = "2.0.0"
HMAC_ENV = "ASGARD_LICENSE_HMAC_KEY"

_MAX_FIELD_LEN = 512
_MAX_VERSION_LEN = 64
_RECORD_OPTIONAL_STRS = (
    "license_name",
    "license_classifier",
    "homepage",
    "author",
    "source",
)

_CI_ENV_VARS = (
    "CI",
    "GITHUB_ACTIONS",
    "GITLAB_CI",
    "TF_BUILD",
    "CIRCLECI",
    "JENKINS_URL",
    "BUILDKITE",
)


def default_use_cache() -> bool:
    """Disk cache is off in CI so a committed cache cannot steer policy."""
    for name in _CI_ENV_VARS:
        raw = os.environ.get(name, "").strip().lower()
        if raw and raw not in ("0", "false", "no", "off"):
            return False
    return True


def entry_key(package_name: str, version: str) -> str:
    """Stable cache key: lowercased name plus exact version."""
    return f"{package_name.strip().lower()}@{version.strip()}"


def _sanitize_record(entry: object) -> Optional[dict]:
    if not isinstance(entry, dict):
        return None
    version = entry.get("version")
    if not isinstance(version, str):
        return None
    version = version.strip()
    if not version or len(version) > _MAX_VERSION_LEN:
        return None
    fetched_at = entry.get("fetched_at")
    if not isinstance(fetched_at, str):
        return None
    try:
        datetime.fromisoformat(fetched_at)
    except ValueError:
        return None
    clean = {"version": version, "fetched_at": fetched_at}
    for field in _RECORD_OPTIONAL_STRS:
        value = entry.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or len(value) > _MAX_FIELD_LEN:
            return None
        clean[field] = value
    return clean


def _sanitize_packages(raw: object) -> Dict[str, dict]:
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, dict] = {}
    for key, entry in raw.items():
        if not isinstance(key, str):
            continue
        clean = _sanitize_record(entry)
        if clean is None:
            continue
        expected = entry_key(key.rsplit("@", 1)[0], clean["version"])
        if key.strip().lower() != expected:
            continue
        out[expected] = clean
    return out


class LicenseDiskCache:
    """Disk-backed license lookup cache with HMAC, versioned keys, and expiry."""

    def __init__(self, scan_path: Path, expiry_days: int = 7,
                 cache_path: Optional[Path] = None,
                 now: Optional[datetime] = None):
        self.scan_path = Path(scan_path)
        self.expiry_days = expiry_days
        self.cache_path = cache_path or (self.scan_path / CACHE_RELATIVE_PATH)
        self._now = now  # injectable clock for tests
        # ASGARD_NO_CACHE=1: never read from nor write into the scanned
        # path (read-only target safety). Lookups miss; save() no-ops.
        from Asgard.Bragi.Dependencies.services.graph_service import no_cache_env
        self._disabled = no_cache_env()
        self._entries: Dict[str, dict] = {} if self._disabled else self._load()
        self._dirty = False

    def _current_time(self) -> datetime:
        return self._now or datetime.now()

    def _key_path(self) -> Path:
        return self.cache_path.with_name(self.cache_path.name + ".key")

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

    def _load(self) -> Dict[str, dict]:
        if not self.cache_path.exists() or self.cache_path.is_symlink():
            return {}
        key = self._hmac_key(create=False)
        if key is None:
            return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or data.get("version") != CACHE_VERSION:
                return {}
            expected = data.pop("hmac", None)
            unsigned = {
                "version": data.get("version"),
                "packages": data.get("packages"),
            }
            if not isinstance(expected, str) or not hmac.compare_digest(
                expected, self._sign(unsigned, key)
            ):
                return {}
            return _sanitize_packages(unsigned["packages"])
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            return {}

    def get(self, package_name: str, version: Optional[str] = None) -> Optional[dict]:
        """Return the cached record for name@version, or None if absent/expired."""
        if not version or not isinstance(version, str) or not version.strip():
            return None
        entry = self._entries.get(entry_key(package_name, version))
        if entry is None:
            return None
        try:
            fetched_at = datetime.fromisoformat(entry.get("fetched_at", ""))
        except (TypeError, ValueError):
            return None
        if self._current_time() - fetched_at > timedelta(days=self.expiry_days):
            return None
        return entry

    def put(self, package_name: str, record: dict) -> None:
        """Store a record keyed by name@version (fetched_at stamped automatically)."""
        record = dict(record)
        version = record.get("version")
        if not isinstance(version, str) or not version.strip():
            return
        record["fetched_at"] = self._current_time().isoformat()
        clean = _sanitize_record(record)
        if clean is None:
            return
        self._entries[entry_key(package_name, version)] = clean
        self._dirty = True

    def save(self) -> None:
        """Persist the signed cache (best-effort; no-op when nothing changed)."""
        if self._disabled or not self._dirty:
            return
        try:
            if self.cache_path.is_symlink():
                return
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            key = self._hmac_key(create=True)
            if key is None:
                return
            body = {"version": CACHE_VERSION, "packages": self._entries}
            payload = dict(body)
            payload["hmac"] = self._sign(body, key)
            tmp_path = self.cache_path.with_name(self.cache_path.name + ".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=1, sort_keys=True)
            os.replace(tmp_path, self.cache_path)
            self._dirty = False
        except OSError:
            pass
