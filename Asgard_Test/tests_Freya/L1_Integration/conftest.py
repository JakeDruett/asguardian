"""
Freya L1 Integration Tests - Shared Fixtures

Provides real HTML fixtures, Playwright browser setup, and baseline images
for comprehensive integration testing of Freya visual/UI testing package.

All tests run in headless mode suitable for CI/CD environments.
"""

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Generator

import pytest
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright.async_api import Error as PlaywrightError

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


# =============================================================================
# Fixtures Directory Structure
# =============================================================================

@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """
    Return the fixtures directory for L1 integration tests.

    Returns:
        Path: L1_Integration fixtures directory
    """
    fixtures = Path(__file__).parent / "fixtures"
    fixtures.mkdir(exist_ok=True)
    return fixtures


@pytest.fixture(scope="session")
def html_fixtures_dir(fixtures_dir) -> Path:
    """
    Return the HTML fixtures directory.

    Returns:
        Path: HTML fixtures directory
    """
    html_dir = fixtures_dir / "html"
    html_dir.mkdir(exist_ok=True)
    return html_dir


@pytest.fixture(scope="session")
def baseline_fixtures_dir(fixtures_dir) -> Path:
    """
    Return the baseline images directory.

    Returns:
        Path: Baseline images directory
    """
    baseline_dir = fixtures_dir / "baselines"
    baseline_dir.mkdir(exist_ok=True)
    return baseline_dir


@pytest.fixture(scope="session")
def output_dir(fixtures_dir) -> Path:
    """
    Return the test output directory.

    Returns:
        Path: Test output directory
    """
    output = fixtures_dir / "output"
    output.mkdir(exist_ok=True)
    return output


# =============================================================================
# HTML Fixtures - Sample Pages for Testing
# =============================================================================

@pytest.fixture(scope="session")
def sample_accessible_page(html_fixtures_dir) -> Path:
    """
    Create a sample accessible HTML page.

    Returns:
        Path: Path to accessible HTML file
    """
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Accessible Sample Page</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #ffffff;
            color: #333333;
        }
        header {
            background-color: #0066cc;
            color: white;
            padding: 20px;
            margin-bottom: 20px;
        }
        nav ul {
            list-style: none;
            padding: 0;
            display: flex;
            gap: 20px;
        }
        nav a {
            color: white;
            text-decoration: none;
            font-size: 18px;
        }
        main {
            min-height: 400px;
        }
        button {
            background-color: #0066cc;
            color: white;
            border: none;
            padding: 12px 24px;
            font-size: 16px;
            cursor: pointer;
            min-width: 48px;
            min-height: 48px;
        }
        button:focus {
            outline: 3px solid #ff9900;
            outline-offset: 2px;
        }
        .card {
            border: 1px solid #ddd;
            padding: 20px;
            margin: 10px 0;
            border-radius: 5px;
        }
        footer {
            margin-top: 40px;
            padding: 20px;
            background-color: #f5f5f5;
            text-align: center;
        }
        @media (max-width: 768px) {
            nav ul {
                flex-direction: column;
            }
            .card {
                padding: 10px;
            }
        }
    </style>
</head>
<body>
    <header>
        <h1>Accessible Sample Page</h1>
        <nav aria-label="Main navigation">
            <ul>
                <li><a href="#home">Home</a></li>
                <li><a href="#about">About</a></li>
                <li><a href="#contact">Contact</a></li>
            </ul>
        </nav>
    </header>

    <main>
        <article>
            <h2>Welcome to Our Sample Page</h2>
            <p>This is a fully accessible sample page designed for testing.</p>

            <section class="card">
                <h3>Features</h3>
                <ul>
                    <li>WCAG 2.1 AA compliant color contrast</li>
                    <li>Proper semantic HTML structure</li>
                    <li>Keyboard accessible navigation</li>
                    <li>Responsive design</li>
                </ul>
            </section>

            <section class="card">
                <h3>Interactive Elements</h3>
                <form>
                    <label for="name">Name:</label>
                    <input type="text" id="name" name="name">

                    <label for="email">Email:</label>
                    <input type="email" id="email" name="email">

                    <button type="submit">Submit Form</button>
                </form>
            </section>

            <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='100'%3E%3Crect width='200' height='100' fill='%230066cc'/%3E%3Ctext x='50' y='50' fill='white' font-size='20'%3ESample%3C/text%3E%3C/svg%3E"
                 alt="Sample image showing text 'Sample' on blue background">
        </article>
    </main>

    <footer>
        <p>Copyright 2026 - Accessible Sample Page</p>
    </footer>
