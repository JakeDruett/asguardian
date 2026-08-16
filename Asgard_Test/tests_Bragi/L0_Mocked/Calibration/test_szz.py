"""
Tests for the Plan 05 Stage-2 SZZ bug-inducing-commit trace.

Builds tiny, real (`git init`) throwaway repos in a tmp dir - the module is
pure git subprocess, so this is the only honest way to test it without
mocking subprocess (which would just re-assert the mock).
"""

import os
import subprocess
from pathlib import Path

import pytest

from Asgard.Bragi.Calibration.models.calibration_models import SZZStatus
from Asgard.Bragi.Calibration.services import szz
from Asgard.Bragi.Calibration.services.szz import (
    MAX_COPY_DETECT_HUNKS,
    MAX_COPY_DETECT_LINES,
    MIN_FIX_COMMITS,
    _blame_inducing_commits,
    _copy_detect_for_hunks,
    _parse_unified_diff_hunks,
    _run_git,
    compute_szz,
    identify_bugfix_commits,
    is_bugfix_subject,
)
from Asgard.Shared.common._git_isolated import isolated_git_env


def _git(repo: Path, *args):
    subprocess.run(["git", "-C", str(repo)] + list(args), check=True, capture_output=True, text=True)


def _commit(repo: Path, message: str, files: dict):
    for name, content in files.items():
        (repo / name).write_text(content)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message, "--no-gpg-sign")


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "test@example.com")
    _git(r, "config", "user.name", "Test")
    return r


class TestBugfixSubjectHeuristic:
    def test_matches_fix_keywords(self):
        assert is_bugfix_subject("fix: null pointer in parser")
        assert is_bugfix_subject("Fixed crash on empty input")
        assert is_bugfix_subject("hotfix login bug")
        assert is_bugfix_subject("patch CVE-2024-1234")

    def test_does_not_match_feature_commits(self):
        assert not is_bugfix_subject("add new export endpoint")
        assert not is_bugfix_subject("refactor: extract helper")


class TestIdentifyBugfixCommits:
    def test_finds_only_fix_commits(self, repo):
        _commit(repo, "initial commit", {"a.py": "x = 1\n"})
        _commit(repo, "add feature", {"a.py": "x = 1\ny = 2\n"})
        _commit(repo, "fix: off by one", {"a.py": "x = 1\ny = 3\n"})
        commits = identify_bugfix_commits(repo)
        assert len(commits) == 1
        assert "fix" in commits[0].subject.lower()

    def test_empty_outside_git_repo(self, tmp_path):
        not_a_repo = tmp_path / "plain"
        not_a_repo.mkdir()
        assert identify_bugfix_commits(not_a_repo) == []


class TestComputeSzz:
    def test_insufficient_data_below_min_fix_commits(self, repo):
        _commit(repo, "initial commit", {"a.py": "x = 1\n"})
        _commit(repo, "fix: typo", {"a.py": "x = 2\n"})
        result = compute_szz(repo, min_fix_commits=MIN_FIX_COMMITS)
        assert result.status == SZZStatus.INSUFFICIENT_DATA
        assert result.fix_commit_count == 1

    def test_traces_inducing_commit_for_modified_line(self, repo):
        # a.py's buggy line is introduced in commit 2, then fixed in commit 3.
        _commit(repo, "initial commit", {"a.py": "def f():\n    return 1\n"})
        _commit(repo, "add bug: wrong constant", {"a.py": "def f():\n    return 42\n"})
        # Pad with enough unrelated fix commits to clear the burn-in gate.
        for i in range(MIN_FIX_COMMITS - 1):
            _commit(repo, f"fix: unrelated issue {i}", {f"noise_{i}.py": f"n = {i}\n"})
        _commit(repo, "fix: wrong constant should be 1", {"a.py": "def f():\n    return 1\n"})

        result = compute_szz(repo, min_fix_commits=MIN_FIX_COMMITS)
        assert result.status == SZZStatus.OK
        assert result.fix_commit_count >= MIN_FIX_COMMITS
        assert result.induced_commit_counts.get("a.py", 0) >= 1

    def test_pure_addition_fix_has_nothing_to_blame(self, repo):
        # A fix that only *adds* a missing null-check line has no old-side
        # line to trace back to - the module must not crash or fabricate.
        _commit(repo, "initial commit", {"a.py": "def f(x):\n    return x.value\n"})
        for i in range(MIN_FIX_COMMITS):
            _commit(repo, f"fix: guard missing case {i}", {f"noise_{i}.py": f"n = {i}\n"})
        result = compute_szz(repo, min_fix_commits=MIN_FIX_COMMITS)
        assert result.status == SZZStatus.OK  # doesn't crash; just no trace for a.py


