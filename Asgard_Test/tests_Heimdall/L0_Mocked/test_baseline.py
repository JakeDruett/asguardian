"""Tests for Asgard.Baseline.*"""
import argparse
import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from Asgard.Baseline.baseline_manager import BaselineManager
from Asgard.Baseline.models import BaselineEntry, BaselineFile, BaselineStats
from Asgard.Baseline._baseline_helpers import (
    generate_violation_id,
    get_violation_message,
    hash_violation_message,
    is_usable_fuzzy_message,
    persistable_violation_message,
    relative_path,
)
from Asgard.Heimdall.cli.handlers.baseline import run_baseline_command
from Asgard.Heimdall.Security.models.security_models_base import (
    SecretFinding,
    SecretType,
    SecuritySeverity,
)


# ---------------------------------------------------------------------------
# BaselineEntry
# ---------------------------------------------------------------------------

class TestBaselineEntryInstantiation:
    def test_entry_can_be_instantiated(self):
        entry = BaselineEntry(
            file_path="src/foo.py",
            line_number=10,
            violation_type="lazy_import",
            violation_id="abc123",
        )
        assert entry is not None


class TestBaselineEntryCleanPath:
    def test_entry_matches_exact(self):
        entry = BaselineEntry(
            file_path="src/foo.py",
            line_number=10,
            violation_type="lazy_import",
            violation_id="abc123",
            message="import os",
        )
        assert entry.matches("src/foo.py", 10, "lazy_import", message="import os") is True

    def test_entry_matches_without_identity_is_false(self):
        entry = BaselineEntry(
            file_path="src/foo.py",
            line_number=10,
            violation_type="lazy_import",
            violation_id="abc123",
            message="import os",
        )
        assert entry.matches("src/foo.py", 10, "lazy_import") is False

    def test_entry_not_expired_by_default(self):
        entry = BaselineEntry(
            file_path="src/foo.py",
            line_number=10,
            violation_type="lazy_import",
            violation_id="abc123",
        )
        assert entry.is_expired is False


class TestBaselineEntryEdgeCases:
    def test_entry_matches_wrong_line_returns_false(self):
        entry = BaselineEntry(
            file_path="src/foo.py",
            line_number=10,
            violation_type="lazy_import",
            violation_id="abc123",
        )
        assert entry.matches("src/foo.py", 99, "lazy_import") is False

    def test_entry_expired_when_expires_at_in_past(self):
        past = datetime.now() - timedelta(days=1)
        entry = BaselineEntry(
            file_path="src/foo.py",
            line_number=1,
            violation_type="lazy_import",
            violation_id="abc123",
            expires_at=past,
        )
        assert entry.is_expired is True

    def test_entry_matches_returns_false_when_expired(self):
        past = datetime.now() - timedelta(days=1)
        entry = BaselineEntry(
            file_path="src/foo.py",
            line_number=1,
            violation_type="lazy_import",
            violation_id="abc123",
            expires_at=past,
        )
        assert entry.matches("src/foo.py", 1, "lazy_import") is False

    def test_fuzzy_match(self):
        entry = BaselineEntry(
            file_path="src/foo.py",
            line_number=1,
            violation_type="lazy_import",
            violation_id="abc123",
            message="some import",
        )
        assert entry.matches_fuzzy("src/foo.py", "lazy_import", "some import") is True

    def test_fuzzy_match_empty_message_is_unmatched(self):
        entry = BaselineEntry(
            file_path="src/foo.py",
            line_number=1,
            violation_type="heimdall_secret",
            violation_id="abc123",
            message="",
        )
        assert entry.matches_fuzzy("src/foo.py", "heimdall_secret", "") is False
        assert entry.matches_fuzzy("src/foo.py", "heimdall_secret", "   ") is False

    def test_fuzzy_match_whitespace_query_against_stored_key_is_unmatched(self):
        entry = BaselineEntry(
            file_path="src/foo.py",
            line_number=1,
            violation_type="heimdall_secret",
            violation_id="abc123",
            message="aws_access_key:AKIA****1111",
        )
        assert entry.matches_fuzzy("src/foo.py", "heimdall_secret", "") is False
        assert entry.matches_fuzzy("src/foo.py", "heimdall_secret", "   ") is False


