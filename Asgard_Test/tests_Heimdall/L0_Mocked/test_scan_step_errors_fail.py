"""CH-0090: scan step exceptions must fail the process, not PASS."""

from pathlib import Path

from Asgard.Heimdall.cli.handlers.scan_steps_1_6 import _run_type_check_step


def test_raising_type_check_step_exits_1(tmp_path, monkeypatch):
    class _Boom:
        def __init__(self, config):
            pass

        def analyze(self, path):
            raise RuntimeError("type checker crashed")

    monkeypatch.setattr(
        "Asgard.Heimdall.cli.handlers.scan_steps_1_6.TypeChecker",
        _Boom,
    )
    scan_results = {}
    step_reports = {}
    rc = _run_type_check_step(
        Path(tmp_path),
        [],
        False,
        False,
        scan_results,
        step_reports,
        0,
    )
    assert rc == 1
    assert scan_results["type_check"]["status"] == "ERROR"
