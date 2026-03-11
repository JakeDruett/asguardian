"""
Heimdall Security Access Models

Pydantic models for access control analysis operations and results.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from Asgard.Heimdall.Security.models.security_models import SecuritySeverity


class AccessFindingType(str, Enum):
    """Types of access control findings."""
    MISSING_AUTH_CHECK = "missing_auth_check"
    MISSING_ROLE_CHECK = "missing_role_check"
    OVERLY_PERMISSIVE = "overly_permissive"
    HARDCODED_ROLE_BYPASS = "hardcoded_role_bypass"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DIRECT_OBJECT_REFERENCE = "direct_object_reference"
    MISSING_OWNERSHIP_CHECK = "missing_ownership_check"
    WILDCARD_PERMISSION = "wildcard_permission"
    DEFAULT_ALLOW = "default_allow"
    INSECURE_ADMIN_CHECK = "insecure_admin_check"


class AccessFinding(BaseModel):
    """A detected access control issue."""
    file_path: str = Field(..., description="Path to the file containing the issue")
    line_number: int = Field(..., description="Line number where the issue was found")
    column_start: int = Field(0, description="Column where the issue starts")
    column_end: int = Field(0, description="Column where the issue ends")
    finding_type: AccessFindingType = Field(..., description="Type of access control issue")
    severity: SecuritySeverity = Field(..., description="Severity of the finding")
    title: str = Field(..., description="Short title describing the issue")
    description: str = Field(..., description="Detailed description of the access control issue")
    code_snippet: str = Field("", description="The problematic code snippet")
    endpoint: Optional[str] = Field(None, description="API endpoint if applicable")
    function_name: Optional[str] = Field(None, description="Function or method name")
    cwe_id: Optional[str] = Field(None, description="CWE ID if applicable")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    remediation: str = Field("", description="Suggested remediation steps")
    references: List[str] = Field(default_factory=list, description="Reference URLs")

    class Config:
        use_enum_values = True


class AccessConfig(BaseModel):
    """Configuration for access control scanning."""
    scan_path: Path = Field(default_factory=lambda: Path("."), description="Root path to scan")
    check_routes: bool = Field(True, description="Check route handlers for auth")
    check_rbac: bool = Field(True, description="Check RBAC patterns")
    check_ownership: bool = Field(True, description="Check resource ownership patterns")
    check_privilege_escalation: bool = Field(True, description="Check for privilege escalation")
    min_severity: SecuritySeverity = Field(SecuritySeverity.LOW, description="Minimum severity to report")
    exclude_patterns: List[str] = Field(
        default_factory=lambda: [
            "__pycache__",
            "node_modules",
            ".git",
            ".venv",
            "venv",
            "build",
            "dist",
            ".next",
            "coverage",
            "*.min.js",
            "*.min.css",
            # Exclude Heimdall's own security detection patterns
            "Heimdall/Security",
            "Heimdall\\Security",
            "Asgard/Heimdall",
            "Asgard\\Heimdall",
            # Exclude test files
            "*_Test",
            "*Test",
            "tests",
            "test_*",
            "Asgard_Test",
            # Exclude tool prototypes
            "_tool_prototypes",
            # Exclude package lock files
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "ui_dump.xml",
        ],
        description="Patterns to exclude from scanning"
    )
    auth_decorators: List[str] = Field(
        default_factory=lambda: [
            "login_required",
            "require_auth",
            "authenticated",
            "jwt_required",
            "token_required",
            "require_role",
            "require_permission",
            "permission_required",
            "role_required",
            "admin_required",
            "Depends",
        ],
        description="Decorator names that indicate authentication"
    )
    route_decorators: List[str] = Field(
        default_factory=lambda: [
            "route",
            "get",
            "post",
            "put",
            "delete",
            "patch",
            "api_view",
            "app.route",
            "router.get",
            "router.post",
            "router.put",
            "router.delete",
        ],
        description="Decorator names that indicate route handlers"
    )
    sensitive_endpoints: List[str] = Field(
        default_factory=lambda: [
            "admin",
            "user",
            "account",
            "profile",
            "settings",
            "delete",
            "update",
            "create",
            "modify",
            "password",
            "payment",
            "billing",
        ],
        description="Keywords indicating sensitive endpoints"
    )

    class Config:
        use_enum_values = True


class AccessReport(BaseModel):
    """Report from access control analysis."""
    scan_path: str = Field(..., description="Root path that was scanned")
    total_files_scanned: int = Field(0, description="Number of files scanned")
    total_routes_analyzed: int = Field(0, description="Number of routes analyzed")
    total_issues: int = Field(0, description="Total access control issues found")
    critical_issues: int = Field(0, description="Critical severity issues")
    high_issues: int = Field(0, description="High severity issues")
    medium_issues: int = Field(0, description="Medium severity issues")
    low_issues: int = Field(0, description="Low severity issues")
    findings: List[AccessFinding] = Field(default_factory=list, description="List of findings")
    routes_without_auth: int = Field(0, description="Routes missing authentication")
    routes_with_auth: int = Field(0, description="Routes with authentication")
    scan_duration_seconds: float = Field(0.0, description="Duration of the scan")
    scanned_at: datetime = Field(default_factory=datetime.now, description="When the scan was performed")
    access_score: float = Field(100.0, ge=0.0, le=100.0, description="Access control score (0-100)")

    class Config:
        use_enum_values = True

    def add_finding(self, finding: AccessFinding) -> None:
        """Add an access control finding to the report."""
        self.total_issues += 1
        self.findings.append(finding)
        self._increment_severity_count(finding.severity)
        self._calculate_access_score()

    def _increment_severity_count(self, severity: str) -> None:
        """Increment the count for a severity level."""
        if severity == SecuritySeverity.CRITICAL.value:
            self.critical_issues += 1
        elif severity == SecuritySeverity.HIGH.value:
            self.high_issues += 1
        elif severity == SecuritySeverity.MEDIUM.value:
            self.medium_issues += 1
        elif severity == SecuritySeverity.LOW.value:
            self.low_issues += 1

    def _calculate_access_score(self) -> None:
        """Calculate the overall access control score."""
        score = 100.0
        score -= self.critical_issues * 25
        score -= self.high_issues * 10
        score -= self.medium_issues * 5
        score -= self.low_issues * 1
        self.access_score = max(0.0, score)

    @property
    def has_issues(self) -> bool:
        """Check if any access control issues were found."""
        return self.total_issues > 0

    @property
    def is_healthy(self) -> bool:
        """Check if the access control scan is healthy."""
        return self.critical_issues == 0 and self.high_issues == 0

    def get_findings_by_type(self) -> Dict[str, List[AccessFinding]]:
        """Group findings by type."""
        result: Dict[str, List[AccessFinding]] = {}
        for finding in self.findings:
            ftype = finding.finding_type
            if ftype not in result:
                result[ftype] = []
            result[ftype].append(finding)
        return result

    def get_findings_by_severity(self) -> Dict[str, List[AccessFinding]]:
        """Group findings by severity level."""
        result: Dict[str, List[AccessFinding]] = {
            SecuritySeverity.CRITICAL.value: [],
            SecuritySeverity.HIGH.value: [],
            SecuritySeverity.MEDIUM.value: [],
            SecuritySeverity.LOW.value: [],
            SecuritySeverity.INFO.value: [],
        }
        for finding in self.findings:
            result[finding.severity].append(finding)
        return result
