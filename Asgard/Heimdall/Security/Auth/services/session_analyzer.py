"""
Heimdall Session Analyzer Service

Service for detecting session management security issues.
"""

import re
import time
from pathlib import Path
from typing import List, Optional

from Asgard.Heimdall.Security.Auth.models.auth_models import (
    AuthConfig,
    AuthFinding,
    AuthFindingType,
    AuthReport,
)
from Asgard.Heimdall.Security.models.security_models import SecuritySeverity
from Asgard.Heimdall.Security.utilities.security_utils import (
    extract_code_snippet,
    find_line_column,
    scan_directory_for_security,
)


class SessionPattern:
    """Defines a pattern for detecting session security issues."""

    def __init__(
        self,
        name: str,
        pattern: str,
        finding_type: AuthFindingType,
        severity: SecuritySeverity,
        title: str,
        description: str,
        cwe_id: str,
        remediation: str,
        confidence: float = 0.7,
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


SESSION_PATTERNS: List[SessionPattern] = [
    SessionPattern(
        name="session_cookie_insecure",
        pattern=r"""SESSION_COOKIE_SECURE\s*=\s*False""",
        finding_type=AuthFindingType.INSECURE_SESSION,
        severity=SecuritySeverity.HIGH,
        title="Session Cookie Not Secure",
        description="Session cookie is not marked as secure, allowing transmission over HTTP.",
        cwe_id="CWE-614",
        remediation="Set SESSION_COOKIE_SECURE = True to ensure cookies are only sent over HTTPS.",
        confidence=0.9,
    ),
    SessionPattern(
        name="session_cookie_no_httponly",
        pattern=r"""SESSION_COOKIE_HTTPONLY\s*=\s*False""",
        finding_type=AuthFindingType.INSECURE_COOKIE,
        severity=SecuritySeverity.HIGH,
        title="Session Cookie Not HttpOnly",
        description="Session cookie is not marked as HttpOnly, making it accessible to JavaScript.",
        cwe_id="CWE-1004",
        remediation="Set SESSION_COOKIE_HTTPONLY = True to prevent XSS attacks from stealing cookies.",
        confidence=0.9,
    ),
    SessionPattern(
        name="session_cookie_samesite_none",
        pattern=r"""SESSION_COOKIE_SAMESITE\s*=\s*['"]?None['"]?""",
        finding_type=AuthFindingType.INSECURE_COOKIE,
        severity=SecuritySeverity.MEDIUM,
        title="Session Cookie SameSite=None",
        description="Session cookie has SameSite=None, which may allow CSRF attacks.",
        cwe_id="CWE-1275",
        remediation="Use SameSite='Lax' or 'Strict' unless cross-site cookies are required.",
        confidence=0.8,
    ),
    SessionPattern(
        name="cookie_secure_false",
        pattern=r"""set_cookie\s*\([^)]*secure\s*=\s*False""",
        finding_type=AuthFindingType.INSECURE_COOKIE,
        severity=SecuritySeverity.HIGH,
        title="Cookie Set Without Secure Flag",
        description="Cookie is explicitly set without the Secure flag.",
        cwe_id="CWE-614",
        remediation="Always set secure=True for cookies containing sensitive data.",
        confidence=0.85,
    ),
    SessionPattern(
        name="cookie_httponly_false",
        pattern=r"""set_cookie\s*\([^)]*httponly\s*=\s*False""",
        finding_type=AuthFindingType.INSECURE_COOKIE,
        severity=SecuritySeverity.HIGH,
        title="Cookie Set Without HttpOnly Flag",
        description="Cookie is explicitly set without the HttpOnly flag.",
        cwe_id="CWE-1004",
        remediation="Always set httponly=True for session cookies.",
        confidence=0.85,
    ),
    SessionPattern(
        name="session_fixation",
        pattern=r"""session\s*\[\s*['"]user['"].*=.*request\.(form|args|data)""",
        finding_type=AuthFindingType.SESSION_FIXATION,
        severity=SecuritySeverity.HIGH,
        title="Potential Session Fixation",
        description="Session appears to be set directly from user input without regeneration.",
        cwe_id="CWE-384",
        remediation="Regenerate the session ID after successful authentication.",
        confidence=0.6,
    ),
    SessionPattern(
        name="remember_me_insecure",
        pattern=r"""remember\s*=\s*(?:request|form|data)\.""",
        finding_type=AuthFindingType.INSECURE_REMEMBER_ME,
        severity=SecuritySeverity.MEDIUM,
        title="Insecure Remember Me Implementation",
        description="Remember me functionality may be implemented insecurely.",
        cwe_id="CWE-613",
        remediation="Use secure token-based remember me with proper expiration and rotation.",
        confidence=0.5,
    ),
    SessionPattern(
        name="permanent_session_long",
        pattern=r"""PERMANENT_SESSION_LIFETIME\s*=\s*timedelta\s*\(\s*days\s*=\s*(\d{3,})""",
        finding_type=AuthFindingType.INSECURE_SESSION,
        severity=SecuritySeverity.MEDIUM,
        title="Excessively Long Session Lifetime",
        description="Session lifetime is set to an excessively long period.",
        cwe_id="CWE-613",
        remediation="Use reasonable session lifetimes (e.g., 30 days max for remember me).",
        confidence=0.7,
    ),
]


class SessionAnalyzer:
    """
    Analyzes session management security.

    Detects:
    - Insecure session cookies
    - Missing HttpOnly/Secure flags
    - Session fixation vulnerabilities
    - Insecure remember me implementation
    """

    def __init__(self, config: Optional[AuthConfig] = None):
        """
        Initialize the session analyzer.

        Args:
            config: Auth configuration. Uses defaults if not provided.
        """
        self.config = config or AuthConfig()
        self.patterns = SESSION_PATTERNS

    def scan(self, scan_path: Optional[Path] = None) -> AuthReport:
        """
        Scan the specified path for session security issues.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            AuthReport containing all findings
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        start_time = time.time()

        report = AuthReport(scan_path=str(path))

        for file_path in scan_directory_for_security(
            path,
            exclude_patterns=self.config.exclude_patterns,
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

    def _scan_file(self, file_path: Path, root_path: Path) -> List[AuthFinding]:
        """
        Scan a single file for session security issues.

        Args:
            file_path: Path to the file to scan
            root_path: Root path for relative path calculation

        Returns:
            List of auth findings in the file
        """
        findings: List[AuthFinding] = []

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

                finding = AuthFinding(
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
