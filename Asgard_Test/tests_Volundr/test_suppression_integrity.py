"""CH-0107: unsigned YAML suppressions cannot delete findings."""

from datetime import date

import pytest
import yaml

from Asgard.Volundr.Validation import (
    Suppression,
    SuppressionEngine,
    SuppressionSet,
    ValidationContext,
    ValidationEngine,
)
from Asgard.Volundr.Validation.models.suppression_models import (
    HMAC_ENV,
    sign_suppressions,
)
from Asgard.Volundr.Validation.models.validation_models import (
    ValidationCategory,
    ValidationResult,
    ValidationSeverity,
)

_EXPIRES = date(2099, 12, 31)

HARDENED = {
    "name": "app",
    "image": "registry.example.com/app@sha256:" + "a" * 64,
    "resources": {
        "limits": {"cpu": "100m", "memory": "128Mi"},
        "requests": {"cpu": "100m", "memory": "128Mi"},
    },
    "securityContext": {
        "runAsNonRoot": True,
        "allowPrivilegeEscalation": False,
        "readOnlyRootFilesystem": True,
        "privileged": True,
        "capabilities": {"drop": ["ALL"]},
        "seccompProfile": {"type": "RuntimeDefault"},
    },
}

PRIVILEGED_DEPLOYMENT = yaml.dump(
    {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "app", "labels": {"app": "app"}},
        "spec": {
            "selector": {"matchLabels": {"app": "app"}},
            "template": {
                "metadata": {"name": "app", "labels": {"app": "app"}},
                "spec": {
                    "automountServiceAccountToken": False,
                    "containers": [HARDENED],
                },
            },
        },
    }
)


def _critical(target="app"):
    return ValidationResult(
        rule_id="VOL-K8S-0009",
        message="privileged container",
        severity=ValidationSeverity.ERROR,
        category=ValidationCategory.SECURITY,
        resource_name=target,
        context={"target": target},
    )


def _exact(**kwargs):
    data = dict(
        rule="VOL-K8S-0009",
        target="app",
        reason="JIRA-1: reviewed exception",
        expires=_EXPIRES,
    )
    data.update(kwargs)
    return Suppression(**data)


def _clear_ci(monkeypatch):
    for name in (
        "CI",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "TF_BUILD",
        "CIRCLECI",
        "JENKINS_URL",
        "BUILDKITE",
        HMAC_ENV,
    ):
        monkeypatch.delenv(name, raising=False)


class TestYamlLoadPolicy:
    def test_star_target_is_rejected(self):
        with pytest.raises(ValueError, match="exact"):
            SuppressionSet.from_yaml(
                "suppressions:\n"
                "  - rule: VOL-K8S-0009\n"
                "    target: '*'\n"
                "    reason: hide critical\n"
                "    expires: 2099-12-31\n",
                require_signature=False,
            )

    def test_glob_target_is_rejected(self):
        with pytest.raises(ValueError, match="exact"):
            SuppressionSet.from_yaml(
                "suppressions:\n"
                "  - rule: VOL-K8S-0009\n"
                "    target: legacy-*\n"
                "    reason: hide critical\n"
                "    expires: 2099-12-31\n",
                require_signature=False,
            )

    def test_missing_expiry_is_rejected(self):
        with pytest.raises(ValueError, match="expires"):
            SuppressionSet.from_yaml(
                "suppressions:\n"
                "  - rule: VOL-K8S-0009\n"
                "    target: app\n"
                "    reason: hide critical\n",
                require_signature=False,
            )

    def test_exact_target_with_expiry_loads_locally(self, monkeypatch):
        _clear_ci(monkeypatch)
        ss = SuppressionSet.from_yaml(
            "suppressions:\n"
            "  - rule: VOL-K8S-0009\n"
            "    target: app\n"
            "    reason: 'JIRA-1: reviewed exception'\n"
            "    expires: 2099-12-31\n",
        )
        assert len(ss) == 1
        assert ss.suppressions[0].target == "app"


