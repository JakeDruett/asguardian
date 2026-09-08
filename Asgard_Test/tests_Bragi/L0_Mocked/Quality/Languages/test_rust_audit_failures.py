"""Cargo-audit protocol failures must remain distinct from completed clean scans."""

import json
from copy import deepcopy

import pytest

from Asgard.Bragi.Quality.languages.common.tool_runner import ToolRunResult
from Asgard.Bragi.Quality.languages.rust.models.rust_toolchain_models import RustAuditConfig
from Asgard.Bragi.Quality.languages.rust.services import rust_audit_analyzer
from Asgard.Bragi.Quality.languages.rust.services.rust_audit_analyzer import RustAuditAnalyzer

_CLEAN = {"vulnerabilities": {"found": False, "count": 0, "list": []}, "warnings": {}}
_VULNERABILITY = {
    "advisory": {
        "id": "RUSTSEC-2021-0001",
        "title": "Vulnerable dependency",
        "description": "A known vulnerability for this parser fixture.",
        "cvss": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "url": None,
    },
    "package": {"name": "example", "version": "0.1.0"},
}


def _report_with(*entries):
    return {"vulnerabilities": {"found": bool(entries), "count": len(entries), "list": list(entries)}}


@pytest.fixture
def scan(tmp_path, monkeypatch):
    (tmp_path / "Cargo.lock").write_text("# lock\n", encoding="utf-8")
    monkeypatch.setattr(rust_audit_analyzer, "find_optional_executable", lambda *args: "/available/cargo-audit")

    def run(payload, returncode=0, *, stderr="", timed_out=False, max_findings=1000, raw=False):
        stdout = payload if raw else json.dumps(payload)
        monkeypatch.setattr(
            rust_audit_analyzer, "run_tool",
            lambda *args, **kwargs: ToolRunResult(returncode, stdout, stderr, timed_out),
        )
        return RustAuditAnalyzer(RustAuditConfig(scan_path=tmp_path, max_findings=max_findings)).analyze()

    return run


def test_completed_clean_audit_passes(scan):
    report = scan(_CLEAN)
    assert not report.tool_failed
    assert not report.tools_unavailable
    assert report.files_analyzed == 1
    assert report.total_findings == 0


def test_vulnerability_exit_is_a_completed_scan_with_findings(scan):
    report = scan(_report_with(_VULNERABILITY), returncode=1)
    assert not report.tool_failed
    assert not report.tools_unavailable
    assert report.error_count == 1
    assert report.findings[0].rule_id == "RUSTSEC-2021-0001"


def test_success_exit_with_vulnerabilities_is_an_inconsistent_result(scan):
    report = scan(_report_with(_VULNERABILITY), returncode=0)
    assert report.tool_failed
    assert report.error_count == 1
    assert "exit 0" in report.tools_unavailable[0]


def test_negative_finding_limit_is_rejected():
    with pytest.raises(ValueError, match="max_findings"):
        RustAuditConfig(max_findings=-1)


def test_zero_finding_limit_preserves_all_findings(scan):
    report = scan(_report_with(_VULNERABILITY, _VULNERABILITY), returncode=1, max_findings=0)
    assert not report.tool_failed
    assert report.total_findings == 2


@pytest.mark.parametrize("returncode", [0, 1, 2])
@pytest.mark.parametrize("error", ["advisory database unavailable", {"message": "advisory database unavailable"}])
def test_parseable_error_object_is_never_clean(scan, returncode, error):
    report = scan({"error": error}, returncode=returncode)
    assert report.tool_failed
    assert report.total_findings == 0
    assert "advisory database unavailable" in report.tools_unavailable[0]
    assert f"exit {returncode}" in report.tools_unavailable[0]


