"""
Heimdall Secrets Detection Service

Service for detecting hardcoded secrets, API keys, passwords, and other sensitive
data in source code files.
"""

import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple

from Asgard.Heimdall.Security.models.security_models import (
    SecretFinding,
    SecretType,
    SecretsReport,
    SecurityScanConfig,
    SecuritySeverity,
)
from Asgard.Heimdall.Security.utilities.security_utils import (
    calculate_entropy,
    extract_code_snippet,
    find_line_column,
    is_in_comment_or_docstring,
    is_example_or_placeholder,
    mask_secret,
    read_file_lines,
    scan_directory_for_security,
)


class SecretPattern:
    """Defines a pattern for detecting a specific type of secret."""

    def __init__(
        self,
        name: str,
        pattern: str,
        secret_type: SecretType,
        severity: SecuritySeverity,
        description: str = "",
        min_entropy: float = 0.0,
        remediation: str = "",
    ):
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        self.secret_type = secret_type
        self.severity = severity
        self.description = description
        self.min_entropy = min_entropy
        self.remediation = remediation


DEFAULT_SECRET_PATTERNS: List[SecretPattern] = [
    SecretPattern(
        name="aws_access_key",
        pattern=r"(?:AKIA|ABIA|ACCA)[0-9A-Z]{16}",
        secret_type=SecretType.AWS_CREDENTIALS,
        severity=SecuritySeverity.CRITICAL,
        description="AWS Access Key ID",
        remediation="Move AWS credentials to environment variables or AWS credentials file. Use IAM roles when possible.",
    ),
    SecretPattern(
        name="aws_secret_key",
        pattern=r"(?:aws_secret_access_key|aws_secret_key|secret_access_key)\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
        secret_type=SecretType.AWS_CREDENTIALS,
        severity=SecuritySeverity.CRITICAL,
        description="AWS Secret Access Key",
        min_entropy=4.0,
        remediation="Move AWS credentials to environment variables or AWS credentials file. Use IAM roles when possible.",
    ),
    SecretPattern(
        name="azure_storage_key",
        pattern=r"(?:DefaultEndpointsProtocol=https;AccountName=)[^\s;]+;AccountKey=[A-Za-z0-9+/=]{88}",
        secret_type=SecretType.AZURE_CREDENTIALS,
        severity=SecuritySeverity.CRITICAL,
        description="Azure Storage Account Key",
        remediation="Use Azure Key Vault or managed identities for Azure credentials.",
    ),
    SecretPattern(
        name="gcp_service_account",
        pattern=r'"type"\s*:\s*"service_account".*"private_key"\s*:\s*"-----BEGIN',
        secret_type=SecretType.GCP_CREDENTIALS,
        severity=SecuritySeverity.CRITICAL,
        description="GCP Service Account Key",
        remediation="Use GCP Secret Manager or workload identity federation.",
    ),
    SecretPattern(
        name="generic_api_key",
        pattern=r"(?:api[_-]?key|apikey)\s*[=:]\s*['\"]?([A-Za-z0-9_\-]{20,64})['\"]?",
        secret_type=SecretType.API_KEY,
        severity=SecuritySeverity.HIGH,
        description="Generic API Key",
        min_entropy=3.5,
        remediation="Store API keys in environment variables or a secrets manager.",
    ),
    SecretPattern(
        name="generic_secret",
        pattern=r"(?:secret|secret[_-]?key|client[_-]?secret)\s*[=:]\s*['\"]?([A-Za-z0-9_\-]{16,64})['\"]?",
        secret_type=SecretType.SECRET_KEY,
        severity=SecuritySeverity.HIGH,
        description="Generic Secret Key",
        min_entropy=3.5,
        remediation="Store secrets in environment variables or a secrets manager.",
    ),
    SecretPattern(
        name="password_assignment",
        pattern=r"(?:password|passwd|pwd)\s*[=:]\s*['\"]([^'\"]{8,})['\"]",
        secret_type=SecretType.PASSWORD,
        severity=SecuritySeverity.HIGH,
        description="Hardcoded Password",
        min_entropy=2.0,
        remediation="Never hardcode passwords. Use environment variables or a secrets manager.",
    ),
    SecretPattern(
        name="private_key_header",
        pattern=r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----",
        secret_type=SecretType.PRIVATE_KEY,
        severity=SecuritySeverity.CRITICAL,
        description="Private Key",
        remediation="Store private keys in secure key management systems. Never commit to version control.",
    ),
    SecretPattern(
        name="jwt_token",
        pattern=r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        secret_type=SecretType.JWT_TOKEN,
        severity=SecuritySeverity.HIGH,
        description="JWT Token",
        remediation="JWT tokens should not be hardcoded. Use proper token management.",
    ),
    SecretPattern(
        name="github_token",
        pattern=r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}",
        secret_type=SecretType.ACCESS_TOKEN,
        severity=SecuritySeverity.CRITICAL,
        description="GitHub Token",
        remediation="Use GitHub Actions secrets or environment variables for tokens.",
    ),
    SecretPattern(
        name="slack_token",
        pattern=r"xox[baprs]-[A-Za-z0-9-]{10,}",
        secret_type=SecretType.ACCESS_TOKEN,
        severity=SecuritySeverity.HIGH,
        description="Slack Token",
        remediation="Store Slack tokens in environment variables or secrets manager.",
    ),
    SecretPattern(
        name="stripe_key",
        pattern=r"(?:sk|pk)_(?:test|live)_[A-Za-z0-9]{24,}",
        secret_type=SecretType.API_KEY,
        severity=SecuritySeverity.CRITICAL,
        description="Stripe API Key",
        remediation="Use environment variables for Stripe keys. Never expose live keys.",
    ),
    SecretPattern(
        name="sendgrid_key",
        pattern=r"SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}",
        secret_type=SecretType.API_KEY,
        severity=SecuritySeverity.HIGH,
        description="SendGrid API Key",
        remediation="Store SendGrid keys in environment variables.",
    ),
    SecretPattern(
        name="twilio_key",
        pattern=r"SK[a-f0-9]{32}",
        secret_type=SecretType.API_KEY,
        severity=SecuritySeverity.HIGH,
        description="Twilio API Key",
        remediation="Store Twilio keys in environment variables.",
    ),
    SecretPattern(
        name="database_url",
        pattern=r"(?:postgres|mysql|mongodb|redis|amqp)(?:ql)?://[^\s'\"]+:[^\s'\"]+@[^\s'\"]+",
        secret_type=SecretType.DATABASE_URL,
        severity=SecuritySeverity.CRITICAL,
        description="Database Connection String with Credentials",
        remediation="Use environment variables for database connection strings.",
    ),
    SecretPattern(
        name="ssh_private_key",
        pattern=r"-----BEGIN OPENSSH PRIVATE KEY-----",
        secret_type=SecretType.SSH_KEY,
        severity=SecuritySeverity.CRITICAL,
        description="SSH Private Key",
        remediation="Never commit SSH keys. Use SSH agent or key management systems.",
    ),
    SecretPattern(
        name="oauth_token",
        pattern=r"(?:oauth[_-]?token|access[_-]?token|bearer[_-]?token)\s*[=:]\s*['\"]?([A-Za-z0-9_\-\.]{20,})['\"]?",
        secret_type=SecretType.OAUTH_TOKEN,
        severity=SecuritySeverity.HIGH,
        description="OAuth/Bearer Token",
        min_entropy=3.0,
        remediation="Store OAuth tokens securely. Use proper token refresh mechanisms.",
    ),
    SecretPattern(
        name="heroku_api_key",
        pattern=r"(?:heroku[_-]?api[_-]?key)\s*[=:]\s*['\"]?([a-f0-9-]{36})['\"]?",
        secret_type=SecretType.API_KEY,
        severity=SecuritySeverity.HIGH,
        description="Heroku API Key",
        remediation="Use environment variables for Heroku API keys.",
    ),
    SecretPattern(
        name="mailchimp_key",
        pattern=r"[a-f0-9]{32}-us[0-9]{1,2}",
        secret_type=SecretType.API_KEY,
        severity=SecuritySeverity.MEDIUM,
        description="Mailchimp API Key",
        remediation="Store Mailchimp keys in environment variables.",
    ),
    SecretPattern(
        name="base64_encoded_secret",
        pattern=r"(?:basic|bearer)\s+[A-Za-z0-9+/]{40,}={0,2}",
        secret_type=SecretType.GENERIC_SECRET,
        severity=SecuritySeverity.MEDIUM,
        description="Base64 Encoded Authentication",
        min_entropy=4.0,
        remediation="Avoid hardcoding authentication headers.",
    ),
]

