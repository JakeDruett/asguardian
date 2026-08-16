"""CH-0114: SecurityAPI loader skips imported *Detector names; scan_all fail-closes."""

import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[2] / "_FutureItems-Security" / "Tools_Security"
_MOD = SourceFileLoader("security_api", str(_TOOLS / "security_api.py")).load_module()
_TK = SourceFileLoader("security_toolkit", str(_TOOLS / "security_toolkit.py")).load_module()

_IMPORTED_DETECTOR = '''
constructed = []

def AlphaDetector():
    constructed.append("func")
    raise AssertionError("imported Detector function must not be called")


class BetaDetector:
    def __init__(self):
        constructed.append("class")
        raise AssertionError("imported Detector class must not be constructed")
'''

_LOCAL_SCANNER = '''
from alpha_detector_import import AlphaDetector, BetaDetector


class LocalScanner:
    def scan_file(self, path):
        return []

    def scan_directory(self, path):
        return []
'''

_BOOM_SCANNER = '''
class BoomScanner:
    def scan_file(self, path):
        raise RuntimeError("scanner crashed")

    def scan_directory(self, path):
        raise RuntimeError("scanner crashed")
'''


def _api_for(tmp_path, tools):
    api = _MOD.SecurityAPI()
    api.tools_dir = tmp_path
    api.TOOLS = dict(tools)
    return api


def test_imported_detector_names_are_not_constructed(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(tmp_path)
    (tmp_path / "alpha_detector_import.py").write_text(_IMPORTED_DETECTOR)
    (tmp_path / "local_ok_scanner.py").write_text(_LOCAL_SCANNER)

    api = _api_for(tmp_path, {"ok": "local_ok_scanner"})
    scanner = api._load_scanner("local_ok_scanner")

    assert type(scanner).__name__ == "LocalScanner"
    import alpha_detector_import as imported

    assert imported.constructed == []


def test_raising_scanner_sets_total_issues_minus_one(tmp_path):
    (tmp_path / "boom_scanner.py").write_text(_BOOM_SCANNER)
    api = _api_for(tmp_path, {"boom": "boom_scanner"})
    target = tmp_path / "target.py"
    target.write_text("x = 1\n")

    results = api.scan_all(str(target), tools=["boom"])
    report = results["boom"]
    assert report.total_issues == -1
    assert report.issues[0]["exception_type"] == "RuntimeError"
    assert "crashed" in report.issues[0]["error"]


def test_scan_all_cli_exits_nonzero_on_scanner_error(tmp_path, monkeypatch, capsys):
    err = _MOD.ScanReport(
        tool="boom",
        target=str(tmp_path),
        timestamp="t",
        duration_ms=0,
        total_issues=-1,
        by_severity={"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
        issues=[{"error": "scanner crashed", "exception_type": "RuntimeError"}],
    )
    monkeypatch.setattr(
        _MOD.SecurityAPI, "scan_all", lambda self, target, tools=None: {"boom": err}
    )
    monkeypatch.setattr(sys, "argv", ["security_api.py", "all", str(tmp_path)])
    monkeypatch.chdir(tmp_path)

    assert _MOD.main() == 1
    captured = capsys.readouterr()
    assert "scanners failed" in captured.err


def test_first_party_scanners_still_load():
    api = _MOD.SecurityAPI()
    sqli = api._load_scanner("sql_injection_scanner")
    crypto = api._load_scanner("encryption_analyzer")
    git = api._load_scanner("git_security_scanner")
    assert type(sqli).__name__ == "SQLInjectionScanner"
    assert type(crypto).__name__ == "EncryptionAnalyzer"
    assert type(git).__name__ == "GitSecurityScanner"
    assert isinstance(sqli, _MOD.BaseScanner)
    assert isinstance(crypto, _MOD.BaseScanner)
    assert isinstance(git, _MOD.BaseScanner)


def test_toolkit_audit_counts_error_as_failure(tmp_path, monkeypatch):
    toolkit = _TK.SecurityToolkit()

    def _boom(_tool_id, _args):
        raise RuntimeError("tool crashed")

    monkeypatch.setattr(toolkit, "run_tool", _boom)
    assert toolkit.run_audit(str(tmp_path)) == 1
