"""CH-0023: the committed `CLAUDE.md` must carry no literal credential values.

CH-0023 originally required `CLAUDE.md` to stay gitignored and untracked, on
the basis recorded in `_Docs/Planning/CyberHardening.md`: the local instruction
file was "documented as credential-bearing", so committing it would put live
credentials into history.

That premise no longer holds. Commit `ec7652a` ("CLAUDE.md structural parity
across the suite") committed the file deliberately and removed the `.gitignore`
entry, in every repository in this workspace, as the standard place for the
shared global rules and the Claude service-credential runbook. Reverting that
here is not a test's decision to make, and the original assertion -- that the
`.gitignore` still lists `CLAUDE.md` -- would be inert even if restored, since
an ignore rule does not untrack an already-tracked file.

What the file actually contains is credential *locations* and the commands that
fetch them at runtime: `~/.vault-claude/claude.env`, `secrets/claude/gitea`,
`vault write ... role_id="$VAULT_ROLE_ID"`. No secret value is written down.
That is the property worth holding, and the one this test now enforces: the
committed instruction file may describe how to obtain a credential, but must
never contain one.

See CH-0023 in `_Docs/Planning/CyberHardening.md` for the standing question of
whether the file should be committed at all, which is Jake's to answer.
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

# Assignments of a literal value to a credential-shaped name. Command
# substitutions (`X=$(...)`), shell variable references (`X="$Y"`) and empty
# assignments are all runtime lookups, not literals, and are allowed.
_LITERAL_ASSIGNMENT = re.compile(
    r'\b(?:[A-Z_]*(?:SECRET|TOKEN|PASSWORD|PASSWD|ROLE_ID|SECRET_ID|API_KEY|APIKEY)[A-Z_]*)'
    r'\s*[:=]\s*'
    r'(?!\s*$)(?![\'"]?\$)(?![\'"]{2})'
    r'[\'"]?([A-Za-z0-9/+_.\-]{12,})',
    re.IGNORECASE,
)

# Credential-shaped literals that are not assigned to a name: Vault tokens,
# GitHub/Gitea personal access tokens, AWS keys, private key blocks.
_BARE_SECRET = re.compile(
    r'\b(?:hv[sb]\.[A-Za-z0-9_-]{20,}'
    r'|gh[pousr]_[A-Za-z0-9]{30,}'
    r'|AKIA[0-9A-Z]{16}'
    r'|sk-[A-Za-z0-9]{20,}'
    r'|xox[abprs]-[A-Za-z0-9-]{10,}'
    r'|-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----)'
)


def test_claude_md_contains_no_literal_credentials():
    claude_md = _ROOT / "CLAUDE.md"
    assert claude_md.is_file(), "CLAUDE.md is expected at the repository root"

    text = claude_md.read_text(encoding="utf-8")

    bare = _BARE_SECRET.findall(text)
    assert not bare, (
        "CLAUDE.md contains what looks like a literal credential. It is committed, "
        "so this would enter history: remove it and rotate the credential."
    )

    assigned = [
        line.strip()
        for line in text.splitlines()
        if _LITERAL_ASSIGNMENT.search(line)
    ]
    assert not assigned, (
        "CLAUDE.md assigns a literal value to a credential-shaped name. Fetch it at "
        "runtime from Vault instead, as every other credential in this file does. "
        f"Offending lines: {assigned}"
    )
