"""Tests for sensitive data scanner."""
import pytest
from pathlib import Path
from Asgard.Heimdall.Security.SensitiveData.services.sensitive_data_scanner import SensitiveDataScanner
from Asgard.Heimdall.Security.SensitiveData.models.sensitive_data_models import (
    SensitiveDataScanConfig,
    SensitiveDataScanReport,
)


class TestSensitiveDataScannerInstantiation:
    def test_scanner_can_be_instantiated(self):
        assert SensitiveDataScanner() is not None


class TestSensitiveDataScannerCleanCode:
    def test_env_var_lookup_returns_no_findings(self, neutral_tmp):
        (neutral_tmp / "safe.py").write_text(
            "import os\n"
            "password = os.environ.get('PASSWORD')\n"
            "api_key = os.environ.get('API_KEY')\n"
        )
        config = SensitiveDataScanConfig(scan_path=neutral_tmp)
        report: SensitiveDataScanReport = SensitiveDataScanner().scan(config)
        assert report.total_findings == 0
        assert len(report.findings) == 0


class TestSensitiveDataScannerBadCode:
    def test_hardcoded_password_and_api_key_detected(self, neutral_tmp):
        (neutral_tmp / "vuln.py").write_text(
            'password = "SuperSecret123"\n'
            'api_key = "sk_live_abc123def456ghi"\n'
        )
        config = SensitiveDataScanConfig(scan_path=neutral_tmp)
        report: SensitiveDataScanReport = SensitiveDataScanner().scan(config)
        assert report.total_findings > 0
