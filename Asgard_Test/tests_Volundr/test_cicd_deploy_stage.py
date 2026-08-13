"""
Regression tests: a stage literally named "deploy" is never silently
dropped by PipelineGenerator (MasterPlan Phase 1.3, discovered Wave 4).

With split_trust=True (the default) a deploy-trusted stage is emitted in
the secondary workflow_run-triggered workflow, so it is absent from
``pipeline_content`` (the primary). That relocation must be preserved in
``files`` AND reported explicitly in ``validation_results`` — never
silent. Built-in job ids (provenance / lint-workflows) must likewise
never clobber user stages.
"""

import pytest

from Asgard.Volundr.CICD.models.cicd_models import (
    CICDPlatform,
    PipelineConfig,
    PipelineStage,
    StepConfig,
    TriggerConfig,
    TriggerType,
)
from Asgard.Volundr.CICD.services.pipeline_generator import PipelineGenerator


DEPLOY_SENTINEL = "make deploy-sentinel"


def _config(platform=CICDPlatform.GITHUB_ACTIONS, **overrides) -> PipelineConfig:
    defaults = dict(
        name="myapp",
        platform=platform,
        triggers=[TriggerConfig(type=TriggerType.PUSH, branches=["main"])],
        stages=[
            PipelineStage(
                name="build",
                steps=[StepConfig(name="build it", run="make build")],
            ),
            PipelineStage(
                name="deploy",
                needs=["build"],
                steps=[StepConfig(name="deploy it", run=DEPLOY_SENTINEL)],
            ),
        ],
    )
    defaults.update(overrides)
    return PipelineConfig(**defaults)


@pytest.fixture
def generator():
    return PipelineGenerator()


class TestDeployStageNeverSilentlyDropped:
    def test_deploy_stage_preserved_across_emitted_files(self, generator):
        """Split-trust default: the deploy stage lives in SOME emitted file."""
        result = generator.generate(_config())
        combined = "".join(result.files.values())
        assert DEPLOY_SENTINEL in combined
        assert "deploy:" in combined

    def test_split_relocation_is_explicitly_reported(self, generator):
        """Absence from the primary workflow carries an explicit receipt."""
        result = generator.generate(_config())
        # The stage is genuinely absent from the primary (split trust)...
        assert DEPLOY_SENTINEL not in result.pipeline_content
        # ...and that is reported, never silent.
        notices = [
            v for v in result.validation_results
            if "VOL-CICD-SPLIT-INFO" in v and "'deploy'" in v
        ]
        assert notices, result.validation_results
        # The receipt names the actual secondary file that was emitted.
        assert ".github/workflows/myapp-deploy.yml" in notices[0]
        assert ".github/workflows/myapp-deploy.yml" in result.files

    def test_no_split_keeps_deploy_in_primary_without_notice(self, generator):
        result = generator.generate(_config(split_trust=False))
        assert DEPLOY_SENTINEL in result.pipeline_content
        assert not any(
            "VOL-CICD-SPLIT-INFO" in v for v in result.validation_results
        )

    def test_deploy_only_pipeline_not_split_and_preserved(self, generator):
        config = _config()
        config = PipelineConfig(**{
            **config.model_dump(),
            "stages": [config.stages[1].model_dump()],
        })
        result = generator.generate(config)
        assert DEPLOY_SENTINEL in result.pipeline_content
        assert len(result.files) == 1

    @pytest.mark.parametrize("platform", [
        CICDPlatform.GITLAB_CI,
        CICDPlatform.AZURE_DEVOPS,
        CICDPlatform.JENKINS,
        CICDPlatform.CIRCLECI,
    ])
    def test_deploy_stage_preserved_on_all_platforms(self, generator, platform):
        result = generator.generate(_config(platform=platform))
        assert DEPLOY_SENTINEL in result.pipeline_content

    def test_save_to_file_writes_deploy_workflow(self, generator, tmp_path):
        result = generator.generate(_config())
        generator.save_to_file(result, str(tmp_path))
        deploy_file = tmp_path / ".github" / "workflows" / "myapp-deploy.yml"
        assert deploy_file.exists()
        assert DEPLOY_SENTINEL in deploy_file.read_text(encoding="utf-8")

    def test_determinism(self, generator):
        a = generator.generate(_config())
        b = generator.generate(_config())
        assert a.files == b.files
        assert a.validation_results == b.validation_results


class TestBuiltInJobIdsNeverClobberUserStages:
    def test_user_stage_named_provenance_survives(self, generator):
        config = _config(
            provenance=True,
            split_trust=False,
            stages=[
                PipelineStage(
                    name="provenance",
                    steps=[StepConfig(name="mine", run="make my-provenance")],
                ),
            ],
        )
        result = generator.generate(config)
        combined = "".join(result.files.values())
        assert "make my-provenance" in combined
        assert "volundr-provenance" in combined

    def test_user_stage_named_lint_workflows_survives(self, generator):
        config = _config(
            self_audit=True,
            split_trust=False,
            stages=[
                PipelineStage(
                    name="lint-workflows",
                    steps=[StepConfig(name="mine", run="make my-lint")],
                ),
            ],
        )
        result = generator.generate(config)
        combined = "".join(result.files.values())
        assert "make my-lint" in combined
        assert "volundr-lint-workflows" in combined


class TestCLIListsAllEmittedFiles:
    def test_cicd_generate_prints_secondary_deploy_file(self, tmp_path, capsys, monkeypatch):
        """The CLI never hides the secondary deploy workflow file."""
        import argparse
        from Asgard.Volundr.cli.handlers_gitops import run_cicd_generate

        # The stock CLI stage set has no deploy stage; patch one in so the
        # split path is exercised end-to-end through the handler.
        from Asgard.Volundr.CICD.services import pipeline_generator as pg
        orig_generate = pg.PipelineGenerator.generate

        def generate_with_deploy(self, config):
            config.stages.append(PipelineStage(
                name="deploy",
                needs=["build"],
                steps=[StepConfig(name="deploy it", run=DEPLOY_SENTINEL)],
            ))
            return orig_generate(self, config)

        monkeypatch.setattr(pg.PipelineGenerator, "generate", generate_with_deploy)

        args = argparse.Namespace(
            name="myapp", platform="github_actions", branch="main",
            docker_image=None, output_dir=str(tmp_path), dry_run=False,
        )
        assert run_cicd_generate(args) == 0
        out = capsys.readouterr().out
        assert ".github/workflows/myapp-deploy.yml" in out
        assert "VOL-CICD-SPLIT-INFO" in out