@pytest.mark.parametrize("returncode", [2, -9])
@pytest.mark.parametrize("with_findings", [False, True])
def test_unexpected_exit_cannot_be_hidden_by_valid_json(scan, returncode, with_findings):
    payload = _report_with(_VULNERABILITY) if with_findings else _CLEAN
    report = scan(payload, returncode=returncode, stderr="audit interrupted")
    assert report.tool_failed
    assert report.total_findings == int(with_findings)
    assert "audit interrupted" in report.tools_unavailable[0]
    assert f"exit {returncode}" in report.tools_unavailable[0]


def test_denied_warnings_with_no_vulnerabilities_still_fail(scan):
    payload = deepcopy(_CLEAN)
    payload["warnings"] = {"unmaintained": [{"advisory": {"id": "RUSTSEC-2021-0001"}}]}
    report = scan(payload, returncode=1)
    assert report.tool_failed
    assert report.total_findings == 0
    assert "exit 1" in report.tools_unavailable[0]


@pytest.mark.parametrize(
    "payload",
    [
        None, [], "not a report", {}, {"vulnerabilities": None},
        {"vulnerabilities": {"list": []}},
        {"vulnerabilities": {"found": False, "count": 0, "list": None}},
        {"vulnerabilities": {"found": False, "count": 0, "list": {}}},
        {"vulnerabilities": {"found": 0, "count": 0, "list": []}},
        {"vulnerabilities": {"found": False, "count": False, "list": []}},
        {"vulnerabilities": {"found": False, "count": -1, "list": []}},
        {"vulnerabilities": {"found": True, "count": 0, "list": []}},
        {"vulnerabilities": {"found": True, "count": 1, "list": []}},
    ],
)
def test_malformed_or_inconsistent_report_is_not_a_clean_scan(scan, payload):
    report = scan(payload)
    assert report.tool_failed
    assert report.total_findings == 0
    assert report.tools_unavailable


@pytest.mark.parametrize(
    "entry",
    [
        None, {}, {"advisory": [], "package": {}},
        {"advisory": {"id": "RUSTSEC-2021-0001"}, "package": []},
        {"advisory": {"id": ""}, "package": {}},
        {"advisory": {"id": 123}, "package": {}},
        {"advisory": {"id": "RUSTSEC-2021-0001", "description": []}, "package": {}},
    ],
)
def test_invalid_tail_is_detected_even_after_finding_limit(scan, entry):
    report = scan(_report_with(_VULNERABILITY, entry), returncode=1, max_findings=1)
    assert report.tool_failed
    assert report.total_findings == 1
    assert report.findings[0].rule_id == "RUSTSEC-2021-0001"
    assert any("invalid vulnerability entry 2" in diagnostic for diagnostic in report.tools_unavailable)


@pytest.mark.parametrize(("stdout", "timed_out"), [("", False), ("{", False), ("", True)])
def test_empty_malformed_or_timed_out_output_is_failure(scan, stdout, timed_out):
    report = scan(stdout, returncode=2, timed_out=timed_out, raw=True)
    assert report.tool_failed
    assert report.total_findings == 0
    assert report.tools_unavailable


@pytest.mark.parametrize("failure_first", [True, False])
def test_failure_remains_visible_across_lockfiles(tmp_path, monkeypatch, failure_first):
    directories = [tmp_path / "a", tmp_path / "b"]
    monkeypatch.setattr(rust_audit_analyzer, "find_optional_executable", lambda *args: "/available/cargo-audit")
    monkeypatch.setattr(rust_audit_analyzer, "find_manifest_dirs", lambda *args: directories)
    results = [
        ToolRunResult(2, '{"error":"database unavailable"}', ""),
        ToolRunResult(1, json.dumps(_report_with(_VULNERABILITY)), ""),
    ]
    if not failure_first:
        results.reverse()
    iterator = iter(results)
    monkeypatch.setattr(rust_audit_analyzer, "run_tool", lambda *args, **kwargs: next(iterator))
    report = RustAuditAnalyzer(RustAuditConfig(scan_path=tmp_path)).analyze()
    assert report.tool_failed
    assert report.total_findings == 1
    assert report.files_analyzed == 2
    assert "database unavailable" in report.tools_unavailable[0]
