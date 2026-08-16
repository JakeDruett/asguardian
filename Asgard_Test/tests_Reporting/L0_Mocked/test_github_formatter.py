"""
Tests for the GitHub Actions formatter and its tuple-building helpers.

L0 behavior tests using lightweight report doubles (SimpleNamespace) —
asserts the exact workflow-command output GitHub Actions will parse.
"""

from pathlib import Path
from types import SimpleNamespace

from Asgard.Reporting.github_formatter import (
    Annotation,
    AnnotationLevel,
    GitHubActionsFormatter,
)


class TestAnnotationWorkflowCommand:
    def test_minimal_command(self):
        ann = Annotation(AnnotationLevel.ERROR, "src/main.py", 10, "Bad thing")
        assert ann.to_workflow_command() == "::error file=src/main.py,line=10::Bad thing"

    def test_all_optional_fields(self):
        ann = Annotation(
            AnnotationLevel.WARNING, "a.py", 5, "msg",
            title="T", end_line=7, col=3, end_col=9,
        )
        cmd = ann.to_workflow_command()
        assert cmd == "::warning file=a.py,line=5,endLine=7,col=3,endColumn=9,title=T::msg"

    def test_notice_level(self):
        ann = Annotation(AnnotationLevel.NOTICE, "a.py", 1, "info")
        assert ann.to_workflow_command().startswith("::notice ")

    def test_encodes_newline_in_file_path(self):
        ann = Annotation(AnnotationLevel.ERROR, "src/evil.py\n::set-output", 1, "x")
        cmd = ann.to_workflow_command()
        assert "\n" not in cmd
        assert "%0A" in cmd
        assert cmd.startswith("::error ")
        assert cmd.count("::") == 2

    def test_encodes_double_colon_in_message(self):
        ann = Annotation(AnnotationLevel.ERROR, "a.py", 1, "see ::error file=pwned")
        cmd = ann.to_workflow_command()
        assert "::error file=pwned" not in cmd
        assert "%3A%3A" in cmd
        assert cmd.count("\n") == 0


class TestSeverityMapping:
    def setup_method(self):
        self.fmt = GitHubActionsFormatter()

    def test_generic_severity(self):
        assert self.fmt._severity_to_level_str("critical") == "error"
        assert self.fmt._severity_to_level_str("high") == "error"
        assert self.fmt._severity_to_level_str("medium") == "warning"
        assert self.fmt._severity_to_level_str("moderate") == "warning"
        assert self.fmt._severity_to_level_str("low") == "notice"

    def test_generic_severity_from_enum_like(self):
        sev = SimpleNamespace(value="high")
        assert self.fmt._severity_to_level_str(sev) == "error"

    def test_complexity_severity(self):
        assert self.fmt._complexity_to_level_str("critical") == "error"
        assert self.fmt._complexity_to_level_str("very_high") == "error"
        assert self.fmt._complexity_to_level_str("high") == "warning"
        assert self.fmt._complexity_to_level_str("moderate") == "notice"

    def test_security_severity(self):
        assert self.fmt._security_to_level_str("critical") == "error"
        assert self.fmt._security_to_level_str("high") == "error"
        assert self.fmt._security_to_level_str("medium") == "warning"
        assert self.fmt._security_to_level_str("low") == "notice"

    def test_level_wrappers_return_enum(self):
        assert self.fmt._severity_to_level("high") is AnnotationLevel.ERROR
        assert self.fmt._complexity_to_level("high") is AnnotationLevel.WARNING
        assert self.fmt._security_to_level("low") is AnnotationLevel.NOTICE


class TestRelativePath:
    def test_path_under_base_made_relative(self, tmp_path):
        fmt = GitHubActionsFormatter(base_path=tmp_path)
        assert fmt._relative_path(str(tmp_path / "src" / "m.py")) == str(Path("src") / "m.py")

    def test_path_outside_base_unchanged(self, tmp_path):
        fmt = GitHubActionsFormatter(base_path=tmp_path / "sub")
        outside = str(tmp_path / "elsewhere.py")
        assert fmt._relative_path(outside) == outside


