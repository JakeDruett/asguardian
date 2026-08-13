"""
L8 Budgeted Performance Smoke Tests.

Unlike the per-module pytest-benchmark suites (which measure but do not
gate), these tests FAIL when a scanner exceeds its explicit latency budget
from ``Asgard_Test/L8_budgets.yaml``. Budgets are generous — they exist to
catch order-of-magnitude regressions, not micro-variance.
"""

import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path

import pytest

from Asgard.Heimdall.Security.services.injection_detection_service import (
    InjectionDetectionService,
)
from Asgard.Heimdall.Security.services.secrets_detection_service import (
    SecretsDetectionService,
)
from Asgard.Heimdall.Security.services.cryptographic_validation_service import (
    CryptographicValidationService,
)
from Asgard.Heimdall.Security.TaintAnalysis.services.taint_analyzer import TaintAnalyzer
from Asgard.Heimdall.Security.TaintAnalysis.models.taint_models import TaintConfig
from Asgard.Forseti.OpenAPI import SpecValidatorService
from Asgard.Verdandi.SLO import ErrorBudgetCalculator, SLIMetric, SLODefinition
from Asgard.Volundr import (
    CICDPlatform,
    DockerfileValidator,
    PipelineConfig,
    PipelineGenerator,
    PipelineStage,
    StepConfig,
    TriggerConfig,
)

# A ~500-line mixed Python payload with a scattering of scanner-relevant
# constructs so the scanners do real work rather than fast-path skipping.
_PY_PAYLOAD = (
    "import hashlib\nimport subprocess\n\n"
    "def handler(cursor, user_id):\n"
    "    value = 'SELECT * FROM t WHERE id = ' + str(user_id)\n"
    "    digest = hashlib.sha256(value.encode()).hexdigest()\n"
    "    return digest\n\n"
    + "\n".join(
        f"def util_{i}(a, b):\n    return a + b + {i}"
        for i in range(120)
    )
    + "\n"
)


def _timed(fn):
    start = time.perf_counter()
    result = fn()
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return result, elapsed_ms


@pytest.fixture
def scan_dir():
    d = Path(tempfile.mkdtemp(prefix="l8fixture_"))
    (d / "module.py").write_text(_PY_PAYLOAD, encoding="utf-8")
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


class TestHeimdallBudgets:
    def test_secrets_detection_within_budget(self, scan_dir, l8_budget):
        report, ms = _timed(lambda: SecretsDetectionService().scan(scan_dir))
        assert report.total_files_scanned >= 1
        assert ms <= l8_budget("heimdall.secrets_detection.single_file_ms")

    def test_injection_detection_within_budget(self, scan_dir, l8_budget):
        report, ms = _timed(lambda: InjectionDetectionService().scan(scan_dir))
        assert report.total_files_scanned >= 1
        assert ms <= l8_budget("heimdall.injection_detection.single_file_ms")

    def test_cryptographic_validation_within_budget(self, scan_dir, l8_budget):
        report, ms = _timed(lambda: CryptographicValidationService().scan(scan_dir))
        assert report.total_files_scanned >= 1
        assert ms <= l8_budget("heimdall.cryptographic_validation.single_file_ms")

    def test_taint_analyzer_within_budget(self, scan_dir, l8_budget):
        analyzer = TaintAnalyzer(TaintConfig(scan_path=str(scan_dir)))
        report, ms = _timed(analyzer.scan)
        assert report.files_analyzed >= 1
        assert ms <= l8_budget("heimdall.taint_analyzer.single_file_ms")


class TestForsetiBudgets:
    def test_openapi_validation_within_budget(self, tmp_path, l8_budget):
        spec = tmp_path / "api.yaml"
        paths = "\n".join(
            f"  /resource{i}:\n"
            f"    get:\n"
            f"      operationId: getResource{i}\n"
            f"      responses:\n"
            f"        '200':\n"
            f"          description: OK\n"
            for i in range(100)
        )
        spec.write_text(
            "openapi: 3.0.0\n"
            "info:\n  title: Bench API\n  version: 1.0.0\n"
            "paths:\n" + paths,
            encoding="utf-8",
        )
        result, ms = _timed(lambda: SpecValidatorService().validate(spec))
        assert result is not None
        assert ms <= l8_budget("forseti.openapi_validation_ms")


class TestVerdandiBudgets:
    def test_error_budget_calc_within_budget(self, l8_budget):
        slo = SLODefinition(
            name="bench", slo_type="availability", target=99.9,
            window_days=30, service_name="bench",
        )
        now = datetime.now()
        metrics = [
            SLIMetric(
                timestamp=now, service_name="bench", slo_type="availability",
                good_events=999, total_events=1000,
            )
            for _ in range(1000)
        ]
        budget, ms = _timed(lambda: ErrorBudgetCalculator().calculate(slo, metrics))
        assert budget.total_events == 1_000_000
        assert ms <= l8_budget("verdandi.error_budget_calc_1k_metrics_ms")


class TestVolundrBudgets:
    def test_dockerfile_lint_within_budget(self, l8_budget):
        content = (
            "FROM python:3.11-slim\n"
            "WORKDIR /app\n"
            + "RUN echo layer\n" * 50
            + "COPY . /app\n"
            "USER app\n"
            'CMD ["python", "-m", "app"]\n'
        )
        report, ms = _timed(lambda: DockerfileValidator().validate_content(content))
        assert report is not None
        assert ms <= l8_budget("volundr.dockerfile_lint_ms")

    def test_pipeline_generation_within_budget(self, tmp_path, l8_budget):
        config = PipelineConfig(
            name="bench",
            platform=CICDPlatform.GITHUB_ACTIONS,
            triggers=[TriggerConfig(type="push", branches=["main"])],
            stages=[
                PipelineStage(
                    name=f"stage-{i}",
                    steps=[StepConfig(name=f"step-{i}", run=f"echo {i}")],
                )
                for i in range(20)
            ],
        )
        gen = PipelineGenerator(output_dir=str(tmp_path))
        pipeline, ms = _timed(lambda: gen.generate(config))
        assert pipeline.pipeline_content
        assert ms <= l8_budget("volundr.pipeline_generation_ms")
