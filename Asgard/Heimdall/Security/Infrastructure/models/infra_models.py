"""
Heimdall Security Infrastructure Models

Pydantic models for infrastructure security analysis operations and results.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from Asgard.Heimdall.Security.models.security_models import SecuritySeverity


class InfraFindingType(str, Enum):
    """Types of infrastructure security findings."""
    DEFAULT_CREDENTIALS = "default_credentials"
    DEBUG_MODE = "debug_mode"
    PERMISSIVE_HOSTS = "permissive_hosts"
    EXPOSED_DEBUG_ENDPOINT = "exposed_debug_endpoint"
    INSECURE_DEFAULT = "insecure_default"
    WORLD_WRITABLE = "world_writable"
    CORS_ALLOW_ALL = "cors_allow_all"
    INSECURE_TRANSPORT = "insecure_transport"
    MISSING_SECURITY_HEADER = "missing_security_header"
    EXPOSED_ADMIN_INTERFACE = "exposed_admin_interface"
    WEAK_CREDENTIAL_PATTERN = "weak_credential_pattern"
    HARDCODED_SECRET_KEY = "hardcoded_secret_key"
    VERBOSE_ERROR_MESSAGES = "verbose_error_messages"
    DISABLED_SECURITY_FEATURE = "disabled_security_feature"


class InfraFinding(BaseModel):
    """A detected infrastructure security issue."""
    file_path: str = Field(..., description="Path to the file containing the issue")
    line_number: int = Field(..., description="Line number where the issue was found")
    column_start: int = Field(0, description="Column where the issue starts")
    column_end: int = Field(0, description="Column where the issue ends")
    finding_type: InfraFindingType = Field(..., description="Type of infrastructure issue")
    severity: SecuritySeverity = Field(..., description="Severity of the finding")
    title: str = Field(..., description="Short title describing the issue")
    description: str = Field(..., description="Detailed description of the infrastructure issue")
    code_snippet: str = Field("", description="The problematic code snippet")
    config_key: Optional[str] = Field(None, description="Configuration key if applicable")
    current_value: Optional[str] = Field(None, description="Current insecure value")
    recommended_value: Optional[str] = Field(None, description="Recommended secure value")
    cwe_id: Optional[str] = Field(None, description="CWE ID if applicable")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    remediation: str = Field("", description="Suggested remediation steps")
    references: List[str] = Field(default_factory=list, description="Reference URLs")

    class Config:
        use_enum_values = True


class InfraConfig(BaseModel):
    """Configuration for infrastructure security scanning."""
    scan_path: Path = Field(default_factory=lambda: Path("."), description="Root path to scan")
    check_credentials: bool = Field(True, description="Check for default/weak credentials")
    check_debug_mode: bool = Field(True, description="Check for debug mode in production")
    check_hosts: bool = Field(True, description="Check for permissive host settings")
    check_endpoints: bool = Field(True, description="Check for exposed debug endpoints")
    check_permissions: bool = Field(True, description="Check for insecure file permissions")
    check_cors: bool = Field(True, description="Check for CORS misconfigurations")
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
    default_credentials: List[tuple] = Field(
        default_factory=lambda: [
            ("admin", "admin"),
            ("admin", "password"),
            ("admin", "123456"),
            ("root", "root"),
            ("root", "password"),
            ("root", "toor"),
            ("user", "user"),
            ("user", "password"),
            ("test", "test"),
            ("guest", "guest"),
            ("demo", "demo"),
            ("administrator", "administrator"),
            ("postgres", "postgres"),
            ("mysql", "mysql"),
            ("sa", "sa"),
            ("oracle", "oracle"),
        ],
        description="Known default credential pairs to detect"
    )
    debug_endpoints: List[str] = Field(
        default_factory=lambda: [
            "/debug",
            "/_debug",
            "/debug/",
            "/_internal",
            "/__debug__",
            "/profiler",
            "/_profiler",
            "/phpinfo",
            "/server-status",
            "/server-info",
            "/.env",
            "/config",
            "/settings",
            # Note: /actuator and /metrics are excluded as they are common production
            # endpoints (Spring Boot, Prometheus). They should be secured but are not
            # inherently debug endpoints.
            # /health is excluded - it's a standard Kubernetes/load balancer endpoint
            "/trace",
            "/dump",
            "/env",
        ],
        description="Debug endpoints to detect (actual debug/diagnostic endpoints only)"
    )
    config_files: List[str] = Field(
        default_factory=lambda: [
            "settings.py",
            "config.py",
            "configuration.py",
            ".env",
            "application.yml",
            "application.yaml",
            "application.properties",
            "config.yml",
            "config.yaml",
            "docker-compose.yml",
            "docker-compose.yaml",
            "Dockerfile",
            "nginx.conf",
            "apache.conf",
            "httpd.conf",
            ".htaccess",
            "web.config",
            "appsettings.json",
            "settings.json",
        ],
        description="Configuration file names to prioritize"
    )

    class Config:
        use_enum_values = True


class InfraReport(BaseModel):
    """Report from infrastructure security analysis."""
    scan_path: str = Field(..., description="Root path that was scanned")
    total_files_scanned: int = Field(0, description="Number of files scanned")
    total_config_files: int = Field(0, description="Number of configuration files scanned")
    total_issues: int = Field(0, description="Total infrastructure issues found")
    critical_issues: int = Field(0, description="Critical severity issues")
    high_issues: int = Field(0, description="High severity issues")
    medium_issues: int = Field(0, description="Medium severity issues")
    low_issues: int = Field(0, description="Low severity issues")
    findings: List[InfraFinding] = Field(default_factory=list, description="List of findings")
    credential_issues: int = Field(0, description="Credential-related issues found")
    config_issues: int = Field(0, description="Configuration-related issues found")
    hardening_issues: int = Field(0, description="Hardening-related issues found")
    scan_duration_seconds: float = Field(0.0, description="Duration of the scan")
    scanned_at: datetime = Field(default_factory=datetime.now, description="When the scan was performed")
    infra_score: float = Field(100.0, ge=0.0, le=100.0, description="Infrastructure security score (0-100)")

    class Config:
        use_enum_values = True

    def add_finding(self, finding: InfraFinding) -> None:
        """Add an infrastructure finding to the report."""
        self.total_issues += 1
        self.findings.append(finding)
        self._increment_severity_count(finding.severity)
        self._increment_type_count(finding.finding_type)
        self._calculate_infra_score()

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

    def _increment_type_count(self, finding_type: str) -> None:
        """Increment the count for a finding type category."""
        credential_types = [
            InfraFindingType.DEFAULT_CREDENTIALS.value,
            InfraFindingType.WEAK_CREDENTIAL_PATTERN.value,
            InfraFindingType.HARDCODED_SECRET_KEY.value,
        ]
        config_types = [
            InfraFindingType.DEBUG_MODE.value,
            InfraFindingType.PERMISSIVE_HOSTS.value,
            InfraFindingType.CORS_ALLOW_ALL.value,
            InfraFindingType.INSECURE_DEFAULT.value,
            InfraFindingType.VERBOSE_ERROR_MESSAGES.value,
        ]
        hardening_types = [
            InfraFindingType.EXPOSED_DEBUG_ENDPOINT.value,
            InfraFindingType.WORLD_WRITABLE.value,
            InfraFindingType.INSECURE_TRANSPORT.value,
            InfraFindingType.MISSING_SECURITY_HEADER.value,
            InfraFindingType.EXPOSED_ADMIN_INTERFACE.value,
            InfraFindingType.DISABLED_SECURITY_FEATURE.value,
        ]

        if finding_type in credential_types:
            self.credential_issues += 1
        elif finding_type in config_types:
            self.config_issues += 1
        elif finding_type in hardening_types:
            self.hardening_issues += 1

    def _calculate_infra_score(self) -> None:
        """Calculate the overall infrastructure security score."""
        score = 100.0
        score -= self.critical_issues * 25
        score -= self.high_issues * 10
        score -= self.medium_issues * 5
        score -= self.low_issues * 1
        self.infra_score = max(0.0, score)

    @property
    def has_issues(self) -> bool:
        """Check if any infrastructure issues were found."""
        return self.total_issues > 0

    @property
    def is_healthy(self) -> bool:
        """Check if the infrastructure scan is healthy."""
        return self.critical_issues == 0 and self.high_issues == 0

    def get_findings_by_type(self) -> Dict[str, List[InfraFinding]]:
        """Group findings by type."""
        result: Dict[str, List[InfraFinding]] = {}
        for finding in self.findings:
            ftype = finding.finding_type
            if ftype not in result:
                result[ftype] = []
            result[ftype].append(finding)
        return result

    def get_findings_by_severity(self) -> Dict[str, List[InfraFinding]]:
        """Group findings by severity level."""
        result: Dict[str, List[InfraFinding]] = {
            SecuritySeverity.CRITICAL.value: [],
            SecuritySeverity.HIGH.value: [],
            SecuritySeverity.MEDIUM.value: [],
            SecuritySeverity.LOW.value: [],
            SecuritySeverity.INFO.value: [],
        }
        for finding in self.findings:
            result[finding.severity].append(finding)
        return result