FALSE_POSITIVE_PATTERNS: List[Pattern] = [
    re.compile(r"example|sample|test|dummy|fake|placeholder|your[_-]?key", re.IGNORECASE),
    re.compile(r"xxx+|000+|111+|aaa+", re.IGNORECASE),
    re.compile(r"<[^>]+>"),
    re.compile(r"\$\{[^}]+\}"),
    re.compile(r"%\([^)]+\)s"),
    re.compile(r"process\.env\.[A-Z_]+"),
    re.compile(r"os\.environ\["),
    re.compile(r"getenv\("),
    # Python f-string variables in connection strings (e.g., f"redis://:{self.password}@{host}")
    re.compile(r"\{self\.\w+\}"),
    re.compile(r"\{[a-z_]+\}"),  # f-string variable references like {password}
    # Enum value definitions - these are type identifiers, not actual secrets
    re.compile(r"^password$", re.IGNORECASE),
    re.compile(r"^passwd$", re.IGNORECASE),
    re.compile(r"^secret$", re.IGNORECASE),
    re.compile(r"^secret[_-]?key$", re.IGNORECASE),
    re.compile(r"^api[_-]?key$", re.IGNORECASE),
    re.compile(r"^access[_-]?key$", re.IGNORECASE),
    re.compile(r"^access[_-]?token$", re.IGNORECASE),
    re.compile(r"^auth[_-]?token$", re.IGNORECASE),
    re.compile(r"^oauth[_-]?token$", re.IGNORECASE),
    re.compile(r"^private[_-]?key$", re.IGNORECASE),
    re.compile(r"^client[_-]?secret$", re.IGNORECASE),
    re.compile(r"^auth[_-]?secret$", re.IGNORECASE),
    re.compile(r"^jwt[_-]?secret$", re.IGNORECASE),
    re.compile(r"^database[_-]?url$", re.IGNORECASE),
    re.compile(r"^connection[_-]?string$", re.IGNORECASE),
    re.compile(r"^rabbitmq[_-]?password$", re.IGNORECASE),
    re.compile(r"^not[_-]?a[_-]?password$", re.IGNORECASE),
]


