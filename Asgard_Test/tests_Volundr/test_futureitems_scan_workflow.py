"""CH-0110: FutureItems security-scan must not fail-open on a missing dir."""

import os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_WF = os.path.join(
    _ROOT,
    "_FutureItems-Security",
    "Tools_Security",
    ".github",
    "workflows",
    "security-scan.yml",
)


def test_scan_workflow_fail_closed():
    text = open(_WF, encoding="utf-8").read()
    assert "cd security-tools" not in text
    assert "continue-on-error" not in text
    assert "total_issues" in text
    assert "sys.exit(1)" in text
    assert os.path.isfile(
        os.path.join(_ROOT, "_FutureItems-Security", "Tools_Security", "security_api.py")
    )