class TestCiFailClosed:
    def test_unsigned_file_refused_in_ci(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CI", "true")
        monkeypatch.delenv(HMAC_ENV, raising=False)
        path = tmp_path / "suppressions.yml"
        path.write_text(
            "suppressions:\n"
            "  - rule: VOL-K8S-0009\n"
            "    target: app\n"
            "    reason: 'JIRA-1: reviewed exception'\n"
            "    expires: 2099-12-31\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="unsigned"):
            SuppressionSet.from_file(str(path))

    def test_signed_file_loads_in_ci(self, tmp_path, monkeypatch):
        key = "test-suppression-hmac-key"
        monkeypatch.setenv("CI", "true")
        monkeypatch.setenv(HMAC_ENV, key)
        items = [_exact()]
        path = tmp_path / "suppressions.yml"
        path.write_text(
            yaml.safe_dump(
                {
                    "hmac": sign_suppressions(items, key),
                    "suppressions": [items[0].model_dump(mode="json")],
                }
            ),
            encoding="utf-8",
        )
        ss = SuppressionSet.from_file(str(path))
        assert len(ss) == 1

    def test_rewritten_hmac_refused_in_ci(self, tmp_path, monkeypatch):
        key = "test-suppression-hmac-key"
        monkeypatch.setenv("CI", "true")
        monkeypatch.setenv(HMAC_ENV, key)
        items = [_exact()]
        doc = {
            "hmac": sign_suppressions(items, key),
            "suppressions": [items[0].model_dump(mode="json")],
        }
        doc["suppressions"][0]["target"] = "other"
        path = tmp_path / "suppressions.yml"
        path.write_text(yaml.safe_dump(doc), encoding="utf-8")
        with pytest.raises(ValueError, match="unsigned or rewritten"):
            SuppressionSet.from_file(str(path))

    def test_ignore_rules_cannot_drop_critical_in_ci(self, monkeypatch):
        monkeypatch.setenv("CI", "true")
        engine = ValidationEngine(
            ValidationContext(ignore_rules=["VOL-K8S-0009"])
        )
        report = engine.validate_kubernetes(PRIVILEGED_DEPLOYMENT, "deploy.yaml")
        assert any(r.rule_id == "VOL-K8S-0009" for r in report.results)
        assert not report.passed


class TestStarCannotHideCritical:
    def test_yaml_star_never_reaches_engine(self):
        with pytest.raises(ValueError, match="exact"):
            SuppressionSet.from_yaml(
                "suppressions:\n"
                "  - rule: VOL-K8S-0009\n"
                "    target: '*'\n"
                "    reason: hide every privileged finding\n"
                "    expires: 2099-12-31\n",
                require_signature=False,
            )

    def test_programmatic_star_does_not_annihilate_critical(self):
        ss = SuppressionSet(
            suppressions=[
                Suppression(
                    rule="VOL-K8S-0009",
                    target="*",
                    reason="hide every privileged finding",
                    expires=_EXPIRES,
                )
            ]
        )
        outcome = SuppressionEngine(ss).apply([_critical("app")])
        assert any(r.rule_id == "VOL-K8S-0009" for r in outcome.results)
        assert any(
            r.rule_id == "VOL-SUPPRESS-WILDCARD-TARGET" for r in outcome.hygiene
        )

    def test_star_cannot_clean_privileged_report(self):
        ss = SuppressionSet(
            suppressions=[
                Suppression(
                    rule="VOL-K8S-0009",
                    target="*",
                    reason="hide every privileged finding",
                    expires=_EXPIRES,
                )
            ]
        )
        report = ValidationEngine(suppressions=ss).validate_kubernetes(
            PRIVILEGED_DEPLOYMENT, "deploy.yaml"
        )
        assert any(r.rule_id == "VOL-K8S-0009" for r in report.results)
        assert any(
            r.rule_id == "VOL-SUPPRESS-WILDCARD-TARGET" for r in report.results
        )
        assert not report.passed

    def test_exact_target_still_annihilates_critical(self):
        ss = SuppressionSet(suppressions=[_exact()])
        outcome = SuppressionEngine(ss).apply([_critical("app")])
        assert outcome.results == []
        assert len(outcome.applied) == 1
