"""Required compiler failures and incomplete capped reports cannot be clean."""

import json

import pytest

from Asgard.Bragi.Quality.languages.common.tool_runner import ToolRunResult
from Asgard.Bragi.Quality.languages.go.models.go_toolchain_models import GoFmtConfig, GoVulnConfig
from Asgard.Bragi.Quality.languages.go.services import go_fmt_analyzer, go_vuln_analyzer
from Asgard.Bragi.Quality.languages.node.models.node_toolchain_models import (
    NodeAuditConfig,
    NodeLintConfig,
    NodeTypecheckConfig,
)
from Asgard.Bragi.Quality.languages.node.services import (
    node_audit_analyzer,
    node_eslint_analyzer,
    node_typecheck_analyzer,
)
from Asgard.Bragi.Quality.languages.rust.models.rust_toolchain_models import RustAuditConfig, RustClippyConfig
from Asgard.Bragi.Quality.languages.rust.services import rust_audit_analyzer, rust_clippy_analyzer
from Asgard.Heimdall.cli.handlers.toolchain_analyzers import _print_report


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text('{"name":"fixture"}')
    (tmp_path / "package-lock.json").write_text("{}")
    (tmp_path / "tsconfig.json").write_text("{}")
    (tmp_path / "eslint.config.js").write_text("export default [];\n")
    (tmp_path / "Cargo.toml").write_text('[package]\nname="fixture"\nversion="0.1.0"\n')
    (tmp_path / "Cargo.lock").write_text("version = 4\n")
    (tmp_path / "go.mod").write_text("module fixture\ngo 1.24.0\n")
    for module in (node_typecheck_analyzer, node_eslint_analyzer):
        monkeypatch.setattr(module, "resolve_node_tool", lambda name, *_: [f"/trusted/{name}"])
    for module in (rust_clippy_analyzer, node_audit_analyzer, go_fmt_analyzer):
        monkeypatch.setattr(module, "require_executable", lambda name, *_: f"/trusted/{name}")
    for module in (rust_audit_analyzer, go_vuln_analyzer):
        monkeypatch.setattr(module, "find_optional_executable", lambda name, *_: f"/trusted/{name}")
    return tmp_path


@pytest.mark.parametrize("code", [1, 2, 101, 127])
@pytest.mark.parametrize(
    "stdout,stderr",
    [
        ("", "npx failed before loading TypeScript"),
        ("error TS5083: Cannot read file tsconfig.base.json", ""),
        ("unrecognized output", ""),
        ("", ""),
    ],
)
def test_typecheck_nonzero_without_error_diagnostics_fails(project, monkeypatch, code, stdout, stderr):
    monkeypatch.setattr(node_typecheck_analyzer, "run_tool", lambda *_, **__: ToolRunResult(code, stdout, stderr))
    report = node_typecheck_analyzer.NodeTypecheckAnalyzer(NodeTypecheckConfig(scan_path=project)).analyze()
    assert report.error_count == 0
    assert report.tool_failed
    assert f"exit {code}" in report.tools_unavailable[0]
    assert _print_report(report, "test", "json", False) == 1


@pytest.mark.parametrize("code", [1, 101, 127])
@pytest.mark.parametrize(
    "stdout,stderr",
    [
        ("", "error: failed to parse manifest"),
        ("not cargo JSON", "error: registry unavailable"),
        ('{"reason":"build-finished","success":false}', ""),
        ("[]\nnull\n", ""),
        ("", ""),
    ],
)
def test_clippy_nonzero_without_compiler_error_fails(project, monkeypatch, code, stdout, stderr):
    monkeypatch.setattr(rust_clippy_analyzer, "run_tool", lambda *_, **__: ToolRunResult(code, stdout, stderr))
    report = rust_clippy_analyzer.RustClippyAnalyzer(RustClippyConfig(scan_path=project)).analyze()
    assert report.error_count == 0
    assert report.tool_failed
    assert f"exit {code}" in report.tools_unavailable[0]
    assert _print_report(report, "test", "json", False) == 1


def clippy_message(level, index):
    return json.dumps(
        {
            "reason": "compiler-message",
            "message": {
                "level": level,
                "message": f"diagnostic {index}",
                "code": {"code": f"lint-{index}"},
                "spans": [],
            },
        }
    )


