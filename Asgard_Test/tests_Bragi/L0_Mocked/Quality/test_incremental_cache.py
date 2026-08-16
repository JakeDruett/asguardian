"""CH-0048: incremental FileHashCache must not skip on planted or stale data."""

from __future__ import annotations

import json
import os
import stat
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from Asgard.Bragi.Quality.services._incremental_cache import (
    CACHE_VERSION,
    HMAC_ENV,
    FileHashCache,
    IncrementalConfig,
    confine_cache_path,
)
from Asgard.Bragi.Quality.services.incremental_scanner import IncrementalScannerMixin


@pytest.fixture
def inc_hmac(monkeypatch):
    monkeypatch.setenv(HMAC_ENV, "test-incremental-cache-key")


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _plant_unsigned(project: Path, entries: dict, name: str = ".asgard-cache.json") -> Path:
    path = project / name
    path.write_text(json.dumps({
        "version": CACHE_VERSION,
        "created_at": datetime.now().isoformat(),
        "project_path": str(project),
        "entries": entries,
    }), encoding="utf-8")
    return path


class _EnabledScanner(IncrementalScannerMixin):
    def __init__(self, project_path: Path, cache_path: str = ".asgard-cache.json"):
        self.incremental_config = IncrementalConfig(enabled=True, cache_path=cache_path)
        self._init_cache(project_path)


class TestEnabledDefault:
    def test_incremental_stays_disabled_by_default(self):
        assert IncrementalConfig().enabled is False


class TestPlantedCacheDoesNotSkip:
    def test_unsigned_planted_cache_does_not_skip(self, tmp_path, inc_hmac):
        src = _write(tmp_path / "a.py", "x = 1\n")
        digest = FileHashCache(tmp_path)._compute_hash(src)
        _plant_unsigned(tmp_path, {
            "a.py": {
                "file_path": "a.py",
                "hash": digest,
                "last_modified": src.stat().st_mtime,
                "size": src.stat().st_size,
                "last_analyzed": datetime.now().isoformat(),
                "result": {"injected": True, "issues": []},
            }
        })
        cache = FileHashCache(tmp_path)
        assert cache.load() is False
        assert cache.is_changed(src) is True
        assert cache.get_cached_result(src) is None

    def test_rewritten_result_without_hmac_is_ignored(self, tmp_path, inc_hmac):
        src = _write(tmp_path / "a.py", "x = 1\n")
        cache = FileHashCache(tmp_path)
        cache.update(src, {"issues": ["real"]})
        cache.save()
        data = json.loads(cache.cache_file.read_text(encoding="utf-8"))
        data["entries"]["a.py"]["result"] = {"issues": []}
        cache.cache_file.write_text(json.dumps(data), encoding="utf-8")
        loaded = FileHashCache(tmp_path)
        assert loaded.load() is False
        assert loaded.is_changed(src) is True
        assert loaded.get_cached_result(src) is None

    def test_mixin_planted_cache_does_not_filter_or_inject(self, tmp_path, inc_hmac):
        src = _write(tmp_path / "a.py", "x = 1\n")
        digest = FileHashCache(tmp_path)._compute_hash(src)
        _plant_unsigned(tmp_path, {
            "a.py": {
                "file_path": "a.py",
                "hash": digest,
                "last_modified": src.stat().st_mtime,
                "size": src.stat().st_size,
                "last_analyzed": datetime.now().isoformat(),
                "result": {"injected": True},
            }
        })
        scanner = _EnabledScanner(tmp_path)
        assert scanner._filter_changed_files([src]) == [src]
        assert scanner._get_cached_result(src) is None


class TestAlwaysRehash:
    def test_same_mtime_and_size_still_rehashes(self, tmp_path, inc_hmac):
        src = _write(tmp_path / "a.py", "AAAA")
        cache = FileHashCache(tmp_path)
        cache.update(src, {"ok": True})
        original_mtime = src.stat().st_mtime
        _write(src, "BBBB")
        os.utime(src, (original_mtime, original_mtime))
        assert src.stat().st_size == 4
        assert src.stat().st_mtime == original_mtime
        assert cache.is_changed(src) is True
        assert cache.get_cached_result(src) is None

    def test_unchanged_content_is_cache_hit(self, tmp_path, inc_hmac):
        src = _write(tmp_path / "a.py", "AAAA")
        cache = FileHashCache(tmp_path)
        cache.update(src, {"ok": True})
        cache.save()
        loaded = FileHashCache(tmp_path)
        assert loaded.load() is True
        assert loaded.is_changed(src) is False
        assert loaded.get_cached_result(src) == {"ok": True}


