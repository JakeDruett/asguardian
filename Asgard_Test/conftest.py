"""
Asgard Test Configuration

Shared pytest configuration and fixtures for all Asgard tests.
"""

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Add Asgard packages to path
asgard_root = Path(__file__).parent.parent
sys.path.insert(0, str(asgard_root))

# Add individual Asgard subpackages to path
for subpackage in ["Volundr", "Heimdall", "Freya", "Verdandi", "Forseti"]:
    subpackage_path = asgard_root / subpackage
    if subpackage_path.exists():
        sys.path.insert(0, str(subpackage_path))


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "volundr: marks tests for Volundr package"
    )
    config.addinivalue_line(
        "markers", "heimdall: marks tests for Heimdall package"
    )
    config.addinivalue_line(
        "markers", "freya: marks tests for Freya package"
    )
    config.addinivalue_line(
        "markers", "verdandi: marks tests for Verdandi package"
    )
    config.addinivalue_line(
        "markers", "forseti: marks tests for Forseti package"
    )
    config.addinivalue_line(
        "markers", "backend_init: marks tests for BackendInit package"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add package markers based on directory
        if "tests_Volundr" in str(item.fspath):
            item.add_marker(pytest.mark.volundr)
        elif "tests_Heimdall" in str(item.fspath):
            item.add_marker(pytest.mark.heimdall)
        elif "tests_Freya" in str(item.fspath):
            item.add_marker(pytest.mark.freya)
        elif "tests_Verdandi" in str(item.fspath):
            item.add_marker(pytest.mark.verdandi)
        elif "tests_Forseti" in str(item.fspath):
            item.add_marker(pytest.mark.forseti)
        elif "backend_init" in str(item.fspath):
            item.add_marker(pytest.mark.backend_init)


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def asgard_root():
    """Return the Asgard package root directory."""
    return Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# neutral_tmp: a temp dir whose path carries NO test-like tokens.
#
# pytest's ``tmp_path`` embeds the test name in the directory path
# (``/tmp/pytest-of-<user>/pytest-N/test_<name>0/``). Asgard's scanners apply
# test-context suppression/downgrading based on the scanned file's path
# (``Asgard.Heimdall.Security.context.test_context``), so a known-bad security
# fixture written under a test-shaped path can be silently muted — the test
# then passes for the wrong reason. Any test that writes known-bad code to
# disk and scans it should use ``neutral_tmp`` instead of ``tmp_path``.
# ---------------------------------------------------------------------------

# Tokens that any test-context heuristic in the codebase keys on. The fixture
# guarantees none of these appear anywhere in the yielded path (substring
# match, case-insensitive — deliberately stricter than the scanners' own
# word-boundary matching, so the path stays neutral even for naive
# ``"test" in path`` checks).
_NEUTRAL_TMP_FORBIDDEN_RE = re.compile(r"test|spec|mock|conftest|fixture", re.IGNORECASE)


@pytest.fixture
def neutral_tmp():
    """
    Function-scoped temporary directory whose absolute path contains no
    test-like tokens, so path-based test-context classification always
    resolves to PRODUCTION for files created beneath it.

    Deliberately NOT rooted under pytest's basetemp: basetemp paths contain
    ``pytest`` (and, if overridden via ``--basetemp``, arbitrary user-chosen
    segments such as ``tests/``), either of which can trip test-context
    heuristics.
    """
    for _ in range(20):
        path = tempfile.mkdtemp(prefix="asgard_scan_")
        if not _NEUTRAL_TMP_FORBIDDEN_RE.search(path):
            break
        # Random suffix (or an unusual system tempdir) spelled a forbidden
        # token: discard and retry.
        shutil.rmtree(path, ignore_errors=True)
    else:
        pytest.skip(
            "could not allocate a neutral temp dir: system temp path "
            f"{tempfile.gettempdir()!r} contains test-like tokens"
        )
    try:
        yield Path(path)
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def temp_output_dir(tmp_path):
    """Provide a temporary directory for test outputs."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