# ---------------------------------------------------------------------------
# BaselineFile
# ---------------------------------------------------------------------------

class TestBaselineFileInstantiation:
    def test_baseline_file_can_be_instantiated(self):
        assert BaselineFile() is not None


class TestBaselineFileCleanPath:
    def test_add_entry_increases_count(self):
        bf = BaselineFile()
        entry = BaselineEntry(
            file_path="src/foo.py",
            line_number=1,
            violation_type="lazy_import",
            violation_id="abc123",
        )
        bf.add_entry(entry)
        assert len(bf.entries) == 1

    def test_remove_entry_by_id(self):
        bf = BaselineFile()
        entry = BaselineEntry(
            file_path="src/foo.py",
            line_number=1,
            violation_type="lazy_import",
            violation_id="abc123",
        )
        bf.add_entry(entry)
        result = bf.remove_entry("abc123")
        assert result is True
        assert len(bf.entries) == 0

    def test_remove_entry_refuses_ambiguous_id(self):
        bf = BaselineFile()
        bf.add_entry(BaselineEntry(
            file_path="a.py", line_number=1, violation_type="lint",
            violation_id="same-id", message="one",
        ))
        bf.add_entry(BaselineEntry(
            file_path="b.py", line_number=2, violation_type="lint",
            violation_id="same-id", message="two",
        ))
        assert bf.remove_entry("same-id") is False
        assert len(bf.entries) == 2
        assert bf.remove_entry("same-id", file_path="a.py", line_number=1) is True
        assert len(bf.entries) == 1

    def test_get_stats_returns_baseline_stats(self):
        bf = BaselineFile()
        stats = bf.get_stats()
        assert isinstance(stats, BaselineStats)
        assert stats.total_entries == 0

    def test_find_match_returns_entry(self):
        bf = BaselineFile()
        entry = BaselineEntry(
            file_path="src/foo.py",
            line_number=5,
            violation_type="complexity",
            violation_id="xyz",
        )
        bf.add_entry(entry)
        found = bf.find_match("src/foo.py", 5, "complexity", violation_id="xyz")
        assert found is not None

    def test_clean_expired_removes_expired_entries(self):
        past = datetime.now() - timedelta(days=1)
        bf = BaselineFile()
        entry = BaselineEntry(
            file_path="src/foo.py",
            line_number=1,
            violation_type="lazy_import",
            violation_id="exp1",
            expires_at=past,
        )
        bf.add_entry(entry)
        removed = bf.clean_expired()
        assert removed == 1
        assert len(bf.entries) == 0


class TestBaselineFileEdgeCases:
    def test_remove_nonexistent_entry_returns_false(self):
        bf = BaselineFile()
        assert bf.remove_entry("no-such-id") is False

    def test_find_match_returns_none_when_not_present(self):
        bf = BaselineFile()
        assert bf.find_match("missing.py", 1, "lazy_import") is None

    def test_stats_entries_by_type(self):
        bf = BaselineFile()
        bf.add_entry(BaselineEntry(file_path="a.py", line_number=1,
                                   violation_type="lazy_import", violation_id="id1"))
        bf.add_entry(BaselineEntry(file_path="b.py", line_number=2,
                                   violation_type="lazy_import", violation_id="id2"))
        bf.add_entry(BaselineEntry(file_path="c.py", line_number=3,
                                   violation_type="complexity", violation_id="id3"))
        stats = bf.get_stats()
        assert stats.entries_by_type["lazy_import"] == 2
        assert stats.entries_by_type["complexity"] == 1

    def test_add_entry_replaces_empty_message_with_violation_id(self):
        bf = BaselineFile()
        bf.add_entry(BaselineEntry(
            file_path="src/foo.py",
            line_number=1,
            violation_type="heimdall_secret",
            violation_id="vid-empty",
            message="",
        ))
        assert bf.entries[0].message == hash_violation_message("vid-empty")

    def test_find_fuzzy_match_empty_message_returns_none(self):
        bf = BaselineFile()
        bf.add_entry(BaselineEntry(
            file_path="src/foo.py",
            line_number=1,
            violation_type="heimdall_secret",
            violation_id="abc123",
            message="aws_access_key:AKIA****1111",
        ))
        assert bf.find_fuzzy_match("src/foo.py", "heimdall_secret", "") is None
        assert bf.find_fuzzy_match("src/foo.py", "heimdall_secret", "   ") is None


