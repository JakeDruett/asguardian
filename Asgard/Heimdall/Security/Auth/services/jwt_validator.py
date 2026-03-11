"""
Heimdall JWT Validator Service

Service for detecting JWT implementation security issues.
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
from Asgard.Heimdall.Security.Auth.utilities.token_utils import (
    extract_algorithm_from_jwt_call,
    find_token_expiration,
)
from Asgard.Heimdall.Security.models.security_models import SecuritySeverity
from Asgard.Heimdall.Security.utilities.security_utils import (
    extract_code_snippet,
    find_line_column,
    is_in_comment_or_docstring,
    scan_directory_for_security,
)


class JWTPattern:
    """Defines a pattern for detecting JWT security issues."""

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


JWT_PATTERNS: List[JWTPattern] = [
    JWTPattern(
        name="jwt_none_algorithm",
        pattern=r"""jwt\.(?:encode|decode)\s*\([^)]*algorithm\s*=\s*['"](?:none|None|NONE)['"]""",
        finding_type=AuthFindingType.JWT_NONE_ALGORITHM,
        severity=SecuritySeverity.CRITICAL,
        title="JWT None Algorithm Used",
        description="JWT is configured with 'none' algorithm which provides no signature verification.",
        cwe_id="CWE-347",
        remediation="Use a secure algorithm like RS256 or ES256. Never use 'none' algorithm.",
        confidence=0.95,
    ),
    JWTPattern(
        name="jwt_hs256_weak",
        pattern=r"""jwt\.encode\s*\([^)]*algorithm\s*=\s*['"]HS256['"]""",
        finding_type=AuthFindingType.WEAK_JWT_ALGORITHM,
        severity=SecuritySeverity.MEDIUM,
        title="JWT Uses HS256 Algorithm",
        description="JWT uses HS256 (symmetric) algorithm. Consider asymmetric algorithms for better security.",
        cwe_id="CWE-327",
        remediation="Use asymmetric algorithms like RS256, ES256, or PS256 for production systems.",
        confidence=0.6,
    ),
    JWTPattern(
        name="jwt_decode_no_verify",
        pattern=r"""jwt\.decode\s*\([^)]*(?:verify\s*=\s*False|options\s*=\s*\{[^}]*verify[^}]*False)""",
        finding_type=AuthFindingType.WEAK_JWT_ALGORITHM,
        severity=SecuritySeverity.CRITICAL,
        title="JWT Signature Verification Disabled",
        description="JWT decode is called with signature verification disabled.",
        cwe_id="CWE-347",
        remediation="Always verify JWT signatures. Never disable verification in production.",
        confidence=0.9,
    ),
    JWTPattern(
        name="jwt_secret_in_code",
        pattern=r"""(?:jwt_secret|JWT_SECRET|secret_key|SECRET_KEY)\s*=\s*['"][^'"]{8,}['"]""",
        finding_type=AuthFindingType.HARDCODED_CREDENTIALS,
        severity=SecuritySeverity.HIGH,
        title="JWT Secret Hardcoded",
        description="JWT secret key appears to be hardcoded in source code.",
        cwe_id="CWE-798",
        remediation="Store JWT secrets in environment variables or a secure vault.",
        confidence=0.75,
    ),
    JWTPattern(
        name="jwt_weak_secret",
        pattern=r"""jwt\.encode\s*\([^)]*,\s*['"](?:secret|password|key|test|dev|123|abc)['"]""",
        finding_type=AuthFindingType.HARDCODED_CREDENTIALS,
        severity=SecuritySeverity.CRITICAL,
        title="JWT Uses Weak Secret",
        description="JWT is signed with a weak or common secret key.",
        cwe_id="CWE-521",
        remediation="Use a strong, randomly generated secret key of at least 256 bits.",
        confidence=0.85,
    ),
]


