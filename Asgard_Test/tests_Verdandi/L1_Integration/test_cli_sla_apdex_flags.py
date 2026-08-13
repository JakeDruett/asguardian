"""
L1 Integration tests for the SLA threshold-fraction and Apdex
--errors/--endpoint CLI flags.
"""

import json

import pytest

from Asgard.Verdandi.cli._parser import create_parser
from Asgard.Verdandi.cli.handlers_analysis import run_apdex, run_sla_check


class TestSLAFractionCLI:
    def setup_method(self):
        self.parser = create_parser()

    def test_parse_target_fraction(self):
        args = self.parser.parse_args(
            ["analyze", "sla", "-d", "100,200", "-t", "500",
             "--target-fraction", "0.99"]
        )
        assert args.target_fraction == 0.99

    def test_fraction_mode_json_output(self, capsys):
        args = self.parser.parse_args(
            ["analyze", "sla", "-d", ",".join(["100"] * 20), "-t", "500",
             "--target-fraction", "0.9"]
        )
        exit_code = run_sla_check(args, "json")
        payload = json.loads(capsys.readouterr().out)
        assert payload["good_events"] == 20
        assert payload["target_fraction"] == 0.9
        assert exit_code == 0

    def test_fraction_mode_breach_exit_code(self, capsys):
        args = self.parser.parse_args(
            ["analyze", "sla", "-d", ",".join(["900"] * 20), "-t", "500",
             "--target-fraction", "0.9"]
        )
        assert run_sla_check(args, "json") == 1

    def test_percentile_mode_unchanged_without_flag(self, capsys):
        args = self.parser.parse_args(
            ["analyze", "sla", "-d", "100,120,130", "-t", "500"]
        )
        exit_code = run_sla_check(args, "json")
        payload = json.loads(capsys.readouterr().out)
        assert "percentile_value" in payload
        assert exit_code == 0


class TestApdexErrorFlagsCLI:
    def setup_method(self):
        self.parser = create_parser()

    def test_parse_errors_and_endpoint(self):
        args = self.parser.parse_args(
            ["analyze", "apdex", "-d", "50,60", "-t", "500",
             "--errors", "0,1", "--endpoint", "/checkout"]
        )
        assert args.errors == "0,1"
        assert args.endpoint == "/checkout"

    def test_errored_fast_request_is_frustrated(self, capsys):
        args = self.parser.parse_args(
            ["analyze", "apdex", "-d", "50,50,50,20", "-t", "500",
             "--errors", "0,0,0,1", "--endpoint", "/checkout"]
        )
        run_apdex(args, "json")
        payload = json.loads(capsys.readouterr().out)
        assert payload["frustrated_count"] == 1
        assert payload["score"] == 0.75
        assert payload["endpoint"] == "/checkout"

    def test_errors_length_mismatch_exits_2(self, capsys):
        args = self.parser.parse_args(
            ["analyze", "apdex", "-d", "50,50", "-t", "500",
             "--errors", "0,0,1"]
        )
        assert run_apdex(args, "json") == 2

    def test_apdex_without_new_flags_unchanged(self, capsys):
        args = self.parser.parse_args(
            ["analyze", "apdex", "-d", "50,50,50", "-t", "500"]
        )
        exit_code = run_apdex(args, "json")
        payload = json.loads(capsys.readouterr().out)
        assert payload["score"] == 1.0
        assert exit_code == 0
