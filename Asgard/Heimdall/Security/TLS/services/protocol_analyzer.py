"""
Heimdall TLS Protocol Analyzer Service

Service for detecting deprecated TLS/SSL protocol versions.
"""

import re
import time
from pathlib import Path
from typing import List, Optional

from Asgard.Heimdall.Security.TLS.models.tls_models import (
    TLSConfig,
    TLSFinding,
    TLSFindingType,
    TLSReport,
)
from Asgard.Heimdall.Security.TLS.utilities.ssl_utils import (
    find_tls_version_usage,
    is_deprecated_protocol,
)
from Asgard.Heimdall.Security.models.security_models import SecuritySeverity
from Asgard.Heimdall.Security.utilities.security_utils import (
    extract_code_snippet,
    find_line_column,
    scan_directory_for_security,
)


class ProtocolPattern:
    """Defines a pattern for detecting deprecated TLS/SSL protocols."""

    def __init__(
        self,
        name: str,
        pattern: str,
        protocol_version: str,
        severity: SecuritySeverity,
        title: str,
        description: str,
        cwe_id: str,
        remediation: str,
        confidence: float = 0.85,
    ):
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        self.protocol_version = protocol_version
        self.severity = severity
        self.title = title
        self.description = description
        self.cwe_id = cwe_id
        self.remediation = remediation
        self.confidence = confidence


PROTOCOL_PATTERNS: List[ProtocolPattern] = [
    ProtocolPattern(
        name="sslv2_usage",
        pattern=r'ssl\.PROTOCOL_SSLv2',
        protocol_version="SSLv2",
        severity=SecuritySeverity.CRITICAL,
        title="SSLv2 Protocol Used",
        description="SSLv2 is severely broken and should never be used. It is vulnerable to multiple attacks.",
        cwe_id="CWE-327",
        remediation="Use TLS 1.2 or TLS 1.3 instead. Remove all SSLv2 references.",
        confidence=0.95,
    ),
    ProtocolPattern(
        name="sslv3_usage",
        pattern=r'ssl\.PROTOCOL_SSLv3',
        protocol_version="SSLv3",
        severity=SecuritySeverity.CRITICAL,
        title="SSLv3 Protocol Used",
        description="SSLv3 is vulnerable to POODLE attack and other security issues.",
        cwe_id="CWE-327",
        remediation="Use TLS 1.2 or TLS 1.3 instead. Remove all SSLv3 references.",
        confidence=0.95,
    ),
    ProtocolPattern(
        name="tlsv1_usage",
        pattern=r'ssl\.PROTOCOL_TLSv1\b',
        protocol_version="TLSv1.0",
        severity=SecuritySeverity.HIGH,
        title="TLS 1.0 Protocol Used",
        description="TLS 1.0 is deprecated and vulnerable to BEAST and other attacks.",
        cwe_id="CWE-327",
        remediation="Use TLS 1.2 or TLS 1.3 instead. TLS 1.0 is deprecated by RFC 8996.",
        confidence=0.9,
    ),
    ProtocolPattern(
        name="tlsv1_1_usage",
        pattern=r'ssl\.PROTOCOL_TLSv1_1',
        protocol_version="TLSv1.1",
        severity=SecuritySeverity.HIGH,
        title="TLS 1.1 Protocol Used",
        description="TLS 1.1 is deprecated and no longer considered secure.",
        cwe_id="CWE-327",
        remediation="Use TLS 1.2 or TLS 1.3 instead. TLS 1.1 is deprecated by RFC 8996.",
        confidence=0.9,
    ),
    ProtocolPattern(
        name="tls_version_tlsv1",
        pattern=r'ssl\.TLSVersion\.TLSv1\b',
        protocol_version="TLSv1.0",
        severity=SecuritySeverity.HIGH,
        title="TLS 1.0 Version Specified",
        description="TLS 1.0 is deprecated and should not be used.",
        cwe_id="CWE-327",
        remediation="Use TLSVersion.TLSv1_2 or TLSVersion.TLSv1_3 instead.",
        confidence=0.9,
    ),
    ProtocolPattern(
        name="tls_version_tlsv1_1",
        pattern=r'ssl\.TLSVersion\.TLSv1_1',
        protocol_version="TLSv1.1",
        severity=SecuritySeverity.HIGH,
        title="TLS 1.1 Version Specified",
        description="TLS 1.1 is deprecated and should not be used.",
        cwe_id="CWE-327",
        remediation="Use TLSVersion.TLSv1_2 or TLSVersion.TLSv1_3 instead.",
        confidence=0.9,
    ),
    ProtocolPattern(
        name="minimum_version_tlsv1",
        pattern=r'minimum_version\s*=\s*ssl\.TLSVersion\.TLSv1\b',
        protocol_version="TLSv1.0",
        severity=SecuritySeverity.HIGH,
        title="Minimum TLS Version Set to 1.0",
        description="Minimum TLS version is set to deprecated TLS 1.0.",
        cwe_id="CWE-327",
        remediation="Set minimum_version to TLSVersion.TLSv1_2 or higher.",
        confidence=0.95,
    ),
    ProtocolPattern(
        name="minimum_version_tlsv1_1",
        pattern=r'minimum_version\s*=\s*ssl\.TLSVersion\.TLSv1_1',
        protocol_version="TLSv1.1",
        severity=SecuritySeverity.HIGH,
        title="Minimum TLS Version Set to 1.1",
        description="Minimum TLS version is set to deprecated TLS 1.1.",
        cwe_id="CWE-327",
        remediation="Set minimum_version to TLSVersion.TLSv1_2 or higher.",
        confidence=0.95,
    ),
    ProtocolPattern(
        name="pyopenssl_sslv2",
        pattern=r'SSLv2_METHOD',
        protocol_version="SSLv2",
        severity=SecuritySeverity.CRITICAL,
        title="OpenSSL SSLv2 Method Used",
        description="SSLv2 method from PyOpenSSL is critically insecure.",
        cwe_id="CWE-327",
        remediation="Use TLS_METHOD or TLS_CLIENT_METHOD with modern TLS versions.",
        confidence=0.9,
    ),
    ProtocolPattern(
        name="pyopenssl_sslv3",
        pattern=r'SSLv3_METHOD',
        protocol_version="SSLv3",
        severity=SecuritySeverity.CRITICAL,
        title="OpenSSL SSLv3 Method Used",
        description="SSLv3 method from PyOpenSSL is vulnerable to POODLE.",
        cwe_id="CWE-327",
        remediation="Use TLS_METHOD or TLS_CLIENT_METHOD with modern TLS versions.",
        confidence=0.9,
    ),
    ProtocolPattern(
        name="pyopenssl_tlsv1",
        pattern=r'TLSv1_METHOD\b',
        protocol_version="TLSv1.0",
        severity=SecuritySeverity.HIGH,
        title="OpenSSL TLSv1 Method Used",
        description="TLSv1 method from PyOpenSSL uses deprecated TLS 1.0.",
        cwe_id="CWE-327",
        remediation="Use TLS_METHOD with minimum version set to TLS 1.2.",
        confidence=0.85,
    ),
]