def _synthetic_unified_diff(hunk_count: int, old_count: int = 1) -> str:
    lines = ["diff --git a/f.py b/f.py", "--- a/f.py", "+++ b/f.py"]
    for i in range(hunk_count):
        lines.append(f"@@ -{i + 1},{old_count} +{i + 1},1 @@")
        lines.extend(["-old"] * old_count)
        lines.append("+new")
    return "\n".join(lines)


def _seed_min_fix_commits(repo):
    _commit(repo, "initial commit", {"seed.py": "x = 0\n"})
    for i in range(MIN_FIX_COMMITS):
        _commit(repo, f"fix: seed issue {i}", {f"seed_{i}.py": f"n = {i}\n"})


class TestHunkParseCap:
    def test_collects_overflow_sentinel_then_stops(self):
        hunks = _parse_unified_diff_hunks(_synthetic_unified_diff(20), max_hunks=5)
        assert len(hunks) == 6
        assert all(path == "f.py" and count == 1 for path, _, count in hunks)

    def test_unlimited_when_max_hunks_is_none(self):
        hunks = _parse_unified_diff_hunks(_synthetic_unified_diff(7))
        assert len(hunks) == 7

    def test_skips_pure_additions(self):
        diff = "diff --git a/f.py b/f.py\n--- a/f.py\n+++ b/f.py\n@@ -3,0 +3,2 @@\n+new\n+new2\n"
        assert _parse_unified_diff_hunks(diff) == []


class TestCopyDetectBudget:
    def test_enabled_for_small_diff(self):
        assert _copy_detect_for_hunks([("a.py", 1, 1)]) is True

    def test_disabled_when_too_many_hunks(self):
        hunks = [("a.py", i + 1, 1) for i in range(MAX_COPY_DETECT_HUNKS + 1)]
        assert _copy_detect_for_hunks(hunks) is False

    def test_disabled_when_hunk_is_tall(self):
        assert _copy_detect_for_hunks([("a.py", 1, MAX_COPY_DETECT_LINES + 1)]) is False

    def test_blame_argv_omits_c_when_disabled(self, repo, monkeypatch):
        captured = []

        def fake_run(_repo, args, timeout=60):
            captured.append(args)
            return None

        monkeypatch.setattr(szz, "_run_git", fake_run)
        _blame_inducing_commits(repo, "abc", "a.py", 1, 1, copy_detect=False)
        assert captured
        assert captured[0][:2] == ["blame", "-w"]
        assert "-C" not in captured[0]

    def test_blame_argv_includes_c_by_default(self, repo, monkeypatch):
        captured = []

        def fake_run(_repo, args, timeout=60):
            captured.append(args)
            return None

        monkeypatch.setattr(szz, "_run_git", fake_run)
        _blame_inducing_commits(repo, "abc", "a.py", 1, 1)
        assert "-C" in captured[0]