# ---------------------------------------------------------------------------
# BaselineManager
# ---------------------------------------------------------------------------

class TestBaselineManagerInstantiation:
    def test_manager_can_be_instantiated(self, tmp_path):
        manager = BaselineManager(project_path=tmp_path)
        assert manager is not None

    def test_absolute_baseline_file_is_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="project path"):
            BaselineManager(project_path=tmp_path, baseline_file="/tmp/x")

    def test_parent_baseline_file_is_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="project path"):
            BaselineManager(project_path=tmp_path, baseline_file="../x")


class TestBaselineManagerCleanPath:
    def test_load_returns_baseline_file_when_no_file_exists(self, tmp_path):
        manager = BaselineManager(project_path=tmp_path)
        bf = manager.load()
        assert isinstance(bf, BaselineFile)

    def test_add_entry_and_save_persists_to_disk(self, tmp_path):
        manager = BaselineManager(project_path=tmp_path)
        result = manager.add_entry(
            file_path=str(tmp_path / "src" / "foo.py"),
            line_number=5,
            violation_type="lazy_import",
            message="import os",
            reason="known",
        )
        assert result is True
        assert manager.baseline_path.exists()

    def test_load_from_existing_file(self, tmp_path):
        bf = BaselineFile(project_path=str(tmp_path))
        baseline_path = tmp_path / ".asgard-baseline.json"
        baseline_path.write_text(
            json.dumps(bf.model_dump(mode="json"), default=str)
        )
        manager = BaselineManager(project_path=tmp_path)
        loaded = manager.load()
        assert isinstance(loaded, BaselineFile)

    def test_get_stats_empty_baseline(self, tmp_path):
        manager = BaselineManager(project_path=tmp_path)
        stats = manager.get_stats()
        assert stats.total_entries == 0

    def test_list_entries_empty(self, tmp_path):
        manager = BaselineManager(project_path=tmp_path)
        entries = manager.list_entries()
        assert entries == []

    def test_generate_report_text(self, tmp_path):
        manager = BaselineManager(project_path=tmp_path)
        report = manager.generate_report("text")
        assert isinstance(report, str)

    def test_generate_report_json(self, tmp_path):
        manager = BaselineManager(project_path=tmp_path)
        report = manager.generate_report("json")
        parsed = json.loads(report)
        assert isinstance(parsed, dict)

    def test_generate_report_markdown(self, tmp_path):
        manager = BaselineManager(project_path=tmp_path)
        report = manager.generate_report("markdown")
        assert isinstance(report, str)


class TestBaselineManagerEdgeCases:
    def test_add_duplicate_entry_returns_false(self, tmp_path):
        manager = BaselineManager(project_path=tmp_path)
        file_path = str(tmp_path / "foo.py")
        manager.add_entry(file_path=file_path, line_number=1, violation_type="lazy_import")
        second = manager.add_entry(file_path=file_path, line_number=1, violation_type="lazy_import")
        assert second is False

    def test_remove_nonexistent_entry_returns_false(self, tmp_path):
        manager = BaselineManager(project_path=tmp_path)
        assert manager.remove_entry("no-such-id") is False

    def test_clean_expired_returns_zero_when_no_expired(self, tmp_path):
        manager = BaselineManager(project_path=tmp_path)
        manager.add_entry(file_path=str(tmp_path / "a.py"), line_number=1,
                          violation_type="lazy_import")
        count = manager.clean_expired()
        assert count == 0

    def test_filter_violations_no_baseline_returns_all(self, tmp_path):
        class FakeViolation:
            def __init__(self):
                self.file_path = str(tmp_path / "a.py")
                self.line_number = 1
                self.message = "issue"
        manager = BaselineManager(project_path=tmp_path)
        violations = [FakeViolation(), FakeViolation()]
        filtered = manager.filter_violations(violations, "lazy_import")
        assert len(filtered) == len(violations)


