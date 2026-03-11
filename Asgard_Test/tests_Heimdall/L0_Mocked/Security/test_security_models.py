"""
Tests for Heimdall Security Models

Unit tests for the Pydantic models used in security analysis.
"""

import pytest
from datetime import datetime
from pathlib import Path

from Asgard.Heimdall.Security.models.security_models import (
    SecuritySeverity,
    SecretType,
    VulnerabilityType,
    DependencyRiskLevel,
    SecretFinding,
    VulnerabilityFinding,
    DependencyVulnerability,
    CryptoFinding,
    SecurityScanConfig,
    SecretsReport,
    VulnerabilityReport,
    DependencyReport,
    CryptoReport,
    SecurityReport,
)


class TestSecuritySeverity:
    """Tests for SecuritySeverity enum."""

    def test_severity_values(self):
        """Test that severity levels have correct string values."""
        assert SecuritySeverity.INFO.value == "info"
        assert SecuritySeverity.LOW.value == "low"
        assert SecuritySeverity.MEDIUM.value == "medium"
        assert SecuritySeverity.HIGH.value == "high"
        assert SecuritySeverity.CRITICAL.value == "critical"


class TestSecretType:
    """Tests for SecretType enum."""

    def test_secret_type_values(self):
        """Test that secret types have correct string values."""
        assert SecretType.API_KEY.value == "api_key"
        assert SecretType.PASSWORD.value == "password"
        assert SecretType.PRIVATE_KEY.value == "private_key"
        assert SecretType.AWS_CREDENTIALS.value == "aws_credentials"
        assert SecretType.JWT_TOKEN.value == "jwt_token"


class TestVulnerabilityType:
    """Tests for VulnerabilityType enum."""

    def test_vulnerability_type_values(self):
        """Test that vulnerability types have correct string values."""
        assert VulnerabilityType.SQL_INJECTION.value == "sql_injection"
        assert VulnerabilityType.XSS.value == "xss"
        assert VulnerabilityType.COMMAND_INJECTION.value == "command_injection"
        assert VulnerabilityType.PATH_TRAVERSAL.value == "path_traversal"


class TestDependencyRiskLevel:
    """Tests for DependencyRiskLevel enum."""

    def test_risk_level_values(self):
        """Test that risk levels have correct string values."""
        assert DependencyRiskLevel.SAFE.value == "safe"
        assert DependencyRiskLevel.LOW.value == "low"
        assert DependencyRiskLevel.MODERATE.value == "moderate"
        assert DependencyRiskLevel.HIGH.value == "high"
        assert DependencyRiskLevel.CRITICAL.value == "critical"


class TestSecretFinding:
    """Tests for SecretFinding model."""

    def test_secret_finding_creation(self):
        """Test creating a SecretFinding instance."""
        finding = SecretFinding(
            file_path="src/config.py",
            line_number=42,
            column_start=10,
            column_end=50,
            secret_type=SecretType.API_KEY,
            severity=SecuritySeverity.HIGH,
            pattern_name="aws_access_key",
            masked_value="AKIA****1234",
            line_content="api_key = 'AKIA****1234'",
            confidence=0.85,
            remediation="Move to environment variables"
        )

        assert finding.file_path == "src/config.py"
        assert finding.line_number == 42
        assert finding.column_start == 10
        assert finding.column_end == 50
        assert finding.secret_type == "api_key"
        assert finding.severity == "high"
        assert finding.pattern_name == "aws_access_key"
        assert finding.masked_value == "AKIA****1234"
        assert finding.confidence == 0.85

    def test_secret_finding_enum_conversion(self):
        """Test that enums are properly converted to string values."""
        finding = SecretFinding(
            file_path="test.py",
            line_number=1,
            secret_type=SecretType.PASSWORD,
            severity=SecuritySeverity.CRITICAL,
            pattern_name="password_pattern",
            masked_value="****",
            line_content="pwd='****'",
            confidence=0.9
        )

        assert isinstance(finding.secret_type, str)
        assert isinstance(finding.severity, str)


