"""
PR Pipeline Scenario (L2 Phase 3)

Models the real-world PR check pipeline: Heimdall (security) + Forseti
(contract validation) + Freya (frontend audit) all run against the change,
and their findings are aggregated into a single combined report.

Freya runs against the deterministic fake-page harness — no browser/network.
"""

from pathlib import Path

import pytest

from Asgard.Forseti.OpenAPI import SpecValidatorService
from Asgard.Heimdall.Security.services.secrets_detection_service import (
    SecretsDetectionService,
)
from Asgard_Test._fixtures.freya_harness import (
    accessible_page_spec,
    inaccessible_page_spec,
    run_accessibility_scan,
)

LEAKY_DIFF_FILE = (
    'AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPL2"\n'
    'DB_PASSWORD = "Sup3rS3cretPr0dPassw0rd!"\n'
)

CLEAN_DIFF_FILE = (
    "import os\n\n"
    'AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]\n'
)


def _run_pr_pipeline(diff_dir: Path, spec_path: Path, page_spec: dict) -> dict:
    """Run all three packages and aggregate into one combined report."""
    secrets_report = SecretsDetectionService().scan(diff_dir)
    contract_result = SpecValidatorService().validate(spec_path)
    a11y_report = run_accessibility_scan(page_spec)

    blocking = (
        secrets_report.secrets_found > 0
        or not contract_result.is_valid
        or a11y_report.critical_count > 0
    )

    return {
        "checks": {
            "heimdall_secrets": {
                "findings": secrets_report.secrets_found,
                "passed": secrets_report.secrets_found == 0,
            },
            "forseti_contract": {
                "errors": len(contract_result.errors),
                "passed": contract_result.is_valid,
            },
            "freya_accessibility": {
                "violations": a11y_report.total_violations,
                "critical": a11y_report.critical_count,
                "score": a11y_report.score,
                "passed": a11y_report.critical_count == 0,
            },
        },
        "blocking": blocking,
    }


@pytest.mark.cross_package
@pytest.mark.scenario
class TestPRPipelineScenario:
    def test_clean_pr_produces_single_passing_combined_report(
        self, neutral_scan_dir: Path, sample_openapi_spec: Path
    ):
        (neutral_scan_dir / "settings.py").write_text(
            CLEAN_DIFF_FILE, encoding="utf-8"
        )

        report = _run_pr_pipeline(
            neutral_scan_dir, sample_openapi_spec, accessible_page_spec()
        )

        assert set(report["checks"]) == {
            "heimdall_secrets",
            "forseti_contract",
            "freya_accessibility",
        }
        assert all(check["passed"] for check in report["checks"].values())
        assert report["blocking"] is False

    def test_pr_with_findings_from_every_package_is_blocking(
        self, neutral_scan_dir: Path, temp_workspace: Path
    ):
        (neutral_scan_dir / "settings.py").write_text(
            LEAKY_DIFF_FILE, encoding="utf-8"
        )
        broken_spec = temp_workspace / "source" / "broken.yaml"
        broken_spec.write_text("openapi: 3.0.0\ninfo:\n  description: no title\n")

        report = _run_pr_pipeline(
            neutral_scan_dir, broken_spec, inaccessible_page_spec()
        )

        # Every package's findings must survive aggregation — nothing muted.
        assert report["checks"]["heimdall_secrets"]["findings"] > 0
        assert report["checks"]["forseti_contract"]["errors"] > 0
        assert report["checks"]["freya_accessibility"]["critical"] > 0
        assert report["blocking"] is True

    def test_single_failing_package_is_sufficient_to_block(
        self, neutral_scan_dir: Path, sample_openapi_spec: Path
    ):
        """Only Freya fails: contract and security are clean."""
        (neutral_scan_dir / "settings.py").write_text(
            CLEAN_DIFF_FILE, encoding="utf-8"
        )

        report = _run_pr_pipeline(
            neutral_scan_dir, sample_openapi_spec, inaccessible_page_spec()
        )

        assert report["checks"]["heimdall_secrets"]["passed"]
        assert report["checks"]["forseti_contract"]["passed"]
        assert not report["checks"]["freya_accessibility"]["passed"]
        assert report["blocking"] is True

    def test_pipeline_output_is_deterministic(
        self, neutral_scan_dir: Path, sample_openapi_spec: Path
    ):
        (neutral_scan_dir / "settings.py").write_text(
            LEAKY_DIFF_FILE, encoding="utf-8"
        )

        first = _run_pr_pipeline(
            neutral_scan_dir, sample_openapi_spec, inaccessible_page_spec()
        )
        second = _run_pr_pipeline(
            neutral_scan_dir, sample_openapi_spec, inaccessible_page_spec()
        )

        assert first == second