class TestBaselineManagerSymlinkSafety:
    def test_save_does_not_overwrite_symlink_target(self, tmp_path):
        target = tmp_path / "secret.json"
        original = '{"keep": true}\n'
        target.write_text(original, encoding="utf-8")
        dest = tmp_path / ".asgard-baseline.json"
        dest.symlink_to(target)

        manager = BaselineManager(project_path=tmp_path)
        manager._baseline = BaselineFile(project_path=str(tmp_path))
        with pytest.raises(ValueError, match="symlink"):
            manager.save()

        assert dest.is_symlink()
        assert dest.resolve() == target.resolve()
        assert target.read_text(encoding="utf-8") == original

    def test_load_missing_file_still_works(self, tmp_path):
        manager = BaselineManager(project_path=tmp_path)
        assert not manager.baseline_path.exists()
        loaded = manager.load()
        assert isinstance(loaded, BaselineFile)
        assert loaded.entries == []
        assert not manager.baseline_path.exists()

    def test_normal_save_persists_json(self, tmp_path):
        manager = BaselineManager(project_path=tmp_path)
        result = manager.add_entry(
            file_path=str(tmp_path / "src" / "foo.py"),
            line_number=5,
            violation_type="lazy_import",
            message="import os",
        )
        assert result is True
        payload = json.loads(manager.baseline_path.read_text(encoding="utf-8"))
        assert payload["entries"][0]["file_path"] == "src/foo.py"
        assert payload["entries"][0]["line_number"] == 5
        assert payload["entries"][0]["violation_type"] == "lazy_import"
        assert not manager.baseline_path.is_symlink()

    def test_load_of_symlink_raises(self, tmp_path):
        target = tmp_path / "secret.json"
        target.write_text("NOT-JSON-DO-NOT-READ", encoding="utf-8")
        dest = tmp_path / ".asgard-baseline.json"
        dest.symlink_to(target)

        manager = BaselineManager(project_path=tmp_path)
        with pytest.raises(ValueError, match="symlink"):
            manager.load()
        assert dest.is_symlink()
        assert target.read_text(encoding="utf-8") == "NOT-JSON-DO-NOT-READ"


# ---------------------------------------------------------------------------
# _baseline_helpers
# ---------------------------------------------------------------------------

class TestBaselineHelpersInstantiation:
    def test_generate_violation_id_returns_string(self):
        vid = generate_violation_id("src/foo.py", 10, "lazy_import", "import os")
        assert isinstance(vid, str)
        assert len(vid) == 64


class TestBaselineHelpersCleanPath:
    def test_generate_violation_id_deterministic(self):
        id1 = generate_violation_id("src/foo.py", 10, "lazy_import", "import os")
        id2 = generate_violation_id("src/foo.py", 10, "lazy_import", "import os")
        assert id1 == id2

    def test_relative_path_converts_absolute(self, tmp_path):
        abs_path = str(tmp_path / "src" / "foo.py")
        rel = relative_path(tmp_path, abs_path)
        assert rel == "src/foo.py"

    def test_get_violation_message_uses_message_attr(self):
        class V:
            message = "hello"
        assert get_violation_message(V()) == "hello"


