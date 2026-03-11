"""
Incremental Scanner Infrastructure

Provides caching support to skip re-analyzing unchanged files.
"""

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Set, TypeVar

R = TypeVar('R')  # Result type


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
    cache_path: str = ".asgard-cache.json"
    store_results: bool = True
    max_cache_age_days: int = 30


class FileHashCache:
    """
    Manages file hash cache for incremental scanning.

    Stores SHA-256 hashes of files along with their analysis results,
    allowing scanners to skip unchanged files.

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
        self.project_path = project_path
        self.config = config or IncrementalConfig()
        self.cache_file = project_path / self.config.cache_path
        self._entries: Dict[str, FileHashEntry] = {}
        self._dirty = False

    def load(self) -> bool:
        """
        Load cache from disk.

        Returns:
            True if cache was loaded successfully
        """
        if not self.cache_file.exists():
            return False

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate and load entries
            entries = data.get('entries', {})
            for path, entry_data in entries.items():
                self._entries[path] = FileHashEntry(**entry_data)

            self._dirty = False
            return True

        except (json.JSONDecodeError, KeyError, TypeError):
            # Invalid cache file, start fresh
            self._entries = {}
            return False

    def save(self) -> None:
        """Save cache to disk."""
        if not self._dirty and self.cache_file.exists():
            return

        data = {
            'version': '1.0.0',
            'created_at': datetime.now().isoformat(),
            'project_path': str(self.project_path),
            'entries': {
                path: {
                    'file_path': entry.file_path,
                    'hash': entry.hash,
                    'last_modified': entry.last_modified,
                    'size': entry.size,
                    'last_analyzed': entry.last_analyzed,
                    'result': entry.result,
                }
                for path, entry in self._entries.items()
            }
        }

        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        self._dirty = False

    def is_changed(self, file_path: Path) -> bool:
        """
        Check if a file has changed since last analysis.

        Args:
            file_path: Path to the file

        Returns:
            True if file has changed or is not in cache
        """
        rel_path = self._relative_path(file_path)

        if rel_path not in self._entries:
            return True

        entry = self._entries[rel_path]

        # Check if file still exists
        if not file_path.exists():
            return True

        # Quick check: modification time and size
        stat = file_path.stat()
        if stat.st_mtime != entry.last_modified or stat.st_size != entry.size:
            # Hash check for definitive answer
            current_hash = self._compute_hash(file_path)
            return current_hash != entry.hash

        return False

    def get_cached_result(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis result for a file.

        Args:
            file_path: Path to the file

        Returns:
            Cached result dictionary or None if not cached
        """
        rel_path = self._relative_path(file_path)
        entry = self._entries.get(rel_path)

        if entry and entry.result:
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
        if not file_path.exists():
            return

        rel_path = self._relative_path(file_path)
        stat = file_path.stat()

        entry = FileHashEntry(
            file_path=rel_path,
            hash=self._compute_hash(file_path),
            last_modified=stat.st_mtime,
            size=stat.st_size,
            last_analyzed=datetime.now().isoformat(),
            result=result if self.config.store_results else None,
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
        if rel_path in self._entries:
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
            full_path = self.project_path / rel_path
            if not full_path.exists():
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
            'total_entries': total,
            'entries_with_results': with_results,
            'cache_file': str(self.cache_file),
            'cache_exists': self.cache_file.exists(),
        }

    def filter_changed(self, files: List[Path]) -> List[Path]:
        """
        Filter a list of files to only those that have changed.

        Args:
            files: List of file paths

        Returns:
            List of files that have changed since last analysis
        """
        return [f for f in files if self.is_changed(f)]

    def _relative_path(self, path: Path) -> str:
        """Convert to relative path for cache key."""
        try:
            return str(path.relative_to(self.project_path))
        except ValueError:
            return str(path)

    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file contents."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()


class IncrementalScannerMixin:
    """
    Mixin class to add incremental scanning capabilities to existing scanners.

    Usage:
        class MyScanner(IncrementalScannerMixin):
            def __init__(self, config):
                self.incremental_config = IncrementalConfig(
                    enabled=config.incremental,
                    cache_path=config.cache_path,
                )
                self._init_cache(Path(config.scan_path))

            def analyze(self, path: Path):
                files = self._discover_files(path)

                if self.incremental_config.enabled:
                    files = self._filter_changed_files(files)

                for file in files:
                    result = self._analyze_file(file)
                    self._update_cache(file, result)

                self._save_cache()
    """

    incremental_config: IncrementalConfig
    _file_cache: Optional[FileHashCache] = None

    def _init_cache(self, project_path: Path) -> None:
        """Initialize the file hash cache."""
        self._file_cache = FileHashCache(project_path, self.incremental_config)
        if self.incremental_config.enabled:
            self._file_cache.load()

    def _filter_changed_files(self, files: List[Path]) -> List[Path]:
        """Filter files to only those that have changed."""
        if not self._file_cache or not self.incremental_config.enabled:
            return files
        return self._file_cache.filter_changed(files)

    def _get_cached_result(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get cached result for a file."""
        if not self._file_cache or not self.incremental_config.enabled:
            return None
        return self._file_cache.get_cached_result(file_path)

    def _update_cache(
        self,
        file_path: Path,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update cache for a file."""
        if not self._file_cache or not self.incremental_config.enabled:
            return
        self._file_cache.update(file_path, result)

    def _save_cache(self) -> None:
        """Save the cache to disk."""
        if self._file_cache and self.incremental_config.enabled:
            self._file_cache.save()

    def _get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self._file_cache:
            return {}
        return self._file_cache.get_stats()
