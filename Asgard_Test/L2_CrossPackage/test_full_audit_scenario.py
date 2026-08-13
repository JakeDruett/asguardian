"""
Full Audit Scenario (L2 Phase 3)

Runs every package's top-level entry point against a curated fixture corpus
and sanity-checks the combined report shape:

- Heimdall: secrets scan over the corpus source tree
- Forseti: OpenAPI contract validation
- Freya: accessibility audit (deterministic fake-page harness)
- Verdandi: SLA check over canned frontend timings
- Volundr: deployment manifest generation for the audited service
"""

import json
from pathlib import Path

import pytest

from Asgard.Forseti.OpenAPI import SpecValidatorService
from Asgard.Heimdall.Security.services.secrets_detection_service import (
    SecretsDetectionService,
)
from Asgard.Verdandi.Analysis import SLAChecker, SLAConfig
from Asgard.Volundr.Kubernetes import ManifestConfig, ManifestGenerator
from Asgard_Test._fixtures.freya_harness import (
    canned_page_load_timings,
    inaccessible_page_spec,
    run_accessibility_scan,
)

CORPUS_SOURCE = (
    "import os\n\n"
    "def handler(event):\n"
    "    return {'key': os.environ.get('API_KEY')}\n"
)


def _run_full_audit(corpus_dir: Path, spec_path: Path, output_dir: Path) -> dict:
    secrets_report = SecretsDetectionService().scan(corpus_dir)
    contract_result = SpecValidatorService().validate(spec_path)
    a11y_report = run_accessibility_scan(inaccessible_page_spec())

    timings = canned_page_load_timings()
    sla_result = SLAChecker(
        SLAConfig(target_percentile=95.0, threshold_ms=3000.0)
    ).check(sorted(timings.values()))

    manifest = ManifestGenerator(output_dir=str(output_dir)).generate(
        ManifestConfig(name="audited-app", image="registry.local/app:1.0.0")
    )

    return {
        "heimdall": {
            "files_scanned": secrets_report.total_files_scanned,
            "secrets_found": secrets_report.secrets_found,
        },
        "forseti": {
            "is_valid": contract_result.is_valid,
            "errors": len(contract_result.errors),
            "warnings": len(contract_result.warnings),
        },
        "freya": {
            "url": a11y_report.url,
            "score": a11y_report.score,
            "violations": a11y_report.total_violations,
            "critical": a11y_report.critical_count,
        },
        "verdandi": {
            "status": getattr(sla_result.status, "value", str(sla_result.status)),
            "p95_ms": sla_result.percentile_value,
        },
        "volundr": {
            "manifest_generated": bool(manifest.yaml_content),
        },
    }


@pytest.mark.cross_package
@pytest.mark.scenario
class TestFullAuditScenario:
    def test_combined_report_has_every_package_section(
        self, neutral_scan_dir: Path, sample_openapi_spec: Path, output_dir: Path
    ):
        (neutral_scan_dir / "handler.py").write_text(CORPUS_SOURCE, encoding="utf-8")

        report = _run_full_audit(neutral_scan_dir, sample_openapi_spec, output_dir)

        assert set(report) == {"heimdall", "forseti", "freya", "verdandi", "volundr"}
        assert report["heimdall"]["files_scanned"] >= 1
        assert report["forseti"]["is_valid"] is True
        assert report["freya"]["violations"] > 0
        assert 0.0 <= report["freya"]["score"] <= 100.0
        assert report["verdandi"]["status"] in ("compliant", "warning", "breached")
        assert report["volundr"]["manifest_generated"] is True

    def test_combined_report_is_json_serializable_and_deterministic(
        self, neutral_scan_dir: Path, sample_openapi_spec: Path, output_dir: Path
    ):
        (neutral_scan_dir / "handler.py").write_text(CORPUS_SOURCE, encoding="utf-8")

        first = _run_full_audit(neutral_scan_dir, sample_openapi_spec, output_dir)
        second = _run_full_audit(neutral_scan_dir, sample_openapi_spec, output_dir)

        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)

    def test_clean_corpus_reports_zero_security_findings_honestly(
        self, neutral_scan_dir: Path, sample_openapi_spec: Path, output_dir: Path
    ):
        """A clean corpus must report clean — but never hide the scan scope."""
        (neutral_scan_dir / "handler.py").write_text(CORPUS_SOURCE, encoding="utf-8")

        report = _run_full_audit(neutral_scan_dir, sample_openapi_spec, output_dir)

        assert report["heimdall"]["secrets_found"] == 0
        # Scope must still be visible: the audit says what it looked at.
        assert report["heimdall"]["files_scanned"] >= 1
