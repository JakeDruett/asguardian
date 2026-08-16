"""CH-0089: --denied reaches LicenseConfig.prohibited_licenses."""

import argparse
from pathlib import Path

from Asgard.Heimdall.cli.common.scan_args import add_licenses_args
from Asgard.Heimdall.cli.handlers.syntax import run_licenses_analysis


def test_denied_flag_populates_prohibited_licenses(tmp_path, monkeypatch):
    (tmp_path / "requirements.txt").write_text("mitpkg==1.0\n")
    parser = argparse.ArgumentParser()
    add_licenses_args(parser)
    args = parser.parse_args([str(tmp_path), "--denied", "GPL-3.0"])
    assert args.denied == ["GPL-3.0"]

    captured = {}

    class _FakeChecker:
        def __init__(self, config):
            captured["config"] = config

        def analyze(self):
            class R:
                has_issues = False
            return R()

        def generate_report(self, result, fmt):
            return "ok"

    monkeypatch.setattr(
        "Asgard.Heimdall.cli.handlers.syntax.LicenseChecker",
        _FakeChecker,
    )
    rc = run_licenses_analysis(args)
    assert rc == 0
    assert "GPL-3.0" in captured["config"].prohibited_licenses


def test_unset_denied_keeps_default_prohibited_list(tmp_path, monkeypatch):
    parser = argparse.ArgumentParser()
    add_licenses_args(parser)
    args = parser.parse_args([str(tmp_path)])
    captured = {}

    class _FakeChecker:
        def __init__(self, config):
            captured["config"] = config

        def analyze(self):
            class R:
                has_issues = False
            return R()

        def generate_report(self, result, fmt):
            return "ok"

    monkeypatch.setattr(
        "Asgard.Heimdall.cli.handlers.syntax.LicenseChecker",
        _FakeChecker,
    )
    run_licenses_analysis(args)
    assert captured["config"].prohibited_licenses  # defaults kept
    assert "GPL-3.0" in captured["config"].prohibited_licenses
