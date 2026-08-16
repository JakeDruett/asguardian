"""
Isolation for linters/type checkers run against an untrusted tree (CH-0049).

Tools are invoked with an empty cwd, Asgard-owned config (no plugins /
init-hooks), and ``--`` before path operands so a hostile repo cannot
execute project config or a local ``node_modules`` shim.
"""

from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Union

# Empty plugins / hooks so --rcfile / --config-file cannot exec project code.
ISOLATED_PYLINT_RC = """\
[MAIN]
init-hook=
load-plugins=
persistent=no

[MASTER]
init-hook=
load-plugins=
persistent=no
"""

ISOLATED_MYPY_INI = """\
[mypy]
plugins =
incremental = False
"""


def scan_root(scan_path: Path) -> Path:
    """Directory used as the untrusted tree root."""
    resolved = Path(scan_path).resolve()
    return resolved if resolved.is_dir() else resolved.parent


def path_is_inside(path: Path, root: Path) -> bool:
    """True if *path* is *root* or a descendant."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


@contextmanager
def isolated_tool_workspace() -> Iterator[Path]:
    """Empty temp directory for tool cwd and Asgard-owned config files."""
    with tempfile.TemporaryDirectory(prefix="asgard-tool-") as tmp:
        yield Path(tmp)


def write_isolated_pylint_rc(workspace: Path) -> Path:
    """Write a plugin-free pylintrc into *workspace* and return its path."""
    path = workspace / "pylintrc"
    path.write_text(ISOLATED_PYLINT_RC, encoding="utf-8")
    return path


def write_isolated_mypy_ini(workspace: Path) -> Path:
    """Write a plugin-free mypy.ini into *workspace* and return its path."""
    path = workspace / "mypy.ini"
    path.write_text(ISOLATED_MYPY_INI, encoding="utf-8")
    return path


def trusted_executable(name: str, scan_path: Path) -> Optional[str]:
    """
    Resolve *name* on PATH, rejecting binaries inside the scanned tree.

    Fail-closed: a PATH entry that points at the scan tree is not skipped
    in favour of a later trusted entry.
    """
    found = shutil.which(name)
    if not found:
        return None
    if path_is_inside(Path(found), scan_root(scan_path)):
        return None
    return found


def pyright_invocation(npx_path: str, scan_path: Path) -> List[str]:
    """Pinned ``pyright`` if trusted, else ``npx --no-install pyright``."""
    pinned = trusted_executable("pyright", scan_path)
    if pinned:
        return [pinned]
    return [npx_path, "--no-install", "pyright"]


def argv_with_paths(prefix: Sequence[str], *paths: Union[Path, str]) -> List[str]:
    """Build argv with ``--`` before path operands."""
    cmd = list(prefix)
    cmd.append("--")
    cmd.extend(str(p) for p in paths)
    return cmd
