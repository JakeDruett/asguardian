"""
L8 budgeted benchmarks over the synthetic corpus and a bounded self-scan.

Corpus: Asgard_Test/_fixtures/l8_bench_corpus (small synthetic repo seeded
with scanner-relevant constructs). Self-scan: Asgard scanning a bounded
slice of its own source (Asgard/Heimdall/Security/services, ~5k LOC) — a
stable, real-code workload.

Budgets live in Asgard_Test/L8_budgets.yaml under `l8_corpus:` and
`self_scan:` and carry >= 5x headroom over observed timings (policy in
_Docs/Testing/L8_Perf_Budget_Policy.md).
"""

import shutil
import time
from pathlib import Path

import pytest

import Asgard
from Asgard.Heimdall.Security.services.injection_detection_service import (
    InjectionDetectionService,
)
from Asgard.Heimdall.Security.services.secrets_detection_service import (
    SecretsDetectionService,
)
from Asgard.Heimdall.Security.TaintAnalysis.services.taint_analyzer import TaintAnalyzer
from Asgard.Heimdall.Security.TaintAnalysis.models.taint_models import TaintConfig

CORPUS_DIR = Path(__file__).parent.parent / "_fixtures" / "l8_bench_corpus"
SELF_SCAN_SLICE = Path(Asgard.__file__).parent / "Heimdall" / "Security" / "services"


def _timed(fn):
    start = time.perf_counter()
    result = fn()
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return result, elapsed_ms


def _copy_tree(src: Path, dst: Path) -> Path:
    """Copy *src* into *dst*, skipping __pycache__.

    Heimdall's default exclude patterns skip anything whose path contains
    'Asgard_Test' or 'Asgard/Heimdall' (test fixtures and Heimdall's own
    detection patterns are intentionally not scanned in the default path).
    Benchmarks therefore scan a neutral temp copy of the workload.
    """
    shutil.copytree(
        src, dst, ignore=shutil.ignore_patterns("__pycache__"), dirs_exist_ok=True
    )
    return dst


@pytest.fixture(scope="session")
def corpus_scan_dir(tmp_path_factory):
    return _copy_tree(CORPUS_DIR, tmp_path_factory.mktemp("l8corpus") / "corpus")


@pytest.fixture(scope="session")
def self_scan_dir(tmp_path_factory):
    return _copy_tree(SELF_SCAN_SLICE, tmp_path_factory.mktemp("l8self") / "services")


class TestCorpusBenchmarks:
    def test_corpus_exists_and_is_nontrivial(self):
        py_files = list(CORPUS_DIR.rglob("*.py"))
        assert len(py_files) >= 4
        assert (CORPUS_DIR / "Dockerfile").is_file()

    def test_secrets_scan_corpus_within_budget(self, corpus_scan_dir, l8_budget):
        report, ms = _timed(lambda: SecretsDetectionService().scan(corpus_scan_dir))
        assert report.total_files_scanned >= 4
        assert ms <= l8_budget("l8_corpus.secrets_scan_ms")

    def test_injection_scan_corpus_within_budget(self, corpus_scan_dir, l8_budget):
        report, ms = _timed(lambda: InjectionDetectionService().scan(corpus_scan_dir))
        assert report.total_files_scanned >= 4
        assert ms <= l8_budget("l8_corpus.injection_scan_ms")

    def test_taint_scan_corpus_within_budget(self, corpus_scan_dir, l8_budget):
        analyzer = TaintAnalyzer(TaintConfig(scan_path=str(corpus_scan_dir)))
        report, ms = _timed(analyzer.scan)
        assert report.files_analyzed >= 4
        assert ms <= l8_budget("l8_corpus.taint_scan_ms")


class TestSelfScanBenchmarks:
    """Asgard scanning a bounded slice of its own source."""

    def test_self_scan_slice_is_bounded(self):
        py_files = list(SELF_SCAN_SLICE.rglob("*.py"))
        # Keep the workload real but bounded: neither empty nor unbounded.
        assert 5 <= len(py_files) <= 200

    def test_secrets_self_scan_within_budget(self, self_scan_dir, l8_budget):
        report, ms = _timed(lambda: SecretsDetectionService().scan(self_scan_dir))
        assert report.total_files_scanned >= 5
        assert ms <= l8_budget("self_scan.heimdall_security_services_secrets_ms")

    def test_injection_self_scan_within_budget(self, self_scan_dir, l8_budget):
        report, ms = _timed(lambda: InjectionDetectionService().scan(self_scan_dir))
        assert report.total_files_scanned >= 5
        assert ms <= l8_budget("self_scan.heimdall_security_services_injection_ms")
