"""CH-0023: local CLAUDE.md must stay untracked."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def test_claude_md_is_gitignored():
    gitignore = (_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert any(line.strip() == "CLAUDE.md" for line in gitignore.splitlines())
