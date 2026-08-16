"""CH-0068: visual baseline index paths must stay under storage_directory."""

import json
from pathlib import Path

import pytest

from Asgard.Freya.Integration.models.integration_models import (
    BaselineConfig,
    BaselineEntry,
)
from Asgard.Freya.Integration.services._baseline_manager_helpers import (
    confine_storage_path,
    load_index,
    version_baseline,
)
from Asgard.Freya.Integration.services.baseline_manager import BaselineManager


def _entry(screenshot_path: str) -> BaselineEntry:
    return BaselineEntry(
        url="https://example.com",
        name="jail_test",
        created_at="2025-01-01T00:00:00",
        updated_at="2025-01-01T00:00:00",
        screenshot_path=screenshot_path,
        viewport_width=1920,
        viewport_height=1080,
        hash="deadbeef",
    )


def _manager(storage: Path) -> BaselineManager:
    return BaselineManager(BaselineConfig(storage_directory=str(storage)))


class TestConfineStoragePath:
    def test_relative_parent_traversal_rejected(self, tmp_path: Path):
        storage = tmp_path / "baselines"
        storage.mkdir()
        with pytest.raises(ValueError, match="escapes"):
            confine_storage_path(storage, "../outside.png")

    def test_absolute_outside_rejected(self, tmp_path: Path):
        storage = tmp_path / "baselines"
        storage.mkdir()
        with pytest.raises(ValueError, match="not under the storage directory"):
            confine_storage_path(storage, "/tmp/outside.png")

    def test_symlink_dest_rejected(self, tmp_path: Path):
        storage = tmp_path / "baselines"
        storage.mkdir()
        outside = tmp_path / "outside.png"
        outside.write_bytes(b"secret")
        link = storage / "link.png"
        link.symlink_to(outside)
        with pytest.raises(ValueError, match="symlink"):
            confine_storage_path(storage, link)

    def test_parent_symlink_escape_rejected(self, tmp_path: Path):
        storage = tmp_path / "baselines"
        storage.mkdir()
        outside = tmp_path / "outside_dir"
        outside.mkdir()
        target = outside / "file.png"
        target.write_bytes(b"secret")
        (storage / "escape").symlink_to(outside)
        with pytest.raises(ValueError):
            confine_storage_path(storage, storage / "escape" / "file.png")

    def test_legitimate_path_accepted(self, tmp_path: Path):
        storage = tmp_path / "baselines"
        nested = storage / "abc123"
        nested.mkdir(parents=True)
        dest = nested / "baseline.png"
        dest.write_bytes(b"ok")
        resolved = confine_storage_path(storage, dest)
        assert resolved == dest.resolve()
        assert resolved.is_relative_to(storage.resolve())


class TestDeleteBaselineJail:
    def test_parent_traversal_does_not_unlink_outside(self, tmp_path: Path):
        storage = tmp_path / "baselines"
        outside = tmp_path / "outside.png"
        outside.write_bytes(b"secret")
        manager = _manager(storage)
        key = manager._generate_key("https://example.com", "jail_test", None)
        manager.baselines[key] = _entry("../outside.png")

        deleted = manager.delete_baseline("https://example.com", "jail_test")

        assert deleted is True
        assert outside.exists()
        assert outside.read_bytes() == b"secret"
        assert key not in manager.baselines

    def test_symlink_dest_does_not_unlink_target(self, tmp_path: Path):
        storage = tmp_path / "baselines"
        storage.mkdir()
        outside = tmp_path / "outside.png"
        outside.write_bytes(b"secret")
        link = storage / "link.png"
        link.symlink_to(outside)
        manager = _manager(storage)
        key = manager._generate_key("https://example.com", "jail_test", None)
        manager.baselines[key] = _entry(str(link))

        deleted = manager.delete_baseline("https://example.com", "jail_test")

        assert deleted is True
        assert outside.exists()
        assert outside.read_bytes() == b"secret"

    def test_legitimate_path_is_deleted(self, tmp_path: Path):
        storage = tmp_path / "baselines"
        manager = _manager(storage)
        key = manager._generate_key("https://example.com", "jail_test", None)
        dest = storage / key / "baseline.png"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"ok")
        manager.baselines[key] = _entry(str(dest))

        deleted = manager.delete_baseline("https://example.com", "jail_test")

        assert deleted is True
        assert not dest.exists()
        assert key not in manager.baselines


class TestVersionBaselineJail:
    def test_parent_traversal_source_is_refused(self, tmp_path: Path):
        storage = tmp_path / "baselines"
        storage.mkdir()
        outside = tmp_path / "outside.png"
        outside.write_bytes(b"secret")

        with pytest.raises(ValueError):
            version_baseline(storage, "abc123", "../outside.png", max_versions=5)

        versions_dir = storage / "abc123" / "versions"
        assert not versions_dir.exists() or list(versions_dir.glob("*.png")) == []
        assert outside.read_bytes() == b"secret"

    def test_symlink_source_is_refused(self, tmp_path: Path):
        storage = tmp_path / "baselines"
        storage.mkdir()
        outside = tmp_path / "outside.png"
        outside.write_bytes(b"secret")
        link = storage / "link.png"
        link.symlink_to(outside)

        with pytest.raises(ValueError, match="symlink"):
            version_baseline(storage, "abc123", str(link), max_versions=5)

        versions_dir = storage / "abc123" / "versions"
        assert not versions_dir.exists() or list(versions_dir.glob("*.png")) == []
        assert outside.read_bytes() == b"secret"

    def test_legitimate_path_is_copied(self, tmp_path: Path):
        storage = tmp_path / "baselines"
        storage.mkdir()
        src = storage / "src.png"
        src.write_bytes(b"ok")

        version_baseline(storage, "abc123", str(src), max_versions=5)

        versions = list((storage / "abc123" / "versions").glob("*.png"))
        assert len(versions) == 1
        assert versions[0].read_bytes() == b"ok"


class TestLoadIndexJail:
    def test_hostile_screenshot_path_is_skipped(self, tmp_path: Path):
        storage = tmp_path / "baselines"
        storage.mkdir()
        outside = tmp_path / "outside.png"
        outside.write_bytes(b"secret")
        index_file = storage / "baselines.json"
        index_file.write_text(json.dumps({
            "deadbeefdeadbeef": {
                "url": "https://example.com",
                "name": "jail_test",
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00",
                "screenshot_path": "../outside.png",
                "viewport_width": 1920,
                "viewport_height": 1080,
                "hash": "deadbeef",
            }
        }))

        loaded = load_index(index_file, storage)
        assert loaded == {}
        manager = _manager(storage)
        assert manager.baselines == {}
        assert manager.delete_baseline("https://example.com", "jail_test") is False
        assert outside.exists()
