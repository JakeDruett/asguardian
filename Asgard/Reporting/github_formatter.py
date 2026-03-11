"""
GitHub Actions Formatter

Formats analysis results in GitHub Actions workflow command format
for inline annotations in pull request diffs.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol


class AnnotationLevel(str, Enum):
    """GitHub annotation levels."""
    ERROR = "error"
    WARNING = "warning"
    NOTICE = "notice"


@dataclass
class Annotation:
    """Represents a GitHub Actions annotation."""
    level: AnnotationLevel
    file: str
    line: int
    message: str
    title: Optional[str] = None
    end_line: Optional[int] = None
    col: Optional[int] = None
    end_col: Optional[int] = None

    def to_workflow_command(self) -> str:
        """Convert to GitHub Actions workflow command format."""
        parts = [f"file={self.file}", f"line={self.line}"]

        if self.end_line:
            parts.append(f"endLine={self.end_line}")
        if self.col:
            parts.append(f"col={self.col}")
        if self.end_col:
            parts.append(f"endColumn={self.end_col}")
        if self.title:
            parts.append(f"title={self.title}")

        properties = ",".join(parts)
        return f"::{self.level.value} {properties}::{self.message}"


class ReportProtocol(Protocol):
    """Protocol for report objects that can be formatted."""
    scan_path: str
    has_violations: bool


class GitHubActionsFormatter:
    """
    Formats analysis results for GitHub Actions workflow commands.

    Outputs annotations in the format:
        ::error file=path/to/file.py,line=10::Message here
        ::warning file=path/to/file.py,line=25::Message here
        ::notice file=path/to/file.py,line=50::Message here

    These annotations appear inline in pull request diffs and the
    Actions summary view.

    Usage:
        formatter = GitHubActionsFormatter()

        # From a lazy import report
        output = formatter.format_lazy_imports(report)
        print(output)

        # From a datetime report
        output = formatter.format_datetime(report)

        # Generic formatting
        annotations = [
            Annotation(AnnotationLevel.ERROR, "src/main.py", 10, "Issue found"),
        ]
        output = formatter.format_annotations(annotations)
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize the GitHub Actions formatter.

        Args:
            base_path: Base path for making file paths relative.
                      If not provided, uses current directory.
        """
        self.base_path = base_path or Path.cwd()

    def _relative_path(self, path: str) -> str:
        """Convert absolute path to relative path."""
        try:
            return str(Path(path).relative_to(self.base_path))
        except ValueError:
            return path

    def format_annotations(self, annotations: List[Annotation]) -> str:
        """
        Format a list of annotations as workflow commands.

        Args:
            annotations: List of Annotation objects

        Returns:
            Newline-separated workflow commands
        """
        return "\n".join(ann.to_workflow_command() for ann in annotations)

    def format_lazy_imports(self, report) -> str:
        """
        Format lazy import report for GitHub Actions.

        Args:
            report: LazyImportReport object

        Returns:
            GitHub Actions workflow commands
        """
        annotations = []

        for violation in report.detected_imports:
            level = self._severity_to_level(violation.severity)
            annotations.append(Annotation(
                level=level,
                file=self._relative_path(violation.file_path),
                line=violation.line_number,
                message=f"Lazy import: {violation.import_statement}",
                title="Lazy Import Detected",
            ))

        return self.format_annotations(annotations)

    def format_forbidden_imports(self, report) -> str:
        """
        Format forbidden imports report for GitHub Actions.

        Args:
            report: ForbiddenImportReport object

        Returns:
            GitHub Actions workflow commands
        """
        annotations = []

        for violation in report.detected_violations:
            annotations.append(Annotation(
                level=AnnotationLevel.ERROR,
                file=self._relative_path(violation.file_path),
                line=violation.line_number,
                col=violation.column if violation.column else None,
                message=f"Forbidden import '{violation.module_name}': {violation.remediation}",
                title="Forbidden Import",
            ))

        return self.format_annotations(annotations)

    def format_datetime(self, report) -> str:
        """
        Format datetime usage report for GitHub Actions.

        Args:
            report: DatetimeReport object

        Returns:
            GitHub Actions workflow commands
        """
        annotations = []

        for violation in report.detected_violations:
            level = self._severity_to_level(violation.severity)
            annotations.append(Annotation(
                level=level,
                file=self._relative_path(violation.file_path),
                line=violation.line_number,
                col=violation.column if violation.column else None,
                message=f"{violation.issue_type}: {violation.remediation}",
                title="Datetime Issue",
            ))

        return self.format_annotations(annotations)

    def format_typing(self, report) -> str:
        """
        Format typing coverage report for GitHub Actions.

        Args:
            report: TypingReport object

        Returns:
            GitHub Actions workflow commands
        """
        annotations = []

        # Add summary notice
        annotations.append(Annotation(
            level=AnnotationLevel.NOTICE if report.is_passing else AnnotationLevel.ERROR,
            file=".",
            line=1,
            message=f"Typing coverage: {report.coverage_percentage:.1f}% (threshold: {report.threshold:.1f}%)",
            title="Typing Coverage Summary",
        ))

        # Add warnings for unannotated functions (limit to 50)
        for func in report.unannotated_functions[:50]:
            level = self._severity_to_level(func.severity)
            missing = ", ".join(func.missing_parameter_names) if func.missing_parameter_names else ""
            ret_msg = " (missing return type)" if not func.has_return_annotation else ""
            param_msg = f" (missing params: {missing})" if missing else ""

            annotations.append(Annotation(
                level=level,
                file=self._relative_path(func.file_path),
                line=func.line_number,
                message=f"Function '{func.qualified_name}' needs annotations{param_msg}{ret_msg}",
                title="Missing Type Annotations",
            ))

        return self.format_annotations(annotations)

    def format_complexity(self, report) -> str:
        """
        Format complexity report for GitHub Actions.

        Args:
            report: ComplexityResult object

        Returns:
            GitHub Actions workflow commands
        """
        annotations = []

        for file_analysis in report.file_analyses:
            for func in file_analysis.functions:
                if func.cyclomatic_severity not in ("low", "moderate"):
                    level = self._complexity_to_level(func.cyclomatic_severity)
                    annotations.append(Annotation(
                        level=level,
                        file=self._relative_path(file_analysis.file_path),
                        line=func.line_number,
                        message=f"High cyclomatic complexity ({func.cyclomatic_complexity}) in '{func.name}'",
                        title="Complex Function",
                    ))

        return self.format_annotations(annotations)

    def format_smells(self, report) -> str:
        """
        Format code smell report for GitHub Actions.

        Args:
            report: SmellReport object

        Returns:
            GitHub Actions workflow commands
        """
        annotations = []

        for smell in report.smells:
            level = self._severity_to_level(smell.severity)
            annotations.append(Annotation(
                level=level,
                file=self._relative_path(smell.file_path),
                line=smell.line_number,
                message=f"{smell.smell_type}: {smell.description}",
                title=f"Code Smell ({smell.category})",
            ))

        return self.format_annotations(annotations)

    def format_security(self, report) -> str:
        """
        Format security report for GitHub Actions.

        Args:
            report: SecurityScanResult object

        Returns:
            GitHub Actions workflow commands
        """
        annotations = []

        for vuln in getattr(report, 'vulnerabilities', []):
            level = self._security_to_level(vuln.severity)
            annotations.append(Annotation(
                level=level,
                file=self._relative_path(vuln.file_path),
                line=vuln.line_number,
                message=f"{vuln.vulnerability_type}: {vuln.description}",
                title=f"Security ({vuln.severity.upper()})",
            ))

        return self.format_annotations(annotations)

    def _severity_to_level(self, severity) -> AnnotationLevel:
        """Map generic severity to GitHub annotation level."""
        severity_str = severity if isinstance(severity, str) else severity.value
        if severity_str in ("high", "critical"):
            return AnnotationLevel.ERROR
        elif severity_str in ("medium", "moderate"):
            return AnnotationLevel.WARNING
        return AnnotationLevel.NOTICE

    def _complexity_to_level(self, severity_str: str) -> AnnotationLevel:
        """Map complexity severity to GitHub annotation level."""
        if severity_str in ("critical", "very_high"):
            return AnnotationLevel.ERROR
        elif severity_str == "high":
            return AnnotationLevel.WARNING
        return AnnotationLevel.NOTICE

    def _security_to_level(self, severity) -> AnnotationLevel:
        """Map security severity to GitHub annotation level."""
        severity_str = severity if isinstance(severity, str) else severity.value
        if severity_str in ("critical", "high"):
            return AnnotationLevel.ERROR
        elif severity_str == "medium":
            return AnnotationLevel.WARNING
        return AnnotationLevel.NOTICE

    def format_summary(
        self,
        title: str,
        results: Dict[str, Any],
        passed: bool,
    ) -> str:
        """
        Generate a GitHub Actions job summary.

        Args:
            title: Summary title
            results: Dictionary of check results
            passed: Whether all checks passed

        Returns:
            Markdown-formatted summary for $GITHUB_STEP_SUMMARY
        """
        status_emoji = "PASS" if passed else "FAIL"

        lines = [
            f"## {title}",
            "",
            f"**Status:** {status_emoji}",
            "",
            "| Check | Result |",
            "|-------|--------|",
        ]

        for check, result in results.items():
            status = "Pass" if result.get("passed", True) else "Fail"
            count = result.get("count", 0)
            lines.append(f"| {check} | {status} ({count} issues) |")

        return "\n".join(lines)
