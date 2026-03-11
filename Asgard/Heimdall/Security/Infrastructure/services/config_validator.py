"""
Heimdall Configuration Validator Service

Service for validating security settings in configuration files.
"""

import re
import time
from pathlib import Path
from typing import List, Optional

from Asgard.Heimdall.Security.Infrastructure.models.infra_models import (
    InfraConfig,
    InfraFinding,
    InfraFindingType,
    InfraReport,
)
from Asgard.Heimdall.Security.models.security_models import SecuritySeverity
from Asgard.Heimdall.Security.utilities.security_utils import (
    extract_code_snippet,
    find_line_column,
    scan_directory_for_security,
)


class ConfigPattern:
    """Defines a pattern for detecting configuration security issues."""

    def __init__(
        self,
        name: str,
        pattern: str,
        finding_type: InfraFindingType,
        severity: SecuritySeverity,
        title: str,
        description: str,
        cwe_id: str,
        remediation: str,
        config_key: Optional[str] = None,
        recommended_value: Optional[str] = None,
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
        self.config_key = config_key
        self.recommended_value = recommended_value
        self.confidence = confidence


CONFIG_PATTERNS: List[ConfigPattern] = [
    ConfigPattern(
        name="debug_mode_true",
        pattern=r"""DEBUG\s*[=:]\s*(?:True|true|1|yes|on|['"](?:True|true|1|yes|on)['"])""",
        finding_type=InfraFindingType.DEBUG_MODE,
        severity=SecuritySeverity.CRITICAL,
        title="Debug Mode Enabled",
        description="DEBUG mode is enabled. This exposes sensitive information and stack traces in production.",
        cwe_id="CWE-489",
        remediation="Set DEBUG = False in production. Use environment variables to control this setting.",
        config_key="DEBUG",
        recommended_value="False",
        confidence=0.95,
    ),
    ConfigPattern(
        name="flask_debug_true",
        pattern=r"""app\.(?:debug|run\([^)]*debug\s*=\s*True)""",
        finding_type=InfraFindingType.DEBUG_MODE,
        severity=SecuritySeverity.CRITICAL,
        title="Flask Debug Mode Enabled",
        description="Flask debug mode is enabled. This allows arbitrary code execution via the debugger.",
        cwe_id="CWE-489",
        remediation="Never run Flask with debug=True in production. Use a production WSGI server.",
        config_key="debug",
        recommended_value="False",
        confidence=0.95,
    ),
    ConfigPattern(
        name="allowed_hosts_wildcard",
        pattern=r"""ALLOWED_HOSTS\s*[=:]\s*\[?\s*['"]\*['"]\s*\]?""",
        finding_type=InfraFindingType.PERMISSIVE_HOSTS,
        severity=SecuritySeverity.HIGH,
        title="Permissive ALLOWED_HOSTS (*)",
        description="ALLOWED_HOSTS is set to '*' which allows any host. This enables HTTP Host header attacks.",
        cwe_id="CWE-16",
        remediation="Set ALLOWED_HOSTS to a specific list of valid hostnames for your application.",
        config_key="ALLOWED_HOSTS",
        recommended_value='["your-domain.com"]',
        confidence=0.95,
    ),
    ConfigPattern(
        name="cors_allow_all",
        pattern=r"""CORS_ORIGIN_ALLOW_ALL\s*[=:]\s*(?:True|true|1)""",
        finding_type=InfraFindingType.CORS_ALLOW_ALL,
        severity=SecuritySeverity.HIGH,
        title="CORS Allow All Origins",
        description="CORS is configured to allow all origins. This bypasses same-origin policy protections.",
        cwe_id="CWE-942",
        remediation="Set CORS_ORIGIN_ALLOW_ALL = False and specify allowed origins explicitly.",
        config_key="CORS_ORIGIN_ALLOW_ALL",
        recommended_value="False",
        confidence=0.95,
    ),
    ConfigPattern(
        name="cors_credentials_allow_all",
        pattern=r"""CORS_ALLOW_CREDENTIALS\s*[=:]\s*(?:True|true|1)[\s\S]{0,100}CORS_ORIGIN_ALLOW_ALL\s*[=:]\s*(?:True|true|1)""",
        finding_type=InfraFindingType.CORS_ALLOW_ALL,
        severity=SecuritySeverity.CRITICAL,
        title="CORS Allow Credentials with All Origins",
        description="CORS is configured to allow credentials with all origins. This is a critical security vulnerability.",
        cwe_id="CWE-942",
        remediation="Never allow credentials with all origins. Specify allowed origins explicitly.",
        config_key="CORS_ALLOW_CREDENTIALS",
        recommended_value="False (or use specific origins)",
        confidence=0.98,
    ),
    ConfigPattern(
        name="access_control_allow_origin_star",
        pattern=r"""Access-Control-Allow-Origin['"]\s*[=:,]\s*['"]\*['"]""",
        finding_type=InfraFindingType.CORS_ALLOW_ALL,
        severity=SecuritySeverity.HIGH,
        title="CORS Header Allow All Origins",
        description="Access-Control-Allow-Origin header is set to '*'. This disables cross-origin restrictions.",
        cwe_id="CWE-942",
        remediation="Set Access-Control-Allow-Origin to specific allowed origins.",
        config_key="Access-Control-Allow-Origin",
        recommended_value="Specific origin",
        confidence=0.9,
    ),
    ConfigPattern(
        name="secure_cookie_false",
        pattern=r"""(?:SESSION_COOKIE_SECURE|CSRF_COOKIE_SECURE|COOKIE_SECURE)\s*[=:]\s*(?:False|false|0)""",
        finding_type=InfraFindingType.INSECURE_DEFAULT,
        severity=SecuritySeverity.HIGH,
        title="Secure Cookie Disabled",
        description="Secure flag is disabled for cookies. Cookies can be transmitted over unencrypted connections.",
        cwe_id="CWE-614",
        remediation="Set SESSION_COOKIE_SECURE = True in production to ensure cookies are only sent over HTTPS.",
        config_key="SESSION_COOKIE_SECURE",
        recommended_value="True",
        confidence=0.9,
    ),
    ConfigPattern(
        name="httponly_cookie_false",
        pattern=r"""(?:SESSION_COOKIE_HTTPONLY|CSRF_COOKIE_HTTPONLY)\s*[=:]\s*(?:False|false|0)""",
        finding_type=InfraFindingType.INSECURE_DEFAULT,
        severity=SecuritySeverity.MEDIUM,
        title="HttpOnly Cookie Disabled",
        description="HttpOnly flag is disabled for cookies. Cookies can be accessed via JavaScript (XSS risk).",
        cwe_id="CWE-1004",
        remediation="Set SESSION_COOKIE_HTTPONLY = True to prevent JavaScript access to session cookies.",
        config_key="SESSION_COOKIE_HTTPONLY",
        recommended_value="True",
        confidence=0.9,
    ),
    ConfigPattern(
        name="ssl_redirect_disabled",
        pattern=r"""SECURE_SSL_REDIRECT\s*[=:]\s*(?:False|false|0)""",
        finding_type=InfraFindingType.INSECURE_TRANSPORT,
        severity=SecuritySeverity.MEDIUM,
        title="SSL Redirect Disabled",
        description="HTTPS redirect is disabled. Users may access the application over unencrypted HTTP.",
        cwe_id="CWE-319",
        remediation="Set SECURE_SSL_REDIRECT = True to force HTTPS in production.",
        config_key="SECURE_SSL_REDIRECT",
        recommended_value="True",
        confidence=0.85,
    ),
    ConfigPattern(
        name="hsts_disabled",
        pattern=r"""SECURE_HSTS_SECONDS\s*[=:]\s*(?:0|None|null)""",
        finding_type=InfraFindingType.MISSING_SECURITY_HEADER,
        severity=SecuritySeverity.MEDIUM,
        title="HSTS Disabled",
        description="HTTP Strict Transport Security is disabled. Browsers will not enforce HTTPS.",
        cwe_id="CWE-319",
        remediation="Set SECURE_HSTS_SECONDS to at least 31536000 (1 year) in production.",
        config_key="SECURE_HSTS_SECONDS",
        recommended_value="31536000",
        confidence=0.85,
    ),
    ConfigPattern(
        name="verbose_errors",
        pattern=r"""(?:PROPAGATE_EXCEPTIONS|SHOW_ERRORS|DISPLAY_ERRORS)\s*[=:]\s*(?:True|true|1|on)""",
        finding_type=InfraFindingType.VERBOSE_ERROR_MESSAGES,
        severity=SecuritySeverity.HIGH,
        title="Verbose Error Messages Enabled",
        description="Verbose error messages are enabled. This exposes internal implementation details.",
        cwe_id="CWE-209",
        remediation="Disable verbose error messages in production. Log errors internally instead.",
        config_key="PROPAGATE_EXCEPTIONS",
        recommended_value="False",
        confidence=0.85,
    ),
    ConfigPattern(
        name="security_disabled",
        pattern=r"""(?:SECURITY_ENABLED|AUTHENTICATION_REQUIRED|AUTH_REQUIRED)\s*[=:]\s*(?:False|false|0|off)""",
        finding_type=InfraFindingType.DISABLED_SECURITY_FEATURE,
        severity=SecuritySeverity.CRITICAL,
        title="Security Feature Disabled",
        description="A security feature is explicitly disabled in configuration.",
        cwe_id="CWE-16",
        remediation="Enable security features in production. Review why this was disabled.",
        config_key="SECURITY_ENABLED",
        recommended_value="True",
        confidence=0.9,
    ),
    ConfigPattern(
        name="csrf_disabled",
        pattern=r"""(?:CSRF_ENABLED|WTF_CSRF_ENABLED|CSRF_PROTECTION)\s*[=:]\s*(?:False|false|0)""",
        finding_type=InfraFindingType.DISABLED_SECURITY_FEATURE,
        severity=SecuritySeverity.CRITICAL,
        title="CSRF Protection Disabled",
        description="Cross-Site Request Forgery protection is disabled. Application is vulnerable to CSRF attacks.",
        cwe_id="CWE-352",
        remediation="Enable CSRF protection. Set CSRF_ENABLED = True.",
        config_key="CSRF_ENABLED",
        recommended_value="True",
        confidence=0.95,
    ),
    ConfigPattern(
        name="xss_protection_disabled",
        pattern=r"""(?:X_XSS_PROTECTION|XSS_PROTECTION)\s*[=:]\s*(?:False|false|0|off|disabled)""",
        finding_type=InfraFindingType.DISABLED_SECURITY_FEATURE,
        severity=SecuritySeverity.HIGH,
        title="XSS Protection Disabled",
        description="Browser XSS protection header is disabled.",
        cwe_id="CWE-79",
        remediation="Enable XSS protection header: X-XSS-Protection: 1; mode=block",
        config_key="X_XSS_PROTECTION",
        recommended_value="1; mode=block",
        confidence=0.85,
    ),
    ConfigPattern(
        name="content_type_nosniff_disabled",
        pattern=r"""(?:X_CONTENT_TYPE_OPTIONS|CONTENT_TYPE_NOSNIFF)\s*[=:]\s*(?:False|false|0|off|disabled)""",
        finding_type=InfraFindingType.MISSING_SECURITY_HEADER,
        severity=SecuritySeverity.MEDIUM,
        title="Content Type Nosniff Disabled",
        description="X-Content-Type-Options header is disabled. Browser may MIME-sniff responses.",
        cwe_id="CWE-16",
        remediation="Set X-Content-Type-Options: nosniff header.",
        config_key="X_CONTENT_TYPE_OPTIONS",
        recommended_value="nosniff",
        confidence=0.8,
    ),
    ConfigPattern(
        name="frame_options_disabled",
        pattern=r"""(?:X_FRAME_OPTIONS|FRAME_OPTIONS)\s*[=:]\s*(?:False|false|off|disabled|['"]ALLOWALL['"])""",
        finding_type=InfraFindingType.MISSING_SECURITY_HEADER,
        severity=SecuritySeverity.HIGH,
        title="Clickjacking Protection Disabled",
        description="X-Frame-Options header is disabled or set to ALLOWALL. Application is vulnerable to clickjacking.",
        cwe_id="CWE-1021",
        remediation="Set X-Frame-Options to DENY or SAMEORIGIN.",
        config_key="X_FRAME_OPTIONS",
        recommended_value="DENY",
        confidence=0.85,
    ),
]


class ConfigValidator:
    """
    Validates security settings in configuration files.

    Detects:
    - DEBUG mode enabled
    - Permissive ALLOWED_HOSTS
    - CORS misconfigurations
    - Insecure cookie settings
    - Disabled security features
    """

    def __init__(self, config: Optional[InfraConfig] = None):
        """
        Initialize the configuration validator.

        Args:
            config: Infrastructure configuration. Uses defaults if not provided.
        """
        self.config = config or InfraConfig()
        self.patterns = CONFIG_PATTERNS

    def scan(self, scan_path: Optional[Path] = None) -> InfraReport:
        """
        Scan the specified path for configuration security issues.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            InfraReport containing all findings
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        start_time = time.time()

        report = InfraReport(scan_path=str(path))

        for file_path in scan_directory_for_security(
            path,
            exclude_patterns=self.config.exclude_patterns,
        ):
            report.total_files_scanned += 1

            if self._is_config_file(file_path):
                report.total_config_files += 1

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

    def _scan_file(self, file_path: Path, root_path: Path) -> List[InfraFinding]:
        """
        Scan a single file for configuration security issues.

        Args:
            file_path: Path to the file to scan
            root_path: Root path for relative path calculation

        Returns:
            List of infrastructure findings in the file
        """
        findings: List[InfraFinding] = []

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

                finding = InfraFinding(
                    file_path=str(file_path.relative_to(root_path)),
                    line_number=line_number,
                    column_start=column,
                    column_end=column + len(match.group(0)),
                    finding_type=pattern.finding_type,
                    severity=pattern.severity,
                    title=pattern.title,
                    description=pattern.description,
                    code_snippet=code_snippet,
                    config_key=pattern.config_key,
                    current_value=match.group(0),
                    recommended_value=pattern.recommended_value,
                    cwe_id=pattern.cwe_id,
                    confidence=pattern.confidence,
                    remediation=pattern.remediation,
                    references=[
                        f"https://cwe.mitre.org/data/definitions/{pattern.cwe_id.replace('CWE-', '')}.html",
                    ],
                )

                findings.append(finding)

        return findings

    def _is_config_file(self, file_path: Path) -> bool:
        """Check if a file is a configuration file."""
        return file_path.name in self.config.config_files

    def _is_in_comment(self, lines: List[str], line_number: int) -> bool:
        """Check if a line is inside a comment."""
        if line_number < 1 or line_number > len(lines):
            return False

        line = lines[line_number - 1].strip()

        if line.startswith("#") or line.startswith("//") or line.startswith("*"):
            return True

        if line.startswith("'''") or line.startswith('"""'):
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
