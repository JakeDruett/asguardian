"""
Heimdall JavaScript/TypeScript Analysis Models

Pydantic models for JavaScript and TypeScript static analysis findings.
Used by both the JavaScript and TypeScript analyzers.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class JSRuleCategory(str, Enum):
    """Categories for JavaScript/TypeScript analysis rules."""
    BUG = "bug"
    CODE_SMELL = "code_smell"
    SECURITY = "security"
    STYLE = "style"
    COMPLEXITY = "complexity"


class JSSeverity(str, Enum):
    """Severity levels for JavaScript/TypeScript findings."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class JSFinding(BaseModel):
    """A single finding from JavaScript or TypeScript analysis."""
    file_path: str = Field(..., description="Absolute path to the file containing the finding")
    line_number: int = Field(..., description="Line number where the finding occurs")
    column: int = Field(0, description="Column number where the finding occurs")
    rule_id: str = Field(..., description="Rule identifier, e.g. 'js.no-var' or 'ts.no-explicit-any'")
    category: JSRuleCategory = Field(..., description="Rule category")
    severity: JSSeverity = Field(..., description="Severity level of the finding")
    title: str = Field(..., description="Short title describing the finding")
    description: str = Field(..., description="Detailed description of the finding")
    code_snippet: str = Field("", description="The code snippet that triggered the finding")
    fix_suggestion: str = Field("", description="Suggested fix for the finding")

    class Config:
        use_enum_values = True


class JSReport(BaseModel):
    """Complete report from a JavaScript or TypeScript analysis run."""
    total_findings: int = Field(0, description="Total number of findings")
    error_count: int = Field(0, description="Number of ERROR severity findings")
    warning_count: int = Field(0, description="Number of WARNING severity findings")
    info_count: int = Field(0, description="Number of INFO severity findings")
    findings: List[JSFinding] = Field(default_factory=list, description="All findings from the analysis")
    files_analyzed: int = Field(0, description="Number of files analyzed")
    scan_path: str = Field("", description="Root path that was scanned")
    scan_duration_seconds: float = Field(0.0, description="Time taken for the scan in seconds")
    scanned_at: datetime = Field(default_factory=datetime.now, description="When the scan was performed")
    language: str = Field("javascript", description="Language analyzed: 'javascript' or 'typescript'")

    class Config:
        use_enum_values = True

    def add_finding(self, finding: JSFinding) -> None:
        """Add a finding and update counts."""
        self.findings.append(finding)
        self.total_findings += 1
        severity = finding.severity if isinstance(finding.severity, str) else finding.severity.value
        if severity == JSSeverity.ERROR.value:
            self.error_count += 1
        elif severity == JSSeverity.WARNING.value:
            self.warning_count += 1
        elif severity == JSSeverity.INFO.value:
            self.info_count += 1

    @property
    def has_findings(self) -> bool:
        """Check if any findings were detected."""
        return self.total_findings > 0

    @property
    def has_errors(self) -> bool:
        """Check if any ERROR severity findings were detected."""
        return self.error_count > 0


class JSAnalysisConfig(BaseModel):
    """Configuration for JavaScript or TypeScript analysis."""
    scan_path: Path = Field(default_factory=lambda: Path("."), description="Root path to scan")
    language: str = Field("javascript", description="Language to analyze: 'javascript' or 'typescript'")
    include_extensions: List[str] = Field(
        default_factory=lambda: [".js", ".jsx"],
        description="File extensions to include in the scan"
    )
    exclude_patterns: List[str] = Field(
        default_factory=lambda: [
            "node_modules",
            ".git",
            "build",
            "dist",
            ".next",
            "coverage",
            "vendor",
        ],
        description="Path patterns to exclude from the scan"
    )
    enabled_rules: Optional[List[str]] = Field(
        None,
        description="List of rule IDs to enable. None means all rules are enabled."
    )
    disabled_rules: List[str] = Field(
        default_factory=list,
        description="List of rule IDs to disable"
    )
    max_complexity: int = Field(10, description="Maximum allowed approximate cyclomatic complexity per function")
    max_function_lines: int = Field(50, description="Maximum allowed lines per function")
    max_file_lines: int = Field(500, description="Maximum allowed lines per file")

    class Config:
        use_enum_values = True

    def is_rule_enabled(self, rule_id: str) -> bool:
        """Check whether a given rule should be applied."""
        if rule_id in self.disabled_rules:
            return False
        if self.enabled_rules is not None:
            return rule_id in self.enabled_rules
        return True