class TestCachePathJail:
    def test_absolute_cache_path_is_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="project path"):
            FileHashCache(tmp_path, IncrementalConfig(cache_path="/tmp/evil.json"))

    def test_parent_cache_path_is_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="project path"):
            FileHashCache(tmp_path, IncrementalConfig(cache_path="../../etc/passwd"))

    def test_relative_cache_path_stays_under_project(self, tmp_path):
        dest = confine_cache_path(tmp_path, ".asgard_cache/inc.json")
        assert dest == tmp_path / ".asgard_cache" / "inc.json"
        assert dest.resolve().is_relative_to(tmp_path.resolve())

    def test_mixin_absolute_cache_path_disables_cache(self, tmp_path):
        src = _write(tmp_path / "a.py", "x = 1\n")
        scanner = _EnabledScanner(tmp_path, cache_path="/tmp/evil.json")
        assert scanner._file_cache is None
        assert scanner._filter_changed_files([src]) == [src]
        assert scanner._get_cached_result(src) is None


class TestTtlHonored:
    def test_expired_entry_does_not_skip(self, tmp_path, inc_hmac):
        src = _write(tmp_path / "a.py", "x = 1\n")
        cache = FileHashCache(tmp_path, IncrementalConfig(max_cache_age_days=30))
        cache.update(src, {"ok": True})
        rel = next(iter(cache._entries))
        cache._entries[rel].last_analyzed = (
            datetime.now() - timedelta(days=31)
        ).isoformat()
        cache._dirty = True
        cache.save()
        loaded = FileHashCache(tmp_path, IncrementalConfig(max_cache_age_days=30))
        assert loaded.load() is True
        assert loaded.is_changed(src) is True
        assert loaded.get_cached_result(src) is None

    def test_fresh_entry_within_ttl_is_reused(self, tmp_path, inc_hmac):
        src = _write(tmp_path / "a.py", "x = 1\n")
        cache = FileHashCache(tmp_path, IncrementalConfig(max_cache_age_days=30))
        cache.update(src, {"ok": True})
        rel = next(iter(cache._entries))
        cache._entries[rel].last_analyzed = (
            datetime.now() - timedelta(days=29)
        ).isoformat()
        cache._dirty = True
        cache.save()
        loaded = FileHashCache(tmp_path, IncrementalConfig(max_cache_age_days=30))
        assert loaded.load() is True
        assert loaded.is_changed(src) is False
        assert loaded.get_cached_result(src) == {"ok": True}


class TestHmacPersistence:
    def test_roundtrip_writes_hmac(self, tmp_path, inc_hmac):
        src = _write(tmp_path / "a.py", "x = 1\n")
        cache = FileHashCache(tmp_path)
        cache.update(src, {"score": 1})
        cache.save()
        payload = json.loads(cache.cache_file.read_text(encoding="utf-8"))
        assert payload.get("hmac")
        assert payload.get("version") == CACHE_VERSION

    def test_save_creates_0600_sibling_key_without_env(self, tmp_path, monkeypatch):
        monkeypatch.delenv(HMAC_ENV, raising=False)
        src = _write(tmp_path / "a.py", "x = 1\n")
        cache = FileHashCache(tmp_path)
        cache.update(src, {"score": 1})
        cache.save()
        key_path = cache.cache_file.with_name(cache.cache_file.name + ".key")
        assert key_path.exists()
        assert stat.S_IMODE(key_path.stat().st_mode) == 0o600
        assert stat.S_IMODE(cache.cache_file.stat().st_mode) == 0o600
        loaded = FileHashCache(tmp_path)
        assert loaded.load() is True
        assert loaded.get_cached_result(src) == {"score": 1}

    def test_symlink_cache_is_ignored(self, tmp_path, inc_hmac):
        src = _write(tmp_path / "a.py", "x = 1\n")
        planted = tmp_path / "planted.json"
        planted.write_text(json.dumps({
            "version": CACHE_VERSION,
            "entries": {},
            "hmac": "00" * 32,
        }), encoding="utf-8")
        planted_bytes = planted.read_bytes()
        link = tmp_path / ".asgard-cache.json"
        link.symlink_to(planted)
        cache = FileHashCache(tmp_path)
        assert cache.load() is False
        cache.update(src, {"ok": True})
        cache.save()
        assert link.is_symlink()
        assert planted.read_bytes() == planted_bytes
        assert cache.get_cached_result(src) == {"ok": True}
        reloaded = FileHashCache(tmp_path)
        assert reloaded.load() is False

    def test_symlink_cache_escaping_project_is_rejected(self, tmp_path):
        project = tmp_path / "proj"
        project.mkdir()
        outside = tmp_path / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        (project / ".asgard-cache.json").symlink_to(outside)
        with pytest.raises(ValueError, match="project path"):
            FileHashCache(project)