class TestBaselineHelpersEdgeCases:
    def test_generate_violation_id_different_inputs_differ(self):
        id1 = generate_violation_id("src/foo.py", 1, "lazy_import", "")
        id2 = generate_violation_id("src/bar.py", 1, "lazy_import", "")
        assert id1 != id2

    def test_relative_path_returns_original_when_not_relative(self, tmp_path):
        other = "/some/other/path/foo.py"
        result = relative_path(tmp_path, other)
        assert result == other

    def test_get_violation_message_returns_empty_for_no_attr(self):
        class V:
            pass
        assert get_violation_message(V()) == ""

    def test_get_violation_message_skips_empty_message_attr(self):
        class V:
            message = ""
            description = "   "
            pattern_name = "aws_access_key"
            masked_value = "AKIA****1111"
        assert get_violation_message(V()) == "aws_access_key:AKIA****1111"

    def test_get_violation_message_secret_finding_like_uses_pattern_and_masked(self):
        class SecretLike:
            file_path = "src/foo.py"
            line_number = 1
            pattern_name = "aws_access_key"
            masked_value = "AKIA****1111"
        assert get_violation_message(SecretLike()) == "aws_access_key:AKIA****1111"

    def test_get_violation_message_falls_back_to_violation_id(self):
        class V:
            violation_id = "stable-id-9"
        assert get_violation_message(V()) == "stable-id-9"

    def test_get_violation_message_uses_secret_finding_property(self):
        finding = SecretFinding(
            file_path="src/foo.py",
            line_number=1,
            secret_type=SecretType.API_KEY,
            severity=SecuritySeverity.HIGH,
            pattern_name="aws_access_key",
            masked_value="AKIA****1111",
            line_content="key=***",
            confidence=0.9,
        )
        assert get_violation_message(finding) == "aws_access_key:AKIA****1111"
        assert finding.message == "aws_access_key:AKIA****1111"

    def test_usable_fuzzy_message_rejects_empty_and_whitespace(self):
        assert is_usable_fuzzy_message("") is False
        assert is_usable_fuzzy_message("   ") is False
        assert is_usable_fuzzy_message("aws_access_key:AKIA****1111") is True

    def test_persistable_message_replaces_empty_with_violation_id(self):
        assert persistable_violation_message("", "vid1") == hash_violation_message("vid1")
        assert persistable_violation_message("   ", "vid1") == hash_violation_message("vid1")
        assert persistable_violation_message("keep", "vid1") == hash_violation_message("keep")


class _SecretLike:
    def __init__(self, file_path, line_number, pattern_name="", masked_value=""):
        self.file_path = file_path
        self.line_number = line_number
        self.pattern_name = pattern_name
        self.masked_value = masked_value


class _BareFinding:
    def __init__(self, file_path, line_number):
        self.file_path = file_path
        self.line_number = line_number


