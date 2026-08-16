"""Tests for the incremental debt state store (Plan 02 Phase E)."""

import json
from pathlib import Path

from Asgard.Bragi.Quality.services._debt_state_store import (
    STATE_RELATIVE_PATH,
    apply_delta,
    changed_files,
    content_hash,
    load_state,
    save_state,
    DebtState,
    FileDebtState,
)
from Asgard.Bragi.Quality.services.technical_debt_analyzer import TechnicalDebtAnalyzer


def _write(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


class TestContentHash:
    def test_hash_stable_for_same_content(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "a.py", "x = 1\n")
        assert content_hash(f) == content_hash(f)

    def test_hash_changes_with_content(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "a.py", "x = 1\n")
        h1 = content_hash(f)
        _write(f, "x = 2\n")
        h2 = content_hash(f)
        assert h1 != h2

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert content_hash(tmp_path / "missing.py") is None


class TestStatePersistence:
    def test_load_missing_state_is_empty(self, tmp_path: Path) -> None:
        state = load_state(tmp_path)
        assert state.files == {}
        assert state.total_debt_minutes == 0.0

    def test_save_then_load_round_trips(self, tmp_path: Path) -> None:
        state = DebtState(scan_root=str(tmp_path), total_debt_minutes=42.0)
        state.files["a.py"] = FileDebtState(content_hash="abc", debt_minutes=42.0, item_count=1)
        save_state(tmp_path, state)
        assert (tmp_path / STATE_RELATIVE_PATH).exists()
        reloaded = load_state(tmp_path)
        assert reloaded.total_debt_minutes == 42.0
        assert reloaded.files["a.py"].content_hash == "abc"

    def test_corrupt_state_file_falls_back_to_empty(self, tmp_path: Path) -> None:
        path = tmp_path / STATE_RELATIVE_PATH
        path.parent.mkdir(parents=True)
        path.write_text("not json{{{")
        state = load_state(tmp_path)
        assert state.files == {}


class TestChangedFiles:
    def test_new_file_is_changed(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "a.py", "x = 1\n")
        result = changed_files(tmp_path, [f])
        assert f in result

    def test_unchanged_file_is_skipped(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "a.py", "x = 1\n")
        state = DebtState(scan_root=str(tmp_path))
        state.files["a.py"] = FileDebtState(content_hash=content_hash(f), debt_minutes=0.0)
        result = changed_files(tmp_path, [f], state=state)
        assert result == []

    def test_modified_file_is_changed(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "a.py", "x = 1\n")
        state = DebtState(scan_root=str(tmp_path))
        state.files["a.py"] = FileDebtState(content_hash=content_hash(f), debt_minutes=0.0)
        _write(f, "x = 2\n")
        result = changed_files(tmp_path, [f], state=state)
        assert f in result


class TestAnalyzeDelta:
    def test_only_changed_file_reprocessed_and_totals_consistent(self, tmp_path: Path) -> None:
        f1 = _write(tmp_path / "a.py", "def f():\n    pass\n")
        f2 = _write(tmp_path / "b.py", "def g():\n    pass\n")

        analyzer = TechnicalDebtAnalyzer()
        first = analyzer.analyze_delta(tmp_path)
        assert set(first.changed_files) == {"a.py", "b.py"}

        # Re-run with no changes: nothing should be reprocessed.
        second = analyzer.analyze_delta(tmp_path)
        assert second.changed_files == []
        assert second.total_debt_minutes == first.total_debt_minutes

        # Mutate one file: only it should be reprocessed.
        _write(f1, "def f():\n    '''doc'''\n    pass\n")
        third = analyzer.analyze_delta(tmp_path)
        assert third.changed_files == ["a.py"]

    def test_deleted_file_removes_its_debt(self, tmp_path: Path) -> None:
        f1 = _write(tmp_path / "a.py", "def f():\n    pass\n")
        analyzer = TechnicalDebtAnalyzer()
        first = analyzer.analyze_delta(tmp_path)
        assert first.total_debt_minutes >= 0

        f1.unlink()
        second = analyzer.analyze_delta(tmp_path)
        assert second.removed_minutes >= 0
        assert second.total_debt_minutes == 0.0

        # cleanup cache dir so it doesn't pollute other tests
        cache = tmp_path / ".asgard_cache"
        if cache.exists():
            for p in cache.iterdir():
                p.unlink()
            cache.rmdir()


class TestSignedDebtState:
    def test_unsigned_planted_state_is_full_rescan(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("ASGARD_DEBT_HMAC_KEY", "test-debt-key")
        f = _write(tmp_path / "a.py", "x = 1\n")
        digest = content_hash(f)
        cache = tmp_path / STATE_RELATIVE_PATH
        cache.parent.mkdir(parents=True)
        cache.write_text(json.dumps({
            "schema_version": 1,
            "scan_root": str(tmp_path),
            "total_debt_minutes": 0.0,
            "files": {
                "a.py": {
                    "content_hash": digest,
                    "debt_minutes": 0.0,
                    "item_count": 0,
                }
            },
        }))
        state = load_state(tmp_path)
        assert state.files == {}
        assert changed_files(tmp_path, [f], state=state) == [f]

    def test_rewritten_hashes_without_hmac_are_rejected(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("ASGARD_DEBT_HMAC_KEY", "test-debt-key")
        f = _write(tmp_path / "a.py", "x = 1\n")
        state = DebtState(scan_root=str(tmp_path), total_debt_minutes=0.0)
        state.files["a.py"] = FileDebtState(content_hash=content_hash(f), debt_minutes=0.0)
        save_state(tmp_path, state)
        data = json.loads((tmp_path / STATE_RELATIVE_PATH).read_text())
        data["files"]["a.py"]["content_hash"] = "0" * 64
        data["total_debt_minutes"] = 0.0
        (tmp_path / STATE_RELATIVE_PATH).write_text(json.dumps(data))
        loaded = load_state(tmp_path)
        assert loaded.files == {}

    def test_escape_rel_is_not_cached(self, tmp_path: Path) -> None:
        state = DebtState(scan_root=str(tmp_path))
        apply_delta(
            tmp_path,
            state,
            {"../outside.py": []},
            ["../outside.py"],
        )
        assert "../outside.py" not in state.files
