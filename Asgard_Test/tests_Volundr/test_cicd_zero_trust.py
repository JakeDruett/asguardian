"""
Zero-trust CI/CD generation tests (Volundr plan 04).

Structural invariants (DEEPTHINK_04):
- every emitted GitHub job has an explicit permissions block and timeout
- zero ``${{`` inside any rendered ``run:`` string (injection immunity)
- every well-known ``uses:`` is SHA-pinned with a version comment
- OIDC over static secrets; build/deploy trust split; SLSA provenance
- reified suppressions with comment receipts and warning annihilation
"""

import os
import re
import shutil
import subprocess

import pytest
import yaml

from Asgard.Volundr.CICD import (
    CICDPlatform,
    OIDCConfig,
    OIDCProvider,
    PipelineConfig,
    PipelineGenerator,
    PipelineStage,
    StepConfig,
    TriggerConfig,
    TriggerType,
)
from Asgard.Volundr.CICD.services.action_pins import (
    KNOWN_ACTION_PINS,
    KNOWN_IMAGE_PINS,
    is_digest_pinned,
    is_sha_pinned,
    pin_container_image,
    resolve_action_ref,
)
from Asgard.Volundr.CICD.services.context_hardening import (
    find_untrusted_interpolations,
    harden_step,
)
from Asgard.Volundr.CICD.services.pipeline_generator_helpers import (
    JENKINS_PROVENANCE_ERROR,
    generate_jenkins,
)
from Asgard.Volundr.Validation.models.suppression_models import Suppression
from Asgard.Volundr.Validation.services.validation_engine import ValidationEngine

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden")
SHA_RE = re.compile(r"@[0-9a-f]{40}$")


def _iter_jobs(content: str):
    for job_name, job in (yaml.safe_load(content).get("jobs") or {}).items():
        yield job_name, job


def _iter_steps(content: str):
    for _job_name, job in _iter_jobs(content):
        for step in job.get("steps") or []:
            yield step


@pytest.fixture
def generator():
    return PipelineGenerator()


@pytest.fixture
def full_config():
    """Representative config touching every zero-trust surface."""
    return PipelineConfig(
        name="CI",
        platform=CICDPlatform.GITHUB_ACTIONS,
        triggers=[
            TriggerConfig(type=TriggerType.PUSH, branches=["main"]),
            TriggerConfig(type=TriggerType.PULL_REQUEST, branches=["main"]),
        ],
        stages=[
            PipelineStage(
                name="Build",
                steps=[
                    StepConfig(name="Checkout", uses="actions/checkout@v4"),
                    StepConfig(
                        name="Setup Python",
                        uses="actions/setup-python@v5",
                        with_params={"python-version": "3.12"},
                    ),
                    StepConfig(name="Test", run="pytest"),
                    StepConfig(name="Upload", uses="actions/upload-artifact@v4"),
                ],
            ),
            PipelineStage(
                name="Deploy",
                needs=["Build"],
                environment="production",
                steps=[StepConfig(name="Deploy", run="make deploy")],
            ),
        ],
        oidc=OIDCConfig(
            provider=OIDCProvider.AWS,
            role="arn:aws:iam::123456789012:role/deploy",
            region="eu-west-1",
        ),
        provenance=True,
        sbom=True,
        harden_runner=True,
    )


class TestStructuralInvariants:
    """Every emitted GitHub workflow satisfies the zero-trust invariants."""

    def test_workflow_level_permissions_empty(self, generator, full_config):
        result = generator.generate(full_config)
        for content in result.files.values():
            assert yaml.safe_load(content)["permissions"] == {}

    def test_every_job_has_permissions_and_timeout(self, generator, full_config):
        result = generator.generate(full_config)
        for content in result.files.values():
            for job_name, job in _iter_jobs(content):
                assert "permissions" in job, f"job {job_name} lacks permissions"
                assert "timeout-minutes" in job, f"job {job_name} lacks timeout"

    def test_zero_interpolation_in_run(self, generator, full_config):
        """Structural injection-immunity invariant: no ${{ in any run:."""
        result = generator.generate(full_config)
        for content in result.files.values():
            for step in _iter_steps(content):
                if "run" in step:
                    assert "${{" not in step["run"]

    def test_all_uses_sha_pinned(self, generator, full_config):
        result = generator.generate(full_config)
        for content in result.files.values():
            for step in _iter_steps(content):
                if "uses" in step:
                    assert is_sha_pinned(step["uses"]), step["uses"]

    def test_pinned_uses_carry_version_comment(self, generator, full_config):
        result = generator.generate(full_config)
        content = result.pipeline_content
        for line in content.splitlines():
            if "uses: actions/checkout@" in line:
                assert "# v4.2.2" in line

    def test_default_concurrency_cancels_pr_builds(self, generator, full_config):
        result = generator.generate(full_config)
        concurrency = yaml.safe_load(result.pipeline_content)["concurrency"]
        assert concurrency["cancel-in-progress"] is True

    def test_rendered_workflow_scores_clean(self, generator, full_config):
        result = generator.generate(full_config)
        assert result.best_practice_score == 100.0


