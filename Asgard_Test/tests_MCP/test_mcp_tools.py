"""
Tests for Asgard MCP Server tool implementations (_mcp_tools).

L0 behavior tests: each tool handler is exercised against a small real
fixture project on disk (no network), or against injected test doubles
where the tool would otherwise touch shared state (issue tracker DB).
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

import Asgard.MCP.server._mcp_tools as mcp_tools
from Asgard.MCP.models.mcp_models import MCPServerConfig
from Asgard.MCP.server._mcp_tools import (
    _COMPLIANCE_EXTRACTORS,
    _extract_cwe_compliance,
    _extract_owasp_compliance,
    tool_compliance_report,
    tool_list_issues,
    tool_quality_analyze,
    tool_quality_gate,
    tool_ratings,
    tool_sbom,
    tool_security_scan,
)


@pytest.fixture(scope="module")
def fixture_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """
    Create a tiny but real Python project to scan.

    Uses tmp_path_factory with a neutral name because the security scanner
    excludes any path containing a 'test_*' component, and per-test tmp_path
    directories are named after the test function.
    """
    tmp_path = tmp_path_factory.mktemp("mcp_fixture_proj")
    (tmp_path / "clean.py").write_text(
        '"""A clean module."""\n\n\ndef add(a: int, b: int) -> int:\n    return a + b\n',
        encoding="utf-8",
    )
    (tmp_path / "risky.py").write_text(
        '"""A module with an obvious security issue."""\n\n'
        "import subprocess\n\n\n"
        "def run(cmd: str) -> None:\n"
        "    subprocess.call(cmd, shell=True)\n\n\n"
        'PASSWORD = "hunter2secret"\n',
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def config(fixture_project: Path) -> MCPServerConfig:
    return MCPServerConfig(project_path=str(fixture_project))


class TestToolQualityAnalyze:
    def test_uses_config_path_when_params_empty(self, config, fixture_project):
        result = tool_quality_analyze({}, config)
        assert result["scan_path"] == str(fixture_project.resolve())

    def test_params_path_overrides_config(self, config, fixture_project):
        nested = fixture_project / "nested"
        nested.mkdir()
        (nested / "m.py").write_text("x = 1\n", encoding="utf-8")
        result = tool_quality_analyze({"path": str(nested)}, config)
        assert result["scan_path"] == str(nested.resolve())

    def test_reports_analyzed_files(self, config):
        result = tool_quality_analyze({}, config)
        assert result["total_files"] >= 2
        assert isinstance(result["total_violations"], int)
        assert isinstance(result["top_violations"], list)

    def test_result_has_timestamp(self, config):
        result = tool_quality_analyze({}, config)
        assert "analyzed_at" in result and result["analyzed_at"]


class TestToolSecurityScan:
    def test_finds_issues_in_risky_code(self, config):
        result = tool_security_scan({}, config)
        assert result["total_findings"] >= 1
        assert len(result["top_findings"]) >= 1

    def test_top_findings_shape(self, config):
        result = tool_security_scan({}, config)
        finding = result["top_findings"][0]
        assert set(finding) == {"file", "line", "title", "severity", "type"}

    def test_top_findings_capped_at_ten(self, config):
        result = tool_security_scan({}, config)
        assert len(result["top_findings"]) <= 10

    def test_scan_path_resolved(self, config, fixture_project):
        result = tool_security_scan({}, config)
        assert result["scan_path"] == str(fixture_project.resolve())


class TestToolQualityGate:
    def test_gate_result_shape(self, config):
        result = tool_quality_gate({}, config)
        assert isinstance(result["passed"], bool)
        assert result["status"]
        assert isinstance(result["conditions"], list)
        assert result["gate_name"]

    def test_conditions_have_metric_and_status(self, config):
        result = tool_quality_gate({}, config)
        assert result["conditions"], "default gate should evaluate at least one condition"
        for cond in result["conditions"]:
            assert cond["metric"]
            assert cond["status"]


class TestToolRatings:
    def test_ratings_axes_present(self, config):
        result = tool_ratings({}, config)
        for axis in ("maintainability", "reliability", "security"):
            assert result[axis]["rating"] in list("ABCDE")

    def test_overall_rating_is_letter(self, config):
        result = tool_ratings({}, config)
        assert result["overall_rating"] in list("ABCDE")


class TestToolSbom:
    def test_default_format_is_cyclonedx(self, config):
        doc = tool_sbom({}, config)
        assert doc.get("bomFormat") == "CycloneDX"

    def test_spdx_format_selected(self, config):
        doc = tool_sbom({"format": "spdx"}, config)
        assert "spdxVersion" in doc

    def test_cyclonedx_includes_declared_dependency(self, config):
        doc = tool_sbom({"format": "cyclonedx"}, config)
        names = {c.get("name") for c in doc.get("components", [])}
        assert "requests" in names


class _FakeTracker:
    """IssueTracker double capturing the filter and returning canned issues."""

    def __init__(self, issues):
        self._issues = issues
        self.last_project_path = None
        self.last_filter = None

    def get_issues(self, project_path, issue_filter=None):
        self.last_project_path = project_path
        self.last_filter = issue_filter
        return self._issues


class TestToolListIssues:
    def _install(self, monkeypatch, issues):
        tracker = _FakeTracker(issues)
        monkeypatch.setattr(mcp_tools, "IssueTracker", lambda: tracker)
        return tracker

    def test_invalid_status_falls_back_to_open(self, monkeypatch, config):
        tracker = self._install(monkeypatch, [])
        tool_list_issues({"status": "bogus"}, config)
        assert list(tracker.last_filter.status) == ["open"]

    def test_limit_caps_returned_issues(self, monkeypatch, config):
        issues = [
            SimpleNamespace(
                issue_id=f"id-{i}", rule_id="R1", file_path="f.py", line_number=i,
                severity="low", status="open", title=f"t{i}", created_at="",
            )
            for i in range(10)
        ]
        self._install(monkeypatch, issues)
        result = tool_list_issues({"limit": "5"}, config)
        assert result["total_returned"] == 5

    def test_project_path_resolved_and_passed(self, monkeypatch, config, fixture_project):
        tracker = self._install(monkeypatch, [])
        tool_list_issues({}, config)
        assert tracker.last_project_path == str(fixture_project.resolve())

    def test_issues_serialized(self, monkeypatch, config):
        issue = SimpleNamespace(
            issue_id="abc-123",
            rule_id="R001",
            file_path="src/x.py",
            line_number=7,
            severity="high",
            status="open",
            title="Something",
            created_at="2026-01-01T00:00:00",
        )
        self._install(monkeypatch, [issue])
        result = tool_list_issues({}, config)
        assert result["total_returned"] == 1
        assert result["issues"][0]["issue_id"] == "abc-123"
        assert result["issues"][0]["line_number"] == 7

    def test_empty_result(self, monkeypatch, config):
        self._install(monkeypatch, [])
        result = tool_list_issues({}, config)
        assert result["total_returned"] == 0
        assert result["issues"] == []


class TestComplianceExtractors:
    def _owasp_report(self):
        cat = SimpleNamespace(category_id="A01", name="Broken Access Control",
                              grade="B", finding_count=2)
        return SimpleNamespace(owasp_compliance=SimpleNamespace(
            categories=[cat], overall_grade="B"))

    def _cwe_report(self):
        cat = SimpleNamespace(cwe_id="CWE-79", name="XSS", grade="C", finding_count=1)
        return SimpleNamespace(cwe_compliance=SimpleNamespace(
            categories=[cat], overall_grade="C"))

    def test_owasp_extractor_returns_none_without_data(self):
        assert _extract_owasp_compliance(SimpleNamespace()) is None

    def test_cwe_extractor_returns_none_without_data(self):
        assert _extract_cwe_compliance(SimpleNamespace()) is None

    def test_owasp_extraction(self):
        data = _extract_owasp_compliance(self._owasp_report())
        assert data["overall_grade"] == "B"
        assert data["owasp_top10"]["A01"]["finding_count"] == 2

    def test_cwe_extraction(self):
        data = _extract_cwe_compliance(self._cwe_report())
        assert data["overall_grade"] == "C"
        assert data["cwe_top25"]["CWE-79"]["name"] == "XSS"

    def test_registry_contains_both_standards(self):
        assert set(_COMPLIANCE_EXTRACTORS) == {"owasp", "cwe"}


class TestToolComplianceReport:
    def test_unknown_standard_yields_honest_note(self, config):
        result = tool_compliance_report({"standard": "pci-dss"}, config)
        assert result["standard"] == "pci-dss"
        assert "not available" in result["note"]
        assert isinstance(result["total_findings"], int)

    def test_known_standard_without_data_yields_note(self, config):
        # The static scan result may not carry owasp compliance data;
        # either real compliance data or an honest note is acceptable,
        # but never neither.
        result = tool_compliance_report({"standard": "owasp"}, config)
        assert ("owasp_top10" in result) != ("note" in result)

    def test_extracted_data_merged(self, monkeypatch, config):
        cat = SimpleNamespace(category_id="A03", name="Injection", grade="D",
                              finding_count=4)
        fake_report = SimpleNamespace(
            owasp_compliance=SimpleNamespace(categories=[cat], overall_grade="D"),
            total_findings=4,
        )

        class _FakeService:
            def __init__(self, cfg):
                pass

            def scan(self, path):
                return fake_report

        monkeypatch.setattr(mcp_tools, "StaticSecurityService", _FakeService)
        result = tool_compliance_report({"standard": "owasp"}, config)
        assert result["overall_grade"] == "D"
        assert result["owasp_top10"]["A03"]["grade"] == "D"
        assert "note" not in result
