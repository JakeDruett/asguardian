"""CH-0009 residual: generated gitignore must not ignore ENV/."""

from Asgard.BackendInit.templates import GITIGNORE_FULL


def test_generated_gitignore_does_not_ignore_env_dir():
    lines = {
        line.strip()
        for line in GITIGNORE_FULL.splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert "ENV/" not in lines