class TestActionPins:
    def test_known_tag_resolves_to_sha(self):
        ref, version = resolve_action_ref("actions/checkout@v4")
        assert SHA_RE.search(ref)
        assert version == "v4.2.2"

    def test_already_pinned_passes_through(self):
        sha_ref = "some/action@" + "a" * 40
        assert resolve_action_ref(sha_ref) == (sha_ref, None)

    def test_unknown_mutable_tag_passes_through(self):
        assert resolve_action_ref("wild/unknown@v1") == ("wild/unknown@v1", None)

    def test_local_action_passes_through(self):
        assert resolve_action_ref("./local/action") == ("./local/action", None)

    def test_all_pins_are_full_shas(self):
        for tag, (sha, version) in KNOWN_ACTION_PINS.items():
            assert re.fullmatch(r"[0-9a-f]{40}", sha), tag
            assert version.startswith("v"), tag

    def test_is_sha_pinned(self):
        assert is_sha_pinned("a/b@" + "0" * 40)
        assert not is_sha_pinned("a/b@v4")
        assert not is_sha_pinned("a/b")

    def test_pypi_publish_tag_resolves_to_sha(self):
        ref, version = resolve_action_ref("pypa/gh-action-pypi-publish@release/v1")
        assert SHA_RE.search(ref)
        assert version == "v1.14.2"

    def test_docker_actionlint_resolves_to_digest(self):
        ref, version = resolve_action_ref("docker://rhysd/actionlint:1.7.7")
        assert ref.startswith("docker://rhysd/actionlint:1.7.7@sha256:")
        assert is_digest_pinned(ref[len("docker://"):])
        assert version is None

    def test_unknown_docker_ref_is_refused(self):
        with pytest.raises(ValueError, match="digest"):
            resolve_action_ref("docker://example/unknown:1.0")

    def test_known_image_pins_are_digests(self):
        for tag, (canonical, digest) in KNOWN_IMAGE_PINS.items():
            assert digest.startswith("sha256:")
            assert is_digest_pinned(f"{canonical}@{digest}"), tag
            pinned = pin_container_image(tag)
            assert is_digest_pinned(pinned)
            assert "latest" not in pinned.split("@", 1)[0]