class TestFormatReports:
    def setup_method(self):
        self.fmt = GitHubActionsFormatter(base_path=Path("/repo"))

    def test_format_lazy_imports(self):
        report = SimpleNamespace(detected_imports=[
            SimpleNamespace(severity="high", file_path="/repo/pkg/a.py",
                            line_number=12, import_statement="import os"),
        ])
        out = self.fmt.format_lazy_imports(report)
        assert out == ("::error file=pkg/a.py,line=12,title=Lazy Import Detected"
                       "::Lazy import: import os")

    def test_format_forbidden_imports_always_error_with_column(self):
        report = SimpleNamespace(detected_violations=[
            SimpleNamespace(file_path="/repo/b.py", line_number=3, column=5,
                            module_name="requests", remediation="use wrapper"),
        ])
        out = self.fmt.format_forbidden_imports(report)
        assert out.startswith("::error file=b.py,line=3,col=5,")
        assert "Forbidden import 'requests': use wrapper" in out

    def test_format_forbidden_imports_zero_column_omitted(self):
        report = SimpleNamespace(detected_violations=[
            SimpleNamespace(file_path="/repo/b.py", line_number=3, column=0,
                            module_name="requests", remediation="fix"),
        ])
        assert "col=" not in self.fmt.format_forbidden_imports(report)

    def test_format_datetime(self):
        report = SimpleNamespace(detected_violations=[
            SimpleNamespace(severity="medium", file_path="/repo/c.py", line_number=8,
                            column=2, issue_type="utcnow", remediation="use now(tz)"),
        ])
        out = self.fmt.format_datetime(report)
        assert out == ("::warning file=c.py,line=8,col=2,title=Datetime Issue"
                       "::utcnow: use now(tz)")

    def test_format_typing_summary_passing(self):
        report = SimpleNamespace(
            is_passing=True, coverage_percentage=91.25, threshold=80.0,
            unannotated_functions=[],
        )
        out = self.fmt.format_typing(report)
        assert out.startswith("::notice ")
        assert "Typing coverage: 91.2%25 (threshold: 80.0%25)" in out

    def test_format_typing_failing_lists_functions(self):
        func = SimpleNamespace(
            severity="high", file_path="/repo/d.py", line_number=4,
            qualified_name="mod.f", missing_parameter_names=["a", "b"],
            has_return_annotation=False,
        )
        report = SimpleNamespace(
            is_passing=False, coverage_percentage=10.0, threshold=80.0,
            unannotated_functions=[func],
        )
        out = self.fmt.format_typing(report)
        lines = out.split("\n")
        assert lines[0].startswith("::error ")
        assert "missing params: a, b" in lines[1]
        assert "missing return type" in lines[1]

    def test_format_complexity_skips_low_and_moderate(self):
        funcs = [
            SimpleNamespace(cyclomatic_severity="low", cyclomatic_complexity=2,
                            name="ok", line_number=1),
            SimpleNamespace(cyclomatic_severity="critical", cyclomatic_complexity=30,
                            name="bad", line_number=9),
        ]
        report = SimpleNamespace(file_analyses=[
            SimpleNamespace(file_path="/repo/e.py", functions=funcs),
        ])
        out = self.fmt.format_complexity(report)
        assert "ok" not in out
        assert "High cyclomatic complexity (30) in 'bad'" in out
        assert out.startswith("::error ")

    def test_format_smells(self):
        report = SimpleNamespace(smells=[
            SimpleNamespace(severity="low", file_path="/repo/f.py", line_number=2,
                            smell_type="LongMethod", description="too long",
                            category="bloat"),
        ])
        out = self.fmt.format_smells(report)
        assert "title=Code Smell (bloat)" in out
        assert "LongMethod: too long" in out

    def test_format_security(self):
        report = SimpleNamespace(vulnerabilities=[
            SimpleNamespace(severity="critical", file_path="/repo/g.py", line_number=6,
                            vulnerability_type="sql_injection", description="raw query"),
        ])
        out = self.fmt.format_security(report)
        assert out.startswith("::error ")
        assert "title=Security (CRITICAL)" in out
        assert "sql_injection: raw query" in out

    def test_format_security_report_without_vulnerabilities_attr(self):
        assert self.fmt.format_security(SimpleNamespace()) == ""

    def test_empty_reports_produce_empty_output(self):
        assert self.fmt.format_lazy_imports(SimpleNamespace(detected_imports=[])) == ""
        assert self.fmt.format_smells(SimpleNamespace(smells=[])) == ""


class TestFormatSummary:
    def test_passing_summary(self):
        fmt = GitHubActionsFormatter()
        out = fmt.format_summary("My Checks", {"lint": {"passed": True, "count": 0}}, True)
        assert "## My Checks" in out
        assert "**Status:** PASS" in out
        assert "| lint | Pass (0 issues) |" in out

    def test_failing_summary(self):
        fmt = GitHubActionsFormatter()
        out = fmt.format_summary("My Checks", {"sec": {"passed": False, "count": 3}}, False)
        assert "**Status:** FAIL" in out
        assert "| sec | Fail (3 issues) |" in out

    def test_missing_result_keys_default_to_pass_zero(self):
        fmt = GitHubActionsFormatter()
        out = fmt.format_summary("T", {"x": {}}, True)
        assert "| x | Pass (0 issues) |" in out
