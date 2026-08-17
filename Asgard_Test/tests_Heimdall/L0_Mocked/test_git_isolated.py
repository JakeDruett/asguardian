"""Tests for isolated git argv/env used against untrusted repos."""

import os

from Asgard.Shared.common._git_isolated import isolated_git_argv, isolated_git_env


class TestIsolatedGitArgv:
    def test_diff_gets_no_ext_diff_and_safe_config(self):
        argv = isolated_git_argv(["diff", "-U0", "HEAD~1", "HEAD"], repo="/tmp/repo")
        assert argv[0] == "git"
        assert "--no-pager" in argv
        assert argv[argv.index("-C") + 1] == "/tmp/repo"
        assert "-c" in argv
        assert "diff.external=" in argv
        assert "core.fsmonitor=" in argv
        assert "core.pager=" in argv
        assert "alias.diff=" in argv
        diff_at = argv.index("diff")
        assert argv[diff_at + 1] == "--no-ext-diff"
        assert argv[diff_at + 2] == "--no-textconv"
        assert argv[-3:] == ["-U0", "HEAD~1", "HEAD"]

    def test_rev_parse_does_not_get_no_ext_diff(self):
        argv = isolated_git_argv(["rev-parse", "--is-inside-work-tree"], repo="/tmp/repo")
        assert "--no-ext-diff" not in argv
        assert argv[-2:] == ["rev-parse", "--is-inside-work-tree"]


class TestIsolatedGitEnv:
    def test_clears_hostile_git_vars(self, monkeypatch):
        monkeypatch.setenv("GIT_EXTERNAL_DIFF", "/tmp/evil")
        monkeypatch.setenv("GIT_PAGER", "evil-pager")
        monkeypatch.setenv("GIT_DIR", "/tmp/hostile.git")
        monkeypatch.setenv("GIT_EXEC_PATH", "/tmp/evil-git")
        monkeypatch.setenv("GIT_WORK_TREE", "/tmp/tree")
        monkeypatch.setenv("GIT_CONFIG_PARAMETERS", "evil")
        monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
        env = isolated_git_env()
        assert "GIT_EXTERNAL_DIFF" not in env
        assert "GIT_PAGER" not in env
        assert "GIT_DIR" not in env
        assert "GIT_EXEC_PATH" not in env
        assert "GIT_WORK_TREE" not in env
        assert "GIT_CONFIG_PARAMETERS" not in env
        assert "GIT_CONFIG_COUNT" not in env
        assert env["GIT_CONFIG_NOSYSTEM"] == "1"
        assert env["GIT_CONFIG_GLOBAL"] == os.devnull
