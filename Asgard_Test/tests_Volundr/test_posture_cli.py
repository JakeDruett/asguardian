"""
Tests for `volundr posture` — CLI wiring of the delivered GWPI
posture-index library (resource-graph PageRank + L3-norm roll-up).
"""

import argparse
import json

import pytest

from Asgard.Volundr.cli import create_parser
from Asgard.Volundr.cli.handlers_posture import (
    _collect_artifact_files,
    _kustomize_edges,
    _load_user_edges,
    run_posture,
)


GOOD_DEPLOYMENT = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 2
  selector:
    matchLabels: {app: web}
  template:
    metadata:
      labels: {app: web}
    spec:
      containers:
        - name: web
          image: nginx:1.27.0
"""

BAD_DEPLOYMENT = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: risky
spec:
  replicas: 1
  selector:
    matchLabels: {app: risky}
  template:
    metadata:
      labels: {app: risky}
    spec:
      containers:
        - name: risky
          image: nginx:latest
          securityContext:
            privileged: true
"""


def _args(path, **overrides):
    defaults = dict(
        path=str(path), edges=None, external_tools_ran=False,
        threshold=0.0, format="text",
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


@pytest.fixture
def portfolio(tmp_path):
    (tmp_path / "web.yaml").write_text(GOOD_DEPLOYMENT, encoding="utf-8")
    (tmp_path / "risky.yaml").write_text(BAD_DEPLOYMENT, encoding="utf-8")
    (tmp_path / "kustomization.yaml").write_text(
        "resources:\n  - web.yaml\n  - risky.yaml\n", encoding="utf-8"
    )
    return tmp_path


class TestParserWiring:
    def test_posture_command_parses(self):
        parser = create_parser()
        args = parser.parse_args(["posture", "somedir"])
        assert args.command == "posture"
        assert args.path == "somedir"
        assert args.threshold == 0.0
        assert args.format == "text"
        assert args.external_tools_ran is False

    def test_posture_flags_parse(self):
        parser = create_parser()
        args = parser.parse_args([
            "posture", "d", "--edges", "e.json", "--threshold", "40",
            "--format", "json", "--external-tools-ran",
        ])
        assert args.edges == "e.json"
        assert args.threshold == 40.0
        assert args.format == "json"
        assert args.external_tools_ran is True


class TestPostureRun:
    def test_missing_path_exits_2(self, tmp_path, capsys):
        assert run_posture(_args(tmp_path / "nope")) == 2

    def test_empty_dir_exits_2(self, tmp_path, capsys):
        assert run_posture(_args(tmp_path)) == 2
        assert "No infrastructure artifacts" in capsys.readouterr().out

    def test_text_output_reports_gwpi(self, portfolio, capsys):
        assert run_posture(_args(portfolio)) == 0
        out = capsys.readouterr().out
        assert "VOLUNDR POSTURE INDEX (GWPI)" in out
        assert "System risk" in out
        assert "web.yaml" in out and "risky.yaml" in out
        # Honesty: invalidating assumptions always shown.
        assert "Invalidating assumptions" in out
        assert "ClickOps divergence" in out

    def test_json_output_shape(self, portfolio, capsys):
        assert run_posture(_args(portfolio, format="json")) == 0
        payload = json.loads(capsys.readouterr().out)
        assert 0.0 <= payload["posture"] <= 100.0
        assert 0.0 <= payload["system_risk"] <= 1.0
        assert set(payload["resources"]) == {
            "kustomization.yaml", "web.yaml", "risky.yaml",
        }
        # Kustomize resources: entries became graph edges.
        assert ["kustomization.yaml", "web.yaml"] in payload["edges"]
        assert ["kustomization.yaml", "risky.yaml"] in payload["edges"]
        assert payload["unvalidated"] == []

    def test_threshold_gates_exit_code(self, portfolio):
        # Epistemic floor caps posture at 60 for static-only runs.
        assert run_posture(_args(portfolio, threshold=99.0)) == 1
        assert run_posture(_args(portfolio, threshold=0.0)) == 0

    def test_risky_portfolio_scores_worse_than_clean(self, tmp_path, capsys):
        clean = tmp_path / "clean"
        risky = tmp_path / "risky"
        clean.mkdir(); risky.mkdir()
        (clean / "web.yaml").write_text(GOOD_DEPLOYMENT, encoding="utf-8")
        (risky / "web.yaml").write_text(BAD_DEPLOYMENT, encoding="utf-8")

        run_posture(_args(clean, format="json"))
        clean_posture = json.loads(capsys.readouterr().out)["posture"]
        run_posture(_args(risky, format="json"))
        risky_posture = json.loads(capsys.readouterr().out)["posture"]
        assert risky_posture < clean_posture

    def test_user_edges_merge(self, portfolio, capsys):
        edges_file = portfolio / "edges.json"
        edges_file.write_text(
            json.dumps([["web.yaml", "risky.yaml"]]), encoding="utf-8"
        )
        assert run_posture(
            _args(portfolio, edges=str(edges_file), format="json")
        ) == 0
        payload = json.loads(capsys.readouterr().out)
        assert ["web.yaml", "risky.yaml"] in payload["edges"]

    def test_bad_edges_file_exits_2(self, portfolio, capsys):
        bad = portfolio / "edges.json"
        bad.write_text('{"not": "a list"}', encoding="utf-8")
        assert run_posture(_args(portfolio, edges=str(bad))) == 2
        assert "Could not load edges file" in capsys.readouterr().out

    def test_determinism(self, portfolio, capsys):
        run_posture(_args(portfolio, format="json"))
        first = capsys.readouterr().out
        run_posture(_args(portfolio, format="json"))
        second = capsys.readouterr().out
        assert first == second


class TestHelpers:
    def test_collect_is_sorted_and_filtered(self, tmp_path):
        (tmp_path / "b.yaml").write_text("a: 1", encoding="utf-8")
        (tmp_path / "a.yml").write_text("a: 1", encoding="utf-8")
        (tmp_path / "notes.txt").write_text("x", encoding="utf-8")
        files = _collect_artifact_files(tmp_path)
        assert [f.name for f in files] == ["a.yml", "b.yaml"]

    def test_kustomize_edges_ignore_unknown_targets(self, tmp_path):
        (tmp_path / "kustomization.yaml").write_text(
            "resources:\n  - web.yaml\n  - missing.yaml\n", encoding="utf-8"
        )
        (tmp_path / "web.yaml").write_text("a: 1", encoding="utf-8")
        edges = _kustomize_edges(_collect_artifact_files(tmp_path), tmp_path)
        assert edges == [("kustomization.yaml", "web.yaml")]

    def test_load_user_edges_rejects_bad_entries(self, tmp_path):
        bad = tmp_path / "e.json"
        bad.write_text(json.dumps([["only-one"]]), encoding="utf-8")
        with pytest.raises(ValueError):
            _load_user_edges(str(bad))
