"""
Baseline + Drift Scenario (L2 Phase 3)

Uses Asgard.Baseline to capture a baseline of Heimdall security findings,
then mutates the fixture and asserts the re-scan reports the
new-findings-only delta correctly — pre-existing findings are suppressed,
new findings are NOT (never mute a real finding that is not baselined).
"""

from pathlib import Path

import pytest

from Asgard.Baseline import BaselineManager
from Asgard.Heimdall.Security.services.secrets_detection_service import (
    SecretsDetectionService,
)

ORIGINAL_SECRET = 'AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPL2"\n'
NEW_SECRET = 'DB_PASSWORD = "Sup3rS3cretPr0dPassw0rd!"\n'

VIOLATION_TYPE = "heimdall_secret"


def _scan(scan_dir: Path):
    return SecretsDetectionService().scan(scan_dir)


@pytest.mark.cross_package
@pytest.mark.scenario
class TestBaselineDriftScenario:
    def test_baselined_findings_are_suppressed_on_rescan(
        self, neutral_scan_dir: Path
    ):
        (neutral_scan_dir / "legacy.py").write_text(ORIGINAL_SECRET, encoding="utf-8")

        report = _scan(neutral_scan_dir)
        assert report.secrets_found > 0, "fixture must produce findings to baseline"

        manager = BaselineManager(project_path=neutral_scan_dir)
        created = manager.create_from_violations(report.findings, VIOLATION_TYPE)
        assert created == len(report.findings)

        # Unchanged code: re-scan, everything is baselined away.
        rescan = _scan(neutral_scan_dir)
        remaining = manager.filter_violations(rescan.findings, VIOLATION_TYPE)
        assert remaining == []

    def test_drift_reports_new_findings_only(self, neutral_scan_dir: Path):
        (neutral_scan_dir / "legacy.py").write_text(ORIGINAL_SECRET, encoding="utf-8")

        baseline_report = _scan(neutral_scan_dir)
        manager = BaselineManager(project_path=neutral_scan_dir)
        manager.create_from_violations(baseline_report.findings, VIOLATION_TYPE)

        # Drift: a brand-new secret lands in a new file.
        (neutral_scan_dir / "newfile.py").write_text(NEW_SECRET, encoding="utf-8")

        drift_report = _scan(neutral_scan_dir)
        assert drift_report.secrets_found > baseline_report.secrets_found

        delta = manager.filter_violations(drift_report.findings, VIOLATION_TYPE)

        # The delta contains ONLY the new finding(s) — old ones suppressed,
        # new ones never muted.
        assert len(delta) == drift_report.secrets_found - baseline_report.secrets_found
        assert all("newfile.py" in f.file_path for f in delta)

    def test_unbaselined_findings_are_never_muted(self, neutral_scan_dir: Path):
        """An empty baseline must pass every finding through untouched."""
        (neutral_scan_dir / "legacy.py").write_text(ORIGINAL_SECRET, encoding="utf-8")

        report = _scan(neutral_scan_dir)
        assert report.secrets_found > 0

        manager = BaselineManager(project_path=neutral_scan_dir)
        remaining = manager.filter_violations(report.findings, VIOLATION_TYPE)

        assert len(remaining) == len(report.findings)

    def test_baseline_is_scoped_by_violation_type(self, neutral_scan_dir: Path):
        """Baselining under one type must not suppress another type."""
        (neutral_scan_dir / "legacy.py").write_text(ORIGINAL_SECRET, encoding="utf-8")

        report = _scan(neutral_scan_dir)
        manager = BaselineManager(project_path=neutral_scan_dir)
        manager.create_from_violations(report.findings, VIOLATION_TYPE)

        other_type = manager.filter_violations(report.findings, "other_check")
        assert len(other_type) == len(report.findings)
