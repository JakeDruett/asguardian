"""
Shared subprocess and tool-discovery helpers for toolchain-orchestrating
quality analysers (Rust/cargo, Node/npm).

Reuses Asgard.Bragi.Quality.services._tool_isolation's fail-closed executable
resolution (a PATH entry that points inside the scanned tree is rejected)
rather than duplicating that trust logic.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

from Asgard.Bragi.Quality.services._tool_isolation import trusted_executable


class ToolNotAvailableError(RuntimeError):
    """Raised when a required external tool cannot be found on PATH.

    Carries a clear, actionable message (what to install and how) rather
    than letting the analyser crash on a missing binary.
    """


@dataclass(frozen=True)
class ToolRunResult:
    """Outcome of running an external tool via subprocess."""
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


def require_executable(name: str, scan_path: Path, install_hint: str) -> str:
    """
    Resolve *name* on PATH, rejecting a binary inside the scanned tree.

    Raises ToolNotAvailableError with *install_hint* appended when the tool
    cannot be found, so callers can print a clear, actionable message
    instead of crashing on a missing dependency.
    """
    resolved = trusted_executable(name, scan_path)
    if not resolved:
        raise ToolNotAvailableError(f"{name} is not available. {install_hint}")
    return resolved


def find_optional_executable(name: str, scan_path: Path) -> Optional[str]:
    """Resolve *name* on PATH, returning None (not raising) when absent."""
    return trusted_executable(name, scan_path)


def resolve_node_tool(name: str, scan_path: Path, install_hint: str) -> List[str]:
    """
    Resolve a Node-ecosystem tool (eslint, tsc) to an argv prefix.

    Mirrors _tool_isolation.pyright_invocation's precedent: prefer a pinned,
    globally-installed binary outside the scanned tree; otherwise fall back
    to ``npx --no-install <name>``, which uses the project's own local
    node_modules/.bin without touching the network. Raises
    ToolNotAvailableError only when neither is possible.
    """
    pinned = trusted_executable(name, scan_path)
    if pinned:
        return [pinned]
    npx_bin = trusted_executable("npx", scan_path)
    if npx_bin:
        return [npx_bin, "--no-install", name]
    raise ToolNotAvailableError(f"{name} is not available. {install_hint}")


def run_tool(
    cmd: Sequence[str],
    *,
    cwd: Path,
    timeout: int = 180,
) -> ToolRunResult:
    """
    Run an external tool via subprocess, capturing stdout/stderr as text.

    A non-zero exit code is not itself an error for these tools: cargo
    clippy, eslint, npm audit, and tsc all exit non-zero when they find
    issues to report, which is the normal, successful case for a quality
    scan. Callers inspect stdout/stderr, not returncode, to decide whether
    the tool itself failed to run.
    """
    try:
        result = subprocess.run(
            list(cmd),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return ToolRunResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return ToolRunResult(returncode=-1, stdout=stdout, stderr=stderr, timed_out=True)
    except FileNotFoundError as exc:
        return ToolRunResult(returncode=-1, stdout="", stderr=str(exc))


def find_manifest_dirs(scan_path: Path, manifest_name: str, max_depth: int = 4) -> List[Path]:
    """
    Return directories under scan_path (or scan_path itself) containing
    *manifest_name* (e.g. 'Cargo.toml', 'package.json'), nearest first.

    Bounded depth and no symlink following, matching the confinement rules
    the rest of the language analysers apply.
    """
    root = Path(scan_path).resolve()
    if root.is_file():
        root = root.parent

    direct = root / manifest_name
    if direct.is_file():
        return [root]

    found: List[Path] = []
    _walk_for_manifest(root, manifest_name, max_depth, found)
    return sorted(found)


def _walk_for_manifest(current: Path, manifest_name: str, depth_remaining: int, found: List[Path]) -> None:
    if depth_remaining <= 0:
        return
    try:
        entries = list(current.iterdir())
    except OSError:
        return
    for entry in entries:
        if entry.is_symlink():
            continue
        if entry.name in ("node_modules", ".git", "target", "dist", "build", "__pycache__"):
            continue
        if entry.is_dir():
            if (entry / manifest_name).is_file():
                found.append(entry)
            else:
                _walk_for_manifest(entry, manifest_name, depth_remaining - 1, found)
