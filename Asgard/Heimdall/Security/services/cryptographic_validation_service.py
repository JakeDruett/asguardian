"""
Heimdall Cryptographic Validation Service

Service for detecting insecure cryptographic implementations,
weak algorithms, and cryptographic anti-patterns.
"""

import re
import time
from pathlib import Path
from typing import List, Optional, Set

from Asgard.Heimdall.Security.models.security_models import (
    CryptoFinding,
    CryptoReport,
    SecurityScanConfig,
    SecuritySeverity,
)
from Asgard.Heimdall.Security.utilities.security_utils import (
    extract_code_snippet,
    find_line_column,
    is_in_comment_or_docstring,
    scan_directory_for_security,
)


class CryptoPattern:
    """Defines a pattern for detecting cryptographic issues."""

    def __init__(
        self,
        name: str,
        pattern: str,
        severity: SecuritySeverity,
        issue_type: str,
        algorithm: str,
        description: str,
        recommendation: str,
        file_types: Optional[Set[str]] = None,
    ):
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        self.severity = severity
        self.issue_type = issue_type
        self.algorithm = algorithm
        self.description = description
        self.recommendation = recommendation
        self.file_types = file_types or {".py", ".js", ".ts", ".java", ".go", ".rb", ".php"}


CRYPTO_PATTERNS: List[CryptoPattern] = [
    CryptoPattern(
        name="md5_hash",
        pattern=r"""(?:hashlib\.md5|MD5\.new|md5\(|createHash\(['""]md5['""]|MessageDigest\.getInstance\(['""]MD5['""])""",
        severity=SecuritySeverity.HIGH,
        issue_type="weak_hash",
        algorithm="MD5",
        description="MD5 is cryptographically broken and should not be used for security purposes.",
        recommendation="Use SHA-256 or SHA-3 for hashing. For passwords, use bcrypt, scrypt, or Argon2.",
    ),
    CryptoPattern(
        name="sha1_hash",
        pattern=r"""(?:hashlib\.sha1|SHA1\.new|sha1\(|createHash\(['""]sha1['""]|MessageDigest\.getInstance\(['""]SHA-?1['""])""",
        severity=SecuritySeverity.MEDIUM,
        issue_type="weak_hash",
        algorithm="SHA-1",
        description="SHA-1 is deprecated and vulnerable to collision attacks.",
        recommendation="Use SHA-256 or SHA-3 for hashing. For passwords, use bcrypt, scrypt, or Argon2.",
    ),
    CryptoPattern(
        name="des_encryption",
        pattern=r"""(?:DES\.new|DES3\.new|TripleDES|createCipheriv\(['""]des|Cipher\.getInstance\(['""]DES)""",
        severity=SecuritySeverity.HIGH,
        issue_type="weak_cipher",
        algorithm="DES/3DES",
        description="DES and 3DES are deprecated due to small block and key sizes.",
        recommendation="Use AES-256-GCM or ChaCha20-Poly1305 for symmetric encryption.",
    ),
    CryptoPattern(
        name="ecb_mode",
        pattern=r"""(?:MODE_ECB|AES\.MODE_ECB|mode\s*[:=]\s*['""]ECB['""]|createCipheriv\(['""]aes-\d+-ecb)""",
        severity=SecuritySeverity.HIGH,
        issue_type="insecure_mode",
        algorithm="ECB Mode",
        description="ECB mode leaks information about plaintext patterns.",
        recommendation="Use GCM, CCM, or CBC with HMAC for authenticated encryption.",
    ),
    CryptoPattern(
        name="static_iv",
        pattern=r"""(?:iv\s*=\s*['""][A-Za-z0-9+/=]{16,}['""]|IV\s*=\s*['""][A-Za-z0-9+/=]{16,}['""]|nonce\s*=\s*['""][^'"]+['""])""",
        severity=SecuritySeverity.HIGH,
        issue_type="static_iv",
        algorithm="Static IV/Nonce",
        description="Static IV or nonce reuse can compromise encryption security.",
        recommendation="Generate a random IV/nonce for each encryption operation.",
    ),
    CryptoPattern(
        name="hardcoded_key",
        pattern=r"""(?:(?:secret|encryption|aes|private)[_-]?key\s*=\s*['""][A-Za-z0-9+/=]{16,}['""])""",
        severity=SecuritySeverity.CRITICAL,
        issue_type="hardcoded_key",
        algorithm="Hardcoded Key",
        description="Cryptographic keys should never be hardcoded in source code.",
        recommendation="Store keys in environment variables, key vaults, or secure key management systems.",
    ),
    CryptoPattern(
        name="weak_random",
        pattern=r"""(?:random\.random\(\)|random\.randint|Math\.random\(\)|rand\(\)|mt_rand)(?![A-Za-z])""",
        severity=SecuritySeverity.MEDIUM,
        issue_type="insecure_random",
        algorithm="Weak PRNG",
        description="Standard random functions are not cryptographically secure.",
        recommendation="Use secrets module (Python), crypto.randomBytes (Node.js), or SecureRandom (Java).",
    ),
    CryptoPattern(
        name="rsa_small_key",
        pattern=r"""(?:RSA\.generate\(\s*(?:512|768|1024)|key_size\s*=\s*(?:512|768|1024)|RSAKeyGenParameterSpec\(\s*(?:512|768|1024))""",
        severity=SecuritySeverity.HIGH,
        issue_type="weak_key_size",
        algorithm="RSA",
        description="RSA key sizes below 2048 bits are considered insecure.",
        recommendation="Use RSA-2048 or higher. Consider using RSA-4096 for long-term security.",
    ),
    CryptoPattern(
        name="password_hash_sha",
        pattern=r"""(?:hashlib\.sha(?:256|512)\([^)]*password|SHA(?:256|512)\.new\([^)]*password|digest\([^)]*password)""",
        severity=SecuritySeverity.HIGH,
        issue_type="weak_password_hash",
        algorithm="SHA for passwords",
        description="Raw SHA hashes are too fast for password hashing and vulnerable to brute force.",
        recommendation="Use bcrypt, scrypt, Argon2, or PBKDF2 with high iteration count for passwords.",
    ),
    CryptoPattern(
        name="bcrypt_low_rounds",
        pattern=r"""(?:bcrypt\.hash(?:pw)?\([^)]*rounds?\s*=\s*[1-9](?!\d)|gensalt\(\s*[1-9](?!\d)|BCrypt\.hashpw\([^)]*\$2[ab]\$0[1-9])""",
        severity=SecuritySeverity.MEDIUM,
        issue_type="weak_work_factor",
        algorithm="bcrypt",
        description="Low bcrypt work factor makes passwords easier to crack.",
        recommendation="Use work factor of at least 12 for bcrypt.",
    ),
    CryptoPattern(
        name="ssl_verify_false",
        pattern=r"""(?:verify\s*=\s*False|CERT_NONE|SSL_VERIFY_NONE|verify_ssl\s*=\s*False|rejectUnauthorized\s*:\s*false)""",
        severity=SecuritySeverity.HIGH,
        issue_type="disabled_verification",
        algorithm="SSL/TLS",
        description="Disabling SSL certificate verification enables man-in-the-middle attacks.",
        recommendation="Always verify SSL certificates in production. Use proper CA certificates.",
    ),
    CryptoPattern(
        name="ssl_v2_v3",
        pattern=r"""(?:SSLv2|SSLv3|ssl\.PROTOCOL_SSLv2|ssl\.PROTOCOL_SSLv3|TLSv1[^.12])""",
        severity=SecuritySeverity.CRITICAL,
        issue_type="deprecated_protocol",
        algorithm="SSLv2/SSLv3/TLSv1.0",
        description="SSL 2.0, SSL 3.0, and TLS 1.0 have known vulnerabilities.",
        recommendation="Use TLS 1.2 or TLS 1.3 only. Disable all older protocols.",
    ),
    CryptoPattern(
        name="jwt_none_algorithm",
        pattern=r"""(?:algorithm\s*=\s*['""]none['""]|algorithms?\s*[=:]\s*\[['""]none['""])""",
        severity=SecuritySeverity.CRITICAL,
        issue_type="jwt_vulnerability",
        algorithm="JWT none",
        description="JWT 'none' algorithm bypasses signature verification entirely.",
        recommendation="Never allow 'none' algorithm. Explicitly specify allowed algorithms.",
    ),
    CryptoPattern(
        name="jwt_hs256_weak_secret",
        pattern=r"""(?:jwt\.(?:encode|sign)\([^)]*['""](?:secret|password|key)['""])""",
        severity=SecuritySeverity.MEDIUM,
        issue_type="weak_jwt_secret",
        algorithm="JWT HS256",
        description="JWT with predictable secret names may indicate weak secrets.",
        recommendation="Use cryptographically random secrets of at least 256 bits for JWT.",
    ),
    CryptoPattern(
        name="pbkdf2_low_iterations",
        pattern=r"""(?:PBKDF2|pbkdf2_hmac)\([^)]*iterations?\s*=\s*(?:[1-9]\d{0,3}|10000)(?!\d)""",
        severity=SecuritySeverity.MEDIUM,
        issue_type="weak_work_factor",
        algorithm="PBKDF2",
        description="PBKDF2 iteration count below 100,000 is insufficient for modern hardware.",
        recommendation="Use at least 100,000 iterations for PBKDF2, or prefer Argon2.",
    ),
    CryptoPattern(
        name="cipher_without_auth",
        pattern=r"""(?:AES\.new\([^)]*(?:MODE_CBC|MODE_CTR|MODE_CFB|MODE_OFB)[^)]*\)(?!.*(?:hmac|HMAC|verify)))""",
        severity=SecuritySeverity.MEDIUM,
        issue_type="unauthenticated_encryption",
        algorithm="AES-CBC/CTR",
        description="Encryption without authentication is vulnerable to padding oracle and other attacks.",
        recommendation="Use authenticated encryption modes like GCM, or encrypt-then-MAC.",
        file_types={".py"},
    ),
    CryptoPattern(
        name="base64_as_encryption",
        pattern=r"""(?:base64\.(?:b64encode|encode)|btoa)\([^)]*(?:password|secret|credential|token)""",
        severity=SecuritySeverity.HIGH,
        issue_type="encoding_not_encryption",
        algorithm="Base64",
        description="Base64 is encoding, not encryption. It provides no security.",
        recommendation="Use proper encryption (AES-GCM) for sensitive data.",
    ),
]


