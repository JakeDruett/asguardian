"""
HMAC-signed incremental file-hash cache (CH-0048).

Unsigned, schema-invalid, or HMAC-mismatched files are a miss and never
skip a rescan. `is_changed` always re-hashes file contents (mtime/size
is not a skip). `cache_path` is jailed under the project root. Entries
older than `max_cache_age_days` are expired. `enabled` stays False.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

HMAC_ENV = "ASGARD_INCREMENTAL_HMAC_KEY"
CACHE_VERSION = "2"
DEFAULT_CACHE_PATH = ".asgard-cache.json"

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_CACHE_BYTES = 8 * 1024 * 1024
_MAX_ENTRIES = 10_000
_MAX_PATH_LEN = 4096
_MAX_RESULT_BYTES = 64 * 1024
_MAX_ANALYZED_LEN = 64


@dataclass
class FileHashEntry:
    """Cache entry for a single file."""
    file_path: str
    hash: str
    last_modified: float
    size: int
    last_analyzed: str
    result: Optional[Dict[str, Any]] = None


@dataclass
class IncrementalConfig:
    """Configuration for incremental scanning."""
    enabled: bool = False
    cache_path: str = DEFAULT_CACHE_PATH
    store_results: bool = True
    max_cache_age_days: int = 30


def confine_cache_path(project_path: Path, cache_path: str) -> Path:
    """Return the unfollowed dest if `cache_path` stays under `project_path`."""
    if not isinstance(cache_path, str) or not cache_path.strip():
        raise ValueError("cache_path must stay under the project path")
    raw = Path(cache_path)
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError("cache_path must stay under the project path")
    root = Path(project_path)
    dest = root / raw
    try:
        resolved = dest.resolve()
        root_resolved = root.resolve()
    except OSError as exc:
        raise ValueError("cache_path must stay under the project path") from exc
    if resolved == root_resolved or not resolved.is_relative_to(root_resolved):
        raise ValueError("cache_path must stay under the project path")
    return dest


def _sanitize_rel_path(rel: str) -> Optional[str]:
    if not isinstance(rel, str) or not rel or len(rel) > _MAX_PATH_LEN:
        return None
    raw = Path(rel)
    if raw.is_absolute() or ".." in raw.parts:
        return None
    return rel


def _sanitize_result(value: Any) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if not isinstance(value, dict):
        return None
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        return None
    if len(encoded.encode("utf-8")) > _MAX_RESULT_BYTES:
        return None
    return value


def _sanitize_entry(key: str, raw: Any) -> Optional[FileHashEntry]:
    rel = _sanitize_rel_path(key)
    if rel is None or not isinstance(raw, dict):
        return None
    file_path = _sanitize_rel_path(raw.get("file_path", ""))
    if file_path is None or Path(file_path) != Path(rel):
        return None
    digest = raw.get("hash")
    if not isinstance(digest, str) or not _HASH_RE.fullmatch(digest):
        return None
    last_modified = raw.get("last_modified")
    if not isinstance(last_modified, (int, float)) or isinstance(last_modified, bool):
        return None
    size = raw.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        return None
    last_analyzed = raw.get("last_analyzed")
    if not isinstance(last_analyzed, str) or not last_analyzed or len(last_analyzed) > _MAX_ANALYZED_LEN:
        return None
    try:
        datetime.fromisoformat(last_analyzed)
    except ValueError:
        return None
    return FileHashEntry(
        file_path=file_path,
        hash=digest,
        last_modified=float(last_modified),
        size=size,
        last_analyzed=last_analyzed,
        result=_sanitize_result(raw.get("result")),
    )


def _read_nofollow(path: Path, max_bytes: int) -> Optional[bytes]:
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


class FileHashCache:
    """
    Manages file hash cache for incremental scanning.

    Stores SHA-256 hashes of files along with their analysis results,
    allowing scanners to skip unchanged files. On-disk records are
    HMAC-SHA256 signed (`ASGARD_INCREMENTAL_HMAC_KEY` or a sibling
    `.key` at `0o600`).

    Usage:
        cache = FileHashCache(project_path)
        cache.load()

        for file in files:
            if cache.is_changed(file):
                result = analyze(file)
                cache.update(file, result)
            else:
                result = cache.get_cached_result(file)

        cache.save()
    """

    def __init__(
        self,
        project_path: Path,
        config: Optional[IncrementalConfig] = None,
    ):
        """
        Initialize the file hash cache.

        Args:
            project_path: Root path of the project
            config: Incremental scanning configuration
        """
        self.project_path = Path(project_path)
        self.config = config or IncrementalConfig()
        self.cache_file = confine_cache_path(self.project_path, self.config.cache_path)
        self._entries: Dict[str, FileHashEntry] = {}
        self._dirty = False

    def _key_path(self) -> Path:
        return self.cache_file.with_name(self.cache_file.name + ".key")

    def _hmac_key(self, *, create: bool = False) -> Optional[bytes]:
        env = os.environ.get(HMAC_ENV, "").strip()
        if env:
            return env.encode("utf-8")
        key_path = self._key_path()
        if key_path.is_symlink():
            return None
        if key_path.exists():
            data = _read_nofollow(key_path, max_bytes=64)
            if not data:
                return None
            return data
        if not create:
            return None
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            return None
        key = os.urandom(32)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(key_path, flags, 0o600)
            try:
                os.write(fd, key)
            finally:
                os.close(fd)
            os.chmod(key_path, 0o600)
        except OSError:
            return None
        return key

    def _sign(self, payload: dict, key: bytes) -> str:
        body = dict(payload)
        body.pop("hmac", None)
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
        return hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def _dest_is_confined(self) -> bool:
        if self.cache_file.is_symlink():
            return False
        try:
            resolved = self.cache_file.resolve()
            root = self.project_path.resolve()
        except OSError:
            return False
        return resolved != root and resolved.is_relative_to(root)

    def load(self) -> bool:
        """
        Load cache from disk.

        Returns:
            True if a signed, schema-valid cache was loaded
        """
        self._entries = {}
        if not self.cache_file.exists() or not self._dest_is_confined():
            return False
        mac_key = self._hmac_key(create=False)
        if mac_key is None:
            return False
        raw = _read_nofollow(self.cache_file, max_bytes=_MAX_CACHE_BYTES)
        if raw is None:
            return False
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False
        if not isinstance(data, dict) or data.get("version") != CACHE_VERSION:
            return False
        expected = data.get("hmac")
        if not isinstance(expected, str) or not hmac.compare_digest(
            expected, self._sign(data, mac_key)
        ):
            return False
        entries = data.get("entries")
        if not isinstance(entries, dict) or len(entries) > _MAX_ENTRIES:
            return False
        loaded: Dict[str, FileHashEntry] = {}
        for path, entry_data in entries.items():
            entry = _sanitize_entry(path, entry_data)
            if entry is None or self._is_expired(entry):
                continue
            loaded[entry.file_path] = entry
        self._entries = loaded
        self._dirty = False
        return True

    def save(self) -> None:
        """Save a signed cache. No-op when unsigned write would be required."""
        if not self._dirty and self.cache_file.exists():
            return
        if self.cache_file.is_symlink() or not self._dest_is_confined():
            return
        mac_key = self._hmac_key(create=True)
        if mac_key is None:
            return
        data = {
            "version": CACHE_VERSION,
            "created_at": datetime.now().isoformat(),
            "project_path": str(self.project_path),
            "entries": {
                path: {
                    "file_path": entry.file_path,
                    "hash": entry.hash,
                    "last_modified": entry.last_modified,
                    "size": entry.size,
                    "last_analyzed": entry.last_analyzed,
                    "result": entry.result,
                }
                for path, entry in self._entries.items()
            },
        }
        data["hmac"] = self._sign(data, mac_key)
        payload = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
        tmp_path = self.cache_file.with_name(self.cache_file.name + ".tmp")
        if tmp_path.is_symlink():
            return
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(tmp_path, flags, 0o600)
            try:
                os.write(fd, payload)
            finally:
                os.close(fd)
            os.chmod(tmp_path, 0o600)
            if self.cache_file.is_symlink() or not self._dest_is_confined():
                tmp_path.unlink(missing_ok=True)
                return
            os.replace(tmp_path, self.cache_file)
        except OSError:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            return
        self._dirty = False

    def is_changed(self, file_path: Path) -> bool:
        """
        Check if a file has changed since last analysis.

        Always re-hashes contents. mtime/size is never a skip.

        Args:
            file_path: Path to the file

        Returns:
            True if file has changed, is expired, or is not in cache
        """
        rel_path = self._relative_path(file_path)
        if rel_path is None or rel_path not in self._entries:
            return True
        if not file_path.exists() or file_path.is_symlink():
            return True
        entry = self._entries[rel_path]
        if self._is_expired(entry):
            return True
        current_hash = self._compute_hash(file_path)
        if current_hash is None:
            return True
        return current_hash != entry.hash

    def get_cached_result(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis result for a file.

        Args:
            file_path: Path to the file

        Returns:
            Cached result dictionary or None if not cached, changed, or expired
        """
        if self.is_changed(file_path):
            return None
        rel_path = self._relative_path(file_path)
        if rel_path is None:
            return None
        entry = self._entries.get(rel_path)
        if entry and isinstance(entry.result, dict):
            return entry.result
        return None

    def update(
        self,
        file_path: Path,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update cache entry for a file.

        Args:
            file_path: Path to the file
            result: Analysis result to cache (optional)
        """
        if not file_path.exists() or file_path.is_symlink():
            return
        rel_path = self._relative_path(file_path)
        if rel_path is None:
            return
        current_hash = self._compute_hash(file_path)
        if current_hash is None:
            return
        stat = file_path.stat()
        entry = FileHashEntry(
            file_path=rel_path,
            hash=current_hash,
            last_modified=stat.st_mtime,
            size=stat.st_size,
            last_analyzed=datetime.now().isoformat(),
            result=_sanitize_result(result) if self.config.store_results else None,
        )
        self._entries[rel_path] = entry
        self._dirty = True

    def invalidate(self, file_path: Path) -> bool:
        """
        Remove a file from the cache.

        Args:
            file_path: Path to invalidate

        Returns:
            True if entry was removed
        """
        rel_path = self._relative_path(file_path)
        if rel_path is not None and rel_path in self._entries:
            del self._entries[rel_path]
            self._dirty = True
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._entries = {}
        self._dirty = True

    def clean_stale(self) -> int:
        """
        Remove entries for files that no longer exist.

        Returns:
            Number of entries removed
        """
        stale_paths = []
        for rel_path in self._entries:
            if _sanitize_rel_path(rel_path) is None:
                stale_paths.append(rel_path)
                continue
            full_path = self.project_path / rel_path
            if not full_path.exists() or full_path.is_symlink():
                stale_paths.append(rel_path)

        for path in stale_paths:
            del self._entries[path]

        if stale_paths:
            self._dirty = True

        return len(stale_paths)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = len(self._entries)
        with_results = sum(1 for e in self._entries.values() if e.result)

        return {
            "total_entries": total,
            "entries_with_results": with_results,
            "cache_file": str(self.cache_file),
            "cache_exists": self.cache_file.exists(),
        }

    def filter_changed(self, files) -> list:
        """
        Filter a list of files to only those that have changed.

        Args:
            files: List of file paths

        Returns:
            List of files that have changed since last analysis
        """
        return [f for f in files if self.is_changed(f)]

    def _is_expired(self, entry: FileHashEntry) -> bool:
        try:
            analyzed = datetime.fromisoformat(entry.last_analyzed)
            age = datetime.now() - analyzed
        except (TypeError, ValueError):
            return True
        max_days = self.config.max_cache_age_days
        if max_days < 0:
            max_days = 0
        return age > timedelta(days=max_days)

    def _relative_path(self, path: Path) -> Optional[str]:
        """Convert to a confined relative path, or None if outside the project."""
        try:
            resolved = Path(path).resolve()
            root = self.project_path.resolve()
            rel = resolved.relative_to(root)
        except (OSError, ValueError):
            return None
        return _sanitize_rel_path(str(rel))

    def _compute_hash(self, file_path: Path) -> Optional[str]:
        """SHA-256 of file contents. Refuses symlinks (`O_NOFOLLOW`)."""
        path = Path(file_path)
        if path.is_symlink():
            return None
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(path, flags)
        except OSError:
            return None
        try:
            hasher = hashlib.sha256()
            while True:
                chunk = os.read(fd, 8192)
                if not chunk:
                    break
                hasher.update(chunk)
            return hasher.hexdigest()
        finally:
            os.close(fd)
