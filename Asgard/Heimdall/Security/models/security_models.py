"""
Heimdall Security Analysis Models

Pydantic models for security analysis operations and results.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field


class SecuritySeverity(str, Enum):
    """Severity level for security findings."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecretType(str, Enum):
    """Types of secrets that can be detected."""
    API_KEY = "api_key"
    PASSWORD = "password"
    PRIVATE_KEY = "private_key"
    ACCESS_TOKEN = "access_token"
    SECRET_KEY = "secret_key"
    DATABASE_URL = "database_url"
    AWS_CREDENTIALS = "aws_credentials"
    AZURE_CREDENTIALS = "azure_credentials"
    GCP_CREDENTIALS = "gcp_credentials"
    JWT_TOKEN = "jwt_token"
    SSH_KEY = "ssh_key"
    CERTIFICATE = "certificate"
    OAUTH_TOKEN = "oauth_token"
    GENERIC_SECRET = "generic_secret"


class VulnerabilityType(str, Enum):
    """Types of vulnerabilities that can be detected."""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    SSRF = "ssrf"
    OPEN_REDIRECT = "open_redirect"
    INSECURE_CRYPTO = "insecure_crypto"
    HARDCODED_SECRET = "hardcoded_secret"
    INSECURE_RANDOM = "insecure_random"
    WEAK_HASH = "weak_hash"
    MISSING_AUTH = "missing_auth"
    IMPROPER_INPUT_VALIDATION = "improper_input_validation"


class DependencyRiskLevel(str, Enum):
    """Risk level for dependency vulnerabilities."""
    SAFE = "safe"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class SecretFinding(BaseModel):
    """A detected secret in the codebase."""
    file_path: str = Field(..., description="Path to the file containing the secret")
    line_number: int = Field(..., description="Line number where the secret was found")
    column_start: int = Field(0, description="Column where the secret starts")
    column_end: int = Field(0, description="Column where the secret ends")
    secret_type: SecretType = Field(..., description="Type of secret detected")
    severity: SecuritySeverity = Field(..., description="Severity of the finding")
    pattern_name: str = Field(..., description="Name of the pattern that matched")
    masked_value: str = Field(..., description="Masked version of the secret")
    line_content: str = Field(..., description="Content of the line (sanitized)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the detection")
    remediation: str = Field("", description="Suggested remediation steps")

    class Config:
        use_enum_values = True


class VulnerabilityFinding(BaseModel):
    """A detected security vulnerability in the code."""
    file_path: str = Field(..., description="Path to the file containing the vulnerability")
    line_number: int = Field(..., description="Line number of the vulnerability")
    column_start: int = Field(0, description="Column where the issue starts")
    column_end: int = Field(0, description="Column where the issue ends")
    vulnerability_type: VulnerabilityType = Field(..., description="Type of vulnerability")
    severity: SecuritySeverity = Field(..., description="Severity of the finding")
    title: str = Field(..., description="Short title describing the issue")
    description: str = Field(..., description="Detailed description of the vulnerability")
    code_snippet: str = Field("", description="The vulnerable code snippet")
    cwe_id: Optional[str] = Field(None, description="CWE ID if applicable")
    owasp_category: Optional[str] = Field(None, description="OWASP category if applicable")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    remediation: str = Field("", description="Suggested remediation steps")
    references: List[str] = Field(default_factory=list, description="Reference URLs")

    class Config:
        use_enum_values = True


class DependencyVulnerability(BaseModel):
    """A vulnerability found in a dependency."""
    package_name: str = Field(..., description="Name of the vulnerable package")
    installed_version: str = Field(..., description="Currently installed version")
    vulnerable_versions: str = Field(..., description="Version range affected")
    fixed_version: Optional[str] = Field(None, description="Version that fixes the issue")
    risk_level: DependencyRiskLevel = Field(..., description="Risk level of the vulnerability")
    cve_id: Optional[str] = Field(None, description="CVE ID if available")
    ghsa_id: Optional[str] = Field(None, description="GitHub Security Advisory ID")
    title: str = Field(..., description="Title of the vulnerability")
    description: str = Field(..., description="Detailed description")
    published_date: Optional[datetime] = Field(None, description="When the vulnerability was published")
    references: List[str] = Field(default_factory=list, description="Reference URLs")
    ecosystem: str = Field("pypi", description="Package ecosystem (pypi, npm, etc.)")

    class Config:
        use_enum_values = True


