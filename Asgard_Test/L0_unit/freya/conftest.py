"""
Pytest Configuration and Fixtures for Freya L0 Unit Tests

Provides shared fixtures and configuration for Freya image optimization tests.
"""

import pytest
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_playwright_page():
    """Mock Playwright Page object for testing"""
    page = AsyncMock()

    # Mock common page methods
    page.goto = AsyncMock()
    page.evaluate = AsyncMock()
    page.screenshot = AsyncMock()

    return page


@pytest.fixture
def mock_playwright_browser():
    """Mock Playwright Browser object for testing"""
    browser = AsyncMock()
    page = AsyncMock()

    browser.new_page = AsyncMock(return_value=page)
    browser.close = AsyncMock()

    return browser, page


@pytest.fixture
def sample_image_data():
    """Sample image data as returned from browser evaluation"""
    return {
        "src": "https://example.com/image.jpg",
        "alt": "Sample image",
        "hasAlt": True,
        "width": "800",
        "height": "600",
        "loading": "lazy",
        "srcset": None,
        "naturalWidth": 800,
        "naturalHeight": 600,
        "displayWidth": 800,
        "displayHeight": 600,
        "isAboveFold": False,
        "html": '<img src="image.jpg" alt="Sample image">',
        "cssSelector": "img.sample",
        "type": "img",
        "isVisible": True,
    }


@pytest.fixture
def sample_image_data_list():
    """List of sample image data for testing multiple images"""
    return [
        {
            "src": "https://example.com/hero.jpg",
            "alt": "Hero image",
            "hasAlt": True,
            "width": None,
            "height": None,
            "loading": None,
            "srcset": None,
            "naturalWidth": 1600,
            "naturalHeight": 900,
            "displayWidth": 800,
            "displayHeight": 450,
            "isAboveFold": True,
            "html": '<img src="hero.jpg" alt="Hero image">',
            "cssSelector": "img.hero",
            "type": "img",
            "isVisible": True,
        },
        {
            "src": "https://example.com/product.png",
            "hasAlt": False,
            "width": "400",
            "height": "400",
            "loading": None,
            "srcset": None,
            "naturalWidth": 800,
            "naturalHeight": 800,
            "displayWidth": 400,
            "displayHeight": 400,
            "isAboveFold": False,
            "html": '<img src="product.png">',
            "cssSelector": "img.product",
            "type": "img",
            "isVisible": True,
        },
        {
            "src": "https://example.com/background.webp",
            "hasAlt": False,
            "width": None,
            "height": None,
            "loading": None,
            "srcset": None,
            "naturalWidth": 0,
            "naturalHeight": 0,
            "displayWidth": 1200,
            "displayHeight": 600,
            "isAboveFold": True,
            "html": "",
            "cssSelector": "div.hero-bg",
            "type": "background",
            "isVisible": True,
        },
    ]


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for HTTP requests"""
    client = AsyncMock()
    client.get = AsyncMock()
    client.aclose = AsyncMock()
    return client
