"""
CLI wiring tests for the `volundr score` extensions:
Terraform (.tf / module dir / tfplan.json) artifact kinds, GitLab/Azure
pipeline detection (no false-clean K8s misdetection), and --baseline
delta mode (plan Vo/07 §2.2).
"""

import json

import pytest

from Asgard.Volundr.cli import main as volundr_main
from Asgard.Volundr.cli._parser import create_parser
from Asgard.Volundr.cli.handlers_score_gitops import _detect_artifact_kind

INSECURE_TF = """\
resource "aws_security_group" "open" {
  name = "open"
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_s3_bucket" "b" {
  bucket = "my-bucket"
}
"""

GITLAB_CI = """\
stages:
  - build
build-job:
  stage: build
  image: node:latest
  script:
    - echo "$CI_COMMIT_MESSAGE" && make build
"""

DEPLOYMENT = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 1
  selector:
    matchLabels: {app: web}
  template:
    metadata:
      labels: {app: web}
    spec:
      containers:
        - name: web
          image: nginx:latest
"""


def _run(argv):
    with pytest.raises(SystemExit) as exc:
        volundr_main(argv)
    return exc.value.code


# ------------------------------------------------------------- detection

def test_detect_terraform_file(tmp_path):
    f = tmp_path / "main.tf"
    f.write_text(INSECURE_TF)
    kind, content = _detect_artifact_kind(f)
    assert kind == "terraform"
    assert "aws_security_group" in content


def test_detect_terraform_dir(tmp_path):
    (tmp_path / "main.tf").write_text(INSECURE_TF)
    kind, content = _detect_artifact_kind(tmp_path)
    assert kind == "terraform-dir"
    assert content is None


def test_detect_terraform_plan(tmp_path):
    f = tmp_path / "tfplan.json"
    f.write_text(json.dumps({"resource_changes": []}))
    kind, _ = _detect_artifact_kind(f)
    assert kind == "terraform-plan"


def test_detect_gitlab_pipeline_not_kubernetes(tmp_path):
    f = tmp_path / "ci.yaml"
    f.write_text(GITLAB_CI)
    kind, _ = _detect_artifact_kind(f)
    assert kind == "pipeline"


# --------------------------------------------------------------- scoring

def test_score_terraform_file_finds_issues(tmp_path, capsys):
    f = tmp_path / "main.tf"
    f.write_text(INSECURE_TF)
    code = _run(["score", str(f), "--format", "json", "--threshold", "0"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_findings"] > 0
    assert payload["composite"] < 100


def test_score_terraform_dir(tmp_path, capsys):
    (tmp_path / "main.tf").write_text(INSECURE_TF)
    code = _run(["score", str(tmp_path), "--format", "json",
                 "--threshold", "0"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_findings"] > 0


def test_score_terraform_plan_public_acl_fails_rule(tmp_path, capsys):
    plan = {
        "format_version": "1.2",
        "resource_changes": [{
            "address": "aws_s3_bucket.b",
            "type": "aws_s3_bucket",
            "name": "b",
            "change": {
                "actions": ["create"],
                "after": {"bucket": "b", "acl": "public-read"},
                "after_unknown": {},
            },
        }],
    }
    f = tmp_path / "tfplan.json"
    f.write_text(json.dumps(plan))
    code = _run(["score", str(f), "--format", "json", "--threshold", "0"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_findings"] > 0


def test_score_gitlab_pipeline_scored_as_pipeline(tmp_path, capsys):
    f = tmp_path / "gitlab-ci.yaml"
    f.write_text(GITLAB_CI)
    code = _run(["score", str(f), "--format", "json", "--threshold", "0"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    # Unpinned image + injectable script must not be a false clean.
    assert payload["total_findings"] > 0


# ------------------------------------------------------------ delta mode

def test_parser_accepts_baseline():
    args = create_parser().parse_args(
        ["score", "x.yaml", "--baseline", "old.json"]
    )
    assert args.score_baseline == "old.json"


def test_score_baseline_delta(tmp_path, capsys):
    f = tmp_path / "deploy.yaml"
    f.write_text(DEPLOYMENT)
    _run(["score", str(f), "--format", "json", "--threshold", "0"])
    baseline = tmp_path / "baseline.json"
    baseline.write_text(capsys.readouterr().out)

    code = _run(["score", str(f), "--format", "json", "--threshold", "0",
                 "--baseline", str(baseline)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert "delta" in payload
    assert payload["delta"]["composite"] == 0.0


def test_score_baseline_delta_text_output(tmp_path, capsys):
    f = tmp_path / "deploy.yaml"
    f.write_text(DEPLOYMENT)
    _run(["score", str(f), "--format", "json", "--threshold", "0"])
    baseline = tmp_path / "baseline.json"
    baseline.write_text(capsys.readouterr().out)

    code = _run(["score", str(f), "--threshold", "0",
                 "--baseline", str(baseline)])
    assert code == 0
    out = capsys.readouterr().out
    assert "Delta vs baseline" in out
    assert "composite" in out


def test_score_bad_baseline_exits_2(tmp_path, capsys):
    f = tmp_path / "deploy.yaml"
    f.write_text(DEPLOYMENT)
    code = _run(["score", str(f), "--baseline", str(tmp_path / "nope.json")])
    assert code == 2
    assert "baseline" in capsys.readouterr().out.lower()


def test_score_determinism_terraform(tmp_path, capsys):
    f = tmp_path / "main.tf"
    f.write_text(INSECURE_TF)
    _run(["score", str(f), "--format", "json", "--threshold", "0"])
    first = json.loads(capsys.readouterr().out)
    _run(["score", str(f), "--format", "json", "--threshold", "0"])
    second = json.loads(capsys.readouterr().out)
    first.pop("created_at", None)
    second.pop("created_at", None)
    assert first == second
