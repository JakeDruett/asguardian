"""
L5 Compliance Tests — Legacy (pre-uplift) Security Scanner Ground Truth.

Covers the four original Heimdall security services that predate the
scanner-per-domain layout:

- ``InjectionDetectionService``  (CWE-89 / CWE-78 / CWE-79 / CWE-22)
- ``SecretsDetectionService``    (CWE-798)
- ``CryptographicValidationService`` (CWE-327 / CWE-330)
- ``TaintAnalyzer``              (end-to-end source→sink flows)

Every scanner gets at least one known-bad positive test (a finding MUST be
produced — if not, the scanner is broken) and one known-good negative test
(clean code MUST NOT produce high-severity noise).
"""

import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def scan_dir():
    """Neutral temp directory whose path contains no 'test' component.

    pytest's ``tmp_path`` embeds the test name, which trips the scanners'
    test-context suppression and would mute the known-bad fixtures.
    """
    d = Path(tempfile.mkdtemp(prefix="l5fixture_"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)

from Asgard.Heimdall.Security.services.injection_detection_service import (
    InjectionDetectionService,
)
from Asgard.Heimdall.Security.services.secrets_detection_service import (
    SecretsDetectionService,
)
from Asgard.Heimdall.Security.services.cryptographic_validation_service import (
    CryptographicValidationService,
)
from Asgard.Heimdall.Security.TaintAnalysis.services.taint_analyzer import TaintAnalyzer
from Asgard.Heimdall.Security.TaintAnalysis.models.taint_models import TaintConfig


def _write(tmp_path: Path, name: str, content: str) -> Path:
    target = tmp_path / name
    target.write_text(content, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Injection — CWE-89 / CWE-78
# ---------------------------------------------------------------------------

SQL_CONCAT_BAD = '''
import sqlite3

def get_user(cursor, user_id):
    query = "SELECT * FROM users WHERE id = '" + user_id + "'"
    cursor.execute(query)
'''

SQL_FSTRING_BAD = '''
def find(cursor, name):
    cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
'''

COMMAND_INJECTION_BAD = '''
import subprocess

def run(user_input):
    subprocess.call("ping " + user_input, shell=True)
'''

INJECTION_GOOD = '''
import subprocess

def get_user(cursor, user_id):
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

def run(host):
    subprocess.call(["ping", "-c", "1", host])
'''


class TestInjectionDetectionCompliance:
    @pytest.mark.parametrize(
        "name,payload",
        [
            ("sql_concat.py", SQL_CONCAT_BAD),
            ("sql_fstring.py", SQL_FSTRING_BAD),
            ("cmd_shell.py", COMMAND_INJECTION_BAD),
        ],
    )
    def test_known_bad_produces_finding(self, scan_dir, name, payload):
        project = _write(scan_dir, name, payload)
        report = InjectionDetectionService().scan(project)
        assert report.vulnerabilities_found > 0, (
            f"InjectionDetectionService missed known-bad fixture {name}"
        )

    def test_known_bad_severity_is_high_or_critical(self, scan_dir):
        project = _write(scan_dir, "sql_concat.py", SQL_CONCAT_BAD)
        report = InjectionDetectionService().scan(project)
        severities = {f.severity for f in report.findings}
        assert severities & {"critical", "high"}, (
            f"Expected CRITICAL/HIGH injection severity, got {severities}"
        )

    def test_known_bad_carries_cwe_metadata(self, scan_dir):
        project = _write(scan_dir, "sql_concat.py", SQL_CONCAT_BAD)
        report = InjectionDetectionService().scan(project)
        cwes = {getattr(f, "cwe_id", "") for f in report.findings}
        assert any(c and c.startswith("CWE-") for c in cwes), (
            f"Injection findings missing CWE tags: {cwes}"
        )

    def test_known_good_produces_no_critical_findings(self, scan_dir):
        project = _write(scan_dir, "safe.py", INJECTION_GOOD)
        report = InjectionDetectionService().scan(project)
        critical = [f for f in report.findings if f.severity == "critical"]
        assert critical == [], (
            f"Parameterized-query fixture produced CRITICAL findings: "
            f"{[f.description for f in critical]}"
        )


# ---------------------------------------------------------------------------
# Secrets — CWE-798
# ---------------------------------------------------------------------------

SECRETS_BAD = '''
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPL2"
DATABASE_PASSWORD = "Sup3rS3cretPr0dPassw0rd!"
'''

SECRETS_PRIVATE_KEY_BAD = (
    'SSH_KEY = "-----BEGIN RSA PRIVATE KEY-----'
    '\\nMIIEpAIBAAKCAQEA7bq7rDual8H0\\n-----END RSA PRIVATE KEY-----"\n'
)

SECRETS_GOOD = '''
import os

AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD")
'''


class TestSecretsDetectionCompliance:
    @pytest.mark.parametrize(
        "name,payload",
        [
            ("hardcoded_creds.py", SECRETS_BAD),
            ("private_key.py", SECRETS_PRIVATE_KEY_BAD),
        ],
    )
    def test_known_bad_produces_finding(self, scan_dir, name, payload):
        project = _write(scan_dir, name, payload)
        report = SecretsDetectionService().scan(project)
        assert report.secrets_found > 0, (
            f"SecretsDetectionService missed known-bad fixture {name}"
        )

    def test_known_bad_severity_is_high_or_critical(self, scan_dir):
        project = _write(scan_dir, "hardcoded_creds.py", SECRETS_BAD)
        report = SecretsDetectionService().scan(project)
        severities = {f.severity for f in report.findings}
        assert severities & {"critical", "high"}, (
            f"Expected CRITICAL/HIGH secret severity, got {severities}"
        )

    def test_known_good_env_lookup_is_clean(self, scan_dir):
        project = _write(scan_dir, "env_config.py", SECRETS_GOOD)
        report = SecretsDetectionService().scan(project)
        assert report.secrets_found == 0, (
            f"Environment-variable config flagged as secrets: "
            f"{[f.description for f in report.findings]}"
        )


# ---------------------------------------------------------------------------
# Crypto — CWE-327 / CWE-330
# ---------------------------------------------------------------------------

CRYPTO_MD5_BAD = '''
import hashlib

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()
'''

CRYPTO_WEAK_RANDOM_BAD = '''
import random

def generate_session_token():
    return str(random.randint(0, 2 ** 128))
'''

CRYPTO_GOOD = '''
import hashlib
import secrets

def hash_data(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def generate_session_token() -> str:
    return secrets.token_urlsafe(32)
'''


class TestCryptographicValidationCompliance:
    @pytest.mark.parametrize(
        "name,payload",
        [
            ("md5_password.py", CRYPTO_MD5_BAD),
            ("weak_random_token.py", CRYPTO_WEAK_RANDOM_BAD),
        ],
    )
    def test_known_bad_produces_finding(self, scan_dir, name, payload):
        project = _write(scan_dir, name, payload)
        report = CryptographicValidationService().scan(project)
        assert report.issues_found > 0, (
            f"CryptographicValidationService missed known-bad fixture {name}"
        )

    def test_known_good_produces_no_high_findings(self, scan_dir):
        project = _write(scan_dir, "safe_crypto.py", CRYPTO_GOOD)
        report = CryptographicValidationService().scan(project)
        noisy = [f for f in report.findings if f.severity in ("critical", "high")]
        assert noisy == [], (
            f"SHA-256/secrets fixture produced HIGH+ crypto findings: "
            f"{[f.description for f in noisy]}"
        )


# ---------------------------------------------------------------------------
# Taint — end-to-end source → sink
# ---------------------------------------------------------------------------

TAINT_FLASK_SQL_BAD = '''
from flask import request
import sqlite3

def lookup():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = " + user_id)
    return cursor.fetchall()
'''

TAINT_OS_SYSTEM_BAD = '''
import os
from flask import request

def ping():
    host = request.args.get("host")
    os.system("ping -c 1 " + host)
'''

TAINT_GOOD = '''
import sqlite3

def lookup(user_id: int):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchall()
'''


class TestTaintAnalyzerCompliance:
    @pytest.mark.parametrize(
        "name,payload",
        [
            ("flask_sql.py", TAINT_FLASK_SQL_BAD),
            ("os_system.py", TAINT_OS_SYSTEM_BAD),
        ],
    )
    def test_known_bad_source_to_sink_flow_detected(self, scan_dir, name, payload):
        project = _write(scan_dir, name, payload)
        report = TaintAnalyzer(TaintConfig(scan_path=str(project))).scan()
        assert report.total_flows > 0, (
            f"TaintAnalyzer missed known-bad source→sink fixture {name}"
        )

    def test_known_bad_flow_carries_cwe_and_severity(self, scan_dir):
        project = _write(scan_dir, "flask_sql.py", TAINT_FLASK_SQL_BAD)
        report = TaintAnalyzer(TaintConfig(scan_path=str(project))).scan()
        assert report.flows, "expected at least one taint flow"
        flow = report.flows[0]
        assert flow.severity in ("critical", "high")
        assert flow.cwe_id.startswith("CWE-")

    def test_known_good_parameterized_query_is_clean(self, scan_dir):
        project = _write(scan_dir, "safe_lookup.py", TAINT_GOOD)
        report = TaintAnalyzer(TaintConfig(scan_path=str(project))).scan()
        assert report.total_flows == 0, (
            f"Parameterized-query fixture produced taint flows: "
            f"{[f.title for f in report.flows]}"
        )
