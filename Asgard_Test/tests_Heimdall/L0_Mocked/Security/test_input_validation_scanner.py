"""Tests for input validation scanner."""
import pytest
from pathlib import Path
from Asgard.Heimdall.Security.InputValidation.services.input_validation_scanner import InputValidationScanner
from Asgard.Heimdall.Security.InputValidation.models.input_validation_models import (
    InputValidationScanConfig,
    InputValidationScanReport,
)


class TestInputValidationScannerInstantiation:
    def test_scanner_can_be_instantiated(self):
        assert InputValidationScanner() is not None


class TestInputValidationScannerCleanCode:
    def test_parameterized_query_returns_no_findings(self, neutral_tmp):
        (neutral_tmp / "safe.py").write_text(
            "def get_user(conn, user_id):\n"
            "    cursor = conn.cursor()\n"
            "    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))\n"
            "    return cursor.fetchone()\n"
        )
        config = InputValidationScanConfig(scan_path=neutral_tmp)
        report: InputValidationScanReport = InputValidationScanner().scan(config)
        assert report.total_findings == 0
        assert len(report.findings) == 0


class TestInputValidationScannerBadCode:
    def test_sql_with_request_param_detected(self, neutral_tmp):
        # Pattern: execute("..." + req.params) triggers sql_string_concat
        (neutral_tmp / "vuln.js").write_text(
            "app.get('/user', (req, res) => {\n"
            "    db.query(\"SELECT * FROM users WHERE id = '\" + req.params.id + \"'\");\n"
            "});\n"
        )
        config = InputValidationScanConfig(scan_path=neutral_tmp)
        report: InputValidationScanReport = InputValidationScanner().scan(config)
        assert report.total_findings > 0