class TestRepoWorkflowPins:
    """Live repo workflows must use SHA-pinned actions (CH-0001)."""

    _REPO_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    _WORKFLOWS = (
        os.path.join(_REPO_ROOT, ".github", "workflows"),
        os.path.join(
            _REPO_ROOT,
            "_FutureItems-Security",
            "Tools_Security",
            ".github",
            "workflows",
        ),
    )
    _USES_RE = re.compile(r"(?:^|\s)uses:\s*(\S+)")

    def test_every_live_uses_is_sha_pinned(self):
        scanned = 0
        for folder in self._WORKFLOWS:
            if not os.path.isdir(folder):
                continue
            for name in os.listdir(folder):
                if not name.endswith((".yml", ".yaml")):
                    continue
                path = os.path.join(folder, name)
                text = open(path, encoding="utf-8").read()
                for line in text.splitlines():
                    if line.lstrip().startswith("#"):
                        # A commented-out `uses:` is documentation, not a step
                        # this workflow runs. This assertion is about live
                        # references, as its name says.
                        continue
                    match = self._USES_RE.search(line)
                    if not match:
                        continue
                    uses = match.group(1)
                    scanned += 1
                    assert is_sha_pinned(uses), f"{path}: unpinned {uses}"

        assert scanned >= 10

    def test_pin_updaters_exist(self):
        assert os.path.isfile(os.path.join(self._REPO_ROOT, "renovate.json"))
        assert os.path.isfile(
            os.path.join(self._REPO_ROOT, ".github", "dependabot.yml")
        )

    def test_ci_pull_request_not_on_shared_arc(self):
        path = os.path.join(self._REPO_ROOT, ".github", "workflows", "ci.yml")
        text = open(path, encoding="utf-8").read()
        data = yaml.safe_load(text)
        assert data["concurrency"]["cancel-in-progress"] is True
        for job_name, job in data["jobs"].items():
            runs_on = job["runs-on"]
            assert "ubuntu-latest" in str(runs_on), job_name
            assert "pull_request" in str(runs_on), job_name
            assert job.get("timeout-minutes") == 30, job_name
        assert "persist-credentials: false" in text
        assert "pip install -e" in text
        # Editable install of the PR tree must be gated off pull_request.
        for i, line in enumerate(text.splitlines()):
            if 'pip install -e' in line:
                window = "\n".join(text.splitlines()[max(0, i - 8) : i + 1])
                assert "pull_request" in window

    def test_publish_is_split_trust(self):
        path = os.path.join(self._REPO_ROOT, ".github", "workflows", "publish.yml")
        data = yaml.safe_load(open(path, encoding="utf-8"))
        assert data["permissions"] == {}
        on_block = data.get("on") or data.get(True)
        assert on_block["push"]["tags"] == ["v[0-9].*"]
        jobs = data["jobs"]
        assert "id-token" not in (jobs["build"].get("permissions") or {})
        assert jobs["build"]["runs-on"] == "ubuntu-latest"
        pub = jobs["publish"]
        assert pub["environment"] == "pypi"
        assert pub["permissions"]["id-token"] == "write"
        assert pub["runs-on"] == "ubuntu-latest"
        assert pub["needs"] == ["build", "provenance"]
        assert jobs["provenance"]["permissions"]["attestations"] == "write"
        uses = [
            step.get("uses", "")
            for job in jobs.values()
            for step in job.get("steps") or []
        ]
        assert any("attest-build-provenance" in u for u in uses)
        assert any("gh-action-pypi-publish" in u for u in uses)
        assert any("download-artifact" in u for u in uses)
        for job in jobs.values():
            assert job.get("timeout-minutes") == 15

    def test_l8_draft_has_least_privilege(self):
        path = os.path.join(
            self._REPO_ROOT, ".github", "workflows", "l8-perf-budgets.yml"
        )
        text = open(path, encoding="utf-8").read()
        data = yaml.safe_load(text)
        assert data.get("permissions") == {"contents": "read"} or data.get("permissions") == {}
        job = data["jobs"]["l8-budgets"]
        assert job["runs-on"] == "ubuntu-latest"
        assert job.get("timeout-minutes") == 20
        assert "persist-credentials: false" in text
        # Editable install of the PR tree must be gated off pull_request (CHC-0001).
        for i, line in enumerate(text.splitlines()):
            if "pip install -e" in line:
                window = "\n".join(text.splitlines()[max(0, i - 8) : i + 1])
                assert "pull_request" in window


class TestInjectionImmunity:
    def test_adversarial_issue_title_is_rewritten(self, generator):
        """User-supplied injection primitive is rewritten, not emitted verbatim."""
        config = PipelineConfig(
            name="Adversarial",
            platform=CICDPlatform.GITHUB_ACTIONS,
            triggers=[TriggerConfig(type=TriggerType.PULL_REQUEST, branches=["main"])],
            stages=[PipelineStage(name="Build", steps=[
                StepConfig(name="Echo", run="echo ${{ github.event.issue.title }}"),
            ])],
        )
        result = generator.generate(config)
        for step in _iter_steps(result.pipeline_content):
            if "run" in step:
                assert "${{" not in step["run"]
                assert '"$GITHUB_EVENT_ISSUE_TITLE"' in step["run"]
                assert step["env"]["GITHUB_EVENT_ISSUE_TITLE"] == (
                    "${{ github.event.issue.title }}"
                )

    def test_multiple_expressions_get_distinct_vars(self):
        step = StepConfig(
            name="s",
            run="echo ${{ github.head_ref }} ${{ github.event.pull_request.title }}",
        )
        hardened = harden_step(step)
        assert "${{" not in hardened.run
        assert len(hardened.env) == 2

    def test_existing_env_var_is_reused(self):
        step = StepConfig(
            name="s",
            run="echo ${{ github.head_ref }}",
            env={"BRANCH": "${{ github.head_ref }}"},
        )
        hardened = harden_step(step)
        assert hardened.run == 'echo "$BRANCH"'
        assert hardened.env == {"BRANCH": "${{ github.head_ref }}"}

    def test_untrusted_context_detection(self):
        found = find_untrusted_interpolations(
            "echo ${{ github.event.issue.title }} ${{ github.sha }}"
        )
        assert found == [
            ("github.event.issue.title", True),
            ("github.sha", False),
        ]

    def test_engine_flags_verbatim_injection_as_critical(self):
        """The validation engine catches injection in third-party workflows."""
        hostile = (
            "jobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    permissions: {contents: read}\n    timeout-minutes: 10\n"
            "    steps:\n"
            "    - name: bad\n"
            "      run: echo ${{ github.event.pull_request.title }}\n"
        )
        report = ValidationEngine().validate_pipeline(hostile)
        assert any(r.rule_id == "VOL-CICD-0004" for r in report.results)


