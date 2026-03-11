"""
Freya Test Configuration

Shared pytest configuration and fixtures for all Freya tests.
"""

import os
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "requires_browser: marks tests that require browser access"
    )
    config.addinivalue_line(
        "markers", "accessibility: marks accessibility-related tests"
    )
    config.addinivalue_line(
        "markers", "visual: marks visual testing-related tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add integration marker to L1 tests
        if "L1_Integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        # Add accessibility marker to Accessibility tests
        if "Accessibility" in str(item.fspath):
            item.add_marker(pytest.mark.accessibility)
        # Add visual marker to Visual tests
        if "Visual" in str(item.fspath):
            item.add_marker(pytest.mark.visual)


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def freya_root():
    """Return the Freya package root directory."""
    return Path(__file__).parent.parent
