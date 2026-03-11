"""
Heimdall TLS Certificate Validator Service

Service for detecting certificate validation issues and insecure SSL configurations.
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
    find_certificate_patterns,
    find_verify_false_patterns,
)
from Asgard.Heimdall.Security.models.security_models import SecuritySeverity
from Asgard.Heimdall.Security.utilities.security_utils import (
    extract_code_snippet,
    find_line_column,
    scan_directory_for_security,
)


class CertificatePattern:
    """Defines a pattern for detecting certificate validation issues."""

    def __init__(
        self,
        name: str,
        pattern: str,
        finding_type: TLSFindingType,
        severity: SecuritySeverity,
        title: str,
        description: str,
        cwe_id: str,
        remediation: str,
        confidence: float = 0.85,
    ):
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        self.finding_type = finding_type
        self.severity = severity
        self.title = title
        self.description = description
        self.cwe_id = cwe_id
        self.remediation = remediation
        self.confidence = confidence


CERTIFICATE_PATTERNS: List[CertificatePattern] = [
    CertificatePattern(
        name="verify_false",
        pattern=r'verify\s*=\s*False',
        finding_type=TLSFindingType.DISABLED_VERIFICATION,
        severity=SecuritySeverity.CRITICAL,
        title="SSL Certificate Verification Disabled",
        description="SSL/TLS certificate verification is disabled, allowing MITM attacks.",
        cwe_id="CWE-295",
        remediation="Always enable certificate verification. Use verify=True or provide a CA bundle.",
        confidence=0.95,
    ),
    CertificatePattern(
        name="verify_ssl_false",
        pattern=r'verify_ssl\s*=\s*False',
        finding_type=TLSFindingType.DISABLED_VERIFICATION,
        severity=SecuritySeverity.CRITICAL,
        title="SSL Verification Disabled (verify_ssl)",
        description="SSL/TLS certificate verification is disabled via verify_ssl parameter.",
        cwe_id="CWE-295",
        remediation="Set verify_ssl=True to enable certificate verification.",
        confidence=0.95,
    ),
    CertificatePattern(
        name="ssl_verify_false",
        pattern=r'ssl_verify\s*=\s*False',
        finding_type=TLSFindingType.DISABLED_VERIFICATION,
        severity=SecuritySeverity.CRITICAL,
        title="SSL Verification Disabled (ssl_verify)",
        description="SSL/TLS certificate verification is disabled via ssl_verify parameter.",
        cwe_id="CWE-295",
        remediation="Set ssl_verify=True to enable certificate verification.",
        confidence=0.95,
    ),
    CertificatePattern(
        name="cert_none",
        pattern=r'cert_reqs\s*=\s*(?:ssl\.)?CERT_NONE',
        finding_type=TLSFindingType.CERT_NONE,
        severity=SecuritySeverity.CRITICAL,
        title="CERT_NONE Used",
        description="SSL context uses CERT_NONE which disables all certificate verification.",
        cwe_id="CWE-295",
        remediation="Use CERT_REQUIRED to require valid certificates.",
        confidence=0.95,
    ),
    CertificatePattern(
        name="verify_mode_none",
        pattern=r'verify_mode\s*=\s*ssl\.CERT_NONE',
        finding_type=TLSFindingType.CERT_NONE,
        severity=SecuritySeverity.CRITICAL,
        title="SSL Context verify_mode Set to CERT_NONE",
        description="SSL context verify_mode is set to CERT_NONE, disabling verification.",
        cwe_id="CWE-295",
        remediation="Set verify_mode to ssl.CERT_REQUIRED.",
        confidence=0.95,
    ),
    CertificatePattern(
        name="check_hostname_false",
        pattern=r'check_hostname\s*=\s*False',
        finding_type=TLSFindingType.DISABLED_HOSTNAME_CHECK,
        severity=SecuritySeverity.HIGH,
        title="Hostname Verification Disabled",
        description="SSL hostname verification is disabled, allowing certificate substitution attacks.",
        cwe_id="CWE-297",
        remediation="Set check_hostname=True to verify the server hostname matches the certificate.",
        confidence=0.9,
    ),
    CertificatePattern(
        name="unverified_context",
        pattern=r'ssl\._create_unverified_context\s*\(',
        finding_type=TLSFindingType.INSECURE_SSL_CONTEXT,
        severity=SecuritySeverity.CRITICAL,
        title="Unverified SSL Context Created",
        description="Using _create_unverified_context disables all SSL security checks.",
        cwe_id="CWE-295",
        remediation="Use ssl.create_default_context() which enables verification by default.",
        confidence=0.95,
    ),
    CertificatePattern(
        name="https_context_override",
        pattern=r'ssl\._create_default_https_context\s*=\s*ssl\._create_unverified_context',
        finding_type=TLSFindingType.INSECURE_SSL_CONTEXT,
        severity=SecuritySeverity.CRITICAL,
        title="Default HTTPS Context Overridden",
        description="The default HTTPS context is being replaced with an unverified context globally.",
        cwe_id="CWE-295",
        remediation="Do not override the default HTTPS context. Fix the root cause of certificate issues.",
        confidence=0.98,
    ),
    CertificatePattern(
        name="urllib3_warnings_disabled",
        pattern=r'urllib3\.disable_warnings\s*\(\s*(?:urllib3\.exceptions\.)?InsecureRequestWarning',
        finding_type=TLSFindingType.DISABLED_VERIFICATION,
        severity=SecuritySeverity.HIGH,
        title="InsecureRequestWarning Suppressed",
        description="Warnings about insecure requests are being suppressed, hiding security issues.",
        cwe_id="CWE-295",
        remediation="Fix the underlying certificate verification issue instead of suppressing warnings.",
        confidence=0.85,
    ),
    CertificatePattern(
        name="requests_no_verify",
        pattern=r'requests\.(?:get|post|put|delete|patch|head|options)\s*\([^)]*verify\s*=\s*False',
        finding_type=TLSFindingType.DISABLED_VERIFICATION,
        severity=SecuritySeverity.CRITICAL,
        title="Requests Library SSL Verification Disabled",
        description="The requests library call has certificate verification disabled.",
        cwe_id="CWE-295",
        remediation="Remove verify=False or set verify=True. Provide a CA bundle if needed.",
        confidence=0.95,
    ),
    CertificatePattern(
        name="aiohttp_no_verify",
        pattern=r'aiohttp\.(?:ClientSession|TCPConnector)\s*\([^)]*ssl\s*=\s*False',
        finding_type=TLSFindingType.DISABLED_VERIFICATION,
        severity=SecuritySeverity.CRITICAL,
        title="aiohttp SSL Verification Disabled",
        description="aiohttp client session has SSL verification disabled.",
        cwe_id="CWE-295",
        remediation="Set ssl=True or provide a proper SSL context with verification enabled.",
        confidence=0.9,
    ),
    CertificatePattern(
        name="httpx_no_verify",
        pattern=r'httpx\.(?:Client|AsyncClient)\s*\([^)]*verify\s*=\s*False',
        finding_type=TLSFindingType.DISABLED_VERIFICATION,
        severity=SecuritySeverity.CRITICAL,
        title="httpx SSL Verification Disabled",
        description="httpx client has certificate verification disabled.",
        cwe_id="CWE-295",
        remediation="Set verify=True or provide a path to a CA bundle.",
        confidence=0.9,
    ),
    CertificatePattern(
        name="cert_optional",
        pattern=r'cert_reqs\s*=\s*(?:ssl\.)?CERT_OPTIONAL',
        finding_type=TLSFindingType.NO_CERT_VALIDATION,
        severity=SecuritySeverity.MEDIUM,
        title="CERT_OPTIONAL Used",
        description="SSL context uses CERT_OPTIONAL which may not require valid certificates.",
        cwe_id="CWE-295",
        remediation="Use CERT_REQUIRED for client authentication. For server-side, ensure proper handling.",
        confidence=0.7,
    ),
    CertificatePattern(
        name="inline_certificate",
        pattern=r'-----BEGIN CERTIFICATE-----',
        finding_type=TLSFindingType.HARDCODED_CERTIFICATE,
        severity=SecuritySeverity.MEDIUM,
        title="Hardcoded Certificate Found",
        description="A certificate is hardcoded in the source code.",
        cwe_id="CWE-321",
        remediation="Store certificates in separate files and load them securely.",
        confidence=0.75,
    ),
    CertificatePattern(
        name="inline_private_key",
        pattern=r'-----BEGIN (?:RSA )?PRIVATE KEY-----',
        finding_type=TLSFindingType.HARDCODED_CERTIFICATE,
        severity=SecuritySeverity.CRITICAL,
        title="Hardcoded Private Key Found",
        description="A private key is hardcoded in the source code.",
        cwe_id="CWE-321",
        remediation="Never hardcode private keys. Use secure key management solutions.",
        confidence=0.95,
    ),
    CertificatePattern(
        name="node_reject_unauthorized",
        pattern=r'rejectUnauthorized\s*:\s*false',
        finding_type=TLSFindingType.DISABLED_VERIFICATION,
        severity=SecuritySeverity.CRITICAL,
        title="Node.js rejectUnauthorized Disabled",
        description="Node.js TLS connection has certificate validation disabled.",
        cwe_id="CWE-295",
        remediation="Set rejectUnauthorized: true to enable certificate validation.",
        confidence=0.95,
    ),
    CertificatePattern(
        name="node_tls_reject_env",
        pattern=r'NODE_TLS_REJECT_UNAUTHORIZED\s*[=:]\s*["\']?0',
        finding_type=TLSFindingType.DISABLED_VERIFICATION,
        severity=SecuritySeverity.CRITICAL,
        title="NODE_TLS_REJECT_UNAUTHORIZED Set to 0",
        description="Environment variable disables all TLS certificate validation globally.",
        cwe_id="CWE-295",
        remediation="Never set NODE_TLS_REJECT_UNAUTHORIZED=0 in production.",
        confidence=0.98,
    ),
]


class CertificateValidator:
    """
    Validates certificate handling for security issues.

    Detects:
    - Disabled certificate verification
    - Disabled hostname checking
    - Insecure SSL contexts
    - Hardcoded certificates/keys
    - Warning suppression
    """

    def __init__(self, config: Optional[TLSConfig] = None):
        """
        Initialize the certificate validator.

        Args:
            config: TLS configuration. Uses defaults if not provided.
        """
        self.config = config or TLSConfig()
        self.patterns = CERTIFICATE_PATTERNS

    def scan(self, scan_path: Optional[Path] = None) -> TLSReport:
        """
        Scan the specified path for certificate validation issues.

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
            include_extensions=[".py", ".js", ".ts", ".jsx", ".tsx", ".env", ".yaml", ".yml"],
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
        Scan a single file for certificate validation issues.

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
                    finding_type=pattern.finding_type,
                    severity=pattern.severity,
                    title=pattern.title,
                    description=pattern.description,
                    code_snippet=code_snippet,
                    cwe_id=pattern.cwe_id,
                    confidence=pattern.confidence,
                    remediation=pattern.remediation,
                    references=[
                        f"https://cwe.mitre.org/data/definitions/{pattern.cwe_id.replace('CWE-', '')}.html",
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
