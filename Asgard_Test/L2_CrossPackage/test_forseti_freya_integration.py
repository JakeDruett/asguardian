"""
Forseti-Freya Integration Tests

Tests for cross-package integration between Forseti (API contract validation)
and Freya (frontend/UI auditing). Scenario: a validated OpenAPI contract
drives generation of a form page fixture (one input per request-body field),
which Freya then audits for accessibility.

Freya runs against the deterministic fake-page harness
(Asgard_Test/_fixtures/freya_harness.py) — no live browser, no network.
"""

from pathlib import Path

import pytest
import yaml

from Asgard.Forseti.OpenAPI import SpecValidatorService
from Asgard_Test._fixtures.freya_harness import run_accessibility_scan


def _form_page_spec_from_contract(spec_path: Path, with_labels: bool) -> dict:
    """
    Build a Freya fake-page spec whose form mirrors the POST /users request
    body of the OpenAPI contract: one input per schema property, plus a
    submit button.
    """
    spec_data = yaml.safe_load(spec_path.read_text())
    schema = spec_data["components"]["schemas"]["UserCreate"]
    fields = sorted(schema["properties"].keys())

    elements = [
        {"tag": "h1", "text": "Create user"},
        {"tag": "main", "text": "Signup form"},
    ]
    for field in fields:
        if with_labels:
            elements.append(
                {"tag": "label", "attrs": {"for": field}, "text": field.title()}
            )
        elements.append(
            {"tag": "input", "attrs": {"type": "text", "id": field, "name": field}}
        )
    elements.append(
        {"tag": "button", "attrs": {"type": "submit"}, "text": "Create account"}
    )

    return {
        "url": "http://fixture.local/signup",
        "title": "Create user - Fixture App",
        "elements": elements,
    }


@pytest.mark.cross_package
@pytest.mark.forseti_freya
class TestContractDrivesAccessibilityFixtures:
    def test_valid_contract_yields_accessible_form(self, sample_openapi_spec: Path):
        validation = SpecValidatorService().validate(sample_openapi_spec)
        assert validation.is_valid, (
            f"fixture spec must validate, got errors: {validation.errors}"
        )

        page_spec = _form_page_spec_from_contract(sample_openapi_spec, with_labels=True)
        report = run_accessibility_scan(page_spec)

        assert report.total_violations == 0, (
            f"labeled contract-driven form must be clean, got: "
            f"{[v.description for v in report.violations]}"
        )
        assert report.score == 100.0

    def test_unlabeled_contract_form_flags_every_contract_field(
        self, sample_openapi_spec: Path
    ):
        validation = SpecValidatorService().validate(sample_openapi_spec)
        assert validation.is_valid

        page_spec = _form_page_spec_from_contract(
            sample_openapi_spec, with_labels=False
        )
        report = run_accessibility_scan(page_spec)

        spec_data = yaml.safe_load(sample_openapi_spec.read_text())
        contract_fields = set(
            spec_data["components"]["schemas"]["UserCreate"]["properties"].keys()
        )

        label_violations = [
            v for v in report.violations if v.wcag_reference == "3.3.2"
        ]
        flagged_fields = {
            v.element_selector.split('"')[1] for v in label_violations
        }

        # Every field in the API contract must surface as an unlabeled input.
        assert flagged_fields == contract_fields

    def test_invalid_contract_blocks_fixture_generation(self, temp_workspace: Path):
        broken_spec = temp_workspace / "source" / "broken_openapi.yaml"
        broken_spec.write_text(
            # Missing required top-level fields (info/paths malformed).
            "openapi: 3.0.0\n"
            "info:\n"
            "  description: missing title and version\n"
        )

        validation = SpecValidatorService().validate(broken_spec)
        assert not validation.is_valid
        assert len(validation.errors) > 0

        # Gate: fixture generation must not proceed from an invalid contract.
        proceed = validation.is_valid
        assert proceed is False


@pytest.mark.cross_package
@pytest.mark.forseti_freya
class TestContractDriftReflectsInAudit:
    def test_added_contract_field_changes_audit_deterministically(
        self, sample_openapi_spec: Path, temp_workspace: Path
    ):
        """Adding a field to the contract adds exactly one new form violation."""
        baseline_spec = _form_page_spec_from_contract(
            sample_openapi_spec, with_labels=False
        )
        baseline_report = run_accessibility_scan(baseline_spec)

        spec_data = yaml.safe_load(sample_openapi_spec.read_text())
        spec_data["components"]["schemas"]["UserCreate"]["properties"]["nickname"] = {
            "type": "string"
        }
        drifted_path = temp_workspace / "source" / "openapi_drifted.yaml"
        drifted_path.write_text(yaml.safe_dump(spec_data))

        validation = SpecValidatorService().validate(drifted_path)
        assert validation.is_valid

        drifted_report = run_accessibility_scan(
            _form_page_spec_from_contract(drifted_path, with_labels=False)
        )

        baseline_labels = [
            v for v in baseline_report.violations if v.wcag_reference == "3.3.2"
        ]
        drifted_labels = [
            v for v in drifted_report.violations if v.wcag_reference == "3.3.2"
        ]
        assert len(drifted_labels) == len(baseline_labels) + 1
        assert any("nickname" in v.element_selector for v in drifted_labels)
