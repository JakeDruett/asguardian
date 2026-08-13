"""
Heimdall-Freya Integration Tests

Tests for cross-package integration between Heimdall (security scanning) and
Freya (frontend/UI auditing). Scenario: a frontend bundle is scanned by
Heimdall for leaked secrets while Freya audits the rendered page; a combined
frontend gate fails if EITHER package finds a blocking issue.

Freya runs against the deterministic fake-page harness
(Asgard_Test/_fixtures/freya_harness.py) — no live browser, no network.
"""

from pathlib import Path

import pytest

from Asgard.Freya.Accessibility.models.accessibility_models import (
    ViolationSeverity,
)
from Asgard.Heimdall.Security.services.secrets_detection_service import (
    SecretsDetectionService,
)
from Asgard_Test._fixtures.freya_harness import (
    accessible_page_spec,
    inaccessible_page_spec,
    run_accessibility_scan,
)

LEAKY_BUNDLE_JS = (
    "// webpack bundle (fixture)\n"
    'const AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPL2";\n'
    'const API_PASSWORD = "Sup3rS3cretPr0dPassw0rd!";\n'
    "export function init() { return AWS_ACCESS_KEY_ID; }\n"
)

CLEAN_BUNDLE_JS = (
    "// webpack bundle (fixture)\n"
    "export function init(config) { return config.apiKeyRef; }\n"
)


def _frontend_gate(secrets_report, a11y_report) -> bool:
    """Deploy gate: no leaked secrets AND no critical accessibility issues."""
    if secrets_report.secrets_found > 0:
        return False
    if a11y_report.critical_count > 0:
        return False
    return True


@pytest.mark.cross_package
@pytest.mark.heimdall_freya
class TestSecretsInBundleGateFrontendAudit:
    def test_leaked_secret_in_bundle_blocks_even_accessible_page(
        self, neutral_scan_dir: Path
    ):
        (neutral_scan_dir / "bundle.js").write_text(LEAKY_BUNDLE_JS, encoding="utf-8")

        secrets_report = SecretsDetectionService().scan(neutral_scan_dir)
        assert secrets_report.secrets_found > 0, (
            "fixture bundle must produce secret findings"
        )

        a11y_report = run_accessibility_scan(accessible_page_spec())
        assert a11y_report.critical_count == 0

        # Even a perfectly accessible page must not pass with a leaked secret.
        assert _frontend_gate(secrets_report, a11y_report) is False

    def test_clean_bundle_and_accessible_page_pass_gate(
        self, neutral_scan_dir: Path
    ):
        (neutral_scan_dir / "bundle.js").write_text(CLEAN_BUNDLE_JS, encoding="utf-8")

        secrets_report = SecretsDetectionService().scan(neutral_scan_dir)
        assert secrets_report.secrets_found == 0, (
            f"clean fixture unexpectedly flagged: "
            f"{[f.description for f in secrets_report.findings]}"
        )

        a11y_report = run_accessibility_scan(accessible_page_spec())
        assert a11y_report.total_violations == 0

        assert _frontend_gate(secrets_report, a11y_report) is True

    def test_clean_bundle_with_inaccessible_page_still_blocks(
        self, neutral_scan_dir: Path
    ):
        (neutral_scan_dir / "bundle.js").write_text(CLEAN_BUNDLE_JS, encoding="utf-8")

        secrets_report = SecretsDetectionService().scan(neutral_scan_dir)
        assert secrets_report.secrets_found == 0

        a11y_report = run_accessibility_scan(inaccessible_page_spec())
        assert a11y_report.critical_count > 0, (
            "inaccessible fixture page must produce critical violations"
        )

        assert _frontend_gate(secrets_report, a11y_report) is False


@pytest.mark.cross_package
@pytest.mark.heimdall_freya
class TestCombinedFrontendFindings:
    def test_combined_report_preserves_both_packages_findings(
        self, neutral_scan_dir: Path
    ):
        (neutral_scan_dir / "bundle.js").write_text(LEAKY_BUNDLE_JS, encoding="utf-8")

        secrets_report = SecretsDetectionService().scan(neutral_scan_dir)
        a11y_report = run_accessibility_scan(inaccessible_page_spec())

        combined = {
            "security": {
                "secrets_found": secrets_report.secrets_found,
                "files_scanned": secrets_report.total_files_scanned,
            },
            "accessibility": {
                "violations": a11y_report.total_violations,
                "critical": a11y_report.critical_count,
                "score": a11y_report.score,
            },
        }

        # Neither package's findings may be muted by the other.
        assert combined["security"]["secrets_found"] > 0
        assert combined["accessibility"]["violations"] > 0
        assert combined["accessibility"]["critical"] > 0
        assert combined["accessibility"]["score"] < 100.0

    def test_severity_is_independent_of_source_package(
        self, neutral_scan_dir: Path
    ):
        """A CRITICAL a11y violation stays CRITICAL next to security findings."""
        (neutral_scan_dir / "bundle.js").write_text(LEAKY_BUNDLE_JS, encoding="utf-8")

        SecretsDetectionService().scan(neutral_scan_dir)
        a11y_report = run_accessibility_scan(inaccessible_page_spec())

        critical = [
            v for v in a11y_report.violations
            if v.severity == ViolationSeverity.CRITICAL
        ]
        assert {v.wcag_reference for v in critical} == {"1.1.1", "4.1.2"}
