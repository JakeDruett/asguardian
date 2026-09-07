"""Unit tests for the shared toolchain subprocess/discovery helpers."""

import os
import stat
import subprocess
from pathlib import Path

import pytest

from Asgard.Bragi.Quality.languages.common.tool_runner import (
    ToolNotAvailableError,
    find_manifest_dirs,
    find_optional_executable,
    require_executable,
    resolve_node_tool,
    run_tool,
)


class TestRequireExecutable:
    def test_raises_actionable_error_when_missing(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("PATH", "")
        with pytest.raises(ToolNotAvailableError) as excinfo:
            require_executable("definitely-not-a-real-binary", tmp_path, "Install it from nowhere.")
        assert "Install it from nowhere." in str(excinfo.value)
        assert "definitely-not-a-real-binary" in str(excinfo.value)

    def test_returns_path_when_found_outside_scan_tree(self, tmp_path: Path, monkeypatch):
        bin_dir = tmp_path.parent / "toolbin"
        bin_dir.mkdir(exist_ok=True)
        fake = bin_dir / "fake-tool"
        fake.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
        resolved = require_executable("fake-tool", tmp_path, "unused hint")
        assert resolved == str(fake)


class TestFindOptionalExecutable:
    def test_returns_none_when_missing(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("PATH", "")
        assert find_optional_executable("cargo-audit", tmp_path) is None


class TestResolveNodeTool:
    def test_prefers_pinned_global_binary(self, tmp_path: Path, monkeypatch):
        bin_dir = tmp_path.parent / "toolbin2"
        bin_dir.mkdir(exist_ok=True)
        fake = bin_dir / "eslint"
        fake.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
        argv = resolve_node_tool("eslint", tmp_path, "install hint")
        assert argv == [str(fake)]

    def test_falls_back_to_npx_no_install(self, tmp_path: Path, monkeypatch):
        bin_dir = tmp_path.parent / "toolbin3"
        bin_dir.mkdir(exist_ok=True)
        npx = bin_dir / "npx"
        npx.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
        npx.chmod(npx.stat().st_mode | stat.S_IEXEC)
        # Only npx on PATH -- eslint itself must not be found globally, so
        # the real system PATH (which may have eslint installed) is replaced
        # rather than extended.
        monkeypatch.setenv("PATH", str(bin_dir))
        argv = resolve_node_tool("eslint", tmp_path, "install hint")
        assert argv == [str(npx), "--no-install", "eslint"]

    def test_raises_when_neither_available(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("PATH", "")
        with pytest.raises(ToolNotAvailableError) as excinfo:
            resolve_node_tool("eslint", tmp_path, "Install Node.js.")
        assert "Install Node.js." in str(excinfo.value)


class TestRunTool:
    def test_captures_stdout_and_returncode(self, tmp_path: Path):
        result = run_tool(["python3", "-c", "print('hello')"], cwd=tmp_path, timeout=10)
        assert result.returncode == 0
        assert "hello" in result.stdout
        assert result.timed_out is False

    def test_timeout_is_reported_not_raised(self, tmp_path: Path):
        result = run_tool(["python3", "-c", "import time; time.sleep(5)"], cwd=tmp_path, timeout=1)
        assert result.timed_out is True

    def test_missing_binary_does_not_raise(self, tmp_path: Path):
        result = run_tool(["definitely-not-a-real-binary-xyz"], cwd=tmp_path, timeout=5)
        assert result.returncode == -1
        assert result.stderr


class TestFindManifestDirs:
    def test_finds_manifest_at_root(self, tmp_path: Path):
        (tmp_path / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
        dirs = find_manifest_dirs(tmp_path, "Cargo.toml")
        assert dirs == [tmp_path.resolve()]

    def test_finds_manifest_in_subdirectory(self, tmp_path: Path):
        crate_dir = tmp_path / "crates" / "one"
        crate_dir.mkdir(parents=True)
        (crate_dir / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
        dirs = find_manifest_dirs(tmp_path, "Cargo.toml")
        assert dirs == [crate_dir.resolve()]

    def test_returns_empty_when_no_manifest(self, tmp_path: Path):
        (tmp_path / "readme.txt").write_text("hi\n", encoding="utf-8")
        assert find_manifest_dirs(tmp_path, "Cargo.toml") == []

    def test_does_not_descend_into_target_or_node_modules(self, tmp_path: Path):
        skipped = tmp_path / "target" / "nested"
        skipped.mkdir(parents=True)
        (skipped / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
        assert find_manifest_dirs(tmp_path, "Cargo.toml") == []
