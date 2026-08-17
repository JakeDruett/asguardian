"""
Incremental Processing Infrastructure - File Hash Cache

FileHashCache class for tracking content changes via hashing.
"""

import hashlib
import hmac
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from Asgard.common._incremental_models import HashEntry, IncrementalConfig

_HMAC_ENV = "ASGARD_COMMON_HASH_HMAC_KEY"


class FileHashCache:
    """
    Manages hash cache for incremental processing.

    Can be used for files, URLs, or any hashable content.

    Usage:
        cache = FileHashCache(project_path)
        cache.load()

        for item in items:
            if cache.is_changed(item_id, content):
                result = process(item)
                cache.update(item_id, content, result)
            else:
                result = cache.get_cached_result(item_id)

        cache.save()
    """

    def __init__(
        self,
        project_path: Path,
        config: Optional[IncrementalConfig] = None,
    ):
        """
        Initialize the hash cache.

        Args:
            project_path: Root path for cache file
            config: Incremental configuration
        """
        self.project_path = Path(project_path).resolve()
        self.config = config or IncrementalConfig()
        self.cache_file = self._confine_cache_path(self.project_path, self.config.cache_path)
        self._entries: Dict[str, HashEntry] = {}
        self._dirty = False

    @staticmethod
    def _confine_cache_path(project_path: Path, cache_path: str) -> Path:
        raw = Path(cache_path)
        if raw.is_absolute() or ".." in raw.parts:
            raise ValueError("cache_path must stay under the project path")
        dest = project_path / raw
        resolved = dest.resolve()
        if not resolved.is_relative_to(project_path.resolve()):
            raise ValueError("cache_path must stay under the project path")
        return dest

    def _hmac_key(self) -> bytes:
        from Asgard.common._hmac_env import hmac_key_from_env

        env = hmac_key_from_env(_HMAC_ENV)
        if env is not None:
            return env
        if getattr(self, "_ephemeral_hmac", None) is None:
            self._ephemeral_hmac = os.urandom(32)
        return self._ephemeral_hmac

    def _sign(self, payload: dict) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hmac.new(self._hmac_key(), canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def load(self) -> bool:
        """
        Load cache from disk.

        Returns:
            True if cache was loaded successfully
        """
        if not self.cache_file.exists() or self.cache_file.is_symlink():
            return False

        try:
            data = json.loads(self.cache_file.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                self._entries = {}
                return False
            expected = data.pop("hmac", None)
            if not isinstance(expected, str) or not hmac.compare_digest(
                expected, self._sign(data)
            ):
                self._entries = {}
                return False
            entries = data.get('entries', {})
            for item_id, entry_data in entries.items():
                self._entries[item_id] = HashEntry(**entry_data)

            self._dirty = False
            return True

        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            self._entries = {}
            return False

    def save(self) -> None:
        """Save cache to disk with HMAC."""
        if not self._dirty and self.cache_file.exists():
            return
        if self.cache_file.is_symlink():
            raise ValueError("hash cache path must not be a symlink")

        payload = {
            'version': '1.0.0',
            'created_at': datetime.now().isoformat(),
            'project_path': str(self.project_path),
            'entries': {
                item_id: {
                    'item_id': entry.item_id,
                    'hash': entry.hash,
                    'last_modified': entry.last_modified,
                    'size': entry.size,
                    'last_processed': entry.last_processed,
                    'result': entry.result,
                    'metadata': entry.metadata,
                }
                for item_id, entry in self._entries.items()
            }
        }
        payload["hmac"] = self._sign({k: v for k, v in payload.items() if k != "hmac"})

        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(payload, indent=2).encode("utf-8")
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.cache_file, flags, 0o600)
        try:
            os.write(fd, raw)
        finally:
            os.close(fd)
        os.chmod(self.cache_file, 0o600)

        self._dirty = False

    def compute_hash(self, content: Union[str, bytes, Path]) -> str:
        """
        Compute hash of content.

        Args:
            content: String, bytes, or file path to hash

        Returns:
            Hash string
        """
        if self.config.hash_func == "sha256":
            hasher = hashlib.sha256()
        elif self.config.hash_func == "sha1":
            hasher = hashlib.sha1()
        else:
            hasher = hashlib.md5()

        if isinstance(content, Path):
            with open(content, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
        elif isinstance(content, str):
            hasher.update(content.encode('utf-8'))
        else:
            hasher.update(content)

        return hasher.hexdigest()

    def is_changed(
        self,
        item_id: str,
        content: Optional[Union[str, bytes, Path]] = None,
        file_path: Optional[Path] = None,
    ) -> bool:
        """
        Check if an item has changed since last processing.

        Args:
            item_id: Unique identifier for the item
            content: Content to hash (optional)
            file_path: File path for stat-based quick check (optional)

        Returns:
            True if item has changed or is not in cache
        """
        if item_id not in self._entries:
            return True

        entry = self._entries[item_id]

        # Always re-hash; mtime/size is not a skip (CWE-345).
        if content is not None:
            current_hash = self.compute_hash(content)
            return current_hash != entry.hash

        # If file_path provided but no quick match, do hash check
        if file_path and file_path.exists():
            current_hash = self.compute_hash(file_path)
            return current_hash != entry.hash

        return True

    def get_cached_result(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached result for an item.

        Args:
            item_id: Unique identifier

        Returns:
            Cached result dictionary or None
        """
        entry = self._entries.get(item_id)
        if entry and entry.result:
            return entry.result
        return None

    def update(
        self,
        item_id: str,
        content: Optional[Union[str, bytes, Path]] = None,
        result: Optional[Dict[str, Any]] = None,
        file_path: Optional[Path] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update cache entry for an item.

        Args:
            item_id: Unique identifier
            content: Content to hash
            result: Processing result to cache
            file_path: File path for stat info
            metadata: Additional metadata to store
        """
        content_hash = ""
        last_modified = None
        size = None

        if content is not None:
            content_hash = self.compute_hash(content)
        elif file_path and file_path.exists():
            content_hash = self.compute_hash(file_path)

        if file_path and file_path.exists():
            stat = file_path.stat()
            last_modified = stat.st_mtime
            size = stat.st_size

        entry = HashEntry(
            item_id=item_id,
            hash=content_hash,
            last_modified=last_modified,
            size=size,
            last_processed=datetime.now().isoformat(),
            result=result if self.config.store_results else None,
            metadata=metadata or {},
        )

        self._entries[item_id] = entry
        self._dirty = True

    def invalidate(self, item_id: str) -> bool:
        """
        Remove an item from the cache.

        Args:
            item_id: Unique identifier

        Returns:
            True if entry was removed
        """
        if item_id in self._entries:
            del self._entries[item_id]
            self._dirty = True
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._entries = {}
        self._dirty = True

    def filter_changed(
        self,
        items: List[Any],
        id_func: Callable[[Any], str],
        content_func: Optional[Callable[[Any], Union[str, bytes, Path]]] = None,
    ) -> List[Any]:
        """
        Filter a list of items to only those that have changed.

        Args:
            items: List of items
            id_func: Function to get ID from item
            content_func: Function to get content from item (optional)

        Returns:
            List of changed items
        """
        changed = []
        for item in items:
            item_id = id_func(item)
            content = content_func(item) if content_func else None
            if self.is_changed(item_id, content):
                changed.append(item)
        return changed

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = len(self._entries)
        with_results = sum(1 for e in self._entries.values() if e.result)

        return {
            'total_entries': total,
            'entries_with_results': with_results,
            'cache_file': str(self.cache_file),
            'cache_exists': self.cache_file.exists(),
        }
