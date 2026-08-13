"""
CLI wiring tests for the Phase-4 Verdandi CLI parity commands:

- `verdandi analyze sketch-merge`   mergeable quantile sketches (plan 03)
- `verdandi analyze co-check`       coordinated-omission quality checks
- `verdandi anomaly regression --profile`  sensitivity-profile presets
"""

import json

import pytest

from Asgard.Verdandi.cli import main as verdandi_main
from Asgard.Verdandi.cli._parser import create_parser
from Asgard.Verdandi.Analysis.services.quantile_sketch import DDSketch, TDigest


def _run(argv):
    with pytest.raises(SystemExit) as exc:
        verdandi_main(argv)
    return exc.value.code


def _write_tdigest(path, values):
    digest = TDigest()
    digest.add_batch(values)
    path.write_text(json.dumps(digest.to_dict()))


def _write_ddsketch(path, values):
    sketch = DDSketch()
    sketch.add_batch(values)
    path.write_text(json.dumps(sketch.to_dict()))


# ---------------------------------------------------------------- parsing

def test_parser_accepts_sketch_merge():
    args = create_parser().parse_args(
        ["analyze", "sketch-merge", "a.json", "b.json"]
    )
    assert args.analyze_command == "sketch-merge"
    assert args.sketch_files == ["a.json", "b.json"]
    assert args.quantiles == "50,90,95,99"


def test_parser_accepts_sketch_merge_options():
    args = create_parser().parse_args(
        ["analyze", "sketch-merge", "a.json", "-q", "99", "-o", "out.json"]
    )
    assert args.quantiles == "99"
    assert args.output == "out.json"


def test_parser_accepts_co_check():
    args = create_parser().parse_args(["analyze", "co-check", "m.json"])
    assert args.analyze_command == "co-check"
    assert args.metrics_file == "m.json"
    assert args.correct is False


def test_parser_accepts_co_check_correct_flag():
    args = create_parser().parse_args(
        ["analyze", "co-check", "m.json", "--correct"]
    )
    assert args.correct is True


def test_parser_accepts_regression_profile():
    args = create_parser().parse_args(
        ["anomaly", "regression", "1,2", "3,4", "--profile", "latency"]
    )
    assert args.profile == "latency"


def test_parser_rejects_unknown_profile():
    with pytest.raises(SystemExit):
        create_parser().parse_args(
            ["anomaly", "regression", "1,2", "3,4", "--profile", "bogus"]
        )


# ---------------------------------------------------------------- sketch-merge

