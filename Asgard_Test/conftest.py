"""
Asgard Test Configuration

Shared pytest configuration and fixtures for all Asgard tests.
"""

import os
import sys
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


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def asgard_root():
    """Return the Asgard package root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def temp_output_dir(tmp_path):
    """Provide a temporary directory for test outputs."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
