"""CHC-0009: empty CST pass is incomplete, not a clean 100."""

from types import SimpleNamespace

from Asgard.Heimdall.cli.handlers._security_dispatch import (
    DispatchScanOutcome,
    mark_incomplete_security_report,
)
from Asgard.Heimdall.Security.engine import DispatchEngine


def test_missing_cst_engine_is_truncated(tmp_path, monkeypatch):
    src = tmp_path / "app.js"
    src.write_text("const x = 1;\n")
    monkeypatch.setattr(
        "Asgard.Heimdall.Security.engine.dispatch.is_engine_enabled",
        lambda lang: False,
    )
    result = DispatchEngine().scan_file(src)
    assert result.taint_flows == []
    assert result.analysis_truncated is True
    assert result.parse_failed is False


def test_cst_parse_failure_is_parse_failed(tmp_path, monkeypatch):
    src = tmp_path / "app.js"
    src.write_text("const x = 1;\n")
    monkeypatch.setattr(
        "Asgard.Heimdall.Security.engine.dispatch.is_engine_enabled",
        lambda lang: True,
    )
    monkeypatch.setattr(
        "Asgard.Heimdall.Security.engine.dispatch.FileParseContext.parse",
        classmethod(lambda cls, *a, **k: SimpleNamespace(root=None)),
    )
    result = DispatchEngine().scan_file(src)
    assert result.parse_failed is True
    assert result.analysis_truncated is False


def test_incomplete_cst_does_not_emit_score_100():
    report = SimpleNamespace(
        domain_errors=[],
        security_score=100.0,
        legacy_score=100.0,
        security_score_v2=100.0,
    )
    mark_incomplete_security_report(
        report,
        DispatchScanOutcome(incomplete=True, truncated_files=1),
    )
    assert report.domain_errors
    assert report.security_score == 0.0
    assert report.legacy_score == 0.0
