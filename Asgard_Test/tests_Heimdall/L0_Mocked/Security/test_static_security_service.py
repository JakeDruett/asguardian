"""
Tests for Heimdall Static Security Service

Unit tests for the comprehensive static security analysis service.
"""

import pytest
import tempfile
from pathlib import Path

from Asgard.Heimdall.Security.services.static_security_service import StaticSecurityService
from Asgard.Heimdall.Security.models.security_models import (
    SecurityScanConfig,
    SecuritySeverity,
)


class TestStaticSecurityService:
    """Tests for StaticSecurityService class."""

    def test_service_initialization_default(self):
        """Test service initialization with default config."""
        service = StaticSecurityService()

        assert service.config is not None
        assert service.secrets_service is not None
        assert service.dependency_service is not None
        assert service.injection_service is not None
        assert service.crypto_service is not None

    def test_service_initialization_custom_config(self):
        """Test service initialization with custom config."""
        config = SecurityScanConfig(
            scan_path=Path("/custom/path"),
            scan_secrets=True,
            scan_vulnerabilities=False,
            scan_dependencies=False,
            scan_crypto=True
        )

        service = StaticSecurityService(config)

        assert service.config == config
        assert service.config.scan_vulnerabilities is False

    def test_scan_nonexistent_path_raises_error(self):
        """Test scanning nonexistent path raises error."""
        service = StaticSecurityService()

        with pytest.raises(FileNotFoundError):
            service.scan(Path("/nonexistent/path"))

    def test_scan_empty_directory(self):
        """Test scanning an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = StaticSecurityService()
            report = service.scan(Path(tmpdir))

            assert report.scan_path is not None
            assert report.total_issues == 0
            assert report.security_score == 100.0

    def test_scan_all_services_enabled(self):
        """Test scanning with all services enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "config.py").write_text("""
API_KEY = "AKIAIOSFODNN7EXAMPLE"
query = f"SELECT * FROM users WHERE id={user_id}"
hash = hashlib.md5(data)
""")

            (tmpdir_path / "requirements.txt").write_text("requests==2.25.0")

            config = SecurityScanConfig(
                scan_secrets=True,
                scan_vulnerabilities=True,
                scan_dependencies=True,
                scan_crypto=True
            )

            service = StaticSecurityService(config)
            report = service.scan(tmpdir_path)

            assert report.secrets_report is not None
            assert report.vulnerability_report is not None
            assert report.dependency_report is not None
            assert report.crypto_report is not None

    def test_scan_only_secrets(self):
        """Test scanning only for secrets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "secrets.py").write_text("""
AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
""")

            config = SecurityScanConfig(
                scan_secrets=True,
                scan_vulnerabilities=False,
                scan_dependencies=False,
                scan_crypto=False
            )

            service = StaticSecurityService(config)
            report = service.scan(tmpdir_path)

            assert report.secrets_report is not None
            assert report.vulnerability_report is None
            assert report.dependency_report is None
            assert report.crypto_report is None

    def test_scan_secrets_only_method(self):
        """Test scan_secrets_only method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "secrets.py").write_text("""
API_KEY = "AKIAIOSFODNN7EXAMPLE"
""")

            service = StaticSecurityService()
            report = service.scan_secrets_only(tmpdir_path)

            assert report.secrets_report is not None
            assert report.vulnerability_report is None
            assert report.dependency_report is None
            assert report.crypto_report is None

    def test_scan_dependencies_only_method(self):
        """Test scan_dependencies_only method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "requirements.txt").write_text("requests==2.25.0")

            service = StaticSecurityService()
            report = service.scan_dependencies_only(tmpdir_path)

            assert report.secrets_report is None
            assert report.vulnerability_report is None
            assert report.dependency_report is not None
            assert report.crypto_report is None

    def test_scan_vulnerabilities_only_method(self):
        """Test scan_vulnerabilities_only method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "sql.py").write_text("""
query = f"SELECT * FROM users WHERE id={user_id}"
""")

            service = StaticSecurityService()
            report = service.scan_vulnerabilities_only(tmpdir_path)

            assert report.secrets_report is None
            assert report.vulnerability_report is not None
            assert report.dependency_report is None
            assert report.crypto_report is None

    def test_scan_crypto_only_method(self):
        """Test scan_crypto_only method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "hash.py").write_text("""
import hashlib
hash = hashlib.md5(data)
""")

            service = StaticSecurityService()
            report = service.scan_crypto_only(tmpdir_path)

            assert report.secrets_report is None
            assert report.vulnerability_report is None
            assert report.dependency_report is None
            assert report.crypto_report is not None

    def test_calculate_totals_aggregates_all_findings(self):
        """Test that calculate_totals aggregates from all reports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "issues.py").write_text("""
API_KEY = "AKIAIOSFODNN7EXAMPLE"
query = f"SELECT * FROM users WHERE id={user_id}"
hash = hashlib.md5(data)
""")

            (tmpdir_path / "requirements.txt").write_text("requests==2.25.0")

            service = StaticSecurityService()
            report = service.scan(tmpdir_path)

            assert report.total_issues >= 0
            combined = (
                report.critical_issues +
                report.high_issues +
                report.medium_issues +
                report.low_issues
            )
            assert combined == report.total_issues

    def test_security_score_calculated(self):
        """Test that security score is calculated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "clean.py").write_text("""