class CryptoFinding(BaseModel):
    """A cryptographic implementation issue."""
    file_path: str = Field(..., description="Path to the file")
    line_number: int = Field(..., description="Line number of the issue")
    issue_type: str = Field(..., description="Type of cryptographic issue")
    severity: SecuritySeverity = Field(..., description="Severity of the finding")
    algorithm: str = Field(..., description="Algorithm or function involved")
    description: str = Field(..., description="Description of the issue")
    recommendation: str = Field(..., description="Recommended secure alternative")
    code_snippet: str = Field("", description="The problematic code snippet")

    class Config:
        use_enum_values = True


class SecurityScanConfig(BaseModel):
    """Configuration for security scanning."""
    scan_path: Path = Field(default_factory=lambda: Path("."), description="Root path to scan")
    scan_secrets: bool = Field(True, description="Enable secrets detection")
    scan_vulnerabilities: bool = Field(True, description="Enable vulnerability scanning")
    scan_dependencies: bool = Field(True, description="Enable dependency scanning")
    scan_crypto: bool = Field(True, description="Enable cryptographic validation")
    scan_access: bool = Field(True, description="Enable access control scanning")
    scan_auth: bool = Field(True, description="Enable authentication scanning")
    scan_headers: bool = Field(True, description="Enable security headers scanning")
    scan_tls: bool = Field(True, description="Enable TLS/SSL scanning")
    scan_container: bool = Field(True, description="Enable container security scanning")
    scan_infrastructure: bool = Field(True, description="Enable infrastructure security scanning")
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
            # Exclude Heimdall's own security detection patterns (they define weak crypto to detect it)
            "Heimdall/Security",
            "Heimdall\\Security",
            "Asgard/Heimdall",
            "Asgard\\Heimdall",
            # Exclude test files (they intentionally contain vulnerable code for testing)
            "*_Test",
            "*Test",
            "tests",
            "test_*",
            "Ankh_Test",
            "Asgard_Test",
            "Hercules",
            # Exclude tool prototypes (experimental code)
            "_tool_prototypes",
            # Exclude package lock files (contain dependency hashes that look like secrets)
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            # Exclude UI dump files
            "ui_dump.xml",
        ],
        description="Patterns to exclude from scanning"
    )
    include_extensions: Optional[List[str]] = Field(
        None,
        description="File extensions to include (None = all code files)"
    )
    custom_patterns: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom regex patterns for secret detection"
    )
    ignore_paths: List[str] = Field(
        default_factory=list,
        description="Specific paths to ignore"
    )
    baseline_file: Optional[Path] = Field(
        None,
        description="Path to baseline file for ignoring known issues"
    )

    class Config:
        use_enum_values = True


class SecretsReport(BaseModel):
    """Report from secrets detection scan."""
    scan_path: str = Field(..., description="Root path that was scanned")
    total_files_scanned: int = Field(0, description="Number of files scanned")
    secrets_found: int = Field(0, description="Total secrets detected")
    findings: List[SecretFinding] = Field(default_factory=list, description="List of findings")
    scan_duration_seconds: float = Field(0.0, description="Duration of the scan")
    scanned_at: datetime = Field(default_factory=datetime.now, description="When the scan was performed")
    patterns_used: List[str] = Field(default_factory=list, description="Patterns used for detection")

    class Config:
        use_enum_values = True

    def add_finding(self, finding: SecretFinding) -> None:
        """Add a secret finding to the report."""
        self.secrets_found += 1
        self.findings.append(finding)

    @property
    def secrets(self) -> List[SecretFinding]:
        """Alias for findings for compatibility."""
        return self.findings

    @property
    def has_findings(self) -> bool:
        """Check if any secrets were found."""
        return self.secrets_found > 0

    def get_findings_by_severity(self) -> Dict[str, List[SecretFinding]]:
        """Group findings by severity level."""
        result: Dict[str, List[SecretFinding]] = {
            SecuritySeverity.CRITICAL.value: [],
            SecuritySeverity.HIGH.value: [],
            SecuritySeverity.MEDIUM.value: [],
            SecuritySeverity.LOW.value: [],
            SecuritySeverity.INFO.value: [],
        }
        for finding in self.findings:
            result[finding.severity].append(finding)
        return result