def test_sketch_merge_tdigest_union(tmp_path, capsys):
    # Two disjoint halves; the merged median must sit near the union
    # median, not near either per-source median.
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _write_tdigest(a, [float(v) for v in range(1, 501)])
    _write_tdigest(b, [float(v) for v in range(501, 1001)])
    code = _run(["--format", "json", "analyze", "sketch-merge",
                 str(a), str(b), "-q", "50"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["sketch_type"] == "tdigest"
    assert data["sources"] == 2
    assert data["count"] == 1000.0
    assert 450 < data["percentiles"]["p50"] < 550


def test_sketch_merge_ddsketch(tmp_path, capsys):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _write_ddsketch(a, [10.0] * 50)
    _write_ddsketch(b, [1000.0] * 50)
    code = _run(["--format", "json", "analyze", "sketch-merge",
                 str(a), str(b), "-q", "99"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["sketch_type"] == "ddsketch"
    # p99 of the union must reflect the slow source within 1% rel. error.
    assert data["percentiles"]["p99"] == pytest.approx(1000.0, rel=0.02)


def test_sketch_merge_text_output(tmp_path, capsys):
    a = tmp_path / "a.json"
    _write_tdigest(a, [1.0, 2.0, 3.0])
    code = _run(["analyze", "sketch-merge", str(a)])
    out = capsys.readouterr().out
    assert code == 0
    assert "MERGED QUANTILE SKETCH" in out
    assert "tdigest" in out


def test_sketch_merge_writes_output_sketch(tmp_path, capsys):
    a = tmp_path / "a.json"
    out_file = tmp_path / "merged.json"
    _write_tdigest(a, [5.0] * 10)
    code = _run(["analyze", "sketch-merge", str(a), "-o", str(out_file)])
    assert code == 0
    merged = TDigest.from_dict(json.loads(out_file.read_text()))
    assert merged.count == 10.0


def test_sketch_merge_rejects_mixed_types(tmp_path, capsys):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _write_tdigest(a, [1.0])
    _write_ddsketch(b, [1.0])
    code = _run(["analyze", "sketch-merge", str(a), str(b)])
    assert code == 1
    assert "mixed sketch types" in capsys.readouterr().out


def test_sketch_merge_rejects_non_sketch_json(tmp_path, capsys):
    a = tmp_path / "a.json"
    a.write_text("[1, 2, 3]")
    code = _run(["analyze", "sketch-merge", str(a)])
    assert code == 1
    assert "Error" in capsys.readouterr().out


def test_sketch_merge_rejects_bad_quantiles(tmp_path, capsys):
    a = tmp_path / "a.json"
    _write_tdigest(a, [1.0])
    code = _run(["analyze", "sketch-merge", str(a), "-q", "0,150"])
    assert code == 1
    assert "Error" in capsys.readouterr().out


# ---------------------------------------------------------------- co-check

def test_co_check_clean_dataset(tmp_path, capsys):
    payload = {"samples_ms": [10.0] * 100, "duration_ms": 60000.0}
    f = tmp_path / "co.json"
    f.write_text(json.dumps(payload))
    code = _run(["--format", "json", "analyze", "co-check", str(f)])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["suspect"] is False
    assert data["quality_flags"] == []


def test_co_check_tene_suspect_exit_1(tmp_path, capsys):
    # avg 10.9 ms with a 1000 ms max over a 1 s run: avg < max^2/(2*duration)
    payload = {
        "samples_ms": [1.0] * 99 + [1000.0],
        "duration_ms": 1000.0,
    }
    f = tmp_path / "co.json"
    f.write_text(json.dumps(payload))
    code = _run(["--format", "json", "analyze", "co-check", str(f)])
    data = json.loads(capsys.readouterr().out)
    assert code == 1
    assert data["suspect"] is True
    assert "SUSPECT_COORDINATED_OMISSION" in data["quality_flags"]


def test_co_check_littles_law_violation(tmp_path, capsys):
    # 1000 rps at 1 s average latency implies 1000 in flight >> 10 allowed.
    payload = {
        "samples_ms": [1000.0] * 10,
        "duration_ms": 100000.0,
        "throughput_rps": 1000.0,
        "max_concurrency": 10.0,
    }
    f = tmp_path / "co.json"
    f.write_text(json.dumps(payload))
    code = _run(["--format", "json", "analyze", "co-check", str(f)])
    data = json.loads(capsys.readouterr().out)
    assert code == 1
    assert "LITTLES_LAW_VIOLATION" in data["quality_flags"]
    assert data["implied_concurrency"] == pytest.approx(1000.0)


def test_co_check_correction_backfills(tmp_path, capsys):
    payload = {
        "samples_ms": [1.0, 1.0, 5.0],
        "duration_ms": 10000.0,
        "expected_interval_ms": 1.0,
    }
    f = tmp_path / "co.json"
    f.write_text(json.dumps(payload))
    _run(["--format", "json", "analyze", "co-check", str(f), "--correct"])
    data = json.loads(capsys.readouterr().out)
    # 5 ms sample at 1 ms interval backfills 4, 3, 2, 1 ms.
    assert data["corrected_sample_count"] == 7
    assert "CO_CORRECTED" in data["quality_flags"]
    assert data["corrected_samples_ms"] == [1.0, 1.0, 5.0, 4.0, 3.0, 2.0, 1.0]


def test_co_check_correct_requires_interval(tmp_path, capsys):
    payload = {"samples_ms": [1.0], "duration_ms": 1000.0}
    f = tmp_path / "co.json"
    f.write_text(json.dumps(payload))
    code = _run(["analyze", "co-check", str(f), "--correct"])
    assert code == 1
    assert "expected_interval_ms" in capsys.readouterr().out


def test_co_check_text_output(tmp_path, capsys):
    payload = {"samples_ms": [10.0] * 20, "duration_ms": 60000.0}
    f = tmp_path / "co.json"
    f.write_text(json.dumps(payload))
    code = _run(["analyze", "co-check", str(f)])
    out = capsys.readouterr().out
    assert code == 0
    assert "COORDINATED-OMISSION CHECK" in out
    assert "Suspect:       False" in out


def test_co_check_rejects_missing_samples(tmp_path, capsys):
    f = tmp_path / "co.json"
    f.write_text(json.dumps({"duration_ms": 1000.0}))
    code = _run(["analyze", "co-check", str(f)])
    assert code == 1
    assert "Error" in capsys.readouterr().out


# ---------------------------------------------------------------- --profile

def test_regression_profile_latency_runs(tmp_path, capsys):
    before = ",".join(["100"] * 15 + ["110"] * 15)
    after = ",".join(["100"] * 15 + ["110"] * 15)
    code = _run(["anomaly", "regression", before, after,
                 "--profile", "latency"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Profile:         latency (bias: specificity, z=3.5)" in out


def test_regression_profile_small_sample_warning(capsys):
    # latency profile min_sample_size is 20; 5 points must warn.
    code = _run(["anomaly", "regression", "1,2,3,4,5", "6,7,8,9,10",
                 "--profile", "latency"])
    out = capsys.readouterr().out
    assert "Sample size below profile minimum" in out
    assert code in (0, 1)


def test_regression_profile_json_output_stays_parseable(capsys):
    before = ",".join(str(100 + i % 3) for i in range(30))
    after = ",".join(str(100 + i % 3) for i in range(30))
    _run(["--format", "json", "anomaly", "regression", before, after,
          "--profile", "error_rate"])
    data = json.loads(capsys.readouterr().out)
    assert data["is_regression"] is False


def test_regression_without_profile_unchanged(capsys):
    # No --profile: existing behavior and output shape are preserved.
    before = ",".join(["100"] * 25)
    after = ",".join(["100"] * 25)
    code = _run(["anomaly", "regression", before, after])
    out = capsys.readouterr().out
    assert code == 0
    assert "Profile:" not in out