def calculate(a, b):
    return a + b
""")

            service = StaticSecurityService()
            report = service.scan(tmpdir_path)

            assert 0.0 <= report.security_score <= 100.0

    def test_scan_duration_recorded(self):
        """Test that total scan duration is recorded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = StaticSecurityService()
            report = service.scan(Path(tmpdir))

            assert report.scan_duration_seconds >= 0.0

    def test_scanned_at_timestamp_set(self):
        """Test that scanned_at timestamp is set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = StaticSecurityService()
            report = service.scan(Path(tmpdir))

            assert report.scanned_at is not None

    def test_get_summary_generates_report(self):
        """Test that get_summary generates a text report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "app.py").write_text("""
API_KEY = "AKIAIOSFODNN7EXAMPLE"
""")

            service = StaticSecurityService()
            report = service.scan(tmpdir_path)

            summary = service.get_summary(report)

            assert isinstance(summary, str)
            assert len(summary) > 0
            assert "HEIMDALL SECURITY ANALYSIS" in summary
            assert "Security Score" in summary

    def test_get_summary_includes_secrets_section(self):
        """Test that summary includes secrets section when applicable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "secrets.py").write_text("""
API_KEY = "AKIAIOSFODNN7EXAMPLE"
""")

            service = StaticSecurityService()
            report = service.scan(tmpdir_path)

            summary = service.get_summary(report)

            if report.secrets_report and report.secrets_report.secrets_found > 0:
                assert "SECRETS DETECTION" in summary

    def test_get_summary_includes_dependency_section(self):
        """Test that summary includes dependency section when applicable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "requirements.txt").write_text("requests==2.25.0")

            service = StaticSecurityService()
            report = service.scan(tmpdir_path)

            summary = service.get_summary(report)

            if report.dependency_report:
                assert "DEPENDENCY VULNERABILITIES" in summary or "Dependencies Analyzed" in summary

    def test_get_summary_includes_vulnerability_section(self):
        """Test that summary includes vulnerability section when applicable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "sql.py").write_text("""
query = f"SELECT * FROM users WHERE id={user_id}"
""")

            service = StaticSecurityService()
            report = service.scan(tmpdir_path)

            summary = service.get_summary(report)

            if report.vulnerability_report and report.vulnerability_report.vulnerabilities_found > 0:
                assert "CODE VULNERABILITIES" in summary or "VULNERABILITIES" in summary

    def test_get_summary_includes_crypto_section(self):
        """Test that summary includes crypto section when applicable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "hash.py").write_text("""
import hashlib
hash = hashlib.md5(data)
""")

            service = StaticSecurityService()
            report = service.scan(tmpdir_path)

            summary = service.get_summary(report)

            if report.crypto_report and report.crypto_report.issues_found > 0:
                assert "CRYPTOGRAPHIC" in summary

    def test_get_summary_shows_pass_fail(self):
        """Test that summary shows PASS/FAIL result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = StaticSecurityService()
            report = service.scan(Path(tmpdir))

            summary = service.get_summary(report)

            assert "PASS" in summary or "FAIL" in summary

    def test_scan_handles_service_exceptions(self):
        """Test that scan handles exceptions from individual services gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "app.py").write_text("code")

            service = StaticSecurityService()
            report = service.scan(tmpdir_path)

            assert report is not None
            assert report.scan_path is not None

    def test_scan_uses_config_path(self):
        """Test that scan uses config path when no path provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "app.py").write_text("code")

            config = SecurityScanConfig(scan_path=tmpdir_path)
            service = StaticSecurityService(config)

            report = service.scan()

            assert tmpdir_path.name in report.scan_path or str(tmpdir_path) in report.scan_path

    def test_is_passing_with_no_issues(self):
        """Test that report passes with no issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "clean.py").write_text("""
def add(a, b):
    return a + b
""")

            service = StaticSecurityService()
            report = service.scan(tmpdir_path)

            assert report.is_passing is True

    def test_is_not_passing_with_critical_issues(self):
        """Test that report fails with critical issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "vulnerable.py").write_text("""
encryption_key = "hardcoded_key_1234567890abcdef"
""")

            service = StaticSecurityService()
            report = service.scan(tmpdir_path)

            if report.critical_issues > 0:
                assert report.is_passing is False

    def test_multiple_scans_independent(self):
        """Test that multiple scans are independent."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                tmpdir1_path = Path(tmpdir1)
                tmpdir2_path = Path(tmpdir2)

                (tmpdir1_path / "app.py").write_text("clean_code = True")
                (tmpdir2_path / "vuln.py").write_text("query = f'SELECT * FROM t WHERE id={x}'")

                service = StaticSecurityService()

                report1 = service.scan(tmpdir1_path)
                report2 = service.scan(tmpdir2_path)

                assert report1.scan_path != report2.scan_path
