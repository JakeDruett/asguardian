"""
Forseti-Volundr Integration Tests

Tests for cross-package integration between Forseti (API contract validation)
and Volundr (CI/CD pipeline generation). Contract validation acts as a
deployment gate: a valid OpenAPI spec unlocks a deploy stage in the generated
pipeline; a broken spec blocks it.
"""

from pathlib import Path

import pytest

from Asgard.Forseti.OpenAPI import SpecValidatorService
from Asgard.Volundr import (
    CICDPlatform,
    PipelineConfig,
    PipelineGenerator,
    PipelineStage,
    StepConfig,
    TriggerConfig,
)


def _build_pipeline_config(include_release: bool) -> PipelineConfig:
    stages = [
        PipelineStage(
            name="contract-check",
            steps=[StepConfig(name="validate-openapi", run="forseti openapi validate api.yaml")],
        )
    ]
    if include_release:
        stages.append(
            PipelineStage(
                name="release",
                needs=["contract-check"],
                steps=[StepConfig(name="release", run="kubectl apply -f k8s/")],
            )
        )
    return PipelineConfig(
        name="api-service",
        platform=CICDPlatform.GITHUB_ACTIONS,
        triggers=[TriggerConfig(type="push", branches=["main"])],
        stages=stages,
    )


@pytest.mark.cross_package
class TestContractValidationGatesPipeline:
    def test_valid_spec_unlocks_deploy_stage(
        self, sample_openapi_spec: Path, output_dir: Path
    ):
        result = SpecValidatorService().validate(sample_openapi_spec)
        assert result.is_valid, f"fixture spec should validate: {result.errors}"

        pipeline = PipelineGenerator(output_dir=str(output_dir)).generate(
            _build_pipeline_config(include_release=result.is_valid)
        )

        assert pipeline is not None
        assert "release" in pipeline.pipeline_content
        assert "contract-check" in pipeline.pipeline_content

    def test_broken_spec_blocks_deploy_stage(
        self, temp_workspace: Path, output_dir: Path
    ):
        broken = temp_workspace / "broken_spec.yaml"
        broken.write_text(
            "openapi: 3.0.0\n"
            "info:\n"
            "  title: Broken API\n"
            "# no version, no paths\n",
            encoding="utf-8",
        )

        result = SpecValidatorService().validate(broken)
        assert not result.is_valid, "spec missing version/paths must fail validation"
        assert result.errors, "invalid spec must carry explicit errors"

        pipeline = PipelineGenerator(output_dir=str(output_dir)).generate(
            _build_pipeline_config(include_release=result.is_valid)
        )

        # The gate held: pipeline exists but has no release stage.
        assert "contract-check" in pipeline.pipeline_content
        assert "release" not in pipeline.pipeline_content
        assert "kubectl apply" not in pipeline.pipeline_content

    def test_validation_errors_surface_in_gate_decision(
        self, temp_workspace: Path
    ):
        broken = temp_workspace / "broken_spec.yaml"
        broken.write_text("openapi: 3.0.0\n", encoding="utf-8")

        result = SpecValidatorService().validate(broken)
        assert not result.is_valid
        # Downstream gates need machine-usable reasons, not just a boolean.
        messages = [e.message for e in result.errors]
        assert all(isinstance(m, str) and m for m in messages)
