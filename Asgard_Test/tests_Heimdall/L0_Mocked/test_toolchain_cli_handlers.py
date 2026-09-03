"""Tests for the Rust/Node toolchain-orchestrating quality CLI handlers."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

import pytest

from Asgard.Bragi.Quality.languages.common.tool_models import (
    ToolCategory,
    ToolFinding,
    ToolReport,
    ToolSeverity,
)
from Asgard.Bragi.Quality.languages.common.tool_runner import ToolNotAvailableError
from Asgard.Heimdall.cli.handlers import lang_analyzers, toolchain_analyzers
from Asgard.Heimdall.cli.handlers.lang_analyzers import run_rust_analysis
from Asgard.Heimdall.cli.handlers.toolchain_analyzers import (
    run_node_audit_analysis,
    run_node_lint_analysis,
    run_node_typecheck_analysis,
    run_rust_audit_analysis,
    run_rust_clippy_analysis,
)


def _make_namespace(**kwargs):
    ns = argparse.Namespace()
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def _finding(severity=ToolSeverity.ERROR) -> ToolFinding:
    return ToolFinding(
        file_path="src/main.rs",
        line_number=1,
        column=1,
        rule_id="clippy::len_zero",
        category=ToolCategory.CODE_SMELL,
        severity=severity,
        title="length comparison to zero",
        description="detail",
        tool="cargo-clippy",
    )


class TestRunRustClippyAnalysis:
    def test_missing_path_reports_error(self, tmp_path: Path):
        args = _make_namespace(path=str(tmp_path / "nope"), format="text", timeout=60)
        assert run_rust_clippy_analysis(args) == 1

    def test_tool_not_available_prints_actionable_message_and_returns_1(self, tmp_path: Path, monkeypatch, capsys):
        def _raise(config):
            raise ToolNotAvailableError("cargo is not available. Install Rust via https://rustup.rs")

        monkeypatch.setattr(
            toolchain_analyzers.RustClippyAnalyzer, "analyze",
            lambda self, scan_path=None: _raise(None),
        )
        args = _make_namespace(path=str(tmp_path), format="text", timeout=60)
        code = run_rust_clippy_analysis(args)
        assert code == 1
        captured = capsys.readouterr()
        assert "rustup.rs" in captured.out

    def test_findings_with_errors_return_exit_1(self, tmp_path: Path, monkeypatch, capsys):
        report = ToolReport(scan_path=str(tmp_path), language="rust", tool="cargo-clippy")
        report.add_finding(_finding(ToolSeverity.ERROR))
        monkeypatch.setattr(
            toolchain_analyzers.RustClippyAnalyzer, "analyze",
            lambda self, scan_path=None: report,
        )
        args = _make_namespace(path=str(tmp_path), format="json", timeout=60)
        code = run_rust_clippy_analysis(args)
        assert code == 1
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["error_count"] == 1

    def test_only_warnings_return_exit_0(self, tmp_path: Path, monkeypatch):
        report = ToolReport(scan_path=str(tmp_path), language="rust", tool="cargo-clippy")
        report.add_finding(_finding(ToolSeverity.WARNING))
        monkeypatch.setattr(
            toolchain_analyzers.RustClippyAnalyzer, "analyze",
            lambda self, scan_path=None: report,
        )
        args = _make_namespace(path=str(tmp_path), format="text", timeout=60)
        assert run_rust_clippy_analysis(args) == 0


class TestRunRustAuditAnalysis:
    def test_tool_not_available_message_surfaces(self, tmp_path: Path, monkeypatch, capsys):
        report = ToolReport(scan_path=str(tmp_path), language="rust", tool="cargo-audit")
        report.tools_unavailable.append("cargo-audit is not installed. Install with: cargo install cargo-audit")
        monkeypatch.setattr(
            toolchain_analyzers.RustAuditAnalyzer, "analyze",
            lambda self, scan_path=None: report,
        )
        args = _make_namespace(path=str(tmp_path), format="text", timeout=60)
        code = run_rust_audit_analysis(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "cargo install cargo-audit" in captured.out


class TestRunNodeLintAnalysis:
    def test_missing_path_reports_error(self, tmp_path: Path):
        args = _make_namespace(path=str(tmp_path / "nope"), format="text", timeout=60)
        assert run_node_lint_analysis(args) == 1

    def test_tool_not_available_prints_actionable_message(self, tmp_path: Path, monkeypatch, capsys):
        def _raise(self, scan_path=None):
            raise ToolNotAvailableError("eslint is not available. Install Node.js from https://nodejs.org")

        monkeypatch.setattr(toolchain_analyzers.NodeEslintAnalyzer, "analyze", _raise)
        args = _make_namespace(path=str(tmp_path), format="text", timeout=60)
        code = run_node_lint_analysis(args)
        assert code == 1
        assert "nodejs.org" in capsys.readouterr().out


class TestRunNodeAuditAnalysis:
    def test_findings_return_exit_1(self, tmp_path: Path, monkeypatch):
        report = ToolReport(scan_path=str(tmp_path), language="node", tool="npm-audit")
        report.add_finding(ToolFinding(
            file_path="package.json", line_number=0, column=0, rule_id="npm-audit::lodash",
            category=ToolCategory.DEPENDENCY, severity=ToolSeverity.ERROR,
            title="lodash vulnerable", description="", tool="npm-audit",
        ))
        monkeypatch.setattr(
            toolchain_analyzers.NodeAuditAnalyzer, "analyze",
            lambda self, scan_path=None: report,
        )
        args = _make_namespace(path=str(tmp_path), format="text", timeout=60)
        assert run_node_audit_analysis(args) == 1


class TestRunNodeTypecheckAnalysis:
    def test_no_findings_return_exit_0(self, tmp_path: Path, monkeypatch):
        report = ToolReport(scan_path=str(tmp_path), language="node", tool="tsc")
        monkeypatch.setattr(
            toolchain_analyzers.NodeTypecheckAnalyzer, "analyze",
            lambda self, scan_path=None: report,
        )
        args = _make_namespace(path=str(tmp_path), format="text", timeout=60)
        assert run_node_typecheck_analysis(args) == 0


@pytest.fixture
def crate_dir():
    """
    A scratch directory outside pytest's own tmp tree.

    RustScanConfig's default exclude_patterns include "*/test*" and
    "*_test*", matched against each file's *full* path (see
    Asgard.Bragi.Quality.languages._confined_walk.matches_exclude). pytest's
    tmp_path always nests under a "test_<function name>0" directory, which
    trips that default and silently excludes everything -- so these tests
    use a plain tempfile.mkdtemp() directory instead.
    """
    path = Path(tempfile.mkdtemp(prefix="asgard-rustcli-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class TestRunRustPatternAnalysis:
    """The regex-based `heimdall quality rust` handler (no toolchain required)."""

    def test_missing_path_reports_error(self, crate_dir: Path):
        args = _make_namespace(path=str(crate_dir / "nope"), format="text", exclude=[], disabled_rules=[])
        assert run_rust_analysis(args) == 1

    def test_detects_unwrap_and_returns_findings(self, crate_dir: Path, capsys):
        (crate_dir / "danger.rs").write_text(
            'fn main() { let x: Option<i32> = None; let y = x.unwrap(); }\n',
            encoding="utf-8",
        )
        args = _make_namespace(path=str(crate_dir), format="json", exclude=[], disabled_rules=[])
        code = run_rust_analysis(args)
        assert code == 0  # unwrap is a WARNING-level finding, not an ERROR
        payload = json.loads(capsys.readouterr().out)
        assert payload["total_findings"] == 1

    def test_json_output_contains_finding(self, crate_dir: Path, capsys):
        (crate_dir / "danger.rs").write_text(
            'fn main() { let x: Option<i32> = None; let y = x.unwrap(); }\n',
            encoding="utf-8",
        )
        args = _make_namespace(path=str(crate_dir), format="json", exclude=[], disabled_rules=[])
        run_rust_analysis(args)
        payload = json.loads(capsys.readouterr().out)
        assert payload["total_findings"] == 1
        assert payload["findings"][0]["rule_id"] == "rust.unwrap-in-production"
        assert payload["warning_count"] == 1

    def test_hardcoded_credential_is_an_error(self, crate_dir: Path, capsys):
        (crate_dir / "danger.rs").write_text(
            'fn main() { let password = "hunter2"; }\n',
            encoding="utf-8",
        )
        args = _make_namespace(path=str(crate_dir), format="json", exclude=[], disabled_rules=[])
        code = run_rust_analysis(args)
        assert code == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["error_count"] == 1

    def test_disabled_rule_suppresses_finding(self, crate_dir: Path, capsys):
        (crate_dir / "danger.rs").write_text(
            'fn main() { let password = "hunter2"; }\n',
            encoding="utf-8",
        )
        args = _make_namespace(
            path=str(crate_dir), format="json", exclude=[],
            disabled_rules=["rust.hardcoded-credentials"],
        )
        run_rust_analysis(args)
        payload = json.loads(capsys.readouterr().out)
        assert payload["total_findings"] == 0