class TestFuzzyEmptyMessageSuppression:
    def test_baselining_secret_like_does_not_hide_other_secrets_when_fuzzy(
        self, tmp_path
    ):
        src = str(tmp_path / "config.py")
        first = _SecretLike(src, 1, "aws_access_key", "AKIA****1111")
        later = _SecretLike(src, 8, "db_password", "Sup3****word")
        manager = BaselineManager(project_path=tmp_path)
        assert manager.create_from_violations([first], "heimdall_secret") == 1

        stored = manager.list_entries()[0].message
        assert stored == hash_violation_message("aws_access_key:AKIA****1111")

        remaining = manager.filter_violations(
            [first, later], "heimdall_secret", use_fuzzy_matching=True
        )
        assert remaining == [later]

        shifted = _SecretLike(src, 99, "aws_access_key", "AKIA****1111")
        still_baselined = manager.filter_violations(
            [shifted], "heimdall_secret", use_fuzzy_matching=True
        )
        assert still_baselined == []

    def test_baselining_object_with_no_message_does_not_hide_same_file_type(
        self, tmp_path
    ):
        src = str(tmp_path / "config.py")
        first = _BareFinding(src, 1)
        later = _BareFinding(src, 12)
        manager = BaselineManager(project_path=tmp_path)
        assert manager.create_from_violations([first], "heimdall_secret") == 1
        assert manager.list_entries()[0].message.strip()

        remaining = manager.filter_violations(
            [later], "heimdall_secret", use_fuzzy_matching=True
        )
        assert remaining == [later]

    def test_empty_message_fuzzy_lookup_is_unmatched(self, tmp_path):
        src = str(tmp_path / "config.py")
        manager = BaselineManager(project_path=tmp_path)
        manager.create_from_violations([_BareFinding(src, 1)], "heimdall_secret")

        query = _BareFinding(src, 1)
        remaining = manager.filter_violations(
            [query], "heimdall_secret", use_fuzzy_matching=True
        )
        assert remaining == [query]

    def test_create_from_violations_does_not_persist_empty_message(self, tmp_path):
        src = str(tmp_path / "config.py")
        manager = BaselineManager(project_path=tmp_path)
        manager.create_from_violations([_BareFinding(src, 3)], "heimdall_secret")
        entry = manager.list_entries()[0]
        assert entry.message
        assert entry.message.strip()
        assert entry.message == hash_violation_message(entry.violation_id)

    def test_add_entry_does_not_persist_empty_message(self, tmp_path):
        manager = BaselineManager(project_path=tmp_path)
        assert manager.add_entry(
            file_path=str(tmp_path / "a.py"),
            line_number=1,
            violation_type="heimdall_secret",
            message="",
        )
        entry = manager.list_entries()[0]
        assert entry.message
        assert entry.message == hash_violation_message(entry.violation_id)

    def test_real_secret_finding_baseline_does_not_hide_other_secret(self, tmp_path):
        src = str(tmp_path / "config.py")
        first = SecretFinding(
            file_path=src,
            line_number=1,
            secret_type=SecretType.API_KEY,
            severity=SecuritySeverity.HIGH,
            pattern_name="aws_access_key",
            masked_value="AKIA****1111",
            line_content="key=***",
            confidence=0.9,
        )
        later = SecretFinding(
            file_path=src,
            line_number=4,
            secret_type=SecretType.PASSWORD,
            severity=SecuritySeverity.CRITICAL,
            pattern_name="db_password",
            masked_value="Sup3****word",
            line_content="pwd=***",
            confidence=0.9,
        )
        manager = BaselineManager(project_path=tmp_path)
        manager.create_from_violations([first], "heimdall_secret")
        remaining = manager.filter_violations(
            [first, later], "heimdall_secret", use_fuzzy_matching=True
        )
        assert remaining == [later]


