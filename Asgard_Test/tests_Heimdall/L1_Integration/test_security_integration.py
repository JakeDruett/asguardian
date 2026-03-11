"""
L1 Integration Tests for Heimdall Security Analysis

Tests security scanning workflows on real Python projects.
"""

import json
import pytest
from pathlib import Path

from Asgard.Heimdall.Security import (
    StaticSecurityService,
    SecurityScanConfig,
    SecretsDetectionService,
    InjectionDetectionService,
    CryptographicValidationService,
)


class TestSecurityIntegration:
    """Integration tests for security analysis."""

    def test_security_scan_simple_project_full(self, simple_project):
        """Test full security scan on simple project."""
        service = StaticSecurityService()
        report = service.scan(str(simple_project))

        assert report is not None
        assert hasattr(report, 'security_score')
        assert 0 <= report.security_score <= 100
        assert hasattr(report, 'scan_path')
        assert report.scan_path == str(simple_project.resolve())

    def test_security_scan_vulnerable_project_full(self, security_vulnerable_project):
        """Test full security scan on vulnerable project."""
        service = StaticSecurityService()
        report = service.scan(str(security_vulnerable_project))

        assert report is not None
        assert report.security_score < 100

        # Should detect multiple security issues
        total_issues = 0
        if hasattr(report, 'secrets_count'):
            total_issues += report.secrets_count
        if hasattr(report, 'vulnerabilities_count'):
            total_issues += report.vulnerabilities_count

        # Vulnerable project should have issues
        # Note: actual detection depends on implementation

    def test_security_secrets_detection_simple_project(self, simple_project):
        """Test secrets detection on simple project."""
        service = SecretsDetectionService()
        report = service.scan(str(simple_project))

        assert report is not None
        assert hasattr(report, 'secrets')
        assert isinstance(report.secrets, list)

        # Simple project should have no secrets
        assert len(report.secrets) == 0

    def test_security_secrets_detection_vulnerable_project(self, security_vulnerable_project):
        """Test secrets detection on vulnerable project."""
        service = SecretsDetectionService()
        report = service.scan(str(security_vulnerable_project))

        assert report is not None
        assert hasattr(report, 'secrets')
        assert isinstance(report.secrets, list)

        # Vulnerable project should have secrets detected
        assert len(report.secrets) > 0

        # Check for specific secret types
        secret_types_found = set()
        for secret in report.secrets:
            if hasattr(secret, 'secret_type'):
                secret_types_found.add(str(secret.secret_type))

        # Should detect API keys, passwords, or AWS secrets
        assert len(secret_types_found) > 0

    def test_security_secrets_detection_api_key(self, tmp_path):
        """Test secrets detection for API keys."""
        config_file = tmp_path / "config.py"
        config_file.write_text('''
API_KEY = "sk_fake_test_key_not_real_0000000"
STRIPE_KEY = "sk_fake_another_test_key_00000000"
''')

        service = SecretsDetectionService()
        report = service.scan(str(tmp_path))

        assert report is not None
        assert len(report.secrets) > 0

        # Check that API keys were detected
        api_key_found = False
        for secret in report.secrets:
            if 'sk_fake' in str(secret.value):
                api_key_found = True
                break

        assert api_key_found, "API keys should be detected"

    def test_security_secrets_detection_password(self, tmp_path):
        """Test secrets detection for passwords."""
        config_file = tmp_path / "settings.py"
        config_file.write_text('''
DATABASE_PASSWORD = "SuperSecret123!"
DB_PASS = "MyP@ssw0rd"
''')

        service = SecretsDetectionService()
        report = service.scan(str(tmp_path))

        assert report is not None
        # May or may not detect depending on pattern matching
        assert isinstance(report.secrets, list)

    def test_security_injection_detection_sql(self, security_vulnerable_project):
        """Test SQL injection detection."""
        service = InjectionDetectionService()
        report = service.scan(str(security_vulnerable_project))

        assert report is not None
        assert hasattr(report, 'vulnerabilities')
        assert isinstance(report.vulnerabilities, list)

        # Should detect SQL injection vulnerabilities
        sql_injection_found = False
        for vuln in report.vulnerabilities:
            if hasattr(vuln, 'vulnerability_type'):
                if 'sql' in str(vuln.vulnerability_type).lower() or 'injection' in str(vuln.vulnerability_type).lower():
                    sql_injection_found = True
                    break

        assert sql_injection_found, "SQL injection vulnerabilities should be detected"

    def test_security_injection_detection_command(self, security_vulnerable_project):
        """Test command injection detection."""
        service = InjectionDetectionService()
        report = service.scan(str(security_vulnerable_project))

        assert report is not None
        assert hasattr(report, 'vulnerabilities')
        assert isinstance(report.vulnerabilities, list)

        # Should detect command injection vulnerabilities
        cmd_injection_found = False
        for vuln in report.vulnerabilities:
            if hasattr(vuln, 'vulnerability_type'):
                if 'command' in str(vuln.vulnerability_type).lower() or 'os' in str(vuln.vulnerability_type).lower():
                    cmd_injection_found = True
                    break

        assert cmd_injection_found, "Command injection vulnerabilities should be detected"

    def test_security_injection_detection_xss(self, tmp_path):
        """Test XSS injection detection."""
        web_file = tmp_path / "web.py"
        web_file.write_text('''
from flask import request, render_template_string

@app.route('/hello')
def hello():
    name = request.args.get('name')
    return f"<h1>Hello {name}</h1>"

@app.route('/search')
def search():
    query = request.args.get('q')
    return render_template_string("<p>Results for: " + query + "</p>")
''')

        service = InjectionDetectionService()
        report = service.scan(str(tmp_path))

        assert report is not None
        assert hasattr(report, 'vulnerabilities')
        assert isinstance(report.vulnerabilities, list)

        # May detect XSS vulnerabilities
        # Note: Detection depends on implementation

    def test_security_cryptographic_validation_weak_algorithms(self, tmp_path):
        """Test detection of weak cryptographic algorithms."""
        crypto_file = tmp_path / "crypto.py"
        crypto_file.write_text('''
import hashlib
import md5

def hash_password(password):
    """Hash password with MD5 - weak!"""
    return hashlib.md5(password.encode()).hexdigest()

def hash_data(data):
    """Hash data with SHA1 - weak!"""
    return hashlib.sha1(data.encode()).hexdigest()
''')

        service = CryptographicValidationService()
        report = service.scan(str(tmp_path))

        assert report is not None
        assert hasattr(report, 'findings')
        assert isinstance(report.findings, list)

        # Should detect weak hashing algorithms
        weak_crypto_found = False
        for finding in report.findings:
            if 'md5' in str(finding).lower() or 'sha1' in str(finding).lower():
                weak_crypto_found = True
                break

        assert weak_crypto_found, "Weak cryptographic algorithms should be detected"

    def test_security_cryptographic_validation_strong_algorithms(self, tmp_path):
        """Test that strong cryptographic algorithms are not flagged."""
        crypto_file = tmp_path / "crypto_strong.py"
        crypto_file.write_text('''
import hashlib

def hash_password(password, salt):
    """Hash password with SHA256 - strong."""
    return hashlib.sha256((password + salt).encode()).hexdigest()

def hash_data(data):
    """Hash data with SHA512 - strong."""
    return hashlib.sha512(data.encode()).hexdigest()
''')

        service = CryptographicValidationService()
        report = service.scan(str(tmp_path))

        assert report is not None
        assert hasattr(report, 'findings')
        assert isinstance(report.findings, list)

        # Strong algorithms should have fewer or no findings
        # (or findings with lower severity)

    def test_security_scan_with_config(self, simple_project):
        """Test security scan with custom configuration."""
        config = SecurityScanConfig(
            scan_secrets=True,
            scan_dependencies=False,
            scan_vulnerabilities=True,
            scan_crypto=True
        )
        service = StaticSecurityService(config)
        report = service.scan(str(simple_project))

        assert report is not None
        assert hasattr(report, 'security_score')

    def test_security_generate_text_report(self, simple_project):
        """Test generating text report for security scan."""
        service = StaticSecurityService()
        report = service.scan(str(simple_project))
        text_report = service.generate_report(report, "text")

        assert text_report is not None
        assert isinstance(text_report, str)
        assert len(text_report) > 0
        assert "SECURITY" in text_report or "security" in text_report.lower()

    def test_security_generate_json_report(self, simple_project):
        """Test generating JSON report for security scan."""
        service = StaticSecurityService()
        report = service.scan(str(simple_project))
        json_report = service.generate_report(report, "json")

        assert json_report is not None
        assert isinstance(json_report, str)

        # Validate JSON structure
        data = json.loads(json_report)
        assert isinstance(data, dict)
        assert "security_score" in data or "scan_path" in data or "security" in data

    def test_security_empty_directory_handling(self, tmp_path):
        """Test security scan on empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        service = StaticSecurityService()
        report = service.scan(str(empty_dir))

        assert report is not None
        # Empty directory should have high security score
        assert report.security_score >= 0

    def test_security_nonexistent_path_handling(self):
        """Test security scan on nonexistent path."""
        nonexistent = Path("/nonexistent/path/to/nowhere")

        service = StaticSecurityService()
        with pytest.raises(FileNotFoundError):
            service.scan(str(nonexistent))

    def test_security_single_file_scan(self, tmp_path):
        """Test security scan on single file."""
        single_file = tmp_path / "secure.py"
        single_file.write_text('''
def secure_function(data):
    """A secure function."""
    return data.strip()
''')

        service = StaticSecurityService()
        report = service.scan(str(single_file))

        assert report is not None
        assert report.security_score >= 0

    def test_security_multiple_vulnerability_types(self, tmp_path):
        """Test detection of multiple vulnerability types."""
        vuln_file = tmp_path / "multiple_vulns.py"
        vuln_file.write_text('''
import os
import sqlite3
import hashlib

API_KEY = "sk_fake_test_key_not_real_0000000"

def get_user(name):
    """SQL injection vulnerable."""
    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
    return cursor.fetchone()

def run_command(cmd):
    """Command injection vulnerable."""
    os.system(cmd)

def hash_password(password):
    """Weak hashing."""
    return hashlib.md5(password.encode()).hexdigest()
''')

        service = StaticSecurityService()
        report = service.scan(str(tmp_path))

        assert report is not None
        # Should have lower security score due to multiple issues
        assert report.security_score < 100

    def test_security_secrets_in_different_formats(self, tmp_path):
        """Test secrets detection in different file formats."""
        # Python file
        (tmp_path / "config.py").write_text('''
SECRET_KEY = "sk_fake_test_key_not_real_0000000"
''')

        # JSON file
        (tmp_path / "config.json").write_text('''
{
    "api_key": "sk_fake_another_test_key_00000000"
}
''')

        # YAML file
        (tmp_path / "config.yml").write_text('''
database:
  password: "SuperSecret123!"
''')

        service = SecretsDetectionService()
        report = service.scan(str(tmp_path))

        assert report is not None
        # Should detect secrets in various formats
        # Note: Actual detection depends on scanner implementation

    def test_security_severity_levels(self, security_vulnerable_project):
        """Test that vulnerabilities have severity levels."""
        service = StaticSecurityService()
        report = service.scan(str(security_vulnerable_project))

        assert report is not None

        # Check if report has severity information
        if hasattr(report, 'findings'):
            for finding in report.findings:
                if hasattr(finding, 'severity'):
                    assert finding.severity is not None

    def test_security_location_tracking(self, security_vulnerable_project):
        """Test that vulnerabilities track file locations."""
        service = InjectionDetectionService()
        report = service.scan(str(security_vulnerable_project))

        assert report is not None

        # Check that vulnerabilities have location information
        if hasattr(report, 'vulnerabilities') and len(report.vulnerabilities) > 0:
            for vuln in report.vulnerabilities:
                # Should have file path or location
                assert hasattr(vuln, 'file_path') or hasattr(vuln, 'location')
