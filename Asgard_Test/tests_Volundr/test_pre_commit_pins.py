"""CH-0006: pre-commit hook revs must be full commit SHAs."""

from pathlib import Path

import yaml

_SHA = __import__("re").compile(r"^[0-9a-f]{40}$")
_ROOT = Path(__file__).resolve().parents[2]


def test_pre_commit_revs_are_full_shas():
    data = yaml.safe_load((_ROOT / ".pre-commit-config.yaml").read_text())
    revs = [repo["rev"] for repo in data["repos"]]
    assert revs
    for rev in revs:
        assert _SHA.fullmatch(rev), rev
    hook_ids = [hook["id"] for repo in data["repos"] for hook in repo["hooks"]]
    assert "detect-secrets" in hook_ids


def test_python_init_template_includes_detect_secrets():
    from Asgard.Shared.Init._templates_python import PRE_COMMIT_CONFIG

    data = yaml.safe_load(PRE_COMMIT_CONFIG.replace("{project_name}", "demo"))
    hook_ids = [hook["id"] for repo in data["repos"] for hook in repo["hooks"]]
    assert "detect-secrets" in hook_ids
