"""Tests for file integrity checker."""
import json
import os
import stat

import pytest
from pathlib import Path
from Asgard.Heimdall.Security.FileIntegrity.services.file_integrity_checker import FileIntegrityChecker
from Asgard.Heimdall.Security.FileIntegrity.models.file_integrity_models import (
    FileIntegrityReport,
    FileRecord,
)


class TestFileIntegrityCheckerInstantiation:
    def test_checker_can_be_instantiated(self):
        assert FileIntegrityChecker() is not None


class TestFileIntegrityCheckerBaseline:
    def test_create_and_verify_detects_modification(self, tmp_path):
        baseline_file = str(tmp_path / ".baseline.json")
        checker = FileIntegrityChecker(baseline_file=baseline_file)
        (tmp_path / "data.txt").write_text("original content")
        checker.create_baseline(tmp_path)
        (tmp_path / "data.txt").write_text("tampered content")
        report: FileIntegrityReport = checker.verify_integrity(tmp_path)
        assert report.modified or report.has_changes

    def test_unchanged_files_produce_no_modifications(self, tmp_path):
        baseline_file = str(tmp_path / ".baseline.json")
        checker = FileIntegrityChecker(baseline_file=baseline_file)
        (tmp_path / "data.txt").write_text("stable content")
        checker.create_baseline(tmp_path)
        report: FileIntegrityReport = checker.verify_integrity(tmp_path)
        assert len(report.modified) == 0


class TestFileIntegrityCheckerHashing:
    def test_same_file_produces_consistent_hash(self, tmp_path):
        checker = FileIntegrityChecker()
        f = tmp_path / "file.txt"
        f.write_text("hello world")
        record1 = checker.hash_file(f)
        record2 = checker.hash_file(f)
        assert record1 is not None
        assert record2 is not None
        assert record1.sha256 == record2.sha256
        assert record1.md5 == record2.md5


class TestFileIntegrityHmacAndAdds:
    def test_added_file_sets_has_changes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ASGARD_INTEGRITY_HMAC_KEY", "test-integrity-key")
        baseline_file = str(tmp_path / ".baseline.json")
        checker = FileIntegrityChecker(baseline_file=baseline_file)
        (tmp_path / "data.txt").write_text("original")
        checker.create_baseline(tmp_path)
        (tmp_path / "extra.txt").write_text("new file")
        report = checker.verify_integrity(tmp_path)
        assert report.added
        assert report.has_changes

    def test_unsigned_baseline_is_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ASGARD_INTEGRITY_HMAC_KEY", "test-integrity-key")
        planted = tmp_path / ".baseline.json"
        planted.write_text(json.dumps({
            "created": "2020-01-01T00:00:00",
            "files": {
                str(tmp_path / "data.txt"): {
                    "path": str(tmp_path / "data.txt"),
                    "size": 8,
                    "md5": "0" * 32,
                    "sha256": "0" * 64,
                    "modified_time": "2020-01-01T00:00:00",
                    "permissions": "644",
                }
            },
        }))
        (tmp_path / "data.txt").write_text("original")
        checker = FileIntegrityChecker(baseline_file=str(planted))
        with pytest.raises(FileNotFoundError):
            checker.verify_integrity(tmp_path)

    def test_rewritten_hash_without_hmac_is_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ASGARD_INTEGRITY_HMAC_KEY", "test-integrity-key")
        baseline_file = tmp_path / ".baseline.json"
        checker = FileIntegrityChecker(baseline_file=str(baseline_file))
        target = tmp_path / "data.txt"
        target.write_text("original")
        checker.create_baseline(tmp_path)
        data = json.loads(baseline_file.read_text())
        rec = next(iter(data["files"].values()))
        rec["sha256"] = "f" * 64
        rec["md5"] = "e" * 32
        baseline_file.write_text(json.dumps(data))
        with pytest.raises(FileNotFoundError):
            checker.verify_integrity(tmp_path)

    def test_symlink_file_is_not_hashed(self, tmp_path):
        dest = tmp_path / "real.txt"
        dest.write_text("secret-outside")
        link = tmp_path / "link.txt"
        link.symlink_to(dest)
        checker = FileIntegrityChecker()
        assert checker.hash_file(link) is None

    def test_symlink_baseline_path_is_refused(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ASGARD_INTEGRITY_HMAC_KEY", "test-integrity-key")
        real = tmp_path / "real_baseline.json"
        real.write_text("{}")
        link = tmp_path / ".baseline.json"
        link.symlink_to(real)
        checker = FileIntegrityChecker(baseline_file=str(link))
        (tmp_path / "data.txt").write_text("x")
        with pytest.raises(ValueError, match="symlink"):
            checker.create_baseline(tmp_path)

    def test_baseline_file_mode_is_0600(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ASGARD_INTEGRITY_HMAC_KEY", "test-integrity-key")
        baseline_file = tmp_path / ".baseline.json"
        checker = FileIntegrityChecker(baseline_file=str(baseline_file))
        (tmp_path / "data.txt").write_text("x")
        checker.create_baseline(tmp_path)
        mode = stat.S_IMODE(os.stat(baseline_file).st_mode)
        assert mode == 0o600


class TestFileIntegrityCrossProcessPersistence:
    """A separate FileIntegrityChecker *instance* (standing in for a separate
    process/CLI invocation) must be able to verify a baseline written by an
    earlier instance, with no HMAC env var set. Before the fix, each instance
    minted its own os.urandom(32) signing key that was never persisted, so
    this cross-instance verify always failed the HMAC check and
    verify_integrity() always raised FileNotFoundError.
    """

    def test_second_instance_can_verify_first_instances_baseline(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ASGARD_INTEGRITY_HMAC_KEY", raising=False)
        baseline_file = str(tmp_path / ".baseline.json")
        (tmp_path / "data.txt").write_text("stable content")

        writer = FileIntegrityChecker(baseline_file=baseline_file)
        writer.create_baseline(tmp_path)

        reader = FileIntegrityChecker(baseline_file=baseline_file)
        report = reader.verify_integrity(tmp_path)
        assert len(report.modified) == 0
        assert report.ok_count == 1

    def test_key_file_persisted_sibling_to_baseline_at_0600(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ASGARD_INTEGRITY_HMAC_KEY", raising=False)
        baseline_file = tmp_path / ".baseline.json"
        (tmp_path / "data.txt").write_text("x")
        checker = FileIntegrityChecker(baseline_file=str(baseline_file))
        checker.create_baseline(tmp_path)

        key_file = tmp_path / ".baseline.json.key"
        assert key_file.exists()
        assert stat.S_IMODE(os.stat(key_file).st_mode) == 0o600
        assert len(key_file.read_bytes()) == 32

    def test_tampered_baseline_still_rejected_across_instances(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ASGARD_INTEGRITY_HMAC_KEY", raising=False)
        baseline_file = tmp_path / ".baseline.json"
        (tmp_path / "data.txt").write_text("original")
        writer = FileIntegrityChecker(baseline_file=str(baseline_file))
        writer.create_baseline(tmp_path)

        data = json.loads(baseline_file.read_text())
        rec = next(iter(data["files"].values()))
        rec["sha256"] = "f" * 64
        rec["md5"] = "e" * 32
        baseline_file.write_text(json.dumps(data))

        reader = FileIntegrityChecker(baseline_file=str(baseline_file))
        with pytest.raises(FileNotFoundError):
            reader.verify_integrity(tmp_path)