class VulnerabilityReport(BaseModel):
    """Report from vulnerability scanning."""
    scan_path: str = Field(..., description="Root path that was scanned")
    total_files_scanned: int = Field(0, description="Number of files scanned")
    vulnerabilities_found: int = Field(0, description="Total vulnerabilities detected")
    findings: List[VulnerabilityFinding] = Field(default_factory=list, description="List of findings")
    scan_duration_seconds: float = Field(0.0, description="Duration of the scan")
    scanned_at: datetime = Field(default_factory=datetime.now, description="When the scan was performed")

    class Config:
        use_enum_values = True

    def add_finding(self, finding: VulnerabilityFinding) -> None:
        """Add a vulnerability finding to the report."""
        self.vulnerabilities_found += 1
        self.findings.append(finding)

    @property
    def vulnerabilities(self) -> List[VulnerabilityFinding]:
        """Alias for findings for compatibility."""
        return self.findings

    @property
    def has_findings(self) -> bool:
        """Check if any vulnerabilities were found."""
        return self.vulnerabilities_found > 0

    def get_findings_by_type(self) -> Dict[str, List[VulnerabilityFinding]]:
        """Group findings by vulnerability type."""
        result: Dict[str, List[VulnerabilityFinding]] = {}
        for finding in self.findings:
            vtype = finding.vulnerability_type
            if vtype not in result:
                result[vtype] = []
            result[vtype].append(finding)
        return result

    def get_findings_by_severity(self) -> Dict[str, List[VulnerabilityFinding]]:
        """Group findings by severity level."""
        result: Dict[str, List[VulnerabilityFinding]] = {
            SecuritySeverity.CRITICAL.value: [],
            SecuritySeverity.HIGH.value: [],
            SecuritySeverity.MEDIUM.value: [],
            SecuritySeverity.LOW.value: [],
            SecuritySeverity.INFO.value: [],
        }
        for finding in self.findings:
            result[finding.severity].append(finding)
        return result


class DependencyReport(BaseModel):
    """Report from dependency vulnerability scanning."""
    scan_path: str = Field(..., description="Root path that was scanned")
    requirements_files: List[str] = Field(default_factory=list, description="Requirements files found")
    total_dependencies: int = Field(0, description="Total dependencies analyzed")
    vulnerable_dependencies: int = Field(0, description="Dependencies with vulnerabilities")
    vulnerabilities: List[DependencyVulnerability] = Field(default_factory=list, description="List of vulnerabilities")
    scan_duration_seconds: float = Field(0.0, description="Duration of the scan")
    scanned_at: datetime = Field(default_factory=datetime.now, description="When the scan was performed")

    class Config:
        use_enum_values = True

    def add_vulnerability(self, vuln: DependencyVulnerability) -> None:
        """Add a dependency vulnerability to the report."""
        self.vulnerabilities.append(vuln)
        unique_packages = set(v.package_name for v in self.vulnerabilities)
        self.vulnerable_dependencies = len(unique_packages)

    @property
    def has_vulnerabilities(self) -> bool:
        """Check if any vulnerabilities were found."""
        return self.vulnerable_dependencies > 0

    def get_vulnerabilities_by_risk(self) -> Dict[str, List[DependencyVulnerability]]:
        """Group vulnerabilities by risk level."""
        result: Dict[str, List[DependencyVulnerability]] = {
            DependencyRiskLevel.CRITICAL.value: [],
            DependencyRiskLevel.HIGH.value: [],
            DependencyRiskLevel.MODERATE.value: [],
            DependencyRiskLevel.LOW.value: [],
            DependencyRiskLevel.SAFE.value: [],
        }
        for vuln in self.vulnerabilities:
            result[vuln.risk_level].append(vuln)
        return result


class CryptoReport(BaseModel):
    """Report from cryptographic implementation analysis."""
    scan_path: str = Field(..., description="Root path that was scanned")
    total_files_scanned: int = Field(0, description="Number of files scanned")
    issues_found: int = Field(0, description="Total cryptographic issues detected")
    findings: List[CryptoFinding] = Field(default_factory=list, description="List of findings")
    scan_duration_seconds: float = Field(0.0, description="Duration of the scan")
    scanned_at: datetime = Field(default_factory=datetime.now, description="When the scan was performed")

    class Config:
        use_enum_values = True

    def add_finding(self, finding: CryptoFinding) -> None:
        """Add a cryptographic finding to the report."""
        self.issues_found += 1
        self.findings.append(finding)

    @property
    def has_findings(self) -> bool:
        """Check if any issues were found."""
        return self.issues_found > 0


