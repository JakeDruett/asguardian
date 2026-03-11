"""
Freya L1 Integration Tests

Comprehensive black-box integration tests for the Freya visual and UI testing package.
Tests use real Playwright browser instances in headless mode with file:// URLs for
local HTML fixtures, making them suitable for CI/CD environments.

Test Structure:
    - test_accessibility_integration.py: Real accessibility scanning tests
    - test_visual_integration.py: Screenshot capture and visual regression tests
    - test_responsive_integration.py: Responsive design and breakpoint tests
    - test_unified_integration.py: Full site testing and report generation tests

Fixtures:
    - conftest.py: Provides HTML fixtures, Playwright browsers, and helper functions
    - fixtures/html/: Sample HTML pages for testing
    - fixtures/baselines/: Baseline images for visual regression
    - fixtures/output/: Test output directory

All tests run in headless Chromium for CI compatibility.
"""

__all__ = [
    "test_accessibility_integration",
    "test_visual_integration",
    "test_responsive_integration",
    "test_unified_integration",
]
