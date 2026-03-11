# Freya L1 Integration Tests

Comprehensive black-box integration tests for the Freya visual and UI testing package.

## Overview

These tests validate the complete functionality of Freya's accessibility, visual, responsive, and unified testing services using real Playwright browser instances and actual HTML fixtures.

## Test Files

### test_accessibility_integration.py
Real accessibility scanning tests including:
- **WCAG Validation**: Tests WCAG 2.1 compliance checking (A, AA, AAA levels)
- **Color Contrast**: Tests color contrast ratio validation against WCAG requirements
- **Keyboard Navigation**: Tests keyboard accessibility and focus management
- **ARIA Validation**: Tests ARIA attribute and role validation

### test_visual_integration.py
Visual regression and layout testing including:
- **Screenshot Capture**: Tests full-page and element-specific screenshot capture
- **Visual Regression**: Tests pixel-by-pixel, perceptual hash, and histogram comparison methods
- **Layout Validation**: Tests layout consistency checking
- **Style Validation**: Tests CSS style consistency validation
- **Regression Suites**: Tests batch visual regression testing with reporting

### test_responsive_integration.py
Responsive design testing including:
- **Breakpoint Testing**: Tests page rendering at mobile, tablet, desktop viewports
- **Touch Target Validation**: Tests minimum touch target size requirements (44x44px)
- **Viewport Configuration**: Tests viewport meta tag presence and configuration
- **Mobile Compatibility**: Tests mobile device compatibility across various devices
- **Horizontal Scroll Detection**: Tests for unwanted horizontal scrolling
- **Overlapping Elements**: Tests for overlapping interactive elements

### test_unified_integration.py
Full site testing and workflow integration including:
- **Unified Testing**: Tests combined accessibility, visual, and responsive testing
- **HTML Report Generation**: Tests comprehensive HTML report creation
- **Baseline Management**: Tests baseline save/load/update/delete operations
- **Site Crawling**: Tests multi-page site discovery and testing
- **End-to-End Workflows**: Tests complete testing workflows from scan to report

## Fixtures

### HTML Fixtures (fixtures/html/)
Sample HTML pages created by conftest.py:
- `accessible_page.html` - WCAG-compliant page with good practices
- `inaccessible_page.html` - Page with accessibility violations
- `responsive_page.html` - Responsive design with breakpoints
- `visual_page.html` - Page for visual regression testing

Additional fixtures created by individual tests:
- `overflow_page.html` - Page with horizontal scroll issues
- `overlap_page.html` - Page with overlapping elements
- `small_target_page.html` - Page with touch targets below minimum size
- `no_viewport_page.html` - Page missing viewport meta tag

### Baseline Images (fixtures/baselines/)
Baseline screenshots for visual regression testing are generated during test execution.

### Output Directory (fixtures/output/)
Test execution generates output in various subdirectories:
- `screenshots/` - Captured screenshots
- `regression/` - Visual regression diff images
- `breakpoints/` - Breakpoint test screenshots
- `reports/` - Generated HTML reports

## Running Tests

### Run All L1 Integration Tests
```bash
pytest Asgard/Asgard_Test/tests_Freya/L1_Integration/ -v
```

### Run Specific Test Category
```bash
# Accessibility tests only
pytest Asgard/Asgard_Test/tests_Freya/L1_Integration/test_accessibility_integration.py -v

# Visual tests only
pytest Asgard/Asgard_Test/tests_Freya/L1_Integration/test_visual_integration.py -v

# Responsive tests only
pytest Asgard/Asgard_Test/tests_Freya/L1_Integration/test_responsive_integration.py -v

# Unified tests only
pytest Asgard/Asgard_Test/tests_Freya/L1_Integration/test_unified_integration.py -v
```

### Run with Markers
```bash
# Run all integration tests
pytest -m integration Asgard/Asgard_Test/tests_Freya/L1_Integration/ -v

# Run accessibility-specific tests
pytest -m accessibility Asgard/Asgard_Test/tests_Freya/L1_Integration/ -v

# Run visual-specific tests
pytest -m visual Asgard/Asgard_Test/tests_Freya/L1_Integration/ -v
```

### Verbose Output
```bash
pytest Asgard/Asgard_Test/tests_Freya/L1_Integration/ -vv -s
```

## Test Characteristics

### Black-Box Testing
- Tests interact only through public Freya APIs
- No internal implementation details are accessed
- Tests validate observable behavior and outputs

### Headless Execution
- All tests run in headless Chromium browser
- Suitable for CI/CD pipelines
- No display server required

### File:// URLs
- Tests use local HTML fixtures via file:// URLs
- No network dependencies
- Fast and reliable execution

### Isolated Tests
- Each test is independent
- Fixtures are created fresh for each test session
- Output directories are separated per test

## Dependencies

Required packages:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `playwright` - Browser automation
- `Pillow` - Image processing (for visual regression)
- `numpy` - Numerical operations (for visual comparison)
- `opencv-python` - Advanced vision (optional, for SSIM)
- `scikit-image` - Image metrics (optional, for SSIM)

Install Playwright browsers:
```bash
playwright install chromium
```

## Coverage

These L1 integration tests provide comprehensive coverage of:
- All Freya accessibility services
- All Freya visual testing services
- All Freya responsive testing services
- All Freya integration/unified services
- Report generation and baseline management
- Multi-page site testing workflows

## CI/CD Compatibility

All tests are designed to run in CI environments:
- Headless browser execution
- No external dependencies
- Self-contained HTML fixtures
- Deterministic test behavior
- Fast execution times

## Troubleshooting

### Playwright Installation Issues
If tests fail with browser not found:
```bash
playwright install chromium
```

### Permission Errors on Fixtures
Ensure the fixtures directory has write permissions:
```bash
chmod -R u+w Asgard/Asgard_Test/tests_Freya/L1_Integration/fixtures/
```

### Import Errors
Ensure project root is in Python path:
```bash
export PYTHONPATH=$(pwd):$PYTHONPATH
```

### Async Test Warnings
If you see "no running event loop" warnings, ensure pytest-asyncio is installed:
```bash
pip install pytest-asyncio
```