class SecurityReport(BaseModel):
    """Comprehensive security analysis report."""
    scan_path: str = Field(..., description="Root path that was scanned")
    scan_config: SecurityScanConfig = Field(..., description="Configuration used for the scan")
    secrets_report: Optional[SecretsReport] = Field(None, description="Secrets detection report")
    vulnerability_report: Optional[VulnerabilityReport] = Field(None, description="Vulnerability scan report")
    dependency_report: Optional[DependencyReport] = Field(None, description="Dependency scan report")
    crypto_report: Optional[CryptoReport] = Field(None, description="Cryptographic analysis report")
    access_report: Optional[Any] = Field(None, description="Access control analysis report")
    auth_report: Optional[Any] = Field(None, description="Authentication analysis report")
    headers_report: Optional[Any] = Field(None, description="Security headers analysis report")
    tls_report: Optional[Any] = Field(None, description="TLS/SSL analysis report")
    container_report: Optional[Any] = Field(None, description="Container security analysis report")
    infrastructure_report: Optional[Any] = Field(None, description="Infrastructure security analysis report")
    total_issues: int = Field(0, description="Total security issues found")
    critical_issues: int = Field(0, description="Critical severity issues")
    high_issues: int = Field(0, description="High severity issues")
    medium_issues: int = Field(0, description="Medium severity issues")
    low_issues: int = Field(0, description="Low severity issues")
    security_score: float = Field(100.0, ge=0.0, le=100.0, description="Overall security score (0-100)")
    scan_duration_seconds: float = Field(0.0, description="Total duration of all scans")
    scanned_at: datetime = Field(default_factory=datetime.now, description="When the scan was performed")

    class Config:
        use_enum_values = True

    def calculate_totals(self) -> None:
        """Calculate total issue counts from all reports."""
        self.total_issues = 0
        self.critical_issues = 0
        self.high_issues = 0
        self.medium_issues = 0
        self.low_issues = 0

        if self.secrets_report:
            for finding in self.secrets_report.findings:
                self.total_issues += 1
                self._increment_severity_count(finding.severity)

        if self.vulnerability_report:
            for finding in self.vulnerability_report.findings:
                self.total_issues += 1
                self._increment_severity_count(finding.severity)

        if self.dependency_report:
            for vuln in self.dependency_report.vulnerabilities:
                self.total_issues += 1
                self._increment_risk_count(vuln.risk_level)

        if self.crypto_report:
            for finding in self.crypto_report.findings:
                self.total_issues += 1
                self._increment_severity_count(finding.severity)

        if self.access_report and hasattr(self.access_report, 'findings'):
            for finding in self.access_report.findings:
                self.total_issues += 1
                self._increment_severity_count(finding.severity)

        if self.auth_report and hasattr(self.auth_report, 'findings'):
            for finding in self.auth_report.findings:
                self.total_issues += 1
                self._increment_severity_count(finding.severity)

        if self.headers_report and hasattr(self.headers_report, 'findings'):
            for finding in self.headers_report.findings:
                self.total_issues += 1
                self._increment_severity_count(finding.severity)

        if self.tls_report and hasattr(self.tls_report, 'findings'):
            for finding in self.tls_report.findings:
                self.total_issues += 1
                self._increment_severity_count(finding.severity)

        if self.container_report and hasattr(self.container_report, 'findings'):
            for finding in self.container_report.findings:
                self.total_issues += 1
                self._increment_severity_count(finding.severity)

        if self.infrastructure_report and hasattr(self.infrastructure_report, 'findings'):
            for finding in self.infrastructure_report.findings:
                self.total_issues += 1
                self._increment_severity_count(finding.severity)

        self._calculate_security_score()

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

    def _increment_risk_count(self, risk: str) -> None:
        """Increment the count for a risk level."""
        if risk == DependencyRiskLevel.CRITICAL.value:
            self.critical_issues += 1
        elif risk == DependencyRiskLevel.HIGH.value:
            self.high_issues += 1
        elif risk == DependencyRiskLevel.MODERATE.value:
            self.medium_issues += 1
        elif risk == DependencyRiskLevel.LOW.value:
            self.low_issues += 1

    def _calculate_security_score(self) -> None:
        """Calculate the overall security score."""
        score = 100.0
        score -= self.critical_issues * 25
        score -= self.high_issues * 10
        score -= self.medium_issues * 5
        score -= self.low_issues * 1
        self.security_score = max(0.0, score)

    @property
    def has_issues(self) -> bool:
        """Check if any security issues were found."""
        return self.total_issues > 0

    @property
    def is_passing(self) -> bool:
        """Check if the scan passes (no critical or high issues)."""
        return self.critical_issues == 0 and self.high_issues == 0

    @property
    def is_healthy(self) -> bool:
        """Check if the security scan is healthy (no critical or high issues)."""
        return self.is_passing