class TestBaselineIdentityAndHmac:
    def test_second_instance_honours_first_instances_baseline_without_env_key(
        self, tmp_path, monkeypatch,
    ):
        """Cross-process round-trip with no ASGARD_BASELINE_HMAC_KEY set: a
        *different* BaselineManager instance (standing in for a separate CI
        run reading `.asgard-baseline.json`) must still suppress a violation
        an earlier instance baselined. Before the persisted-.key-file fix,
        each instance minted its own os.urandom(32) signing key, so a fresh
        instance's HMAC check on a prior instance's baseline always failed,
        silently discarding the entire baseline (and un-suppressing every
        previously-accepted violation) on every separate run.
        """
        monkeypatch.delenv("ASGARD_BASELINE_HMAC_KEY", raising=False)

        class FakeViolation:
            def __init__(self):
                self.file_path = str(tmp_path / "a.py")
                self.line_number = 10
                self.message = "known issue"

        writer = BaselineManager(project_path=tmp_path)
        writer.create_from_violations([FakeViolation()], "lint")

        key_file = writer.baseline_path.with_name(writer.baseline_path.name + ".key")
        assert key_file.exists()
        assert len(key_file.read_bytes()) == 32

        reader = BaselineManager(project_path=tmp_path)
        remaining = reader.filter_violations([FakeViolation()], "lint")
        assert remaining == []

    def test_same_locus_different_message_is_not_suppressed(self, tmp_path):
        class FakeViolation:
            def __init__(self, message):
                self.file_path = str(tmp_path / "a.py")
                self.line_number = 10
                self.message = message

        manager = BaselineManager(project_path=tmp_path)
        manager.create_from_violations([FakeViolation("old issue")], "lint")
        remaining = manager.filter_violations([FakeViolation("new issue")], "lint")
        assert len(remaining) == 1
        assert remaining[0].message == "new issue"

    def test_unsigned_planted_baseline_does_not_suppress(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ASGARD_BASELINE_HMAC_KEY", "test-baseline-key")
        planted = {
            "version": "1.0.0",
            "created_at": "2020-01-01T00:00:00",
            "updated_at": "2020-01-01T00:00:00",
            "project_path": str(tmp_path),
            "entries": [{
                "file_path": "a.py",
                "line_number": 1,
                "violation_type": "lint",
                "violation_id": "planted",
                "message": "issue",
                "reason": "plant",
                "created_at": "2020-01-01T00:00:00",
                "created_by": "attacker",
                "expires_at": None,
            }],
            "metadata": {},
        }
        (tmp_path / ".asgard-baseline.json").write_text(json.dumps(planted))

        class FakeViolation:
            file_path = "a.py"
            line_number = 1
            message = "issue"

        manager = BaselineManager(project_path=tmp_path)
        remaining = manager.filter_violations([FakeViolation()], "lint")
        assert len(remaining) == 1

    def test_rewritten_entries_without_hmac_do_not_suppress(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ASGARD_BASELINE_HMAC_KEY", "test-baseline-key")

        class FakeViolation:
            def __init__(self):
                self.file_path = str(tmp_path / "a.py")
                self.line_number = 1
                self.message = "issue"

        manager = BaselineManager(project_path=tmp_path)
        manager.create_from_violations([FakeViolation()], "lint")
        data = json.loads(manager.baseline_path.read_text())
        data["entries"].append({
            "file_path": "b.py",
            "line_number": 2,
            "violation_type": "lint",
            "violation_id": "planted",
            "message": "other",
            "reason": "plant",
            "created_at": "2020-01-01T00:00:00",
            "created_by": "attacker",
            "expires_at": None,
        })
        manager.baseline_path.write_text(json.dumps(data))
        other = type("V", (), {
            "file_path": str(tmp_path / "b.py"),
            "line_number": 2,
            "message": "other",
        })()
        fresh = BaselineManager(project_path=tmp_path)
        remaining = fresh.filter_violations([other], "lint")
        assert remaining == [other]


_FAKE_SECRET = "sk_test_fake_CH0013_not_a_real_secret_xyz"


class _SnippetFinding:
    def __init__(self, file_path, line_number, description="", code_snippet=""):
        self.file_path = file_path
        self.line_number = line_number
        self.description = description
        self.code_snippet = code_snippet


def _baseline_cli_args(tmp_path, command, output_format="json"):
    return argparse.Namespace(
        path=str(tmp_path),
        baseline_file=".asgard-baseline.json",
        format=output_format,
        baseline_command=command,
        type=None,
        file=None,
        id=None,
    )


class TestRawViolationTextNotPersisted:
    def test_hash_violation_message_is_idempotent(self):
        first = hash_violation_message("import os")
        assert first.startswith("sha256:")
        assert hash_violation_message(first) == first

    def test_get_violation_message_hashes_description_without_hook(self):
        finding = _SnippetFinding(
            "a.py", 1, description=f"secret {_FAKE_SECRET}"
        )
        identity = get_violation_message(finding)
        assert _FAKE_SECRET not in identity
        assert identity == hash_violation_message(f"secret {_FAKE_SECRET}")

    def test_get_violation_message_hashes_code_snippet_without_hook(self):
        finding = _SnippetFinding(
            "a.py", 1, code_snippet=f'api_key = "{_FAKE_SECRET}"'
        )
        identity = get_violation_message(finding)
        assert _FAKE_SECRET not in identity
        assert identity == hash_violation_message(f'api_key = "{_FAKE_SECRET}"')

    def test_redaction_hook_can_replace_sensitive_text(self):
        finding = _SnippetFinding(
            "a.py", 1, description=f"secret {_FAKE_SECRET}"
        )

        def redact(attr, value):
            assert attr == "description"
            assert _FAKE_SECRET in value
            return "credential:redacted"

        assert get_violation_message(finding, redact=redact) == "credential:redacted"

    def test_secret_in_description_not_stored_in_baseline_json(self, tmp_path):
        src = str(tmp_path / "config.py")
        finding = _SnippetFinding(
            src, 3, description=f"hardcoded credential {_FAKE_SECRET}"
        )
        manager = BaselineManager(project_path=tmp_path)
        assert manager.create_from_violations([finding], "lint") == 1

        on_disk = manager.baseline_path.read_text(encoding="utf-8")
        assert _FAKE_SECRET not in on_disk
        payload = json.loads(on_disk)
        stored = payload["entries"][0]["message"]
        assert stored == hash_violation_message(f"hardcoded credential {_FAKE_SECRET}")

    def test_secret_in_code_snippet_not_stored_in_baseline_json(self, tmp_path):
        src = str(tmp_path / "config.py")
        finding = _SnippetFinding(
            src, 4, code_snippet=f'api_key = "{_FAKE_SECRET}"'
        )
        manager = BaselineManager(project_path=tmp_path)
        assert manager.create_from_violations([finding], "lint") == 1

        on_disk = manager.baseline_path.read_text(encoding="utf-8")
        assert _FAKE_SECRET not in on_disk
        assert "api_key" not in on_disk

    def test_message_attr_secret_not_stored_in_baseline_json(self, tmp_path):
        manager = BaselineManager(project_path=tmp_path)
        assert manager.add_entry(
            file_path=str(tmp_path / "a.py"),
            line_number=1,
            violation_type="lint",
            message=f"found {_FAKE_SECRET}",
        )
        on_disk = manager.baseline_path.read_text(encoding="utf-8")
        assert _FAKE_SECRET not in on_disk
        payload = json.loads(on_disk)
        assert payload["entries"][0]["message"] == hash_violation_message(
            f"found {_FAKE_SECRET}"
        )

    def test_secret_not_in_default_json_report(self, tmp_path):
        src = str(tmp_path / "config.py")
        finding = _SnippetFinding(
            src,
            5,
            description=f"hardcoded credential {_FAKE_SECRET}",
            code_snippet=f'api_key = "{_FAKE_SECRET}"',
        )
        manager = BaselineManager(project_path=tmp_path)
        manager.create_from_violations([finding], "lint")

        report = manager.generate_report("json")
        parsed = json.loads(report)
        assert _FAKE_SECRET not in report
        assert "message" not in parsed["entries"][0]

    def test_hashed_identity_still_suppresses_same_finding(self, tmp_path):
        src = str(tmp_path / "config.py")
        finding = _SnippetFinding(
            src, 6, description=f"hardcoded credential {_FAKE_SECRET}"
        )
        later = _SnippetFinding(
            src, 9, description=f"other finding {_FAKE_SECRET}_other"
        )
        manager = BaselineManager(project_path=tmp_path)
        manager.create_from_violations([finding], "lint")

        remaining = manager.filter_violations([finding, later], "lint")
        assert remaining == [later]

        shifted = _SnippetFinding(
            src, 99, description=f"hardcoded credential {_FAKE_SECRET}"
        )
        still_baselined = manager.filter_violations(
            [shifted], "lint", use_fuzzy_matching=True
        )
        assert still_baselined == []

    def test_cli_json_list_and_show_omit_secret(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setenv("ASGARD_BASELINE_HMAC_KEY", "test-baseline-key")
        src = str(tmp_path / "config.py")
        finding = _SnippetFinding(
            src,
            7,
            description=f"hardcoded credential {_FAKE_SECRET}",
            code_snippet=f'api_key = "{_FAKE_SECRET}"',
        )
        manager = BaselineManager(project_path=tmp_path)
        manager.create_from_violations([finding], "lint")

        assert run_baseline_command(_baseline_cli_args(tmp_path, "list")) == 0
        listed = capsys.readouterr().out
        assert _FAKE_SECRET not in listed
        listed_payload = json.loads(listed)
        assert "message" not in listed_payload[0]

        assert run_baseline_command(_baseline_cli_args(tmp_path, "show")) == 0
        shown = capsys.readouterr().out
        assert _FAKE_SECRET not in shown
        shown_payload = json.loads(shown)
        assert "message" not in shown_payload["entries"][0]
