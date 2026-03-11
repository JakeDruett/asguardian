"""
Heimdall Password Analyzer Service

Service for detecting password handling security issues.
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
    is_in_comment_or_docstring,
    scan_directory_for_security,
)


class PasswordPattern:
    """Defines a pattern for detecting password security issues."""

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


PASSWORD_PATTERNS: List[PasswordPattern] = [
    PasswordPattern(
        name="plaintext_password_compare",
        pattern=r"""if\s+.*password\s*[=!]=\s*(?:user|account|record)\.password""",
        finding_type=AuthFindingType.PLAINTEXT_PASSWORD,
        severity=SecuritySeverity.CRITICAL,
        title="Plaintext Password Comparison",
        description="Password appears to be compared directly without hashing.",
        cwe_id="CWE-256",
        remediation="Use bcrypt, argon2, or scrypt to hash and verify passwords.",
        confidence=0.85,
    ),
    PasswordPattern(
        name="password_in_log",
        pattern=r"""(?:log|logger|print|console\.log)\s*\([^)]*password""",
        finding_type=AuthFindingType.PASSWORD_IN_LOG,
        severity=SecuritySeverity.CRITICAL,
        title="Password Logged",
        description="Password is being written to logs.",
        cwe_id="CWE-532",
        remediation="Never log passwords or sensitive credentials. Remove password from log statements.",
        confidence=0.9,
    ),
    PasswordPattern(
        name="password_in_error",
        pattern=r"""(?:raise|throw)\s+.*password""",
        finding_type=AuthFindingType.PASSWORD_IN_LOG,
        severity=SecuritySeverity.HIGH,
        title="Password in Error Message",
        description="Password may be included in error messages.",
        cwe_id="CWE-209",
        remediation="Remove sensitive data from error messages.",
        confidence=0.7,
    ),
    PasswordPattern(
        name="md5_password_hash",
        pattern=r"""(?:hashlib\.md5|md5\s*\()\s*\([^)]*password""",
        finding_type=AuthFindingType.WEAK_PASSWORD_HASH,
        severity=SecuritySeverity.CRITICAL,
        title="MD5 Used for Password Hashing",
        description="MD5 is cryptographically broken and should not be used for passwords.",
        cwe_id="CWE-328",
        remediation="Use bcrypt, argon2, or PBKDF2 with a high iteration count.",
        confidence=0.95,
    ),
    PasswordPattern(
        name="sha1_password_hash",
        pattern=r"""(?:hashlib\.sha1|sha1\s*\()\s*\([^)]*password""",
        finding_type=AuthFindingType.WEAK_PASSWORD_HASH,
        severity=SecuritySeverity.HIGH,
        title="SHA1 Used for Password Hashing",
        description="SHA1 is deprecated for security use and should not be used for passwords.",
        cwe_id="CWE-328",
        remediation="Use bcrypt, argon2, or PBKDF2 with a high iteration count.",
        confidence=0.9,
    ),
    PasswordPattern(
        name="sha256_no_salt",
        pattern=r"""hashlib\.sha256\s*\(\s*password""",
        finding_type=AuthFindingType.WEAK_PASSWORD_HASH,
        severity=SecuritySeverity.HIGH,
        title="SHA256 Password Without Salt",
        description="Password hashed with SHA256 without visible salt, vulnerable to rainbow tables.",
        cwe_id="CWE-916",
        remediation="Use bcrypt or argon2 which include automatic salting.",
        confidence=0.75,
    ),
    PasswordPattern(
        name="hardcoded_password",
        pattern=r"""(?:password|passwd|pwd)\s*=\s*['"][^'"]{4,}['"]""",
        finding_type=AuthFindingType.HARDCODED_CREDENTIALS,
        severity=SecuritySeverity.HIGH,
        title="Hardcoded Password",
        description="Password appears to be hardcoded in source code.",
        cwe_id="CWE-798",
        remediation="Store passwords in environment variables or a secure vault.",
        confidence=0.7,
    ),
    PasswordPattern(
        name="password_in_url",
        pattern=r"""(?:url|uri|endpoint)\s*=.*password\s*=""",
        finding_type=AuthFindingType.HARDCODED_CREDENTIALS,
        severity=SecuritySeverity.HIGH,
        title="Password in URL",
        description="Password appears to be included in a URL.",
        cwe_id="CWE-598",
        remediation="Never include passwords in URLs. Use POST requests with encrypted body.",
        confidence=0.8,
    ),
    PasswordPattern(
        name="password_storage_plain",
        pattern=r"""(?:user|account)\.password\s*=\s*(?:request|form|data)\.(?:password|pwd)""",
        finding_type=AuthFindingType.PLAINTEXT_PASSWORD,
        severity=SecuritySeverity.CRITICAL,
        title="Password Stored Without Hashing",
        description="Password is being stored directly from user input without hashing.",
        cwe_id="CWE-256",
        remediation="Hash passwords using bcrypt or argon2 before storing.",
        confidence=0.85,
    ),
]


class PasswordAnalyzer:
    """
    Analyzes password handling security.

    Detects:
    - Plaintext password storage
    - Passwords in logs
    - Weak password hashing
    - Hardcoded credentials
    """

    def __init__(self, config: Optional[AuthConfig] = None):
        """
        Initialize the password analyzer.

        Args:
            config: Auth configuration. Uses defaults if not provided.
        """
        self.config = config or AuthConfig()
        self.patterns = PASSWORD_PATTERNS

    def scan(self, scan_path: Optional[Path] = None) -> AuthReport:
        """
        Scan the specified path for password security issues.

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

    # Patterns that indicate enum value definitions, not actual hardcoded credentials
    ENUM_VALUE_PATTERNS = [
        r"^password$", r"^passwd$", r"^secret$", r"^secret[_-]?key$",
        r"^api[_-]?key$", r"^access[_-]?key$", r"^access[_-]?token$",
        r"^auth[_-]?token$", r"^oauth[_-]?token$", r"^private[_-]?key$",
        r"^client[_-]?secret$", r"^auth[_-]?secret$", r"^jwt[_-]?secret$",
        r"^not[_-]?a[_-]?password$", r"^rabbitmq[_-]?password$",
    ]

    def _scan_file(self, file_path: Path, root_path: Path) -> List[AuthFinding]:
        """
        Scan a single file for password security issues.

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

                # Check for false positive in comments or docstrings
                file_ext = file_path.suffix
                if is_in_comment_or_docstring(content, lines, line_number, match.start(), file_ext):
                    continue

                # Check for false positive enum values
                if self._is_enum_value(match.group(0)):
                    continue

                # Check for false positive JSON/documentation examples
                if self._is_json_example(content, match.start()):
                    continue

                # Check if "password" is just mentioned in a message, not logged as a value
                if pattern.name == "password_in_log" and self._is_status_message(match.group(0)):
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

    def _is_enum_value(self, matched_text: str) -> bool:
        """Check if matched text is an enum value definition, not a real credential."""
        # Extract the value part (after = sign)
        if "=" in matched_text:
            value_part = matched_text.split("=", 1)[1].strip().strip("'\"")
            for pattern in self.ENUM_VALUE_PATTERNS:
                if re.match(pattern, value_part, re.IGNORECASE):
                    return True
        return False

    def _is_status_message(self, matched_text: str) -> bool:
        """
        Check if the log statement just mentions 'password' in text, not logging actual value.

        Returns True for status messages like:
        - "updating password"
        - "password changed"
        - "resetting password"

        Returns False for actual password logging like:
        - f"Password: {password}"
        - f"password={user.password}"
        """
        lower_match = matched_text.lower()

        # Check if password is followed by variable interpolation (actual logging)
        # Patterns like: password={, password:", password=', password+, password:
        actual_password_patterns = [
            r'password\s*[=:]\s*[{"\'\[]',  # password={var} or password="val" etc
            r'password\s*[=:]\s*\$',  # password=$var
            r'password\s*[=:]\s*%',  # password=%s
            r'\{[^}]*password[^}]*\}',  # {password} or {user.password}
            r'password\s*\+',  # password + var
        ]

        for pattern in actual_password_patterns:
            if re.search(pattern, lower_match):
                return False  # This looks like actual password logging

        # Status message patterns (just mentioning password, not logging it)
        status_patterns = [
            r'(updating|update|changed|change|reset|resetting|rotating|rotated)\s+password',
            r'password\s+(updated|changed|reset|rotated|failed|succeeded|complete)',
            r'(new|old|current|temporary)\s+password\s+\w',  # "new password set"
            r'password\s+(is|was|has|will)',  # "password is being reset"
        ]

        for pattern in status_patterns:
            if re.search(pattern, lower_match):
                return True  # This is just a status message

        return False

    def _is_json_example(self, content: str, match_start: int) -> bool:
        """
        Check if match is inside a JSON documentation/example context.

        Detects patterns like:
        - "credential_type": "password" (JSON key definition)
        - print('''{ ... "password" ... }''') (JSON example in print)
        """
        # Look for context around the match
        context_start = max(0, match_start - 200)
        context_end = min(len(content), match_start + 200)
        context = content[context_start:context_end]

        # Check if it looks like JSON example in a print statement
        if 'print(' in context and ('"""' in context or "'''" in context):
            # Check if the pattern is part of a JSON structure example
            json_indicators = [
                '"credential_type":', "'credential_type':",
                '"type":', '"field":', '"key":',
                '"example"', '"sample"', 'example:', 'sample:',
            ]
            if any(ind in context.lower() for ind in json_indicators):
                return True

        # Check if "password" is a JSON key/type value, not an actual password
        # Pattern: "credential_type": "password" or "type": "password"
        type_patterns = [
            r'"(?:credential_type|type|field_type|secret_type)":\s*"password"',
            r"'(?:credential_type|type|field_type|secret_type)':\s*'password'",
        ]
        for pattern in type_patterns:
            if re.search(pattern, context, re.IGNORECASE):
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
