"""Unit tests for the shared toolchain-orchestration report/finding models."""

from Asgard.Bragi.Quality.languages.common.tool_models import (
    ToolCategory,
    ToolFinding,
    ToolReport,
    ToolSeverity,
)


def _finding(severity: ToolSeverity, rule_id: str = "some.rule") -> ToolFinding:
    return ToolFinding(
        file_path="src/main.rs",
        line_number=1,
        column=1,
        rule_id=rule_id,
        category=ToolCategory.CODE_SMELL,
        severity=severity,
        title="title",
        description="description",
        tool="cargo-clippy",
    )


class TestToolReportCounters:
    def test_add_finding_increments_total(self):
        report = ToolReport()
        report.add_finding(_finding(ToolSeverity.WARNING))
        assert report.total_findings == 1
        assert len(report.findings) == 1

    def test_add_finding_buckets_by_severity(self):
        report = ToolReport()
        report.add_finding(_finding(ToolSeverity.ERROR))
        report.add_finding(_finding(ToolSeverity.WARNING))
        report.add_finding(_finding(ToolSeverity.WARNING))
        report.add_finding(_finding(ToolSeverity.INFO))
        assert report.error_count == 1
        assert report.warning_count == 2
        assert report.info_count == 1
        assert report.total_findings == 4

    def test_has_findings_false_when_empty(self):
        report = ToolReport()
        assert report.has_findings is False

    def test_has_findings_true_after_add(self):
        report = ToolReport()
        report.add_finding(_finding(ToolSeverity.ERROR))
        assert report.has_findings is True

    def test_tools_unavailable_defaults_to_empty(self):
        report = ToolReport()
        assert report.tools_unavailable == []

    def test_tool_failed_defaults_to_false(self):
        report = ToolReport()
        assert report.tool_failed is False

    def test_dict_round_trips_all_stored_fields(self):
        report = ToolReport(scan_path="/tmp/x", language="rust", tool="cargo-clippy")
        report.add_finding(_finding(ToolSeverity.ERROR))
        payload = report.dict()
        assert payload["scan_path"] == "/tmp/x"
        assert payload["language"] == "rust"
        assert payload["tool"] == "cargo-clippy"
        assert payload["error_count"] == 1
        assert payload["total_findings"] == 1
        assert len(payload["findings"]) == 1


class TestToolFindingShape:
    def test_finding_requires_rule_id_and_title(self):
        finding = _finding(ToolSeverity.ERROR, rule_id="clippy::transmute")
        assert finding.rule_id == "clippy::transmute"
        assert finding.category == ToolCategory.CODE_SMELL
        assert finding.tool == "cargo-clippy"
