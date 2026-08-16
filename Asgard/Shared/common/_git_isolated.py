"""Isolated `git` subprocess for untrusted, caller-supplied repositories.

Local/global config and inherited env can execute helpers (`diff.external`,
`GIT_EXTERNAL_DIFF`, pager, fsmonitor, `!` aliases). Every product git call
against a caller path must go through this module.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Union

# Env keys that retarget the repo or inject an executable helper.
_UNSET_ENV = ("GIT_EXTERNAL_DIFF", "GIT_PAGER", "GIT_DIR")

_SAFE_CONFIG = (
    "diff.external=",
    "core.fsmonitor=",
    "core.pager=",
)

# `--no-ext-diff` is a diff-family option. Other commands reject it
# (ls-tree/fsck/branch) or echo it as a revision (rev-parse).
_NO_EXT_DIFF_COMMANDS = frozenset({"diff", "log", "show", "blame"})


def isolated_git_env(base: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    """Copy `base` (default: current env) and strip/override hostile git vars."""
    env = dict(os.environ if base is None else base)
    for key in _UNSET_ENV:
        env.pop(key, None)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    return env


def _subcommand(args: Sequence[str]) -> Optional[str]:
    for arg in args:
        if arg == "--":
            return None
        if not arg.startswith("-"):
            return arg
    return None


def isolated_git_argv(
    args: Sequence[str],
    *,
    repo: Optional[Union[str, Path]] = None,
) -> List[str]:
    """Build `git --no-pager [-C repo] -c ... <cmd> [--no-ext-diff] ...`."""
    argv: List[str] = ["git", "--no-pager"]
    if repo is not None:
        argv.extend(["-C", str(repo)])
    for spec in _SAFE_CONFIG:
        argv.extend(["-c", spec])
    command = _subcommand(args)
    if command:
        argv.extend(["-c", f"alias.{command}="])
    insert_no_ext = command in _NO_EXT_DIFF_COMMANDS and "--no-ext-diff" not in args
    for arg in args:
        argv.append(arg)
        if insert_no_ext and arg == command:
            argv.append("--no-ext-diff")
            insert_no_ext = False
    return argv


def run_isolated_git(
    args: Sequence[str],
    *,
    repo: Optional[Union[str, Path]] = None,
    cwd: Optional[Union[str, Path]] = None,
    timeout: int = 60,
    check: bool = False,
) -> subprocess.CompletedProcess:
    """Run `args` under isolated git config/env. Exceptions propagate."""
    return subprocess.run(
        isolated_git_argv(args, repo=repo),
        cwd=None if cwd is None else str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
        env=isolated_git_env(),
    )
