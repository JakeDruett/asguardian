"""CHC-0005: current-file secret scan uses one git grep -I, not per-file show."""

from Asgard.Heimdall.Security.Git.services.git_scanner import GitSecurityScanner


def test_current_file_secrets_use_single_grep(monkeypatch):
    scanner = GitSecurityScanner()
    calls = []

    def _git(args):
        calls.append(args)
        return "app.py:1:password = 'supersecret'\n"

    monkeypatch.setattr(scanner, "_git", _git)
    findings = scanner._check_secrets_in_current_files()
    assert calls
    assert calls[0][0] == "grep"
    assert "-I" in calls[0]
    assert all(cmd[0] != "show" for cmd in calls)
    assert findings