@pytest.mark.parametrize("family", ["eslint", "npm-audit", "tsc", "clippy", "rust-audit", "go-vuln", "go-fmt"])
@pytest.mark.parametrize("late_error", [True, False])
@pytest.mark.parametrize("limit", [1, 1000])
def test_warning_limit_never_hides_later_error_or_claims_unseen_output_clean(
    project, monkeypatch, family, late_error, limit
):
    levels = ["warning"] * limit + ["error" if late_error else "warning"]
    if family == "eslint":
        module = node_eslint_analyzer
        output = json.dumps(
            [
                {
                    "filePath": str(project / "index.js"),
                    "messages": [
                        {"severity": 2 if level == "error" else 1, "ruleId": f"rule-{i}", "message": "diagnostic"}
                        for i, level in enumerate(levels)
                    ],
                }
            ]
        )
        analyzer = module.NodeEslintAnalyzer(NodeLintConfig(scan_path=project, max_findings=limit))
    elif family == "npm-audit":
        module = node_audit_analyzer
        output = json.dumps(
            {
                "vulnerabilities": {
                    f"package-{i}": {"severity": "high" if level == "error" else "moderate", "via": []}
                    for i, level in enumerate(levels)
                }
            }
        )
        analyzer = module.NodeAuditAnalyzer(NodeAuditConfig(scan_path=project, max_findings=limit))
    elif family == "tsc":
        module = node_typecheck_analyzer
        output = "\n".join(f"index.ts({i + 1},1): {level} TS9999: diagnostic" for i, level in enumerate(levels))
        analyzer = module.NodeTypecheckAnalyzer(NodeTypecheckConfig(scan_path=project, max_findings=limit))
    elif family == "clippy":
        module = rust_clippy_analyzer
        output = "\n".join(clippy_message(level, i) for i, level in enumerate(levels))
        analyzer = module.RustClippyAnalyzer(RustClippyConfig(scan_path=project, max_findings=limit))
    elif family == "rust-audit":
        module = rust_audit_analyzer
        output = json.dumps(
            {
                "vulnerabilities": {
                    "found": True,
                    "count": len(levels),
                    "list": [
                        {
                            "advisory": {
                                "id": f"RUSTSEC-2026-{i:04}",
                                "cvss": {"severity": "high" if level == "error" else "medium"},
                            },
                            "package": {"name": f"package-{i}", "version": "1.0.0"},
                        }
                        for i, level in enumerate(levels)
                    ],
                }
            }
        )
        analyzer = module.RustAuditAnalyzer(RustAuditConfig(scan_path=project, max_findings=limit))
    elif family == "go-vuln":
        module = go_vuln_analyzer
        output = "\n".join(
            json.dumps(
                {
                    "finding": {
                        "osv": f"GO-2026-{i}",
                        "trace": [
                            {
                                "package": "example.invalid/package",
                                "function": "Vulnerable" if level == "error" else "",
                            }
                        ],
                    }
                }
            )
            for i, level in enumerate(levels)
        )
        analyzer = module.GoVulnAnalyzer(GoVulnConfig(scan_path=project, max_findings=limit))
    else:
        module = go_fmt_analyzer
        output = "\n".join(
            f"file{i}.go:1:1: expected declaration" if level == "error" else f"file{i}.go"
            for i, level in enumerate(levels)
        )
        analyzer = module.GoFmtAnalyzer(GoFmtConfig(scan_path=project, max_findings=limit))
    code = {"rust-audit": 1, "go-vuln": 3, "go-fmt": 2 if late_error else 0}.get(family, int(late_error))
    monkeypatch.setattr(module, "run_tool", lambda *_, **__: ToolRunResult(code, output, ""))
    report = analyzer.analyze()
    assert report.total_findings == limit
    assert report.error_count == 0  # The later error was beyond the retained cap.
    assert report.tool_failed
    assert any("limit reached" in note and "unverified" in note for note in report.tools_unavailable)
    assert _print_report(report, "test", "json", False) == 1


@pytest.mark.parametrize("family", ["tsc", "clippy"])
def test_genuine_uncapped_error_stays_a_finding(project, monkeypatch, family):
    if family == "tsc":
        module = node_typecheck_analyzer
        output = "index.ts(1,1): error TS2322: wrong type"
        analyzer = module.NodeTypecheckAnalyzer(NodeTypecheckConfig(scan_path=project))
    else:
        module = rust_clippy_analyzer
        output = clippy_message("error", 1)
        analyzer = module.RustClippyAnalyzer(RustClippyConfig(scan_path=project))
    monkeypatch.setattr(module, "run_tool", lambda *_, **__: ToolRunResult(1, output, ""))
    report = analyzer.analyze()
    assert report.error_count == 1
    assert not report.tool_failed
    assert _print_report(report, "test", "json", False) == 1