class ProtocolAnalyzer:
    """
    Analyzes TLS/SSL protocol usage for security issues.

    Detects:
    - SSLv2/SSLv3 usage
    - TLS 1.0/1.1 usage
    - Deprecated protocol configurations
    """

    def __init__(self, config: Optional[TLSConfig] = None):
        """
        Initialize the protocol analyzer.

        Args:
            config: TLS configuration. Uses defaults if not provided.
        """
        self.config = config or TLSConfig()
        self.patterns = PROTOCOL_PATTERNS

    def scan(self, scan_path: Optional[Path] = None) -> TLSReport:
        """
        Scan the specified path for deprecated TLS/SSL protocol usage.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            TLSReport containing all findings
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        start_time = time.time()

        report = TLSReport(scan_path=str(path))

        for file_path in scan_directory_for_security(
            path,
            exclude_patterns=self.config.exclude_patterns,
            include_extensions=[".py", ".js", ".ts"],
        ):
            report.total_files_scanned += 1
            findings = self._scan_file(file_path, path)

            for finding in findings:
                if self._severity_meets_threshold(finding.severity):
                    report.add_finding(finding)

        report.scan_duration_seconds = time.time() - start_time

        report.findings.sort(
            key=lambda f: (
                self._severity_order(f.severity),
                f.file_path,
                f.line_number,
            )
        )

        return report

    def _scan_file(self, file_path: Path, root_path: Path) -> List[TLSFinding]:
        """
        Scan a single file for deprecated protocol usage.

        Args:
            file_path: Path to the file to scan
            root_path: Root path for relative path calculation

        Returns:
            List of TLS findings in the file
        """
        findings: List[TLSFinding] = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except (IOError, OSError):
            return findings

        lines = content.split("\n")

        for pattern in self.patterns:
            for match in pattern.pattern.finditer(content):
                line_number, column = find_line_column(content, match.start())

                if self._is_in_comment(lines, line_number):
                    continue

                code_snippet = extract_code_snippet(lines, line_number)

                finding = TLSFinding(
                    file_path=str(file_path.relative_to(root_path)),
                    line_number=line_number,
                    column_start=column,
                    column_end=column + len(match.group(0)),
                    finding_type=TLSFindingType.DEPRECATED_TLS_VERSION,
                    severity=pattern.severity,
                    title=pattern.title,
                    description=pattern.description,
                    code_snippet=code_snippet,
                    protocol_version=pattern.protocol_version,
                    cwe_id=pattern.cwe_id,
                    confidence=pattern.confidence,
                    remediation=pattern.remediation,
                    references=[
                        f"https://cwe.mitre.org/data/definitions/{pattern.cwe_id.replace('CWE-', '')}.html",
                        "https://tools.ietf.org/html/rfc8996",
                    ],
                )

                findings.append(finding)

        return findings

    def _is_in_comment(self, lines: List[str], line_number: int) -> bool:
        """Check if a line is inside a comment."""
        if line_number < 1 or line_number > len(lines):
            return False

        line = lines[line_number - 1].strip()

        if line.startswith("#") or line.startswith("//") or line.startswith("*"):
            return True

        return False

    def _severity_meets_threshold(self, severity: str) -> bool:
        """Check if a severity level meets the configured threshold."""
        severity_order = {
            SecuritySeverity.INFO.value: 0,
            SecuritySeverity.LOW.value: 1,
            SecuritySeverity.MEDIUM.value: 2,
            SecuritySeverity.HIGH.value: 3,
            SecuritySeverity.CRITICAL.value: 4,
        }

        min_level = severity_order.get(self.config.min_severity, 1)
        finding_level = severity_order.get(severity, 1)

        return finding_level >= min_level

    def _severity_order(self, severity: str) -> int:
        """Get sort order for severity (critical first)."""
        order = {
            SecuritySeverity.CRITICAL.value: 0,
            SecuritySeverity.HIGH.value: 1,
            SecuritySeverity.MEDIUM.value: 2,
            SecuritySeverity.LOW.value: 3,
            SecuritySeverity.INFO.value: 4,
        }
        return order.get(severity, 5)
