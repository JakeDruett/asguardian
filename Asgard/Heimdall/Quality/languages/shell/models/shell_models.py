"""
Heimdall Shell Script Analysis Models

Pydantic models for shell script static analysis findings.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class ShellRuleCategory(str, Enum):
    """Categories for shell script analysis rules."""
    SECURITY = "security"
    BUG = "bug"
    STYLE = "style"
    PORTABILITY = "portability"


class ShellSeverity(str, Enum):
    """Severity levels for shell script findings."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ShellFinding(BaseModel):
    """A single finding from shell script analysis."""
    file_path: str = Field(..., description="Absolute path to the shell file containing the finding")
    line_number: int = Field(..., description="Line number where the finding occurs")
    rule_id: str = Field(..., description="Rule identifier, e.g. 'shell.eval-injection'")
    category: ShellRuleCategory = Field(..., description="Rule category")
    severity: ShellSeverity = Field(..., description="Severity level of the finding")
    title: str = Field(..., description="Short title describing the finding")
    description: str = Field(..., description="Detailed description of the finding")
    code_snippet: str = Field("", description="The code snippet that triggered the finding")
    fix_suggestion: str = Field("", description="Suggested fix for the finding")

    class Config:
        use_enum_values = True


class ShellReport(BaseModel):
    """Complete report from a shell script analysis run."""
    total_findings: int = Field(0, description="Total number of findings")
    error_count: int = Field(0, description="Number of ERROR severity findings")
    warning_count: int = Field(0, description="Number of WARNING severity findings")
    info_count: int = Field(0, description="Number of INFO severity findings")
    findings: List[ShellFinding] = Field(default_factory=list, description="All findings from the analysis")
    files_analyzed: int = Field(0, description="Number of files analyzed")
    scan_path: str = Field("", description="Root path that was scanned")
    scan_duration_seconds: float = Field(0.0, description="Time taken for the scan in seconds")
    scanned_at: datetime = Field(default_factory=datetime.now, description="When the scan was performed")

    class Config:
        use_enum_values = True

    def add_finding(self, finding: ShellFinding) -> None:
        """Add a finding and update severity counts."""
        self.findings.append(finding)
        self.total_findings += 1
        severity = finding.severity if isinstance(finding.severity, str) else finding.severity.value
        if severity == ShellSeverity.ERROR.value:
            self.error_count += 1
        elif severity == ShellSeverity.WARNING.value:
            self.warning_count += 1
        elif severity == ShellSeverity.INFO.value:
            self.info_count += 1

    @property
    def has_findings(self) -> bool:
        """Check if any findings were detected."""
        return self.total_findings > 0

    @property
    def has_errors(self) -> bool:
        """Check if any ERROR severity findings were detected."""
        return self.error_count > 0


class ShellAnalysisConfig(BaseModel):
    """Configuration for shell script analysis."""
    scan_path: Path = Field(default_factory=lambda: Path("."), description="Root path to scan")
    include_extensions: List[str] = Field(
        default_factory=lambda: [".sh", ".bash"],
        description="File extensions to include in the scan"
    )
    also_check_shebangs: bool = Field(
        True,
        description=(
            "Also analyze files with no extension that start with a bash or sh shebang: "
            "#!/bin/bash, #!/bin/sh, or #!/usr/bin/env bash"
        )
    )
    exclude_patterns: List[str] = Field(
        default_factory=lambda: [
            "node_modules",
            ".git",
            "build",
            "dist",
            "vendor",
            "__pycache__",
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

    class Config:
        use_enum_values = True

    def is_rule_enabled(self, rule_id: str) -> bool:
        """Check whether a given rule should be applied."""
        if rule_id in self.disabled_rules:
            return False
        if self.enabled_rules is not None:
            return rule_id in self.enabled_rules
        return True