class SecretsDetectionService:
    """
    Detects hardcoded secrets and sensitive data in source code.

    Supports detection of:
    - API keys (AWS, Azure, GCP, generic)
    - Passwords and credentials
    - Private keys and certificates
    - Database connection strings
    - OAuth/JWT tokens
    - Service-specific tokens (GitHub, Slack, Stripe, etc.)
    """

    def __init__(self, config: Optional[SecurityScanConfig] = None):
        """
        Initialize the secrets detection service.

        Args:
            config: Security scan configuration. Uses defaults if not provided.
        """
        self.config = config or SecurityScanConfig()
        self.patterns = list(DEFAULT_SECRET_PATTERNS)

        for name, pattern in self.config.custom_patterns.items():
            self.patterns.append(
                SecretPattern(
                    name=f"custom_{name}",
                    pattern=pattern,
                    secret_type=SecretType.GENERIC_SECRET,
                    severity=SecuritySeverity.HIGH,
                    description=f"Custom pattern: {name}",
                )
            )

    def scan(self, scan_path: Optional[Path] = None) -> SecretsReport:
        """
        Scan the specified path for hardcoded secrets.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            SecretsReport containing all findings
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        start_time = time.time()

        report = SecretsReport(
            scan_path=str(path),
            patterns_used=[p.name for p in self.patterns],
        )

        for file_path in scan_directory_for_security(
            path,
            exclude_patterns=self.config.exclude_patterns,
            include_extensions=self.config.include_extensions,
        ):
            if str(file_path) in self.config.ignore_paths:
                continue

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

    def _scan_file(self, file_path: Path, root_path: Path) -> List[SecretFinding]:
        """
        Scan a single file for secrets.

        Args:
            file_path: Path to the file to scan
            root_path: Root path for relative path calculation

        Returns:
            List of secret findings in the file
        """
        findings: List[SecretFinding] = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except (IOError, OSError):
            return findings

        lines = content.split("\n")
        file_ext = file_path.suffix.lower()

        for pattern in self.patterns:
            for match in pattern.pattern.finditer(content):
                matched_text = match.group(0)
                secret_value = match.group(1) if match.lastindex and match.lastindex >= 1 else matched_text

                line_number, column = find_line_column(content, match.start())

                # Skip matches in comments or docstrings
                if is_in_comment_or_docstring(content, lines, line_number, match.start(), file_ext):
                    continue

                # Check if this is an example or placeholder
                context_start = max(0, match.start() - 200)
                context_end = min(len(content), match.end() + 100)
                context = content[context_start:context_end]

                if is_example_or_placeholder(secret_value, context):
                    continue

                if self._is_false_positive(secret_value, matched_text, content, match.start()):
                    continue

                if pattern.min_entropy > 0:
                    entropy = calculate_entropy(secret_value)
                    if entropy < pattern.min_entropy:
                        continue

                line_content = lines[line_number - 1] if line_number <= len(lines) else ""

                finding = SecretFinding(
                    file_path=str(file_path.relative_to(root_path)),
                    line_number=line_number,
                    column_start=column,
                    column_end=column + len(matched_text),
                    secret_type=pattern.secret_type,
                    severity=pattern.severity,
                    pattern_name=pattern.name,
                    masked_value=mask_secret(secret_value),
                    line_content=self._sanitize_line(line_content, secret_value),
                    confidence=self._calculate_confidence(pattern, secret_value, entropy if pattern.min_entropy > 0 else None),
                    remediation=pattern.remediation or f"Remove hardcoded {pattern.description.lower()} from source code.",
                )

                findings.append(finding)

        return findings

    def _is_false_positive(
        self,
        secret_value: str,
        matched_text: str,
        content: str,
        match_start: int
    ) -> bool:
        """
        Check if a match is likely a false positive.

        Args:
            secret_value: The detected secret value
            matched_text: The full matched text
            content: Full file content
            match_start: Start position of the match

        Returns:
            True if the match is likely a false positive
        """
        for fp_pattern in FALSE_POSITIVE_PATTERNS:
            if fp_pattern.search(secret_value):
                return True
            if fp_pattern.search(matched_text):
                return True

        context_start = max(0, match_start - 100)
        context_end = min(len(content), match_start + len(matched_text) + 100)
        context = content[context_start:context_end]

        if "example" in context.lower() or "sample" in context.lower():
            return True

        if "process.env" in context or "os.environ" in context or "getenv" in context:
            return True

        return False

    def _calculate_confidence(
        self,
        pattern: SecretPattern,
        secret_value: str,
        entropy: Optional[float]
    ) -> float:
        """
        Calculate confidence score for a finding.

        Args:
            pattern: The pattern that matched
            secret_value: The secret value detected
            entropy: Entropy of the secret (if calculated)

        Returns:
            Confidence score between 0 and 1
        """
        confidence = 0.7

        if pattern.secret_type in {SecretType.PRIVATE_KEY, SecretType.SSH_KEY}:
            confidence = 0.95

        if pattern.name.startswith("aws_") or pattern.name.startswith("github_"):
            confidence = 0.9

        if entropy:
            if entropy > 4.5:
                confidence = min(0.95, confidence + 0.1)
            elif entropy < 3.0:
                confidence = max(0.3, confidence - 0.2)

        if len(secret_value) > 32:
            confidence = min(0.95, confidence + 0.05)

        return round(confidence, 2)

    def _sanitize_line(self, line: str, secret_value: str) -> str:
        """
        Sanitize a line by masking the secret value.

        Args:
            line: The original line content
            secret_value: The secret value to mask

        Returns:
            Sanitized line with masked secret
        """
        if secret_value in line:
            return line.replace(secret_value, mask_secret(secret_value))
        return line

    def _severity_meets_threshold(self, severity: str) -> bool:
        """
        Check if a severity level meets the configured threshold.

        Args:
            severity: The severity level to check

        Returns:
            True if the severity meets or exceeds the threshold
        """
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
        """
        Get sort order for severity (critical first).

        Args:
            severity: The severity level

        Returns:
            Sort order (lower = higher priority)
        """
        order = {
            SecuritySeverity.CRITICAL.value: 0,
            SecuritySeverity.HIGH.value: 1,
            SecuritySeverity.MEDIUM.value: 2,
            SecuritySeverity.LOW.value: 3,
            SecuritySeverity.INFO.value: 4,
        }
        return order.get(severity, 5)

    def add_pattern(self, pattern: SecretPattern) -> None:
        """
        Add a custom pattern to the detection list.

        Args:
            pattern: The pattern to add
        """
        self.patterns.append(pattern)

    def get_patterns(self) -> List[str]:
        """
        Get list of pattern names being used.

        Returns:
            List of pattern names
        """
        return [p.name for p in self.patterns]
