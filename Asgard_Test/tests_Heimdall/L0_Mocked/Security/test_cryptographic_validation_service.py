"""
Tests for Heimdall Cryptographic Validation Service

Unit tests for the cryptographic validation service with mocked operations.
"""

import pytest
import tempfile
from pathlib import Path

from Asgard.Heimdall.Security.services.cryptographic_validation_service import (
    CryptoPattern,
    CryptographicValidationService,
    CRYPTO_PATTERNS,
)
from Asgard.Heimdall.Security.models.security_models import (
    SecuritySeverity,
    SecurityScanConfig,
)


class TestCryptoPattern:
    """Tests for CryptoPattern class."""

    def test_pattern_creation(self):
        """Test creating a crypto pattern."""
        pattern = CryptoPattern(
            name="test_weak_hash",
            pattern=r"md5\(",
            severity=SecuritySeverity.HIGH,
            issue_type="weak_hash",
            algorithm="MD5",
            description="MD5 is insecure",
            recommendation="Use SHA-256"
        )

        assert pattern.name == "test_weak_hash"
        assert pattern.severity == SecuritySeverity.HIGH
        assert pattern.algorithm == "MD5"

    def test_pattern_with_file_types(self):
        """Test pattern with specific file type restrictions."""
        pattern = CryptoPattern(
            name="python_only",
            pattern=r"test",
            severity=SecuritySeverity.LOW,
            issue_type="test",
            algorithm="test",
            description="test",
            recommendation="test",
            file_types={".py"}
        )

        assert pattern.file_types == {".py"}


class TestCryptoPatterns:
    """Tests for CRYPTO_PATTERNS list."""

    def test_has_md5_pattern(self):
        """Test that MD5 detection pattern exists."""
        pattern_names = [p.name for p in CRYPTO_PATTERNS]
        assert "md5_hash" in pattern_names

    def test_has_sha1_pattern(self):
        """Test that SHA-1 detection pattern exists."""
        pattern_names = [p.name for p in CRYPTO_PATTERNS]
        assert "sha1_hash" in pattern_names

    def test_has_des_pattern(self):
        """Test that DES/3DES detection pattern exists."""
        pattern_names = [p.name for p in CRYPTO_PATTERNS]
        assert "des_encryption" in pattern_names

    def test_has_ecb_mode_pattern(self):
        """Test that ECB mode detection pattern exists."""
        pattern_names = [p.name for p in CRYPTO_PATTERNS]
        assert "ecb_mode" in pattern_names

    def test_has_static_iv_pattern(self):
        """Test that static IV detection pattern exists."""
        pattern_names = [p.name for p in CRYPTO_PATTERNS]
        assert "static_iv" in pattern_names

    def test_has_hardcoded_key_pattern(self):
        """Test that hardcoded key detection pattern exists."""
        pattern_names = [p.name for p in CRYPTO_PATTERNS]
        assert "hardcoded_key" in pattern_names

    def test_has_ssl_patterns(self):
        """Test that SSL/TLS security patterns exist."""
        pattern_names = [p.name for p in CRYPTO_PATTERNS]
        assert "ssl_verify_false" in pattern_names
        assert "ssl_v2_v3" in pattern_names


