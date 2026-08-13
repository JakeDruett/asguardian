"""
Deployment Gate Scenario (L2 Phase 3)

Models the real-world deploy gate: Verdandi SLO check + Heimdall security
gate + Volundr config lint must ALL pass; failing any single one blocks the
deployment.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

from Asgard.Heimdall.Security.services.secrets_detection_service import (
    SecretsDetectionService,
)
from Asgard.Verdandi.SLO import (
    ErrorBudgetCalculator,
    SLIMetric,
    SLOComplianceStatus,
    SLODefinition,
)
from Asgard.Volundr.Kubernetes import ManifestConfig, ManifestGenerator

LEAKY_CONFIG = 'AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPL2"\n'
CLEAN_CONFIG = 'import os\nKEY = os.environ["AWS_ACCESS_KEY_ID"]\n'


def _slo() -> SLODefinition:
    return SLODefinition(
        name="api-availability",
        slo_type="availability",
        target=99.9,
        window_days=30,
        service_name="api",
    )


def _sli(good: int, total: int) -> list:
    return [
        SLIMetric(
            timestamp=datetime.now() - timedelta(hours=1),
            service_name="api",
            slo_type="availability",
            good_events=good,
            total_events=total,
        )
    ]


def _slo_gate_passes(good: int, total: int) -> bool:
    budget = ErrorBudgetCalculator().calculate(_slo(), _sli(good, total))
    status = getattr(budget.status, "value", budget.status)
    return status == "compliant" or budget.status == SLOComplianceStatus.COMPLIANT


def _security_gate_passes(scan_dir: Path) -> bool:
    return SecretsDetectionService().scan(scan_dir).secrets_found == 0


def _config_lint_passes(output_dir: Path, replicas: int) -> bool:
    """Volundr config lint: manifest must generate and parse as valid YAML
    with a positive replica count."""
    try:
        config = ManifestConfig(
            name="api", image="registry.local/api:1.2.3", replicas=replicas
        )
    except Exception:
        return False
    manifest = ManifestGenerator(output_dir=str(output_dir)).generate(config)
    documents = [
        doc for doc in yaml.safe_load_all(manifest.yaml_content) if doc is not None
    ]
    if not documents:
        return False
    deployments = [d for d in documents if d.get("kind") == "Deployment"]
    return all(d["spec"]["replicas"] > 0 for d in deployments)


def _deploy_allowed(slo_ok: bool, security_ok: bool, lint_ok: bool) -> bool:
    return slo_ok and security_ok and lint_ok


@pytest.mark.cross_package
@pytest.mark.scenario
class TestDeploymentGateScenario:
    def test_all_gates_pass_allows_deploy(
        self, neutral_scan_dir: Path, output_dir: Path
    ):
        (neutral_scan_dir / "config.py").write_text(CLEAN_CONFIG, encoding="utf-8")

        slo_ok = _slo_gate_passes(good=100_000, total=100_000)
        security_ok = _security_gate_passes(neutral_scan_dir)
        lint_ok = _config_lint_passes(output_dir, replicas=3)

        assert slo_ok and security_ok and lint_ok
        assert _deploy_allowed(slo_ok, security_ok, lint_ok) is True

    def test_breached_slo_alone_blocks_deploy(
        self, neutral_scan_dir: Path, output_dir: Path
    ):
        (neutral_scan_dir / "config.py").write_text(CLEAN_CONFIG, encoding="utf-8")

        # 5% bad events against a 99.9% target: budget is destroyed.
        slo_ok = _slo_gate_passes(good=95_000, total=100_000)
        security_ok = _security_gate_passes(neutral_scan_dir)
        lint_ok = _config_lint_passes(output_dir, replicas=3)

        assert not slo_ok
        assert security_ok and lint_ok
        assert _deploy_allowed(slo_ok, security_ok, lint_ok) is False

    def test_security_findings_alone_block_deploy(
        self, neutral_scan_dir: Path, output_dir: Path
    ):
        (neutral_scan_dir / "config.py").write_text(LEAKY_CONFIG, encoding="utf-8")

        slo_ok = _slo_gate_passes(good=100_000, total=100_000)
        security_ok = _security_gate_passes(neutral_scan_dir)
        lint_ok = _config_lint_passes(output_dir, replicas=3)

        assert not security_ok, "leaky fixture must fail the security gate"
        assert slo_ok and lint_ok
        assert _deploy_allowed(slo_ok, security_ok, lint_ok) is False

    def test_config_lint_failure_alone_blocks_deploy(
        self, neutral_scan_dir: Path, output_dir: Path
    ):
        (neutral_scan_dir / "config.py").write_text(CLEAN_CONFIG, encoding="utf-8")

        slo_ok = _slo_gate_passes(good=100_000, total=100_000)
        security_ok = _security_gate_passes(neutral_scan_dir)
        # Zero replicas: an invalid rollout configuration.
        lint_ok = _config_lint_passes(output_dir, replicas=0)

        assert not lint_ok
        assert slo_ok and security_ok
        assert _deploy_allowed(slo_ok, security_ok, lint_ok) is False
