"""On-disk cache for triage verdicts, keyed by finding fingerprint + code hash.

Opt-in path only -- never touched by the default (non-assist) scan path. Honors
``ASGARD_NO_CACHE`` (any truthy value disables reads and writes, forcing every
call to re-invoke the adapter).

Entries are HMAC-SHA256 signed (``ASGARD_TRIAGE_HMAC_KEY`` or a sibling
``.key`` at ``0o600``). The cache directory is created mode ``0o700``.
Unsigned, HMAC-mismatched, schema-invalid, or path-escaping records are a
miss and never a trusted ``likely_false_positive``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Optional

from Asgard.Heimdall.Security.triage.models.triage_models import TriageLabel, TriageVerdict

_CACHE_DIRNAME = ".asgard_cache"
_CACHE_SUBDIR = "triage"
_KEY_FILENAME = ".key"
HMAC_ENV = "ASGARD_TRIAGE_HMAC_KEY"
CACHE_VERSION = "1"

_HEX_KEY_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_LABELS = frozenset(item.value for item in TriageLabel)
_MAX_CACHE_BYTES = 64 * 1024
_MAX_RATIONALE_LEN = 4096
_MAX_REASON_LEN = 1024
_MAX_KEY_FILE_BYTES = 64


def _no_cache() -> bool:
    return bool(os.environ.get("ASGARD_NO_CACHE"))


def fingerprint(finding: Any, code_context: str) -> str:
    """Stable content-hash key for a (finding, code_context) pair."""
    parts = [
        str(getattr(finding, "file_path", "")),
        str(getattr(finding, "line_number", "")),
        str(getattr(finding, "vulnerability_type", "")),
        str(getattr(finding, "title", "")),
        str(getattr(finding, "description", "")),
        code_context or "",
    ]
    digest = hashlib.sha256("\x00".join(parts).encode("utf-8", errors="replace")).hexdigest()
    return digest


def _sanitize_verdict(raw: Any) -> Optional[dict]:
    """Allowlisted verdict fields only; extra keys and bad types are a miss."""
    if not isinstance(raw, dict):
        return None
    label = raw.get("label")
    if isinstance(label, TriageLabel):
        label = label.value
    if not isinstance(label, str) or label not in _ALLOWED_LABELS:
        return None
    rationale = raw.get("rationale", "")
    if not isinstance(rationale, str) or len(rationale) > _MAX_RATIONALE_LEN:
        return None
    confidence = raw.get("confidence", 0.0)
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return None
    conf = float(confidence)
    if conf < 0.0 or conf > 1.0:
        return None
    reason = raw.get("reason")
    if reason is not None:
        if not isinstance(reason, str) or len(reason) > _MAX_REASON_LEN:
            return None
    clean: dict = {
        "label": label,
        "rationale": rationale,
        "confidence": conf,
        "from_cache": False,
    }
    if reason is not None:
        clean["reason"] = reason
    return clean


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


class TriageCache:
    """HMAC-signed on-disk JSON cache, one file per hex fingerprint.

    Instantiated with a root directory (defaults to ``./.asgard_cache/triage``);
    reads/writes are skipped entirely when ``ASGARD_NO_CACHE`` is set, or when
    disk I/O or integrity checks fail (cache is best-effort, never fatal).
    Keys must be 64 lowercase hex chars; dest paths are ``resolve`` +
    ``is_relative_to`` confined.
    """

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root) if root else Path.cwd() / _CACHE_DIRNAME / _CACHE_SUBDIR

    def _confined_path(self, key: str) -> Optional[Path]:
        if not _HEX_KEY_RE.fullmatch(key or ""):
            return None
        try:
            root = self.root.resolve()
            dest = (root / f"{key}.json").resolve()
        except OSError:
            return None
        if not dest.is_relative_to(root):
            return None
        return dest

    def _path_for(self, key: str) -> Optional[Path]:
        return self._confined_path(key)

    def _key_path(self) -> Path:
        return self.root / _KEY_FILENAME

    def _dir_is_private(self) -> bool:
        try:
            if self.root.is_symlink():
                return False
            mode = stat.S_IMODE(self.root.stat().st_mode)
            return (mode & 0o077) == 0
        except OSError:
            return False

    def _ensure_cache_dir(self) -> bool:
        try:
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            if self.root.is_symlink():
                return False
            os.chmod(self.root, 0o700)
        except OSError:
            return False
        return self._dir_is_private()

    def _hmac_key(self, *, create: bool = False) -> Optional[bytes]:
        from Asgard.common._hmac_env import hmac_key_from_env, persisted_hmac_key

        env = hmac_key_from_env(HMAC_ENV)
        if env is not None:
            return env
        return persisted_hmac_key(self._key_path(), create=create)

    def _sign(self, payload: dict, key: bytes) -> str:
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str,
        )
        return hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def get(self, key: str) -> Optional[TriageVerdict]:
        if _no_cache():
            return None
        if not self._dir_is_private():
            return None
        try:
            path = self._confined_path(key)
            if path is None or path.is_symlink():
                return None
            raw = _read_limited(path, max_bytes=_MAX_CACHE_BYTES)
            if raw is None:
                return None
            envelope = json.loads(raw.decode("utf-8"))
            if not isinstance(envelope, dict):
                return None
            mac_key = self._hmac_key(create=False)
            if mac_key is None:
                return None
            expected = envelope.get("hmac")
            unsigned = {
                "version": envelope.get("version"),
                "key": envelope.get("key"),
                "verdict": envelope.get("verdict"),
            }
            if not isinstance(expected, str) or not hmac.compare_digest(
                expected, self._sign(unsigned, mac_key)
            ):
                return None
            if unsigned["version"] != CACHE_VERSION or unsigned["key"] != key:
                return None
            clean = _sanitize_verdict(unsigned["verdict"])
            if clean is None:
                return None
            clean["from_cache"] = True
            return TriageVerdict(**clean)
        except Exception:
            # Cache is best-effort; any corruption/IO/integrity error is a miss.
            return None

    def set(self, key: str, verdict: TriageVerdict) -> None:
        if _no_cache():
            return
        try:
            clean = _sanitize_verdict({
                "label": getattr(verdict, "label", None),
                "rationale": getattr(verdict, "rationale", ""),
                "confidence": getattr(verdict, "confidence", 0.0),
                "reason": getattr(verdict, "reason", None),
            })
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
                "verdict": clean,
            }
            envelope = dict(unsigned)
            envelope["hmac"] = self._sign(unsigned, mac_key)
            payload = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
            tmp_path = path.with_suffix(".json.tmp")
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
        except Exception:
            # Best-effort: a failed cache write must never fail the triage call.
            pass