class TestOIDCAndStaticSecrets:
    def test_oidc_step_and_id_token_permission(self, generator, full_config):
        result = generator.generate(full_config)
        deploy = [c for p, c in result.files.items() if p.endswith("-deploy.yml")][0]
        job = yaml.safe_load(deploy)["jobs"]["deploy"]
        assert job["permissions"]["id-token"] == "write"
        assert any(
            "configure-aws-credentials" in (s.get("uses") or "")
            for s in job["steps"]
        )

    @pytest.mark.parametrize("provider,marker", [
        (OIDCProvider.GCP, "google-github-actions/auth"),
        (OIDCProvider.AZURE, "azure/login"),
        (OIDCProvider.VAULT, "hashicorp/vault-action"),
    ])
    def test_other_oidc_providers(self, generator, provider, marker):
        config = PipelineConfig(
            name="CI", platform=CICDPlatform.GITHUB_ACTIONS,
            triggers=[TriggerConfig(type=TriggerType.PUSH, branches=["main"])],
            stages=[PipelineStage(name="Deploy", environment="prod",
                                  steps=[StepConfig(name="d", run="make deploy")])],
            oidc=OIDCConfig(provider=provider, role="some-role"),
            split_trust=False,
        )
        result = generator.generate(config)
        assert marker in result.pipeline_content

    def test_static_cloud_secret_yields_finding(self, generator):
        config = PipelineConfig(
            name="CI", platform=CICDPlatform.GITHUB_ACTIONS,
            triggers=[TriggerConfig(type=TriggerType.PUSH, branches=["main"])],
            stages=[PipelineStage(name="Build",
                                  steps=[StepConfig(name="b", run="make")])],
            secrets=["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
        )
        result = generator.generate(config)
        assert any("VOL-CICD-0005" in issue for issue in result.validation_results)

    def test_engine_flags_static_secret_env(self):
        content = (
            "jobs:\n  deploy:\n    runs-on: ubuntu-latest\n"
            "    permissions: {contents: read}\n    timeout-minutes: 10\n"
            "    steps:\n"
            "    - name: d\n      run: aws s3 sync . s3://bucket\n"
            "      env:\n"
            "        AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}\n"
        )
        report = ValidationEngine().validate_pipeline(content)
        assert any(r.rule_id == "VOL-CICD-0005" for r in report.results)


class TestSplitTrust:
    def test_build_workflow_has_no_secrets_or_oidc(self, generator, full_config):
        result = generator.generate(full_config)
        build = result.pipeline_content
        assert "secrets." not in build
        assert "configure-aws-credentials" not in build
        assert "id-token" not in yaml.safe_load(build)["jobs"]["build"]["permissions"]

    def test_deploy_workflow_triggers_on_workflow_run_only(self, generator, full_config):
        result = generator.generate(full_config)
        deploy = [c for p, c in result.files.items() if p.endswith("-deploy.yml")][0]
        on = yaml.safe_load(deploy)["on"]
        assert list(on.keys()) == ["workflow_run"]
        assert on["workflow_run"]["workflows"] == ["CI"]

    def test_no_split_when_disabled(self, generator, full_config):
        full_config.split_trust = False
        result = generator.generate(full_config)
        assert len(result.files) == 1
        assert "deploy:" in result.pipeline_content

    def test_no_split_without_deploy_stage(self, generator):
        config = PipelineConfig(
            name="CI", platform=CICDPlatform.GITHUB_ACTIONS,
            triggers=[TriggerConfig(type=TriggerType.PUSH, branches=["main"])],
            stages=[PipelineStage(name="Build",
                                  steps=[StepConfig(name="b", run="make")])],
        )
        result = generator.generate(config)
        assert len(result.files) == 1

    def test_save_to_file_writes_all_files(self, generator, full_config, tmp_path):
        result = generator.generate(full_config)
        generator.save_to_file(result, str(tmp_path))
        for rel_path in result.files:
            assert (tmp_path / rel_path).exists()


class TestProvenanceAndSBOM:
    def test_provenance_job_permissions(self, generator, full_config):
        result = generator.generate(full_config)
        job = yaml.safe_load(result.pipeline_content)["jobs"]["provenance"]
        assert job["permissions"] == {
            "id-token": "write", "attestations": "write", "contents": "read",
        }
        assert any(
            "attest-build-provenance" in (s.get("uses") or "") for s in job["steps"]
        )

    def test_sbom_step_in_build_job(self, generator, full_config):
        result = generator.generate(full_config)
        build = yaml.safe_load(result.pipeline_content)["jobs"]["build"]
        assert any("sbom-action" in (s.get("uses") or "") for s in build["steps"])

    def test_jenkins_provenance_refused_with_actionable_message(self):
        config = PipelineConfig(
            name="CI", platform=CICDPlatform.JENKINS,
            stages=[PipelineStage(name="Build",
                                  steps=[StepConfig(name="b", run="make")])],
            provenance=True,
        )
        with pytest.raises(ValueError, match="Tekton Chains"):
            generate_jenkins(config)
        with pytest.raises(ValueError, match="Tekton Chains"):
            PipelineGenerator().generate(config)
        assert "Tekton Chains" in JENKINS_PROVENANCE_ERROR

    def test_jenkins_refuses_triple_quote_breakout(self):
        config = PipelineConfig(
            name="CI",
            platform=CICDPlatform.JENKINS,
            stages=[PipelineStage(
                name="Build",
                steps=[StepConfig(name="x", run="'''; sh 'id")],
            )],
        )
        with pytest.raises(ValueError, match="'''"):
            generate_jenkins(config)

    def test_jenkins_refuses_hostile_env_key(self):
        config = PipelineConfig(
            name="CI",
            platform=CICDPlatform.JENKINS,
            env={"FOO\nsh 'id'": "bar"},
            stages=[PipelineStage(
                name="Build",
                steps=[StepConfig(name="x", run="make")],
            )],
        )
        with pytest.raises(ValueError, match="env key"):
            generate_jenkins(config)

    def test_jenkins_emits_quoted_sh_not_raw_triple_quotes(self):
        config = PipelineConfig(
            name="CI",
            platform=CICDPlatform.JENKINS,
            stages=[PipelineStage(
                name="Build",
                steps=[StepConfig(name="x", run="make test")],
            )],
        )
        rendered = generate_jenkins(config)
        assert "sh('make test')" in rendered
        assert "sh '''" not in rendered

    def test_gitlab_provenance_variable(self, generator):
        config = PipelineConfig(
            name="CI", platform=CICDPlatform.GITLAB_CI,
            stages=[PipelineStage(name="Build",
                                  steps=[StepConfig(name="b", run="make")])],
            provenance=True,
        )
        result = generator.generate(config)
        assert "RUNNER_GENERATE_ARTIFACTS_METADATA" in result.pipeline_content


class TestOtherPlatformHardening:
    def test_gitlab_jobs_have_timeout(self, generator):
        config = PipelineConfig(
            name="CI", platform=CICDPlatform.GITLAB_CI,
            stages=[PipelineStage(name="Build",
                                  steps=[StepConfig(name="b", run="make")])],
        )
        result = generator.generate(config)
        parsed = yaml.safe_load(result.pipeline_content)
        assert parsed["build"]["timeout"] == "30 minutes"
        assert "Zero-trust notes" in result.pipeline_content

    def test_azure_jobs_have_timeout(self, generator):
        config = PipelineConfig(
            name="CI", platform=CICDPlatform.AZURE_DEVOPS,
            triggers=[TriggerConfig(type=TriggerType.PUSH, branches=["main"])],
            stages=[PipelineStage(name="Build",
                                  steps=[StepConfig(name="b", run="make")])],
        )
        result = generator.generate(config)
        parsed = yaml.safe_load(result.pipeline_content)
        job = parsed["stages"][0]["jobs"][0]
        assert job["timeoutInMinutes"] == 30

    def test_jenkins_has_stage_timeouts(self, generator):
        config = PipelineConfig(
            name="CI", platform=CICDPlatform.JENKINS,
            stages=[PipelineStage(name="Build", timeout_minutes=17,
                                  steps=[StepConfig(name="b", run="make")])],
        )
        result = generator.generate(config)
        assert "timeout(time: 17, unit: 'MINUTES')" in result.pipeline_content

    def test_circleci_emitter_exists_and_is_valid_yaml(self, generator):
        config = PipelineConfig(
            name="CI", platform=CICDPlatform.CIRCLECI,
            stages=[
                PipelineStage(name="Build",
                              steps=[StepConfig(name="b", run="make")]),
                PipelineStage(name="Deploy", needs=["Build"], environment="prod",
                              steps=[StepConfig(name="d", run="make deploy")]),
            ],
        )
        result = generator.generate(config)
        parsed = yaml.safe_load(result.pipeline_content)
        assert parsed["version"] == 2.1
        assert "build" in parsed["jobs"]
        assert result.file_path == ".circleci/config.yml"
        # Deploy job restricted to protected branch + context.
        wf_jobs = parsed["workflows"]["ci"]["jobs"]
        deploy_entry = [j for j in wf_jobs if isinstance(j, dict) and "deploy" in j][0]
        assert deploy_entry["deploy"]["filters"]["branches"]["only"] == ["main"]


class TestNonGitHubHardeningAndScoring:
    """Plan 04 + 07: GitLab CI and Azure DevOps must not be second-class —
    injection-immunity and the shared Validation+Scoring engine apply to
    them exactly as they do to GitHub Actions, instead of emitting raw
    ``${{ }}`` interpolation and falling back to the legacy config-shape
    score."""

    def test_gitlab_script_is_hardened_no_raw_interpolation(self, generator):
        config = PipelineConfig(
            name="CI", platform=CICDPlatform.GITLAB_CI,
            stages=[PipelineStage(
                name="Build",
                steps=[StepConfig(
                    name="b",
                    run='echo "${{ github.event.pull_request.title }}"',
                )],
            )],
        )
        result = generator.generate(config)
        parsed = yaml.safe_load(result.pipeline_content)
        job = parsed["build"]
        # The script text itself must never carry a raw interpolation
        # primitive; the expression is hoisted into a job variable instead
        # (the variable's own value still carries the GHA-context
        # expression text as provenance — GitLab has no equivalent syntax
        # to resolve it into, so this is documentation, not a functional
        # substitution).
        assert not any("${{" in s for s in job.get("script", []))
        assert any("github.event.pull_request.title" in str(v)
                   for v in job.get("variables", {}).values())

    def test_azure_script_is_hardened_no_raw_interpolation(self, generator):
        config = PipelineConfig(
            name="CI", platform=CICDPlatform.AZURE_DEVOPS,
            triggers=[TriggerConfig(type=TriggerType.PUSH, branches=["main"])],
            stages=[PipelineStage(
                name="Build",
                steps=[StepConfig(
                    name="b",
                    run='echo "${{ github.event.issue.title }}"',
                )],
            )],
        )
        result = generator.generate(config)
        parsed = yaml.safe_load(result.pipeline_content)
        job = parsed["stages"][0]["jobs"][0]
        assert not any(
            "${{" in (s.get("script") or "") for s in job.get("steps", [])
        )
        assert any("github.event.issue.title" in str(v)
                   for v in job.get("variables", {}).values())

    def test_gitlab_routes_through_validation_and_scoring_engine(self, generator):
        config = PipelineConfig(
            name="CI", platform=CICDPlatform.GITLAB_CI,
            stages=[PipelineStage(name="Build",
                                  steps=[StepConfig(name="b", run="make")])],
        )
        result = generator.generate(config)
        assert result.score_report is not None
        assert result.best_practice_score == result.score_report.composite

    def test_azure_routes_through_validation_and_scoring_engine(self, generator):
        config = PipelineConfig(
            name="CI", platform=CICDPlatform.AZURE_DEVOPS,
            triggers=[TriggerConfig(type=TriggerType.PUSH, branches=["main"])],
            stages=[PipelineStage(name="Build",
                                  steps=[StepConfig(name="b", run="make")])],
        )
        result = generator.generate(config)
        assert result.score_report is not None
        assert result.best_practice_score == result.score_report.composite

    def test_gitlab_static_secret_flagged_by_shared_engine(self, generator):
        config = PipelineConfig(
            name="CI", platform=CICDPlatform.GITLAB_CI,
            stages=[PipelineStage(
                name="Deploy",
                environment="prod",
                steps=[StepConfig(
                    name="d",
                    run="deploy.sh",
                    env={"KEY": "${{ secrets.AWS_ACCESS_KEY_ID }}"},
                )],
            )],
        )
        result = generator.generate(config)
        assert any(
            "VOL-CICD-0005" in v for v in result.validation_results
        ), result.validation_results

    def test_jenkins_and_circleci_still_use_legacy_score(self, generator):
        # Jenkins (Groovy DSL) and CircleCI (schema not normalized) are
        # explicitly out of scope for this pass — they must keep working
        # via the legacy config-shape score rather than erroring.
        for platform in (CICDPlatform.JENKINS, CICDPlatform.CIRCLECI):
            config = PipelineConfig(
                name="CI", platform=platform,
                stages=[PipelineStage(name="Build",
                                      steps=[StepConfig(name="b", run="make")])],
            )
            result = generator.generate(config)
            assert result.score_report is None
            assert isinstance(result.best_practice_score, float)


class TestSuppressions:
    def _config_with_unknown_action(self, suppressions):
        return PipelineConfig(
            name="CI", platform=CICDPlatform.GITHUB_ACTIONS,
            triggers=[TriggerConfig(type=TriggerType.PUSH, branches=["main"])],
            stages=[PipelineStage(name="Build", steps=[
                StepConfig(name="Checkout", uses="actions/checkout@v4"),
                StepConfig(name="Custom", uses="acme/internal-action@v1"),
            ])],
            suppressions=suppressions,
        )

    def test_unknown_mutable_action_yields_pin_finding(self, generator):
        result = generator.generate(self._config_with_unknown_action([]))
        assert any("VOL-CICD-0002" in issue for issue in result.validation_results)
        assert result.best_practice_score < 100.0

    def test_suppression_annihilates_finding_and_leaves_receipt(self, generator):
        suppression = Suppression(
            rule="VOL-CICD-0002", target="build",
            reason="internal action, repo is access-controlled (TICKET-42)",
        )
        result = generator.generate(self._config_with_unknown_action([suppression]))
        assert not any(
            "VOL-CICD-0002" in issue for issue in result.validation_results
        )
        assert result.best_practice_score == 100.0
        assert (
            "# volundr:suppress=VOL-CICD-0002 internal action, repo is "
            "access-controlled (TICKET-42)"
        ) in result.pipeline_content

    def test_stale_suppression_yields_hygiene_warning(self, generator):
        suppression = Suppression(
            rule="VOL-CICD-0002", target="nonexistent-job", reason="stale",
        )
        result = generator.generate(self._config_with_unknown_action([suppression]))
        assert any("VOL-SUPPRESS-STALE" in issue for issue in result.validation_results)


class TestGoldenFiles:
    """Snapshot of the full rendered output; diffs reviewed like code.

    Regenerate deliberately with:
    UPDATE_GOLDEN=1 python3 -m pytest Asgard_Test/tests_Volundr/test_cicd_zero_trust.py -k golden
    """

    def test_github_zero_trust_golden(self, generator, full_config):
        result = generator.generate(full_config)
        for rel_path, content in result.files.items():
            golden_path = os.path.join(GOLDEN_DIR, os.path.basename(rel_path))
            if os.environ.get("UPDATE_GOLDEN"):
                os.makedirs(GOLDEN_DIR, exist_ok=True)
                with open(golden_path, "w", encoding="utf-8") as f:
                    f.write(content)
            assert os.path.exists(golden_path), (
                f"golden file missing: {golden_path} (run with UPDATE_GOLDEN=1)"
            )
            with open(golden_path, encoding="utf-8") as f:
                assert content == f.read(), f"golden drift in {rel_path}"


class TestExternalLint:
    """actionlint contract check on rendered output (skip-if-unavailable)."""

    def test_actionlint_clean_on_generated_workflows(self, generator, full_config, tmp_path):
        if shutil.which("actionlint") is None:
            pytest.skip("actionlint not installed")
        result = generator.generate(full_config)
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        for rel_path, content in result.files.items():
            (workflows / os.path.basename(rel_path)).write_text(content)
        proc = subprocess.run(
            ["actionlint"], cwd=tmp_path, capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr


class TestSelfAudit:
    """Plan 04 §8: optional zizmor/actionlint self-audit job."""

    def _config(self, self_audit=True, harden_runner=False):
        return PipelineConfig(
            name="CI",
            platform=CICDPlatform.GITHUB_ACTIONS,
            triggers=[TriggerConfig(type=TriggerType.PUSH, branches=["main"])],
            stages=[PipelineStage(
                name="Build",
                steps=[StepConfig(name="Test", run="pytest")],
            )],
            self_audit=self_audit,
            harden_runner=harden_runner,
        )

    def test_self_audit_job_emitted(self, generator):
        result = generator.generate(self._config())
        jobs = yaml.safe_load(result.pipeline_content)["jobs"]
        job = jobs["lint-workflows"]
        assert job["permissions"] == {"contents": "read"}
        assert "timeout-minutes" in job
        steps = job["steps"]
        assert any("zizmor==" in (s.get("run") or "") for s in steps)
        assert any("actionlint" in (s.get("uses") or "") for s in steps)
        actionlint = next(s for s in steps if "actionlint" in (s.get("uses") or ""))
        assert is_sha_pinned(actionlint["uses"])

    def test_self_audit_off_by_default(self, generator):
        result = generator.generate(self._config(self_audit=False))
        jobs = yaml.safe_load(result.pipeline_content)["jobs"]
        assert "lint-workflows" not in jobs

    def test_self_audit_no_untrusted_interpolation(self, generator):
        result = generator.generate(self._config())
        job = yaml.safe_load(result.pipeline_content)["jobs"]["lint-workflows"]
        for step in job["steps"]:
            if "run" in step:
                assert "${{" not in step["run"]

    def test_self_audit_checkout_sha_pinned_no_credentials(self, generator):
        result = generator.generate(self._config())
        job = yaml.safe_load(result.pipeline_content)["jobs"]["lint-workflows"]
        checkout = next(
            s for s in job["steps"]
            if "actions/checkout" in (s.get("uses") or "")
        )
        assert is_sha_pinned(checkout["uses"].split(" ")[0])
        assert checkout["with"]["persist-credentials"] is False

    def test_self_audit_harden_runner_first_step(self, generator):
        result = generator.generate(self._config(harden_runner=True))
        job = yaml.safe_load(result.pipeline_content)["jobs"]["lint-workflows"]
        assert "harden-runner" in (job["steps"][0].get("uses") or "")

    def test_self_audit_ignored_on_gitlab(self, generator):
        config = self._config()
        config.platform = CICDPlatform.GITLAB_CI
        result = generator.generate(config)
        assert "lint-workflows" not in result.pipeline_content
        assert "zizmor" not in result.pipeline_content


class TestFloatingTagsVaultAndPrivileged:
    """CH-0105: pin generator images, require https Vault, reject privileged."""

    def test_http_vault_url_is_rejected(self):
        with pytest.raises(ValueError, match="https"):
            OIDCConfig(
                provider=OIDCProvider.VAULT,
                role="ci",
                vault_url="http://vault",
            )

    def test_https_vault_url_is_emitted(self, generator):
        config = PipelineConfig(
            name="CI",
            platform=CICDPlatform.GITHUB_ACTIONS,
            triggers=[TriggerConfig(type=TriggerType.PUSH, branches=["main"])],
            stages=[PipelineStage(
                name="Deploy",
                environment="prod",
                steps=[StepConfig(name="d", run="make deploy")],
            )],
            oidc=OIDCConfig(
                provider=OIDCProvider.VAULT,
                role="ci",
                vault_url="https://vault.example.com",
            ),
            split_trust=False,
        )
        result = generator.generate(config)
        parsed = yaml.safe_load(result.pipeline_content)
        vault_step = next(
            s for s in parsed["jobs"]["deploy"]["steps"]
            if "vault-action" in (s.get("uses") or "")
        )
        assert vault_step["with"]["url"] == "https://vault.example.com"

    def test_privileged_service_is_rejected(self):
        with pytest.raises(ValueError, match="privileged"):
            PipelineStage(
                name="test",
                services={"db": {"image": "postgres:15", "privileged": True}},
            )

    def test_privileged_service_options_are_rejected(self):
        with pytest.raises(ValueError, match="privileged"):
            PipelineStage(
                name="test",
                services={"db": {"image": "postgres:15", "options": "--privileged"}},
            )

    def test_privileged_equals_true_option_is_rejected(self):
        with pytest.raises(ValueError, match="privileged"):
            PipelineStage(
                name="test",
                services={"db": {"image": "postgres:15", "options": "--privileged=true"}},
            )

    def test_floating_service_image_is_rejected(self):
        with pytest.raises(ValueError, match="floating"):
            PipelineStage(
                name="test",
                services={"db": {"image": "postgres:latest"}},
            )

    def test_versioned_service_image_is_kept(self):
        stage = PipelineStage(
            name="test",
            services={"postgres": {"image": "postgres:15", "env": {"POSTGRES_PASSWORD": "test"}}},
        )
        assert stage.services["postgres"]["image"] == "postgres:15"

    def test_gitlab_default_image_is_digest_pinned(self, generator):
        config = PipelineConfig(
            name="CI",
            platform=CICDPlatform.GITLAB_CI,
            stages=[PipelineStage(name="Build", steps=[StepConfig(name="b", run="make")])],
        )
        result = generator.generate(config)
        parsed = yaml.safe_load(result.pipeline_content)
        image = parsed["build"]["image"]
        assert is_digest_pinned(image)
        assert ":latest" not in image.split("@", 1)[0]

    def test_circleci_base_image_is_digest_pinned(self, generator):
        config = PipelineConfig(
            name="CI",
            platform=CICDPlatform.CIRCLECI,
            stages=[PipelineStage(name="Build", steps=[StepConfig(name="b", run="make")])],
        )
        result = generator.generate(config)
        parsed = yaml.safe_load(result.pipeline_content)
        image = parsed["jobs"]["build"]["docker"][0]["image"]
        assert is_digest_pinned(image)
        assert image.startswith("cimg/base:")
