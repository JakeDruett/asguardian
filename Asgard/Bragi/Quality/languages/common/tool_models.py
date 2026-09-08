"""
Shared models for toolchain-orchestrating quality analysers.

Heimdall's Python quality checks mostly reimplement analysis directly (AST
visitors, regex rules). For Rust and Node there is no equivalent need: both
ecosystems ship mature, maintained tools (cargo clippy, cargo audit, ESLint,
npm audit, tsc) that already do this analysis correctly. These models give
every analyser that orchestrates one of those external tools a single,
consistent finding/report shape, so ratings, quality gates, and issue
tracking work identically regardless of which language or tool produced the
finding.

This mirrors the shape of Asgard.Bragi.Quality.languages.javascript.models.
js_models (JSFinding/JSReport) deliberately, so the existing text/JSON
report-printing conventions used by the CLI extend to these findings with no
special-casing. It is kept as its own module rather than imported from the
javascript package because these findings come from real external tools, not
regex rules, and a future change to the regex-rule models should not have to
consider tool-orchestrated callers.
"""

from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    """Category of a tool-produced finding."""
    BUG = "bug"
    CODE_SMELL = "code_smell"
    SECURITY = "security"
    STYLE = "style"
    COMPLEXITY = "complexity"
    DEPENDENCY = "dependency"
    TYPE = "type"


class ToolSeverity(str, Enum):
    """Severity level for a tool-produced finding."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ToolFinding(BaseModel):
    """A single finding produced by an orchestrated external tool."""
    file_path: str = Field(..., description="Path to the file containing the finding")
    line_number: int = Field(0, description="1-based line number of the finding")
    column: int = Field(0, description="1-based column offset of the finding")
    rule_id: str = Field(..., description="Rule/lint/advisory identifier from the source tool")
    category: ToolCategory = Field(..., description="Finding category")
    severity: ToolSeverity = Field(..., description="Severity level")
    title: str = Field(..., description="Short human-readable summary")
    description: str = Field("", description="Full message/detail from the tool")
    code_snippet: str = Field("", description="The offending line of source, when available")
    fix_suggestion: str = Field("", description="Suggested remediation, when the tool provides one")
    tool: str = Field(..., description="The external tool that produced this finding, e.g. 'cargo-clippy'")

    class Config:
        use_enum_values = True


class ToolReport(BaseModel):
    """Complete analysis report produced by an orchestrated external tool."""
    total_findings: int = Field(0, description="Total number of findings")
    error_count: int = Field(0, description="Number of ERROR-severity findings")
    warning_count: int = Field(0, description="Number of WARNING-severity findings")
    info_count: int = Field(0, description="Number of INFO-severity findings")
    findings: List[ToolFinding] = Field(default_factory=list, description="All findings")
    files_analyzed: int = Field(0, description="Number of files the tool reported against")
    scan_path: str = Field("", description="Root path that was scanned")
    scan_duration_seconds: float = Field(0.0, description="Duration of the scan in seconds")
    scanned_at: datetime = Field(default_factory=datetime.now, description="Timestamp of the scan")
    language: str = Field("", description="Language that was analyzed, e.g. 'rust', 'node'")
    tool: str = Field("", description="The external tool orchestrated for this report")
    tool_version: str = Field("", description="Version string of the orchestrated tool, when known")
    tools_unavailable: List[str] = Field(
        default_factory=list,
        description=(
            "Human-readable reasons the scan skipped part of its work, e.g. "
            "'no Cargo.toml found' or 'cargo-audit is not installed'. Distinct "
            "from an execution failure: the report is valid but incomplete. "
            "An explicitly requested CLI check exits nonzero for this outcome."
        ),
    )
    tool_failed: bool = Field(
        False,
        description=(
            "True when the orchestrated tool was found and invoked but did not "
            "complete a real scan (crashed, timed out, or produced output the "
            "analyser could not parse). Distinct from a merely empty scan (no "
            "matching files/manifest, or the tool itself not installed): a CLI "
            "caller must not report this outcome as a clean pass."
        ),
    )

    class Config:
        use_enum_values = True

    def add_finding(self, finding: ToolFinding) -> None:
        """Append a finding and update summary counters."""
        self.findings.append(finding)
        self.total_findings += 1
        severity = finding.severity if isinstance(finding.severity, str) else finding.severity.value
        if severity == ToolSeverity.ERROR.value:
            self.error_count += 1
        elif severity == ToolSeverity.WARNING.value:
            self.warning_count += 1
        else:
            self.info_count += 1

    @property
    def has_findings(self) -> bool:
        """Return True when at least one finding exists."""
        return self.total_findings > 0
