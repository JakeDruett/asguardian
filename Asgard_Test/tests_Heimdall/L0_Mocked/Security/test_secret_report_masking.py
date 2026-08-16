"""CH-0079: Secret reports must not leak prefix+suffix; 32-char tokens are not reconstructible."""

import tempfile
from pathlib import Path

from Asgard.Heimdall.Security.models.security_models import SecurityScanConfig
from Asgard.Heimdall.Security.services._config_secrets_report import (
    generate_json_report as generate_config_json_report,
    generate_markdown_report as generate_config_markdown_report,
    generate_text_report as generate_config_text_report,
)
from Asgard.Heimdall.Security.services._static_security_report_json_md import (
    generate_json_report,
    generate_markdown_report,
)
from Asgard.Heimdall.Security.services.config_secrets_scanner import ConfigSecretsScanner
from Asgard.Heimdall.Security.services.secrets_detection_service import SecretsDetectionService
from Asgard.Heimdall.Security.services.static_security_service import StaticSecurityService
from Asgard.Heimdall.Security.utilities.security_utils import mask_secret

# Unique 32-char token (not a placeholder; high entropy; no "test"/"example").
_TOKEN_32 = "Tk7mQ2wL9pN4xR8eY3vB6cH1zJ5uA0Xy"


def _assert_not_reconstructible(token: str, *blobs: str) -> None:
    joined = "\n".join(blob or "" for blob in blobs)
    assert len(token) == 32
    assert token not in joined
    # Old first-4 + last-4 mask would put both of these in the report.
    assert token[:4] not in joined
    assert token[-4:] not in joined
    for blob in blobs:
        if not blob:
            continue
        visible = blob.replace("*", "")
        assert not (
            visible.startswith(token[:2])
            and visible.endswith(token[-2:])
            and len(visible) > 2
        )


class TestSecretReportMasking:
    def test_32_char_token_not_reconstructible_from_secrets_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "app.py").write_text(f'API_KEY = "{_TOKEN_32}"\n')
            report = SecretsDetectionService().scan(tmp_path)
            assert report.secrets_found > 0
            finding = next(f for f in report.findings if f.masked_value)
            assert _TOKEN_32 not in finding.masked_value
            assert _TOKEN_32 not in finding.line_content
            assert finding.masked_value == mask_secret(_TOKEN_32)
            assert "*" * 32 in finding.line_content
            assert _TOKEN_32[:4] not in finding.line_content
            dumped = finding.model_dump_json()
            _assert_not_reconstructible(
                _TOKEN_32,
                finding.masked_value,
                finding.line_content,
                dumped,
                finding.message,
            )

    def test_32_char_token_not_reconstructible_from_json_md_reports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "app.py").write_text(f'API_KEY = "{_TOKEN_32}"\n')
            config = SecurityScanConfig(
                scan_path=tmp_path,
                scan_secrets=True,
                scan_vulnerabilities=False,
                scan_dependencies=False,
                scan_crypto=False,
                scan_access=False,
                scan_auth=False,
                scan_headers=False,
                scan_tls=False,
                scan_container=False,
                scan_infrastructure=False,
            )
            security_report = StaticSecurityService(config).scan(tmp_path)
            json_report = generate_json_report(security_report)
            md_report = generate_markdown_report(security_report)
            text_report = StaticSecurityService(config).generate_report(security_report, "text")
            _assert_not_reconstructible(_TOKEN_32, json_report, md_report, text_report)
            assert '"masked_value"' in json_report

    def test_32_char_token_not_reconstructible_from_config_secret_reports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "settings.yaml").write_text(
                f"database:\n  password: {_TOKEN_32}\n"
            )
            scanner = ConfigSecretsScanner()
            report = scanner.analyze(tmp_path)
            assert report.has_findings
            finding = report.detected_findings[0]
            assert finding.masked_value == mask_secret(_TOKEN_32)
            text = generate_config_text_report(report)
            json_report = generate_config_json_report(report)
            md = generate_config_markdown_report(report)
            _assert_not_reconstructible(
                _TOKEN_32,
                finding.masked_value,
                finding.context_description,
                text,
                json_report,
                md,
            )
