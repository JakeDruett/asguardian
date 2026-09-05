"""L3 Contract tests for the toolchain-orchestrating analyser models.

Covers the shared finding/report shape in
``Asgard.Bragi.Quality.languages.common.tool_models`` and the per-language
orchestration configs for Go, Node and Rust.

These models are the seam between an external tool (cargo clippy, cargo audit,
ESLint, npm audit, tsc, go vet/build/test, gofmt, govulncheck) and everything
downstream that consumes findings -- ratings, quality gates, issue tracking,
the CLI's report printers. Their contract is what lets those consumers treat
a clippy lint and an npm advisory identically, so it is worth pinning
explicitly rather than inferring from whichever analyser happens to be tested.
"""

import pytest
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from Asgard.Bragi.Quality.languages.common.tool_models import (
    ToolCategory,
    ToolSeverity,
    ToolFinding,
    ToolReport,
)
from Asgard.Bragi.Quality.languages.go.models.go_toolchain_models import (
    GoVetConfig,
    GoBuildConfig,
    GoFmtConfig,
    GoTestConfig,
    GoVulnConfig,
)
from Asgard.Bragi.Quality.languages.node.models.node_toolchain_models import (
    NodeLintConfig,
    NodeAuditConfig,
    NodeTypecheckConfig,
)
from Asgard.Bragi.Quality.languages.rust.models.rust_toolchain_models import (
    RustClippyConfig,
    RustAuditConfig,
)


def _finding(**overrides) -> ToolFinding:
    fields = dict(
        file_path="src/lib.rs",
        rule_id="clippy::needless_return",
        category=ToolCategory.CODE_SMELL,
        severity=ToolSeverity.WARNING,
        title="unneeded return statement",
        tool="cargo-clippy",
    )
    fields.update(overrides)
    return ToolFinding(**fields)


class TestToolFindingContract:
    def test_requires_its_identifying_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ToolFinding()

    def test_instantiates_with_required_fields(self):
        finding = _finding()
        assert finding.file_path == "src/lib.rs"
        assert finding.rule_id == "clippy::needless_return"
        assert finding.tool == "cargo-clippy"

    def test_has_model_fields(self):
        fields = set(ToolFinding.model_fields.keys())
        for name in (
            "file_path",
            "line_number",
            "column",
            "rule_id",
            "category",
            "severity",
            "title",
            "description",
            "code_snippet",
            "fix_suggestion",
            "tool",
        ):
            assert name in fields

    def test_positional_fields_default_to_zero(self):
        # 0 rather than 1: a tool that reports no position must not be
        # rendered as pointing at line 1.
        finding = _finding()
        assert finding.line_number == 0
        assert finding.column == 0

    def test_optional_text_fields_default_to_empty_strings(self):
        finding = _finding()
        assert finding.description == ""
        assert finding.code_snippet == ""
        assert finding.fix_suggestion == ""

    def test_enums_serialise_as_their_values(self):
        # use_enum_values: consumers and the JSON report printers see plain
        # strings, not Enum members.
        finding = _finding()
        assert finding.category == "code_smell"
        assert finding.severity == "warning"

    def test_rejects_an_unknown_category(self):
        with pytest.raises(ValidationError):
            _finding(category="not-a-category")

    def test_rejects_an_unknown_severity(self):
        with pytest.raises(ValidationError):
            _finding(severity="critical")