class TestVulnerabilityFinding:
    """Tests for VulnerabilityFinding model."""

    def test_vulnerability_finding_creation(self):
        """Test creating a VulnerabilityFinding instance."""
        finding = VulnerabilityFinding(
            file_path="api/views.py",
            line_number=100,
            column_start=5,
            column_end=45,
            vulnerability_type=VulnerabilityType.SQL_INJECTION,
            severity=SecuritySeverity.CRITICAL,
            title="SQL Injection in user query",
            description="User input is directly concatenated into SQL query",
            code_snippet="query = f'SELECT * FROM users WHERE id={user_id}'",
            cwe_id="CWE-89",
            owasp_category="A03:2021",
            confidence=0.95,
            remediation="Use parameterized queries",
            references=["https://owasp.org/www-community/attacks/SQL_Injection"]
        )

        assert finding.file_path == "api/views.py"
        assert finding.vulnerability_type == "sql_injection"
        assert finding.severity == "critical"
        assert finding.cwe_id == "CWE-89"
        assert finding.confidence == 0.95
        assert len(finding.references) == 1

    def test_vulnerability_finding_defaults(self):
        """Test default values for optional fields."""
        finding = VulnerabilityFinding(
            file_path="test.py",
            line_number=1,
            vulnerability_type=VulnerabilityType.XSS,
            severity=SecuritySeverity.HIGH,
            title="XSS Vulnerability",
            description="User input not sanitized",
            confidence=0.8
        )

        assert finding.code_snippet == ""
        assert finding.cwe_id is None
        assert finding.remediation == ""
        assert finding.references == []


class TestDependencyVulnerability:
    """Tests for DependencyVulnerability model."""

    def test_dependency_vulnerability_creation(self):
        """Test creating a DependencyVulnerability instance."""
        vuln = DependencyVulnerability(
            package_name="requests",
            installed_version="2.25.0",
            vulnerable_versions="<2.31.0",
            fixed_version="2.31.0",
            risk_level=DependencyRiskLevel.MODERATE,
            cve_id="CVE-2023-32681",
            title="Proxy authorization header leak",
            description="Requests may leak Proxy-Authorization header",
            references=["https://nvd.nist.gov/vuln/detail/CVE-2023-32681"],
            ecosystem="pypi"
        )

        assert vuln.package_name == "requests"
        assert vuln.installed_version == "2.25.0"
        assert vuln.risk_level == "moderate"
        assert vuln.cve_id == "CVE-2023-32681"
        assert vuln.ecosystem == "pypi"

    def test_dependency_vulnerability_with_ghsa(self):
        """Test creating vulnerability with GitHub Security Advisory."""
        vuln = DependencyVulnerability(
            package_name="django",
            installed_version="4.0.0",
            vulnerable_versions=">=4.0,<4.2.10",
            fixed_version="4.2.10",
            risk_level=DependencyRiskLevel.HIGH,
            ghsa_id="GHSA-1234-5678-9012",
            title="Django DoS vulnerability",
            description="Denial of service in template filter",
            ecosystem="pypi"
        )

        assert vuln.ghsa_id == "GHSA-1234-5678-9012"
        assert vuln.cve_id is None


class TestCryptoFinding:
    """Tests for CryptoFinding model."""

    def test_crypto_finding_creation(self):
        """Test creating a CryptoFinding instance."""
        finding = CryptoFinding(
            file_path="crypto/hashing.py",
            line_number=25,
            issue_type="weak_hash",
            severity=SecuritySeverity.HIGH,
            algorithm="MD5",
            description="MD5 is cryptographically broken",
            recommendation="Use SHA-256 or SHA-3",
            code_snippet="hash = hashlib.md5(data)"
        )

        assert finding.file_path == "crypto/hashing.py"
        assert finding.issue_type == "weak_hash"
        assert finding.algorithm == "MD5"
        assert finding.severity == "high"

    def test_crypto_finding_without_snippet(self):
        """Test crypto finding with empty code snippet."""
        finding = CryptoFinding(
            file_path="test.py",
            line_number=1,
            issue_type="weak_cipher",
            severity=SecuritySeverity.CRITICAL,
            algorithm="DES",
            description="DES is deprecated",
            recommendation="Use AES-256-GCM"
        )

        assert finding.code_snippet == ""


