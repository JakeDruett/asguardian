"""
Shared access to the L5 known-bad fixture library.

L5 tests must never scan fixtures from pytest ``tmp_path`` (the path
contains ``test``, which trips test-context suppression heuristics and
mutes real findings). ``neutral_copy`` stages a fixture into a plain
``tempfile.mkdtemp`` directory instead.
"""

import shutil
import tempfile
from pathlib import Path

#: Root of the per-CWE known-bad fixture library.
LIBRARY_ROOT = Path(__file__).resolve().parents[1] / "L5_known_bad"


def fixture_path(relative: str) -> Path:
    """Absolute path of a fixture inside the library; must exist."""
    path = LIBRARY_ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(f"L5 fixture missing from library: {relative}")
    return path


def neutral_copy(relative: str, target_name: str | None = None) -> Path:
    """
    Copy a library fixture into a neutral temp dir (no 'test' in the path)
    and return the copy's path. Caller may leave cleanup to the OS tmp
    reaper; directories are tiny and uniquely prefixed.
    """
    source = fixture_path(relative)
    neutral_dir = Path(tempfile.mkdtemp(prefix="asgard-l5-"))
    destination = neutral_dir / (target_name or source.name)
    shutil.copyfile(source, destination)
    return destination