class TestBlameProcessBudget:
    def test_hunk_cap_returns_insufficient_data_without_blaming(self, repo, monkeypatch):
        _seed_min_fix_commits(repo)
        blame_calls = []

        def fake_hunks(_repo, _commit, max_hunks=32):
            return [("a.py", i + 1, 1) for i in range(max_hunks + 1)]

        def fake_blame(*_args, **_kwargs):
            blame_calls.append(1)
            return {"a" * 40}

        monkeypatch.setattr(szz, "_fix_commit_hunks", fake_hunks)
        monkeypatch.setattr(szz, "_blame_inducing_commits", fake_blame)

        result = compute_szz(repo, min_fix_commits=MIN_FIX_COMMITS, max_hunks_per_commit=3)
        assert result.status == SZZStatus.INSUFFICIENT_DATA
        assert "hunk" in result.note.lower()
        assert blame_calls == []

    def test_total_blame_cap_returns_insufficient_data_without_blaming(self, repo, monkeypatch):
        _seed_min_fix_commits(repo)
        blame_calls = []

        def fake_hunks(_repo, _commit, max_hunks=32):
            return [("a.py", 1, 1), ("b.py", 1, 1)]

        def fake_blame(*_args, **_kwargs):
            blame_calls.append(1)
            return {"a" * 40}

        monkeypatch.setattr(szz, "_fix_commit_hunks", fake_hunks)
        monkeypatch.setattr(szz, "_blame_inducing_commits", fake_blame)

        result = compute_szz(
            repo,
            min_fix_commits=MIN_FIX_COMMITS,
            max_hunks_per_commit=8,
            max_blame_calls=1,
        )
        assert result.status == SZZStatus.INSUFFICIENT_DATA
        assert "blame budget" in result.note.lower()
        assert blame_calls == []

    def test_wide_diff_skips_copy_detect(self, repo, monkeypatch):
        _seed_min_fix_commits(repo)
        flags = []

        def fake_hunks(_repo, _commit, max_hunks=32):
            return [("a.py", i + 1, 1) for i in range(MAX_COPY_DETECT_HUNKS + 1)]

        def fake_blame(*_args, **kwargs):
            flags.append(kwargs.get("copy_detect", True))
            return set()

        monkeypatch.setattr(szz, "_fix_commit_hunks", fake_hunks)
        monkeypatch.setattr(szz, "_blame_inducing_commits", fake_blame)

        result = compute_szz(
            repo,
            min_fix_commits=MIN_FIX_COMMITS,
            max_hunks_per_commit=MAX_COPY_DETECT_HUNKS + 2,
            max_blame_calls=200,
        )
        assert result.status == SZZStatus.OK
        assert flags
        assert all(flag is False for flag in flags)

    def test_small_diff_keeps_copy_detect(self, repo, monkeypatch):
        _seed_min_fix_commits(repo)
        flags = []

        def fake_hunks(_repo, _commit, max_hunks=32):
            return [("a.py", 1, 1)]

        def fake_blame(*_args, **kwargs):
            flags.append(kwargs.get("copy_detect", True))
            return set()

        monkeypatch.setattr(szz, "_fix_commit_hunks", fake_hunks)
        monkeypatch.setattr(szz, "_blame_inducing_commits", fake_blame)

        result = compute_szz(repo, min_fix_commits=MIN_FIX_COMMITS)
        assert result.status == SZZStatus.OK
        assert flags
        assert all(flag is True for flag in flags)


class TestGitIsolation:
    def test_diff_external_is_not_executed(self, repo, tmp_path, monkeypatch):
        sentinel = tmp_path / "pwned"
        script = tmp_path / "evil.sh"
        script.write_text("#!/bin/sh\nprintf x > \"$SENTINEL\"\n")
        script.chmod(0o755)
        monkeypatch.setenv("SENTINEL", str(sentinel))

        _commit(repo, "initial commit", {"a.py": "x = 1\n"})
        _commit(repo, "fix: typo", {"a.py": "x = 2\n"})
        _git(repo, "config", "diff.external", str(script))

        subprocess.run(
            ["git", "-C", str(repo), "diff", "HEAD~1", "HEAD"],
            check=False, capture_output=True, text=True,
            env={**os.environ, "SENTINEL": str(sentinel)},
        )
        assert sentinel.exists(), "control: unisolated git must honor diff.external"
        sentinel.unlink()

        out = _run_git(repo, ["diff", "-U0", "--no-color", "HEAD~1", "HEAD"])
        assert not sentinel.exists()
        assert out is not None
        assert "a.py" in out

    def test_git_external_diff_env_is_cleared(self, repo, tmp_path, monkeypatch):
        sentinel = tmp_path / "pwned"
        script = tmp_path / "evil.sh"
        script.write_text("#!/bin/sh\nprintf x > \"$SENTINEL\"\n")
        script.chmod(0o755)
        monkeypatch.setenv("SENTINEL", str(sentinel))
        monkeypatch.setenv("GIT_EXTERNAL_DIFF", str(script))
        monkeypatch.setenv("GIT_PAGER", str(script))
        monkeypatch.setenv("GIT_DIR", str(repo / ".git"))

        env = isolated_git_env()
        assert "GIT_EXTERNAL_DIFF" not in env
        assert "GIT_PAGER" not in env
        assert "GIT_DIR" not in env
        assert env["GIT_CONFIG_NOSYSTEM"] == "1"

        _commit(repo, "initial commit", {"a.py": "x = 1\n"})
        _commit(repo, "fix: typo", {"a.py": "x = 2\n"})
        out = _run_git(repo, ["diff", "-U0", "--no-color", "HEAD~1", "HEAD"])
        assert not sentinel.exists()
        assert out is not None
        assert "a.py" in out