class JWTValidator:
    """
    Validates JWT implementation security.

    Detects:
    - Weak or 'none' algorithms
    - Missing token expiration
    - Hardcoded secrets
    - Disabled signature verification
    """

    def __init__(self, config: Optional[AuthConfig] = None):
        """
        Initialize the JWT validator.

        Args:
            config: Auth configuration. Uses defaults if not provided.
        """
        self.config = config or AuthConfig()
        self.patterns = JWT_PATTERNS

    def scan(self, scan_path: Optional[Path] = None) -> AuthReport:
        """
        Scan the specified path for JWT security issues.

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

    # Patterns that indicate enum value definitions, not actual hardcoded credentials
    ENUM_VALUE_PATTERNS = [
        r"^secret$", r"^secret[_-]?key$", r"^jwt[_-]?secret$",
        r"^api[_-]?key$", r"^access[_-]?key$", r"^access[_-]?token$",
        r"^auth[_-]?token$", r"^oauth[_-]?token$", r"^private[_-]?key$",
        r"^client[_-]?secret$", r"^auth[_-]?secret$",
    ]

    # Patterns indicating intentional JWT verification bypass (legitimate use cases)
    INTENTIONAL_NO_VERIFY_PATTERNS = [
        r"decode_without_verification",
        r"decode_unverified",
        r"inspect_token",
        r"extract_claims",
        r"get_unverified_header",
        r"peek_token",
        r"except\s+.*Error",  # Inside exception handler
        r"WARNING",  # Has warning in context
        r"debug",  # Debug function
        r"logging",  # Logging context
    ]

    def _scan_file(self, file_path: Path, root_path: Path) -> List[AuthFinding]:
        """
        Scan a single file for JWT security issues.

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
        file_ext = file_path.suffix.lower()

        for pattern in self.patterns:
            for match in pattern.pattern.finditer(content):
                line_number, column = find_line_column(content, match.start())

                # Skip matches in comments or docstrings
                if is_in_comment_or_docstring(content, lines, line_number, match.start(), file_ext):
                    continue

                # Check for false positive enum values
                if self._is_enum_value(match.group(0)):
                    continue

                # For JWT signature verification disabled pattern, check for legitimate use cases
                if pattern.name == "jwt_decode_no_verify":
                    if self._is_intentional_no_verify(content, match.start(), lines, line_number):
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

        expiration_findings = self._check_token_expiration(content, lines, file_path, root_path)
        findings.extend(expiration_findings)

        return findings

    def _check_token_expiration(
        self,
        content: str,
        lines: List[str],
        file_path: Path,
        root_path: Path,
    ) -> List[AuthFinding]:
        """
        Check for missing token expiration.

        Args:
            content: File content
            lines: File lines
            file_path: Path to file
            root_path: Root path

        Returns:
            List of findings for missing expiration
        """
        findings = []

        exp_results = find_token_expiration(content)

        for line_number, has_exp, context in exp_results:
            if not has_exp:
                code_snippet = extract_code_snippet(lines, line_number)

                finding = AuthFinding(
                    file_path=str(file_path.relative_to(root_path)),
                    line_number=line_number,
                    finding_type=AuthFindingType.MISSING_TOKEN_EXPIRATION,
                    severity=SecuritySeverity.HIGH,
                    title="JWT Missing Expiration Claim",
                    description="JWT token is created without an expiration (exp) claim.",
                    code_snippet=code_snippet,
                    cwe_id="CWE-613",
                    confidence=0.7,
                    remediation=(
                        "Add an 'exp' claim to JWT tokens. Use a reasonable expiration time "
                        "(e.g., 15 minutes for access tokens, 7 days for refresh tokens)."
                    ),
                    references=[
                        "https://cwe.mitre.org/data/definitions/613.html",
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

    def _is_enum_value(self, matched_text: str) -> bool:
        """Check if matched text is an enum value definition, not a real credential."""
        # Extract the value part (after = sign)
        if "=" in matched_text:
            value_part = matched_text.split("=", 1)[1].strip().strip("'\"")
            for pattern in self.ENUM_VALUE_PATTERNS:
                if re.match(pattern, value_part, re.IGNORECASE):
                    return True
        return False

    def _is_intentional_no_verify(
        self,
        content: str,
        match_start: int,
        lines: List[str],
        line_number: int
    ) -> bool:
        """
        Check if JWT verification disabled is intentional/legitimate.

        Legitimate use cases include:
        - Debug/inspection functions with clear naming
        - Error handling to extract info from failed tokens
        - Functions with WARNING documentation

        Args:
            content: Full file content
            match_start: Start position of the match
            lines: File content as lines
            line_number: Line number of the match

        Returns:
            True if the unverified decode appears intentional
        """
        # Get context around the match (function/method context)
        context_start = max(0, match_start - 500)
        context_end = min(len(content), match_start + 200)
        context = content[context_start:context_end]

        # Check for patterns indicating intentional use
        for pattern in self.INTENTIONAL_NO_VERIFY_PATTERNS:
            if re.search(pattern, context, re.IGNORECASE):
                return True

        # Check if we're inside a try-except block (error handling)
        # Look backwards for "try:" and forwards for "except"
        before_match = content[max(0, match_start - 300):match_start]
        after_match = content[match_start:min(len(content), match_start + 300)]

        if "try:" in before_match and "except" in after_match:
            return True

        # Check if the enclosing function has a warning-related docstring
        # Look for function definition before this line
        for i in range(line_number - 1, max(0, line_number - 30), -1):
            if i < len(lines):
                line = lines[i].strip()
                if line.startswith("def "):
                    # Check if next few lines contain WARNING in docstring
                    docstring_check = "\n".join(lines[i:min(len(lines), i + 10)])
                    if "WARNING" in docstring_check or "Never trust" in docstring_check:
                        return True
                    # Check if function name suggests debug/inspection purpose
                    if any(pattern in line.lower() for pattern in ["without_verification", "unverified", "inspect", "debug", "peek"]):
                        return True
                    break

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
