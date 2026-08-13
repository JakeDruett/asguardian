"""
Heimdall-Verdandi Integration Tests

Tests for cross-package integration between Heimdall (security scanning) and
Verdandi (SLO / error-budget accounting). Security findings are treated as
"bad events" against a security-quality SLO: a codebase riddled with critical
findings must consume error budget; a clean codebase must not.
"""

import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from Asgard.Heimdall.Security.services.secrets_detection_service import (
    SecretsDetectionService,
)
from Asgard.Verdandi.SLO import (
    ErrorBudgetCalculator,
    SLIMetric,
    SLODefinition,
    SLOComplianceStatus,
)

VULNERABLE_MODULE = (
    'AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPL2"\n'
    'DATABASE_PASSWORD = "Sup3rS3cretPr0dPassw0rd!"\n'
    'SSH_KEY = "-----BEGIN RSA PRIVATE KEY-----\\nMIIEpAIB\\n'
    '-----END RSA PRIVATE KEY-----"\n'
)

CLEAN_MODULE = (
    "import os\n\n"
    'AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]\n'
    'DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD")\n'
)


@pytest.fixture
def scan_dir():
    """Neutral temp dir (tmp_path embeds the test name, which triggers the
    scanners' test-context suppression and would mute findings)."""
    d = Path(tempfile.mkdtemp(prefix="l2fixture_"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _security_slo() -> SLODefinition:
    return SLODefinition(
        name="scanned-files-secret-free",
        slo_type="quality",
        target=99.0,
        window_days=30,
        service_name="payments-api",
    )


def _metrics_from_report(report) -> list:
    """Each scanned file is an event; a file with a finding is a bad event."""
    dirty_files = {f.file_path for f in report.findings}
    total = max(report.total_files_scanned, 1)
    good = total - min(len(dirty_files), total)
    return [
        SLIMetric(
            timestamp=datetime.now() - timedelta(days=1),
            service_name="payments-api",
            slo_type="quality",
            good_events=good,
            total_events=total,
        )
    ]


@pytest.mark.cross_package
class TestSecurityFindingsFeedErrorBudget:
    def test_critical_findings_breach_security_slo(self, scan_dir):
        (scan_dir / "config.py").write_text(VULNERABLE_MODULE, encoding="utf-8")

        report = SecretsDetectionService().scan(scan_dir)
        assert report.secrets_found > 0, "fixture must produce secret findings"

        budget = ErrorBudgetCalculator().calculate(
            _security_slo(), _metrics_from_report(report)
        )

        # The single scanned file is dirty → SLI is 0% against a 99% target.
        assert budget.bad_events > 0
        assert budget.status in (
            SLOComplianceStatus.BREACHED,
            SLOComplianceStatus.AT_RISK,
            "breached",
            "at_risk",
        ), f"critical Heimdall findings must consume error budget, got {budget.status}"

    def test_clean_codebase_keeps_budget_compliant(self, scan_dir):
        (scan_dir / "config.py").write_text(CLEAN_MODULE, encoding="utf-8")

        report = SecretsDetectionService().scan(scan_dir)
        assert report.secrets_found == 0, (
            f"clean fixture unexpectedly flagged: "
            f"{[f.description for f in report.findings]}"
        )

        budget = ErrorBudgetCalculator().calculate(
            _security_slo(), _metrics_from_report(report)
        )

        assert budget.bad_events == 0
        assert budget.status in (SLOComplianceStatus.COMPLIANT, "compliant"), (
            f"clean scan must not consume error budget, got {budget.status}"
        )

    def test_budget_consumption_is_monotonic_in_findings(self, scan_dir):
        """More dirty files must never report LESS budget consumption."""
        (scan_dir / "clean.py").write_text(CLEAN_MODULE, encoding="utf-8")
        report_one = SecretsDetectionService().scan(scan_dir)
        (scan_dir / "dirty.py").write_text(VULNERABLE_MODULE, encoding="utf-8")
        report_two = SecretsDetectionService().scan(scan_dir)

        calc = ErrorBudgetCalculator()
        slo = _security_slo()
        consumed_one = calc.calculate(slo, _metrics_from_report(report_one))
        consumed_two = calc.calculate(slo, _metrics_from_report(report_two))

        assert (
            consumed_two.budget_consumed_percent
            >= consumed_one.budget_consumed_percent
        )