class TestToolReportContract:
    def test_instantiates_with_no_arguments(self):
        report = ToolReport()
        assert report.total_findings == 0
        assert report.findings == []

    def test_has_model_fields(self):
        fields = set(ToolReport.model_fields.keys())
        for name in (
            "total_findings",
            "error_count",
            "warning_count",
            "info_count",
            "findings",
            "files_analyzed",
            "scan_path",
            "scan_duration_seconds",
            "scanned_at",
            "language",
            "tool",
            "tool_version",
            "tools_unavailable",
            "tool_failed",
        ):
            assert name in fields

    def test_scanned_at_defaults_to_a_datetime(self):
        assert isinstance(ToolReport().scanned_at, datetime)

    def test_findings_default_is_not_shared_between_instances(self):
        first, second = ToolReport(), ToolReport()
        first.add_finding(_finding())
        assert second.findings == []

    def test_add_finding_updates_the_total_and_the_matching_counter(self):
        report = ToolReport()
        report.add_finding(_finding(severity=ToolSeverity.ERROR))
        report.add_finding(_finding(severity=ToolSeverity.WARNING))
        report.add_finding(_finding(severity=ToolSeverity.INFO))

        assert report.total_findings == 3
        assert report.error_count == 1
        assert report.warning_count == 1
        assert report.info_count == 1

    def test_has_findings_tracks_the_total(self):
        report = ToolReport()
        assert report.has_findings is False
        report.add_finding(_finding())
        assert report.has_findings is True

    def test_tool_failed_defaults_false_and_is_separate_from_an_empty_scan(self):
        # The distinction the field exists for: a scan that found nothing is
        # not the same as a tool that could not complete, and a CLI caller
        # must not report the second as a clean pass.
        empty = ToolReport()
        assert empty.tool_failed is False
        assert empty.has_findings is False

        failed = ToolReport(tool_failed=True)
        assert failed.tool_failed is True
        assert failed.has_findings is False

    def test_tools_unavailable_defaults_empty_and_accepts_reasons(self):
        report = ToolReport(tools_unavailable=["cargo-audit is not installed"])
        assert ToolReport().tools_unavailable == []
        assert report.tools_unavailable == ["cargo-audit is not installed"]
        # A partial scan is still a valid report, not a failure.
        assert report.tool_failed is False


_CONFIGS_WITH_TIMEOUT = [
    (GoVetConfig, 180),
    (GoBuildConfig, 300),
    (GoFmtConfig, 120),
    (GoTestConfig, 600),
    (GoVulnConfig, 300),
    (NodeLintConfig, 300),
    (NodeAuditConfig, 180),
    (NodeTypecheckConfig, 300),
    (RustClippyConfig, 300),
    (RustAuditConfig, 180),
]

_ALL_CONFIGS = [model for model, _ in _CONFIGS_WITH_TIMEOUT]

_CONFIGS_WITH_EXTRA_ARGS = [NodeLintConfig, RustClippyConfig]


class TestToolchainConfigContract:
    @pytest.mark.parametrize("model", _ALL_CONFIGS)
    def test_instantiates_with_no_arguments(self, model):
        # Every orchestrator config is fully defaulted: an analyser can be
        # constructed without one.
        assert model() is not None

    @pytest.mark.parametrize("model", _ALL_CONFIGS)
    def test_scan_path_defaults_to_the_current_directory(self, model):
        assert model().scan_path == Path(".")

    @pytest.mark.parametrize("model", _ALL_CONFIGS)
    def test_scan_path_is_coerced_to_a_path(self, model):
        config = model(scan_path="some/where")
        assert isinstance(config.scan_path, Path)
        assert config.scan_path == Path("some/where")

    @pytest.mark.parametrize("model", _ALL_CONFIGS)
    def test_max_findings_defaults_to_one_thousand(self, model):
        assert model().max_findings == 1000

    @pytest.mark.parametrize("model, expected", _CONFIGS_WITH_TIMEOUT)
    def test_timeout_default_matches_the_tool_it_orchestrates(self, model, expected):
        # These differ per tool on purpose -- gofmt is quick, go test is not --
        # so a shared default would be wrong for most of them.
        assert model().timeout_seconds == expected

    @pytest.mark.parametrize("model", _ALL_CONFIGS)
    def test_rejects_a_non_integer_timeout(self, model):
        with pytest.raises(ValidationError):
            model(timeout_seconds="soon")

    @pytest.mark.parametrize("model", _CONFIGS_WITH_EXTRA_ARGS)
    def test_extra_args_defaults_empty_and_is_not_shared(self, model):
        first, second = model(), model()
        assert first.extra_args == []
        first.extra_args.append("--all-targets")
        assert second.extra_args == []

    @pytest.mark.parametrize("model", _CONFIGS_WITH_EXTRA_ARGS)
    def test_extra_args_accepts_a_list_of_strings(self, model):
        config = model(extra_args=["--all-targets", "--all-features"])
        assert config.extra_args == ["--all-targets", "--all-features"]