</body>
</html>"""

    file_path = html_fixtures_dir / "accessible_page.html"
    file_path.write_text(html_content, encoding="utf-8")
    return file_path


@pytest.fixture(scope="session")
def sample_inaccessible_page(html_fixtures_dir) -> Path:
    """
    Create a sample page with accessibility violations.

    Returns:
        Path: Path to inaccessible HTML file
    """
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title></title>
    <style>
        body {
            font-family: Arial;
            background-color: #cccccc;
            color: #aaaaaa;
        }
        .small-button {
            width: 20px;
            height: 20px;
            background: red;
        }
        div:focus {
            outline: none;
        }
    </style>
</head>
<body>
    <div>
        <span style="font-size: 24px">Page Title</span>
    </div>

    <div onclick="alert('clicked')">Click me</div>

    <img src="test.jpg">

    <form>
        <input type="text" placeholder="Enter name">
        <button class="small-button"></button>
    </form>

    <a href="#">link</a>

    <div role="invalid-role">Content</div>
</body>
</html>"""

    file_path = html_fixtures_dir / "inaccessible_page.html"
    file_path.write_text(html_content, encoding="utf-8")
    return file_path


@pytest.fixture(scope="session")
def sample_responsive_page(html_fixtures_dir) -> Path:
    """
    Create a sample responsive page for testing breakpoints.

    Returns:
        Path: Path to responsive HTML file
    """
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Responsive Test Page</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: Arial, sans-serif;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
        }
        .card {
            background: #f5f5f5;
            padding: 20px;
            border-radius: 5px;
        }
        .touch-target {
            width: 48px;
            height: 48px;
            background: #0066cc;
            color: white;
            border: none;
            margin: 10px;
            cursor: pointer;
        }

        @media (max-width: 1024px) {
            .grid {
                grid-template-columns: repeat(3, 1fr);
            }
        }

        @media (max-width: 768px) {
            .grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 480px) {
            .grid {
                grid-template-columns: 1fr;
            }
            .touch-target {
                width: 44px;
                height: 44px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Responsive Grid Layout</h1>

        <div class="grid">
            <div class="card">Card 1</div>
            <div class="card">Card 2</div>
            <div class="card">Card 3</div>
            <div class="card">Card 4</div>
        </div>

        <div>
            <button class="touch-target" aria-label="Button 1">1</button>
            <button class="touch-target" aria-label="Button 2">2</button>
            <button class="touch-target" aria-label="Button 3">3</button>
        </div>
    </div>
</body>
</html>"""

    file_path = html_fixtures_dir / "responsive_page.html"
    file_path.write_text(html_content, encoding="utf-8")
    return file_path


@pytest.fixture(scope="session")
def sample_visual_page(html_fixtures_dir) -> Path:
    """
    Create a sample page for visual regression testing.

    Returns:
        Path: Path to visual test HTML file
    """
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visual Test Page</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .box {
            width: 300px;
            height: 200px;
            background-color: white;
            border: 2px solid #333;
            border-radius: 10px;
            padding: 20px;
            margin: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1 {
            color: white;
            text-align: center;
            font-size: 48px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
    </style>
</head>
<body>
    <h1>Visual Test Page</h1>
    <div class="box">
        <h2>Box 1</h2>
        <p>This is a sample box for visual testing.</p>
    </div>
    <div class="box">
        <h2>Box 2</h2>
        <p>Another box with consistent styling.</p>
    </div>
</body>
</html>"""

    file_path = html_fixtures_dir / "visual_page.html"
    file_path.write_text(html_content, encoding="utf-8")
    return file_path


# =============================================================================
# Playwright Browser Fixtures
# =============================================================================

_BROWSER_LAUNCH_ERROR: "str | None" = None
_BROWSER_PROBED = False


_PROBE_SOURCE = """
import sys
from playwright.sync_api import sync_playwright

try:
    with sync_playwright() as p:
        p.chromium.launch(headless=True).close()
except Exception as exc:
    sys.stdout.write(str(exc).strip().splitlines()[0])
    sys.exit(1)
sys.exit(0)
"""


def _browser_launch_error() -> "str | None":
    """Return why a Chromium launch fails here, or None if it works.

    Probed once per session and cached.

    The probe runs in a subprocess, which matters: this directory sits beside
    Freya's L0 suites, which patch `async_playwright` inside the modules under
    test. An in-process probe run after those is answering a question about a
    session whose playwright surface other tests have been reaching into, and
    it gave the wrong answer -- reporting a launchable browser in a
    package-wide run on a machine where every real launch failed. A fresh
    interpreter cannot be affected by any of that.
    """
    global _BROWSER_LAUNCH_ERROR, _BROWSER_PROBED
    if _BROWSER_PROBED:
        return _BROWSER_LAUNCH_ERROR

    completed = subprocess.run(
        [sys.executable, "-c", _PROBE_SOURCE],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        _BROWSER_LAUNCH_ERROR = (
            completed.stdout.strip()
            or completed.stderr.strip().splitlines()[-1:] and completed.stderr.strip().splitlines()[-1]
            or f"probe exited {completed.returncode}"
        )
    _BROWSER_PROBED = True
    return _BROWSER_LAUNCH_ERROR


@pytest.fixture(scope="session", autouse=True)
def _require_a_launchable_browser():
    """Skip this directory when no Playwright browser can be launched.

    Every test here drives a real Chromium, and the Freya services under test
    launch their own browsers rather than taking one from a fixture -- so the
    `browser` fixture below does not gate them. Without this probe, a machine
    with no matching browser build reports dozens of Freya failures, each
    carrying Playwright's "please run playwright install" banner, which reads
    as the package being broken rather than a dependency being absent.

    This can only ever skip, never pass something that would otherwise fail:
    the probe launches a browser and closes it, and asserts nothing about
    Freya.
    """
    error = _browser_launch_error()
    if error:
        pytest.skip(
            "Freya L1 integration tests need a launchable Playwright Chromium, and "
            f"the probe launch failed: {error}. Install the browsers matching the "
            "installed playwright package (`playwright install chromium`), or point "
            "PLAYWRIGHT_BROWSERS_PATH at a build of the revision it expects."
        )


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for async tests.

    Yields:
        asyncio event loop
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def browser() -> Generator[Browser, None, None]:
    """
    Create a Playwright browser instance for the test session.

    Skips rather than errors when no browser is installed. Every test in this
    directory drives a real Chromium; without one there is nothing to
    integrate against, and Playwright's "Executable doesn't exist ... please
    run playwright install" is raised once per test, which reads as dozens of
    Freya failures rather than one missing dependency. A skip says which it
    is. It also stays a skip and never a silent pass: these tests assert
    nothing without the browser fixture.

    Yields:
        Browser: Chromium browser instance
    """
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
        except PlaywrightError as exc:
            pytest.skip(
                "Freya L1 integration tests need a Playwright Chromium build, and "
                f"launching one failed: {exc}. Install the browsers matching the "
                "installed playwright package (`playwright install chromium`), or "
                "point PLAYWRIGHT_BROWSERS_PATH at a build of the right revision."
            )
        yield browser
        await browser.close()


@pytest.fixture
async def browser_context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """
    Create a new browser context for each test.

    Args:
        browser: Browser instance

    Yields:
        BrowserContext: Fresh browser context
    """
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        device_scale_factor=1,
    )
    yield context
    await context.close()


@pytest.fixture
async def page(browser_context: BrowserContext) -> Generator[Page, None, None]:
    """
    Create a new page for each test.

    Args:
        browser_context: Browser context

    Yields:
        Page: Fresh page instance
    """
    page = await browser_context.new_page()
    yield page
    await page.close()


# =============================================================================
# Helper Functions
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def _freya_l1_allow_file_urls():
    """L1 fixtures are local HTML files; production still refuses file:."""
    from Asgard.Freya.Integration.services import _url_safety

    previous = _url_safety.allow_file_default
    _url_safety.allow_file_default = True
    yield
    _url_safety.allow_file_default = previous


def file_url(file_path: Path) -> str:
    """
    Convert a file path to a file:// URL.

    Args:
        file_path: Path to file

    Returns:
        str: file:// URL
    """
    return f"file://{file_path.absolute()}"
