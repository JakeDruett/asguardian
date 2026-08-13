"""
L5 Compliance Tests — Volundr IaC Misconfiguration Ground Truths.

Known-bad Dockerfiles, Kubernetes manifests, Terraform and CI/CD workflow
fixtures MUST be flagged by the corresponding validator; hardened
equivalents MUST be clean of those findings. References: CIS Docker 4.1,
CIS Kubernetes 5.2.1, CIS AWS Foundations, CWE-250/284/311/94.
Fixtures are scanned from neutral temp dirs — never pytest tmp_path.
"""

import yaml

from Asgard.Volundr.CICD.services.context_hardening import (
    find_untrusted_interpolations,
)
from Asgard.Volundr.Validation.models.validation_models import ValidationSeverity
from Asgard.Volundr.Validation.services.dockerfile_validator import (
    DockerfileValidator,
)
from Asgard.Volundr.Validation.services.kubernetes_validator import (
    KubernetesValidator,
)
from Asgard.Volundr.Validation.services.terraform_validator import TerraformValidator

from Asgard_Test.L5_Meta.l5_fixtures import fixture_path, neutral_copy


def _rule_ids(report) -> set:
    return {r.rule_id for r in report.results}


class TestDockerfileCISCompliance:
    """CIS Docker 4.1 / CWE-250: root user and unpinned base image."""

    def test_root_user_and_latest_tag_flagged(self) -> None:
        path = neutral_copy(
            "CWE-250_unnecessary_privileges/Dockerfile.root_user",
            target_name="Dockerfile",
        )
        report = DockerfileValidator().validate_file(str(path))
        rule_ids = _rule_ids(report)
        assert "DL3002" in rule_ids, f"Root USER not flagged; got {sorted(rule_ids)}"
        assert "DL3007" in rule_ids, f"latest tag not flagged; got {sorted(rule_ids)}"

    def test_hardened_dockerfile_clean_of_those_rules(self) -> None:
        good = (
            "FROM python:3.12-slim\n"
            "WORKDIR /app\n"
            "COPY requirements.txt /app/\n"
            "RUN useradd --no-log-init -r appuser\n"
            "COPY . /app\n"
            "USER appuser\n"
            'CMD ["python", "-m", "app"]\n'
        )
        report = DockerfileValidator().validate_content(good)
        rule_ids = _rule_ids(report)
        assert "DL3002" not in rule_ids
        assert "DL3007" not in rule_ids


class TestKubernetesCISCompliance:
    """CIS Kubernetes 5.2.1 / CWE-250: privileged containers."""

    def test_privileged_pod_flagged_as_error(self) -> None:
        path = neutral_copy(
            "CWE-250_unnecessary_privileges/k8s_privileged_deployment.yaml"
        )
        report = KubernetesValidator().validate_file(str(path))
        privileged = [
            r for r in report.results if r.rule_id == "privileged-container"
        ]
        assert privileged, (
            f"privileged: true not flagged; got {sorted(_rule_ids(report))}"
        )
        assert privileged[0].severity == ValidationSeverity.ERROR, (
            "Privileged container must be ERROR severity"
        )
        assert "privilege-escalation-allowed" in _rule_ids(report)

    def test_hardened_pod_clean_of_privilege_rules(self) -> None:
        hardened = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "app", "labels": {"app": "app"}},
            "spec": {
                "selector": {"matchLabels": {"app": "app"}},
                "template": {
                    "metadata": {"labels": {"app": "app"}},
                    "spec": {"containers": [{
                "name": "app",
                "image": "registry.example.com/app@sha256:" + "a" * 64,
                "resources": {
                    "limits": {"cpu": "100m", "memory": "128Mi"},
                    "requests": {"cpu": "100m", "memory": "128Mi"},
                },
                        "securityContext": {
                            "runAsNonRoot": True,
                            "allowPrivilegeEscalation": False,
                            "privileged": False,
                        },
                    }]},
                },
            },
        }
        report = KubernetesValidator().validate_content(yaml.safe_dump(hardened))
        rule_ids = _rule_ids(report)
        assert "privileged-container" not in rule_ids
        assert "privilege-escalation-allowed" not in rule_ids


class TestTerraformCISCompliance:
    """CIS AWS Foundations / CWE-284, CWE-311: open SG and unencrypted RDS."""

    def test_open_security_group_flagged(self) -> None:
        path = neutral_copy(
            "CWE-284_improper_access_control/terraform_open_security_group.tf",
            target_name="main.tf",
        )
        report = TerraformValidator().validate_file(str(path))
        rule_ids = _rule_ids(report)
        assert "VOL-TF-0005" in rule_ids, (
            f"0.0.0.0/0 ingress not flagged; got {sorted(rule_ids)}"
        )
        assert "VOL-TF-0006" in rule_ids, (
            f"all-ports SG not flagged; got {sorted(rule_ids)}"
        )

    def test_unencrypted_rds_flagged(self) -> None:
        path = neutral_copy(
            "CWE-311_missing_encryption/terraform_unencrypted_rds.tf",
            target_name="main.tf",
        )
        report = TerraformValidator().validate_file(str(path))
        assert "VOL-TF-0004" in _rule_ids(report), (
            f"Unencrypted RDS not flagged; got {sorted(_rule_ids(report))}"
        )

    def test_restricted_security_group_clean(self) -> None:
        good = (
            'resource "aws_security_group" "restricted" {\n'
            '  name = "restricted"\n'
            "  ingress {\n"
            "    from_port   = 443\n"
            "    to_port     = 443\n"
            '    protocol    = "tcp"\n'
            '    cidr_blocks = ["10.0.0.0/8"]\n'
            "  }\n"
            "}\n"
        )
        report = TerraformValidator().validate_content(good)
        rule_ids = _rule_ids(report)
        assert "VOL-TF-0005" not in rule_ids
        assert "VOL-TF-0006" not in rule_ids


class TestCICDWorkflowCompliance:
    """CWE-94: untrusted github context interpolated into a run script."""

    def test_script_injection_fixture_flagged(self) -> None:
        workflow = yaml.safe_load(
            fixture_path(
                "CWE-94_code_injection/github_workflow_script_injection.yml"
            ).read_text(encoding="utf-8")
        )
        script = workflow["jobs"]["build"]["steps"][0]["run"]
        found = find_untrusted_interpolations(script)
        assert found, "Interpolation in run script must be detected"
        assert any(untrusted for _, untrusted in found), (
            f"github.event.* interpolation must be marked untrusted: {found}"
        )

    def test_trusted_context_not_marked_untrusted(self) -> None:
        found = find_untrusted_interpolations('echo "${{ runner.os }}"')
        assert found and all(not untrusted for _, untrusted in found)

    def test_plain_script_has_no_interpolations(self) -> None:
        assert find_untrusted_interpolations('echo "hello"') == []
