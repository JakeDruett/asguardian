"""CH-0085: secret FP filters must not drop values that merely contain test/example."""

import tempfile
from pathlib import Path

import pytest

from Asgard.Heimdall.Security.models.security_models import SecretType
from Asgard.Heimdall.Security.services._secrets_detection_helpers import (
    is_false_positive,
)
from Asgard.Heimdall.Security.services.secrets_detection_service import (
    SecretsDetectionService,
)

TESTHOST_URL = "postgres://u:p@testhost/db"
CONTEST_PASSWORD = "ContestWinner1"
AWS_KEY_WITH_TEST = "AKIATESTTESTTESTTEST"
GITHUB_TOKEN_WITH_TEST = "ghp_testtesttesttesttesttesttesttesttes1"
AWS_SECRET_WITH_TEST = "odJFCrnl2edlBDtestdz1C5Jau2RJtBRnlWmTSHf"


def _fp(
    value: str,
    *,
    matched_text: str | None = None,
    secret_type: SecretType | None = None,
    pattern_name: str = "",
) -> bool:
    return is_false_positive(
        value,
        matched_text if matched_text is not None else value,
        "nearby example sample test fixture",
        0,
        secret_type=secret_type,
        pattern_name=pattern_name,
    )


def _scan(source: str):
    # Default exclude_patterns match pytest tmp_path names (`test_*`).
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "app.py").write_text(source, encoding="utf-8")
        return SecretsDetectionService().scan(root)


class TestIsFalsePositiveWholeValue:
    @pytest.mark.parametrize(
        "value",
        [
            "example_key",
            "sample_secret",
            "test_password",
            "dummy_token",
            "your_key_here",
            "xxxxxxxx",
            "<api_key>",
            "${SECRET}",
        ],
    )
    def test_whole_value_placeholders_are_dropped(self, value):
        assert _fp(value) is True

    @pytest.mark.parametrize(
        "value",
        [
            TESTHOST_URL,
            CONTEST_PASSWORD,
            "sk_test_51NotARealStripeKey000000",
            "AKIAIOSFODNN7EXAMPLE",
            AWS_KEY_WITH_TEST,
            GITHUB_TOKEN_WITH_TEST,
        ],
    )
    def test_embedded_test_example_is_not_a_placeholder(self, value):
        assert _fp(value) is False

    def test_matched_text_substring_does_not_drop_value(self):
        assert (
            _fp(
                CONTEST_PASSWORD,
                matched_text='password = "ContestWinner1"  # test example sample',
            )
            is False
        )
        assert (
            _fp(
                TESTHOST_URL,
                matched_text=TESTHOST_URL,
            )
            is False
        )

    @pytest.mark.parametrize(
        ("value", "secret_type", "pattern_name"),
        [
            (AWS_KEY_WITH_TEST, SecretType.AWS_CREDENTIALS, "aws_access_key"),
            ("AKIAIOSFODNN7EXAMPLE", SecretType.AWS_CREDENTIALS, "aws_access_key"),
            (GITHUB_TOKEN_WITH_TEST, SecretType.ACCESS_TOKEN, "github_token"),
            (
                "-----BEGIN RSA PRIVATE KEY-----",
                SecretType.PRIVATE_KEY,
                "private_key_header",
            ),
            (
                "-----BEGIN OPENSSH PRIVATE KEY-----",
                SecretType.SSH_KEY,
                "ssh_private_key",
            ),
        ],
    )
    def test_high_signal_types_never_drop_on_test_substring(
        self, value, secret_type, pattern_name
    ):
        assert (
            _fp(value, secret_type=secret_type, pattern_name=pattern_name) is False
        )

    def test_high_signal_template_values_still_drop(self):
        assert (
            _fp(
                "${AWS_SECRET}",
                secret_type=SecretType.AWS_CREDENTIALS,
                pattern_name="aws_secret_key",
            )
            is True
        )


class TestSecretsScanKeepsEmbeddedTest:
    def test_testhost_database_url_is_reported(self):
        report = _scan(f'DATABASE_URL = "{TESTHOST_URL}"\n')
        db_findings = [
            finding
            for finding in report.findings
            if finding.secret_type == SecretType.DATABASE_URL
            or "database" in finding.pattern_name.lower()
        ]
        assert db_findings, "postgres://u:p@testhost/db must be reported"

    def test_contest_winner_password_is_reported(self):
        report = _scan(f'password = "{CONTEST_PASSWORD}"\n')
        password_findings = [
            finding
            for finding in report.findings
            if finding.secret_type == SecretType.PASSWORD
            or "password" in finding.pattern_name.lower()
        ]
        assert password_findings, "ContestWinner1 must be reported"

    def test_aws_access_key_containing_test_is_reported(self):
        report = _scan(f'AWS_ACCESS_KEY = "{AWS_KEY_WITH_TEST}"\n')
        aws_findings = [
            finding
            for finding in report.findings
            if finding.secret_type == SecretType.AWS_CREDENTIALS
            or finding.pattern_name.startswith("aws_")
        ]
        assert aws_findings, "AWS key embedding TEST must not be dropped"

    def test_github_token_containing_test_is_reported(self):
        report = _scan(f'GITHUB_TOKEN = "{GITHUB_TOKEN_WITH_TEST}"\n')
        github_findings = [
            finding
            for finding in report.findings
            if finding.pattern_name == "github_token"
        ]
        assert github_findings, "GitHub token embedding test must not be dropped"

    def test_aws_secret_containing_test_is_reported(self):
        report = _scan(f'aws_secret_access_key = "{AWS_SECRET_WITH_TEST}"\n')
        aws_findings = [
            finding
            for finding in report.findings
            if "aws" in finding.pattern_name.lower()
        ]
        assert aws_findings, "AWS secret embedding test must not be dropped"

    def test_private_key_is_reported_beside_test_wording(self):
        report = _scan(
            "# test example sample fixture\n"
            'PRIVATE_KEY = ("-----BEGIN RSA PRIVATE KEY-----\\n"\n'
            '               "MIIEpAIBAAKCAQEAabcdefghijklmnopqrstuvwxyz0123456789\\n"\n'
            '               "-----END RSA PRIVATE KEY-----")\n'
        )
        key_findings = [
            finding
            for finding in report.findings
            if finding.secret_type in {SecretType.PRIVATE_KEY, SecretType.SSH_KEY}
            or "private_key" in finding.pattern_name
        ]
        assert key_findings, "private key must not drop because nearby text says test"

    def test_whole_value_placeholder_still_dropped(self):
        report = _scan(
            'EXAMPLE_API_KEY = "your_api_key_here"\n'
            'SAMPLE_PASSWORD = "example_password"\n'
            'TEST_SECRET = "xxxxxxxxxxxxxxxx"\n'
        )
        assert report.secrets_found == 0