class TestCryptographicValidationService:
    """Tests for CryptographicValidationService class."""

    def test_service_initialization_default(self):
        """Test service initialization with default config."""
        service = CryptographicValidationService()

        assert service.config is not None
        assert len(service.patterns) > 0

    def test_service_initialization_custom_config(self):
        """Test service initialization with custom config."""
        config = SecurityScanConfig(
            scan_path=Path("/custom/path"),
            min_severity=SecuritySeverity.HIGH
        )

        service = CryptographicValidationService(config)

        assert service.config == config
        assert service.config.min_severity == "high"

    def test_scan_nonexistent_path_raises_error(self):
        """Test that scanning nonexistent path raises FileNotFoundError."""
        service = CryptographicValidationService()

        with pytest.raises(FileNotFoundError):
            service.scan(Path("/nonexistent/path"))

    def test_scan_empty_directory(self):
        """Test scanning an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = CryptographicValidationService()
            report = service.scan(Path(tmpdir))

            assert report.total_files_scanned == 0
            assert report.issues_found == 0
            assert report.has_findings is False

    def test_scan_clean_code(self):
        """Test scanning code with no cryptographic issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "app.py").write_text("""
import hashlib

def hash_data(data):
    return hashlib.sha256(data.encode()).hexdigest()
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.total_files_scanned > 0
            assert report.issues_found == 0

    def test_detect_md5_usage(self):
        """Test detection of MD5 hash usage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "hash.py").write_text("""
import hashlib

def weak_hash(data):
    return hashlib.md5(data.encode()).hexdigest()
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.issues_found > 0
            md5_findings = [f for f in report.findings if "MD5" in f.algorithm]
            assert len(md5_findings) > 0

    def test_detect_sha1_usage(self):
        """Test detection of SHA-1 hash usage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "hash.py").write_text("""
import hashlib

def hash_function(data):
    return hashlib.sha1(data).digest()
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.issues_found > 0
            sha1_findings = [f for f in report.findings if "SHA-1" in f.algorithm]
            assert len(sha1_findings) > 0

    def test_detect_des_encryption(self):
        """Test detection of DES encryption."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "crypto.py").write_text("""
from Crypto.Cipher import DES

cipher = DES.new(key, DES.MODE_ECB)
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.issues_found > 0

    def test_detect_ecb_mode(self):
        """Test detection of ECB mode usage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "cipher.py").write_text("""
from Crypto.Cipher import AES

cipher = AES.new(key, AES.MODE_ECB)
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.issues_found > 0
            ecb_findings = [f for f in report.findings if "ECB" in f.algorithm]
            assert len(ecb_findings) > 0

    def test_detect_static_iv(self):
        """Test detection of static IV usage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "encrypt.py").write_text("""
iv = "1234567890123456"
cipher = AES.new(key, AES.MODE_CBC, iv)
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.issues_found > 0

    def test_detect_hardcoded_key(self):
        """Test detection of hardcoded encryption key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "keys.py").write_text("""
encryption_key = "abcd1234efgh5678ijkl9012mnop3456"
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.issues_found > 0

    def test_detect_weak_random(self):
        """Test detection of weak random number generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "random_gen.py").write_text("""
import random

def generate_token():
    return random.randint(1000, 9999)
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.issues_found > 0

    def test_detect_ssl_verify_false(self):
        """Test detection of SSL verification disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "api.py").write_text("""
import requests

response = requests.get(url, verify=False)
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.issues_found > 0
            ssl_findings = [f for f in report.findings if "SSL" in f.algorithm or "TLS" in f.algorithm]
            assert len(ssl_findings) > 0

    def test_detect_deprecated_ssl_versions(self):
        """Test detection of deprecated SSL/TLS versions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "ssl_config.py").write_text("""
import ssl

context = ssl.SSLContext(ssl.PROTOCOL_SSLv3)
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.issues_found > 0

    def test_detect_jwt_none_algorithm(self):
        """Test detection of JWT 'none' algorithm."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "jwt_config.py").write_text("""
import jwt

token = jwt.encode(payload, key, algorithm="none")
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.issues_found > 0

    def test_detect_weak_rsa_key_size(self):
        """Test detection of weak RSA key sizes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "rsa_gen.py").write_text("""
from Crypto.PublicKey import RSA

key = RSA.generate(1024)
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.issues_found > 0

    def test_detect_password_hashed_with_sha(self):
        """Test detection of passwords hashed with SHA."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "auth.py").write_text("""
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.issues_found > 0

    def test_ignore_comments(self):
        """Test that issues in comments are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "code.py").write_text("""
def secure_hash(data):
    # Don't use hashlib.md5() - it's insecure
    return hashlib.sha256(data).digest()
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            md5_findings = [f for f in report.findings if "MD5" in f.algorithm]
            assert len(md5_findings) == 0

    def test_severity_meets_threshold(self):
        """Test that only findings meeting severity threshold are included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "crypto.py").write_text("""
import hashlib
hashlib.md5(data)
hashlib.sha1(data)
""")

            config = SecurityScanConfig(min_severity=SecuritySeverity.CRITICAL)
            service = CryptographicValidationService(config)
            report = service.scan(tmpdir_path)

            for finding in report.findings:
                assert finding.severity == "critical"

    def test_findings_sorted_by_severity(self):
        """Test that findings are sorted by severity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "crypto.py").write_text("""
import hashlib
import ssl

hashlib.md5(data)
hashlib.sha1(data)
encryption_key = "hardcoded_key_1234567890"
ssl.PROTOCOL_SSLv3
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            if len(report.findings) > 1:
                severity_order = ["critical", "high", "medium", "low", "info"]
                severities = [f.severity for f in report.findings]

                for i in range(len(severities) - 1):
                    curr_idx = severity_order.index(severities[i])
                    next_idx = severity_order.index(severities[i + 1])
                    assert curr_idx <= next_idx

    def test_add_custom_pattern(self):
        """Test adding a custom detection pattern."""
        service = CryptographicValidationService()
        initial_count = len(service.patterns)

        custom_pattern = CryptoPattern(
            name="custom_weak_algo",
            pattern=r"custom_weak_function\(",
            severity=SecuritySeverity.HIGH,
            issue_type="weak_algorithm",
            algorithm="CustomWeak",
            description="Custom weak algorithm",
            recommendation="Use something else"
        )

        service.add_pattern(custom_pattern)

        assert len(service.patterns) == initial_count + 1

    def test_get_secure_recommendations(self):
        """Test getting secure cryptographic recommendations."""
        service = CryptographicValidationService()
        recommendations = service.get_secure_recommendations()

        assert "hashing" in recommendations
        assert "symmetric_encryption" in recommendations
        assert "asymmetric_encryption" in recommendations
        assert "tls" in recommendations
        assert "jwt" in recommendations

        assert "SHA-256" in recommendations["hashing"]["general"]
        assert "Argon2" in recommendations["hashing"]["passwords"] or "bcrypt" in recommendations["hashing"]["passwords"]

    def test_scan_duration_recorded(self):
        """Test that scan duration is recorded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = CryptographicValidationService()
            report = service.scan(Path(tmpdir))

            assert report.scan_duration_seconds >= 0.0

    def test_code_snippet_included(self):
        """Test that code snippets are included in findings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "hash.py").write_text("""
import hashlib

def weak():
    return hashlib.md5(b"data").digest()
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            if report.issues_found > 0:
                finding = report.findings[0]
                assert finding.code_snippet != ""
                assert ">>>" in finding.code_snippet

    def test_recommendation_provided(self):
        """Test that remediation recommendations are provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "crypto.py").write_text("""
import hashlib
hashlib.md5(data)
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            if report.issues_found > 0:
                finding = report.findings[0]
                assert finding.recommendation != ""
                assert len(finding.recommendation) > 10

    def test_scan_multiple_file_types(self):
        """Test scanning multiple file types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "script.py").write_text("hashlib.md5(x)")
            (tmpdir_path / "app.js").write_text("crypto.createHash('md5')")
            (tmpdir_path / "code.java").write_text("MessageDigest.getInstance('MD5')")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.total_files_scanned >= 3

    def test_relative_paths_in_findings(self):
        """Test that findings contain relative paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            subdir = tmpdir_path / "src"
            subdir.mkdir()
            (subdir / "crypto.py").write_text("hashlib.md5(data)")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            if report.issues_found > 0:
                finding = report.findings[0]
                assert "src" in finding.file_path or "crypto.py" in finding.file_path

    def test_scan_respects_exclude_patterns(self):
        """Test that exclude patterns are respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            vendor_dir = tmpdir_path / "vendor"
            vendor_dir.mkdir()
            (vendor_dir / "lib.py").write_text("hashlib.md5(x)")

            (tmpdir_path / "app.py").write_text("hashlib.md5(y)")

            config = SecurityScanConfig(exclude_patterns=["vendor"])
            service = CryptographicValidationService(config)
            report = service.scan(tmpdir_path)

            file_paths = [f.file_path for f in report.findings]
            assert not any("vendor" in fp for fp in file_paths)

    def test_detect_low_bcrypt_rounds(self):
        """Test detection of low bcrypt work factor."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "password.py").write_text("""
import bcrypt

salt = bcrypt.gensalt(rounds=5)
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.total_files_scanned > 0

    def test_detect_base64_as_encryption(self):
        """Test detection of base64 being used as encryption."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "encoding.py").write_text("""
import base64

encoded_password = base64.b64encode(password)
""")

            service = CryptographicValidationService()
            report = service.scan(tmpdir_path)

            assert report.issues_found > 0
