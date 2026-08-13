"""
CLI wiring tests for `verdandi cache slo` (segmented hit/miss SLIs,
plan 04 §B CLI parity) and the `network classify` alias for `signature`.
"""

import json

import pytest

from Asgard.Verdandi.cli import main as verdandi_main
from Asgard.Verdandi.cli._parser import create_parser


def _run(argv):
    with pytest.raises(SystemExit) as exc:
        verdandi_main(argv)
    return exc.value.code


# ---------------------------------------------------------------- parsing

def test_parser_accepts_cache_slo():
    args = create_parser().parse_args(["cache", "slo", "m.json"])
    assert args.cache_command == "slo"
    assert args.metrics_file == "m.json"


def test_parser_accepts_cache_slo_thresholds():
    args = create_parser().parse_args(
        ["cache", "slo", "m.json", "--hit-threshold", "15",
         "--miss-threshold", "500"]
    )
    assert args.hit_threshold == 15.0
    assert args.miss_threshold == 500.0


def test_parser_accepts_network_classify_alias():
    args = create_parser().parse_args(["network", "classify", "m.json"])
    assert args.network_command == "classify"


# ---------------------------------------------------------------- happy paths

def test_cache_slo_labeled(tmp_path, capsys):
    payload = {
        "hit_latencies_ms": [8, 10, 12, 25],
        "miss_latencies_ms": [700, 800, 1200],
    }
    f = tmp_path / "slo.json"
    f.write_text(json.dumps(payload))
    code = _run(["cache", "slo", str(f)])
    out = capsys.readouterr().out
    assert "SEGMENTED CACHE SLO" in out
    assert "Hit SLI:  0.7500" in out
    assert "Miss SLI: 0.6667" in out
    assert code == 0


def test_cache_slo_json_output(tmp_path, capsys):
    payload = {
        "hit_latencies_ms": [10.0] * 9 + [30.0],
        "miss_latencies_ms": [500.0] * 20,
    }
    f = tmp_path / "slo.json"
    f.write_text(json.dumps(payload))
    _run(["--format", "json", "cache", "slo", str(f)])
    data = json.loads(capsys.readouterr().out)
    assert data["hit_sli"] == 0.9
    assert data["miss_sli"] == 1.0
    assert data["labeled"] is True


def test_cache_slo_mode_shift_alert_exit_1(tmp_path, capsys):
    # Fast-path regression: hit median migrates 10 ms -> 200 ms while
    # everything stays under the miss threshold (the Apdex-masked case).
    payload = {
        "hit_latencies_ms": [195, 200, 205, 210],
        "miss_latencies_ms": [700, 800],
        "baseline_hit_median_ms": 10,
        "baseline_hit_mad_ms": 2,
    }
    f = tmp_path / "slo.json"
    f.write_text(json.dumps(payload))
    code = _run(["cache", "slo", str(f)])
    out = capsys.readouterr().out
    assert "Mode-shift alert: True" in out
    assert code == 1


def test_cache_slo_custom_thresholds(tmp_path, capsys):
    payload = {
        "hit_latencies_ms": [12, 14],
        "miss_latencies_ms": [600],
    }
    f = tmp_path / "slo.json"
    f.write_text(json.dumps(payload))
    _run(["--format", "json", "cache", "slo", str(f),
          "--hit-threshold", "10", "--miss-threshold", "500"])
    data = json.loads(capsys.readouterr().out)
    assert data["hit_sli"] == 0.0
    assert data["miss_sli"] == 0.0
    assert data["hit_threshold_ms"] == 10.0
    assert data["miss_threshold_ms"] == 500.0


def test_cache_slo_unlabeled(tmp_path, capsys):
    payload = {"latencies_ms": [10.0] * 40 + [800.0] * 20}
    f = tmp_path / "slo.json"
    f.write_text(json.dumps(payload))
    _run(["--format", "json", "cache", "slo", str(f)])
    data = json.loads(capsys.readouterr().out)
    # Honest labeling: unlabeled split must not claim labeled provenance.
    assert data["labeled"] is False


# ---------------------------------------------------------------- errors

def test_cache_slo_rejects_non_object(tmp_path, capsys):
    f = tmp_path / "slo.json"
    f.write_text("[1, 2, 3]")
    code = _run(["cache", "slo", str(f)])
    assert code == 1
    assert "Error" in capsys.readouterr().out


def test_cache_slo_rejects_empty_object(tmp_path, capsys):
    f = tmp_path / "slo.json"
    f.write_text("{}")
    code = _run(["cache", "slo", str(f)])
    assert code == 1
    assert "Error" in capsys.readouterr().out


def test_network_classify_alias_runs(tmp_path, capsys):
    payload = {"rtt_series": [1.0, 1.1, 1.0, 1.2, 1.1, 1.0]}
    f = tmp_path / "net.json"
    f.write_text(json.dumps(payload))
    _run(["network", "classify", str(f)])
    out = capsys.readouterr().out
    assert out.strip()  # dispatched to the signature handler, not an error
    assert "Unknown network command" not in out