class TestSecurityScanConfig:
    """Tests for SecurityScanConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SecurityScanConfig()

        assert config.scan_secrets is True
        assert config.scan_vulnerabilities is True
        assert config.scan_dependencies is True
        assert config.scan_crypto is True
        assert config.min_severity == SecuritySeverity.LOW
        assert "__pycache__" in config.exclude_patterns
        assert "node_modules" in config.exclude_patterns

    def test_custom_config(self):
        """Test creating custom configuration."""
        config = SecurityScanConfig(
            scan_path=Path("/custom/path"),
            scan_secrets=True,
            scan_vulnerabilities=False,
            scan_dependencies=False,
            scan_crypto=True,
            min_severity=SecuritySeverity.HIGH,
            exclude_patterns=["custom_folder"],
            custom_patterns={"my_pattern": r"secret_\d+"}
        )

        assert "custom" in str(config.scan_path) and "path" in str(config.scan_path)
        assert config.scan_vulnerabilities is False
        assert config.min_severity == "high"
        assert "custom_folder" in config.exclude_patterns
        assert "my_pattern" in config.custom_patterns

    def test_config_ignore_paths(self):
        """Test configuration with ignore paths."""
        config = SecurityScanConfig(
            ignore_paths=["/path/to/ignore/file1.py", "/path/to/ignore/file2.js"]
        )

        assert len(config.ignore_paths) == 2
        assert "/path/to/ignore/file1.py" in config.ignore_paths


class TestSecretsReport:
    """Tests for SecretsReport model."""

    def test_secrets_report_defaults(self):
        """Test SecretsReport default values."""
        report = SecretsReport(
            scan_path="/test/path"
        )

        assert report.total_files_scanned == 0
        assert report.secrets_found == 0
        assert report.findings == []
        assert report.has_findings is False

    def test_add_finding(self):
        """Test adding findings to secrets report."""
        report = SecretsReport(scan_path="/test/path")

        finding = SecretFinding(
            file_path="config.py",
            line_number=10,
            secret_type=SecretType.API_KEY,
            severity=SecuritySeverity.HIGH,
            pattern_name="api_key",
            masked_value="sk_****",
            line_content="api_key = 'sk_****'",
            confidence=0.9
        )

        report.add_finding(finding)

        assert report.secrets_found == 1
        assert len(report.findings) == 1
        assert report.has_findings is True

    def test_get_findings_by_severity(self):
        """Test grouping findings by severity."""
        report = SecretsReport(scan_path="/test/path")

        severities = [
            SecuritySeverity.CRITICAL,
            SecuritySeverity.HIGH,
            SecuritySeverity.MEDIUM,
            SecuritySeverity.LOW,
        ]

        for severity in severities:
            finding = SecretFinding(
                file_path=f"{severity.value}.py",
                line_number=1,
                secret_type=SecretType.API_KEY,
                severity=severity,
                pattern_name="test",
                masked_value="****",
                line_content="test",
                confidence=0.8
            )
            report.add_finding(finding)

        by_severity = report.get_findings_by_severity()

        assert len(by_severity["critical"]) == 1
        assert len(by_severity["high"]) == 1
        assert len(by_severity["medium"]) == 1
        assert len(by_severity["low"]) == 1


class TestVulnerabilityReport:
    """Tests for VulnerabilityReport model."""

    def test_vulnerability_report_defaults(self):
        """Test VulnerabilityReport default values."""
        report = VulnerabilityReport(scan_path="/test/path")

        assert report.total_files_scanned == 0
        assert report.vulnerabilities_found == 0
        assert report.has_findings is False

    def test_add_vulnerability_finding(self):
        """Test adding vulnerability findings."""
        report = VulnerabilityReport(scan_path="/test/path")

        finding = VulnerabilityFinding(
            file_path="views.py",
            line_number=50,
            vulnerability_type=VulnerabilityType.SQL_INJECTION,
            severity=SecuritySeverity.CRITICAL,
            title="SQL Injection",
            description="Vulnerable to SQL injection",
            confidence=0.95
        )

        report.add_finding(finding)

        assert report.vulnerabilities_found == 1
        assert report.has_findings is True

    def test_get_findings_by_type(self):
        """Test grouping findings by vulnerability type."""
        report = VulnerabilityReport(scan_path="/test/path")

        types = [
            VulnerabilityType.SQL_INJECTION,
            VulnerabilityType.XSS,
            VulnerabilityType.COMMAND_INJECTION,
        ]

        for vuln_type in types:
            finding = VulnerabilityFinding(
                file_path=f"{vuln_type.value}.py",
                line_number=1,
                vulnerability_type=vuln_type,
                severity=SecuritySeverity.HIGH,
                title=f"{vuln_type.value} vulnerability",
                description="Test vulnerability",
                confidence=0.8
            )
            report.add_finding(finding)

        by_type = report.get_findings_by_type()

        assert len(by_type["sql_injection"]) == 1
        assert len(by_type["xss"]) == 1
        assert len(by_type["command_injection"]) == 1


class TestDependencyReport:
    """Tests for DependencyReport model."""

    def test_dependency_report_defaults(self):
        """Test DependencyReport default values."""
        report = DependencyReport(scan_path="/test/path")

        assert report.total_dependencies == 0
        assert report.vulnerable_dependencies == 0
        assert report.has_vulnerabilities is False

    def test_add_vulnerability(self):
        """Test adding dependency vulnerabilities."""
        report = DependencyReport(scan_path="/test/path")

        vuln = DependencyVulnerability(
            package_name="requests",
            installed_version="2.25.0",
            vulnerable_versions="<2.31.0",
            fixed_version="2.31.0",
            risk_level=DependencyRiskLevel.MODERATE,
            title="Security issue",
            description="Test vulnerability",
            ecosystem="pypi"
        )

        report.add_vulnerability(vuln)

        assert report.vulnerable_dependencies == 1
        assert len(report.vulnerabilities) == 1
        assert report.has_vulnerabilities is True

    def test_multiple_vulnerabilities_same_package(self):
        """Test counting unique packages with multiple vulnerabilities."""
        report = DependencyReport(scan_path="/test/path")

        for i in range(3):
            vuln = DependencyVulnerability(
                package_name="requests",
                installed_version="2.25.0",
                vulnerable_versions="<2.31.0",
                fixed_version="2.31.0",
                risk_level=DependencyRiskLevel.HIGH,
                title=f"Issue {i}",
                description="Test",
                ecosystem="pypi"
            )
            report.add_vulnerability(vuln)

        assert len(report.vulnerabilities) == 3
        assert report.vulnerable_dependencies == 1

    def test_get_vulnerabilities_by_risk(self):
        """Test grouping vulnerabilities by risk level."""
        report = DependencyReport(scan_path="/test/path")

        risks = [
            DependencyRiskLevel.CRITICAL,
            DependencyRiskLevel.HIGH,
            DependencyRiskLevel.MODERATE,
        ]

        for i, risk in enumerate(risks):
            vuln = DependencyVulnerability(
                package_name=f"package{i}",
                installed_version="1.0.0",
                vulnerable_versions="<2.0.0",
                fixed_version="2.0.0",
                risk_level=risk,
                title="Test vulnerability",
                description="Test",
                ecosystem="pypi"
            )
            report.add_vulnerability(vuln)

        by_risk = report.get_vulnerabilities_by_risk()

        assert len(by_risk["critical"]) == 1
        assert len(by_risk["high"]) == 1
        assert len(by_risk["moderate"]) == 1


class TestCryptoReport:
    """Tests for CryptoReport model."""

    def test_crypto_report_defaults(self):
        """Test CryptoReport default values."""
        report = CryptoReport(scan_path="/test/path")

        assert report.total_files_scanned == 0
        assert report.issues_found == 0
        assert report.has_findings is False

    def test_add_crypto_finding(self):
        """Test adding cryptographic findings."""
        report = CryptoReport(scan_path="/test/path")

        finding = CryptoFinding(
            file_path="crypto.py",
            line_number=10,
            issue_type="weak_hash",
            severity=SecuritySeverity.HIGH,
            algorithm="MD5",
            description="MD5 is insecure",
            recommendation="Use SHA-256"
        )

        report.add_finding(finding)

        assert report.issues_found == 1
        assert len(report.findings) == 1
        assert report.has_findings is True


class TestSecurityReport:
    """Tests for comprehensive SecurityReport model."""

    def test_security_report_defaults(self):
        """Test SecurityReport default values."""
        config = SecurityScanConfig()
        report = SecurityReport(
            scan_path="/test/path",
            scan_config=config
        )

        assert report.total_issues == 0
        assert report.critical_issues == 0
        assert report.high_issues == 0
        assert report.medium_issues == 0
        assert report.low_issues == 0
        assert report.security_score == 100.0
        assert report.has_issues is False
        assert report.is_passing is True

    def test_calculate_totals_with_secrets(self):
        """Test total calculation with secrets findings."""
        config = SecurityScanConfig()
        report = SecurityReport(
            scan_path="/test/path",
            scan_config=config
        )

        secrets_report = SecretsReport(scan_path="/test/path")

        finding = SecretFinding(
            file_path="config.py",
            line_number=1,
            secret_type=SecretType.API_KEY,
            severity=SecuritySeverity.CRITICAL,
            pattern_name="test",
            masked_value="****",
            line_content="test",
            confidence=0.9
        )
        secrets_report.add_finding(finding)

        report.secrets_report = secrets_report
        report.calculate_totals()

        assert report.total_issues == 1
        assert report.critical_issues == 1
        assert report.has_issues is True
        assert report.is_passing is False

    def test_calculate_totals_with_vulnerabilities(self):
        """Test total calculation with vulnerability findings."""
        config = SecurityScanConfig()
        report = SecurityReport(
            scan_path="/test/path",
            scan_config=config
        )

        vuln_report = VulnerabilityReport(scan_path="/test/path")

        finding = VulnerabilityFinding(
            file_path="views.py",
            line_number=1,
            vulnerability_type=VulnerabilityType.SQL_INJECTION,
            severity=SecuritySeverity.HIGH,
            title="SQL Injection",
            description="Test",
            confidence=0.9
        )
        vuln_report.add_finding(finding)

        report.vulnerability_report = vuln_report
        report.calculate_totals()

        assert report.total_issues == 1
        assert report.high_issues == 1
        assert report.is_passing is False

    def test_calculate_totals_with_dependencies(self):
        """Test total calculation with dependency vulnerabilities."""
        config = SecurityScanConfig()
        report = SecurityReport(
            scan_path="/test/path",
            scan_config=config
        )

        dep_report = DependencyReport(scan_path="/test/path")

        vuln = DependencyVulnerability(
            package_name="requests",
            installed_version="1.0.0",
            vulnerable_versions="<2.0.0",
            fixed_version="2.0.0",
            risk_level=DependencyRiskLevel.MODERATE,
            title="Test",
            description="Test",
            ecosystem="pypi"
        )
        dep_report.add_vulnerability(vuln)

        report.dependency_report = dep_report
        report.calculate_totals()

        assert report.total_issues == 1
        assert report.medium_issues == 1

    def test_security_score_calculation(self):
        """Test security score calculation with multiple issues."""
        config = SecurityScanConfig()
        report = SecurityReport(
            scan_path="/test/path",
            scan_config=config
        )

        secrets_report = SecretsReport(scan_path="/test/path")

        secrets_report.add_finding(SecretFinding(
            file_path="f1.py", line_number=1, secret_type=SecretType.API_KEY,
            severity=SecuritySeverity.CRITICAL, pattern_name="t", masked_value="*",
            line_content="t", confidence=0.9
        ))

        secrets_report.add_finding(SecretFinding(
            file_path="f2.py", line_number=1, secret_type=SecretType.API_KEY,
            severity=SecuritySeverity.HIGH, pattern_name="t", masked_value="*",
            line_content="t", confidence=0.9
        ))

        secrets_report.add_finding(SecretFinding(
            file_path="f3.py", line_number=1, secret_type=SecretType.API_KEY,
            severity=SecuritySeverity.MEDIUM, pattern_name="t", masked_value="*",
            line_content="t", confidence=0.9
        ))

        report.secrets_report = secrets_report
        report.calculate_totals()

        expected_score = 100.0 - (1 * 25) - (1 * 10) - (1 * 5)
        assert report.security_score == expected_score
        assert report.total_issues == 3

    def test_security_score_minimum_zero(self):
        """Test that security score doesn't go below zero."""
        config = SecurityScanConfig()
        report = SecurityReport(
            scan_path="/test/path",
            scan_config=config
        )

        secrets_report = SecretsReport(scan_path="/test/path")

        for _ in range(10):
            secrets_report.add_finding(SecretFinding(
                file_path="f.py", line_number=1, secret_type=SecretType.API_KEY,
                severity=SecuritySeverity.CRITICAL, pattern_name="t", masked_value="*",
                line_content="t", confidence=0.9
            ))

        report.secrets_report = secrets_report
        report.calculate_totals()

        assert report.security_score == 0.0
        assert report.security_score >= 0.0

    def test_is_passing_with_low_severity_only(self):
        """Test that report passes with only low severity issues."""
        config = SecurityScanConfig()
        report = SecurityReport(
            scan_path="/test/path",
            scan_config=config
        )

        secrets_report = SecretsReport(scan_path="/test/path")

        secrets_report.add_finding(SecretFinding(
            file_path="f.py", line_number=1, secret_type=SecretType.API_KEY,
            severity=SecuritySeverity.LOW, pattern_name="t", masked_value="*",
            line_content="t", confidence=0.9
        ))

        report.secrets_report = secrets_report
        report.calculate_totals()

        assert report.is_passing is True
        assert report.critical_issues == 0
        assert report.high_issues == 0