class CryptographicValidationService:
    """
    Validates cryptographic implementations in source code.

    Detects:
    - Weak hash algorithms (MD5, SHA-1)
    - Deprecated ciphers (DES, 3DES)
    - Insecure cipher modes (ECB)
    - Static IVs and hardcoded keys
    - Weak random number generators
    - Insufficient key sizes
    - Improper password hashing
    - SSL/TLS misconfigurations
    - JWT vulnerabilities
    """

    def __init__(self, config: Optional[SecurityScanConfig] = None):
        """
        Initialize the cryptographic validation service.

        Args:
            config: Security scan configuration. Uses defaults if not provided.
        """
        self.config = config or SecurityScanConfig()
        self.patterns = list(CRYPTO_PATTERNS)

    def scan(self, scan_path: Optional[Path] = None) -> CryptoReport:
        """
        Scan the specified path for cryptographic issues.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            CryptoReport containing all findings
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        start_time = time.time()

        report = CryptoReport(
            scan_path=str(path),
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

    def _scan_file(self, file_path: Path, root_path: Path) -> List[CryptoFinding]:
        """
        Scan a single file for cryptographic issues.

        Args:
            file_path: Path to the file to scan
            root_path: Root path for relative path calculation

        Returns:
            List of cryptographic findings in the file
        """
        findings: List[CryptoFinding] = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except (IOError, OSError):
            return findings

        lines = content.split("\n")
        file_ext = file_path.suffix.lower()

        for pattern in self.patterns:
            if pattern.file_types and file_ext not in pattern.file_types:
                continue

            for match in pattern.pattern.finditer(content):
                line_number, column = find_line_column(content, match.start())

                # Skip matches in comments or docstrings
                if is_in_comment_or_docstring(content, lines, line_number, match.start(), file_ext):
                    continue

                if self._is_in_test_context(file_path, lines, line_number):
                    continue

                # For static IV/nonce detection, check for false positives
                if pattern.name == "static_iv":
                    if self._is_iv_nonce_false_positive(content, match.start(), lines, line_number):
                        continue

                code_snippet = extract_code_snippet(lines, line_number)

                finding = CryptoFinding(
                    file_path=str(file_path.relative_to(root_path)),
                    line_number=line_number,
                    issue_type=pattern.issue_type,
                    severity=pattern.severity,
                    algorithm=pattern.algorithm,
                    description=pattern.description,
                    recommendation=pattern.recommendation,
                    code_snippet=code_snippet,
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

        if line.startswith("'''") or line.startswith('"""'):
            return True

        return False

    def _is_in_test_context(
        self,
        file_path: Path,
        lines: List[str],
        line_number: int
    ) -> bool:
        """
        Check if a finding is in a test context.

        Some weak crypto usage is acceptable in tests.

        Args:
            file_path: Path to the file
            lines: File content lines
            line_number: Line number of the finding

        Returns:
            True if the finding is in a test context
        """
        file_name = file_path.name.lower()
        if "test" in file_name or "_test" in file_name or "spec" in file_name:
            return False

        return False

    def _is_iv_nonce_false_positive(
        self,
        content: str,
        match_start: int,
        lines: List[str],
        line_number: int
    ) -> bool:
        """
        Check if a static IV/nonce match is a false positive.

        False positives include:
        - Nonce validation (checking if nonce exists, not setting static nonce)
        - Template literals with variable interpolation
        - String building for CSP headers
        - Functions that generate random nonces

        Args:
            content: Full file content
            match_start: Start position of the match
            lines: File content as lines
            line_number: Line number of the match

        Returns:
            True if this appears to be a false positive
        """
        # Get context around the match
        context_start = max(0, match_start - 200)
        context_end = min(len(content), match_start + 200)
        context = content[context_start:context_end]

        # Check for validation patterns (not setting a static nonce)
        validation_patterns = [
            r"includes\s*\(",           # script.includes(`nonce="...`)
            r"contains\s*\(",           # checking if contains nonce
            r"validate",                # validation function
            r"check",                   # checking nonce
            r"verify",                  # verifying nonce
            r"match\s*\(",              # matching nonce
            r"test\s*\(",               # testing nonce
            r"search\s*\(",             # searching for nonce
            r"indexOf\s*\(",            # finding nonce position
        ]

        for pattern in validation_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                return True

        # Check for template literals with variable interpolation (dynamic nonces)
        if re.search(r'\$\{[^}]+\}', context):
            return True

        # Check for f-string with variable (Python dynamic nonces)
        if re.search(r'\{[a-z_][a-z_0-9]*\}', context, re.IGNORECASE):
            return True

        # Check if line contains random generation functions
        line = lines[line_number - 1] if line_number <= len(lines) else ""
        if re.search(r'(?:random|generate|create|crypto\.)', line, re.IGNORECASE):
            return True

        # Check if the enclosing function is about generating nonces
        for i in range(line_number - 1, max(0, line_number - 20), -1):
            if i < len(lines):
                fn_line = lines[i].strip()
                if fn_line.startswith("def ") or fn_line.startswith("function ") or "=>" in fn_line:
                    if re.search(r'generate|create|random', fn_line, re.IGNORECASE):
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

    def add_pattern(self, pattern: CryptoPattern) -> None:
        """
        Add a custom pattern to the detection list.

        Args:
            pattern: The pattern to add
        """
        self.patterns.append(pattern)

    def get_secure_recommendations(self) -> dict:
        """
        Get recommendations for secure cryptographic implementations.

        Returns:
            Dictionary of recommendations by category
        """
        return {
            "hashing": {
                "general": "SHA-256 or SHA-3",
                "passwords": "Argon2id (preferred), bcrypt, or scrypt",
                "avoid": ["MD5", "SHA-1"],
            },
            "symmetric_encryption": {
                "recommended": "AES-256-GCM or ChaCha20-Poly1305",
                "key_size": "256 bits minimum",
                "mode": "GCM, CCM, or CBC with HMAC",
                "avoid": ["DES", "3DES", "ECB mode", "RC4"],
            },
            "asymmetric_encryption": {
                "rsa": "RSA-2048 minimum, RSA-4096 preferred",
                "ecc": "P-256, P-384, or Ed25519",
                "avoid": ["RSA-1024 or smaller", "DSA"],
            },
            "random_numbers": {
                "python": "secrets module",
                "javascript": "crypto.randomBytes or crypto.getRandomValues",
                "java": "SecureRandom",
                "avoid": ["random module", "Math.random()"],
            },
            "tls": {
                "minimum_version": "TLS 1.2",
                "preferred_version": "TLS 1.3",
                "verify_certificates": True,
                "avoid": ["SSL 2.0", "SSL 3.0", "TLS 1.0", "TLS 1.1"],
            },
            "jwt": {
                "algorithms": ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
                "secret_size": "256 bits minimum for HS256",
                "avoid": ["none algorithm", "HS256 with weak secrets"],
            },
        }
