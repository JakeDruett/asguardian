"""
Common Mock Patterns

Pre-configured mocks for common testing scenarios including Playwright,
databases, HTTP responses, and file systems.
"""

from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, Mock


def mock_playwright_page() -> MagicMock:
    """
    Create a mock Playwright page with common methods.

    Returns:
        MagicMock configured with Playwright page interface

    Example:
        >>> page = mock_playwright_page()
        >>> page.goto.return_value = None
        >>> page.screenshot.return_value = b"fake_screenshot_data"
        >>>
        >>> # Use in tests
        >>> import asyncio
        >>> asyncio.run(page.goto("https://example.com"))
        >>> asyncio.run(page.screenshot(path="/tmp/test.png"))
    """
    page = AsyncMock()

    # Navigation methods
    page.goto = AsyncMock(return_value=None)
    page.reload = AsyncMock(return_value=None)
    page.go_back = AsyncMock(return_value=None)
    page.go_forward = AsyncMock(return_value=None)

    # Element selection
    page.query_selector = AsyncMock(return_value=None)
    page.query_selector_all = AsyncMock(return_value=[])
    page.locator = Mock(return_value=AsyncMock())
    page.wait_for_selector = AsyncMock(return_value=AsyncMock())

    # Screenshots and PDFs
    page.screenshot = AsyncMock(return_value=b"fake_screenshot_data")
    page.pdf = AsyncMock(return_value=b"fake_pdf_data")

    # JavaScript evaluation
    page.evaluate = AsyncMock(return_value={})
    page.evaluate_handle = AsyncMock(return_value=AsyncMock())

    # Waiting
    page.wait_for_load_state = AsyncMock(return_value=None)
    page.wait_for_timeout = AsyncMock(return_value=None)
    page.wait_for_function = AsyncMock(return_value=None)

    # Properties
    page.url = "https://example.com"
    page.title = AsyncMock(return_value="Example Domain")
    page.content = AsyncMock(return_value="<html><body>Test</body></html>")

    # Configuration
    page.set_default_timeout = Mock(return_value=None)
    page.set_viewport_size = AsyncMock(return_value=None)
    page.set_extra_http_headers = AsyncMock(return_value=None)

    # Media emulation
    page.emulate_media = AsyncMock(return_value=None)

    # Accessibility
    page.accessibility = AsyncMock()
    page.accessibility.snapshot = AsyncMock(return_value={
        "role": "WebArea",
        "name": "Test Page",
        "children": []
    })

    # Events
    page.on = Mock(return_value=None)
    page.once = Mock(return_value=None)

    # Keyboard and Mouse
    page.keyboard = AsyncMock()
    page.mouse = AsyncMock()

    # Context
    page.context = AsyncMock()

    return page


def mock_playwright_browser() -> MagicMock:
    """
    Create a mock Playwright browser with common methods.

    Returns:
        MagicMock configured with Playwright browser interface

    Example:
        >>> browser = mock_playwright_browser()
        >>> context = asyncio.run(browser.new_context())
        >>> page = asyncio.run(context.new_page())
    """
    browser = AsyncMock()

    # Context creation
    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_playwright_page())
    mock_context.close = AsyncMock(return_value=None)
    mock_context.new_cdp_session = AsyncMock(return_value=AsyncMock())

    browser.new_context = AsyncMock(return_value=mock_context)
    browser.new_page = AsyncMock(return_value=mock_playwright_page())

    # Browser control
    browser.close = AsyncMock(return_value=None)
    browser.is_connected = Mock(return_value=True)

    # Properties
    browser.version = "1.0.0"
    browser.browser_type = "chromium"

    # Contexts
    browser.contexts = []

    return browser


def mock_database_connection() -> MagicMock:
    """
    Create a mock SQLAlchemy-style database connection.

    Returns:
        MagicMock configured with database connection interface

    Example:
        >>> db = mock_database_connection()
        >>> db.execute.return_value.fetchall.return_value = [
        ...     {"id": 1, "name": "Test User"}
        ... ]
        >>> result = db.execute("SELECT * FROM users")
        >>> rows = result.fetchall()
        >>> assert len(rows) == 1
    """
    connection = MagicMock()

    # Query execution
    result_proxy = MagicMock()
    result_proxy.fetchall = Mock(return_value=[])
    result_proxy.fetchone = Mock(return_value=None)
    result_proxy.fetchmany = Mock(return_value=[])
    result_proxy.rowcount = 0
    result_proxy.lastrowid = 1

    connection.execute = Mock(return_value=result_proxy)

    # Transaction management
    connection.begin = Mock(return_value=MagicMock())
    connection.commit = Mock(return_value=None)
    connection.rollback = Mock(return_value=None)

    # Connection management
    connection.close = Mock(return_value=None)
    connection.closed = False

    # Session-style methods (for ORM)
    connection.query = Mock(return_value=MagicMock())
    connection.add = Mock(return_value=None)
    connection.delete = Mock(return_value=None)
    connection.flush = Mock(return_value=None)
    connection.refresh = Mock(return_value=None)

    # Relationship loading
    def mock_relationship(lazy_load=True):
        """Create a mock relationship."""
        rel = MagicMock()
        rel.all = Mock(return_value=[])
        rel.first = Mock(return_value=None)
        rel.filter = Mock(return_value=rel)
        return rel

    connection.relationship = mock_relationship

    return connection


def mock_http_response(status: int = 200, body: Dict[str, Any] = None) -> MagicMock:
    """
    Create a mock HTTP response object.

    Args:
        status: HTTP status code (default: 200)
        body: Response body as dictionary (default: {})

    Returns:
        MagicMock configured with HTTP response interface

    Example:
        >>> response = mock_http_response(200, {"success": True, "data": {"id": 1}})
        >>> assert response.status_code == 200
        >>> assert response.json() == {"success": True, "data": {"id": 1}}
        >>>
        >>> error_response = mock_http_response(404, {"error": "Not Found"})
        >>> assert error_response.status_code == 404
        >>> assert error_response.ok is False
    """
    if body is None:
        body = {}

    response = MagicMock()

    # Status
    response.status_code = status
    response.ok = 200 <= status < 300
    response.is_error = status >= 400
    response.is_redirect = 300 <= status < 400

    # Body
    response.json = Mock(return_value=body)
    response.text = str(body)
    response.content = str(body).encode("utf-8")

    # Headers
    response.headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(response.content))
    }

    # Cookies
    response.cookies = {}

    # Methods
    response.raise_for_status = Mock(
        side_effect=Exception(f"HTTP {status}") if status >= 400 else None
    )

    # Request info
    response.url = "https://api.example.com/endpoint"
    response.request = MagicMock()
    response.request.method = "GET"
    response.request.url = response.url

    # Timing
    response.elapsed = MagicMock()
    response.elapsed.total_seconds = Mock(return_value=0.123)

    return response


def mock_file_system() -> MagicMock:
    """
    Create a mock file system with common operations.

    Returns:
        MagicMock configured with file system interface

    Example:
        >>> fs = mock_file_system()
        >>> fs.exists.return_value = True
        >>> fs.read_text.return_value = "file content"
        >>> fs.write_text.return_value = None
        >>>
        >>> assert fs.exists("/path/to/file.txt")
        >>> content = fs.read_text("/path/to/file.txt")
        >>> fs.write_text("/path/to/output.txt", "new content")
    """
    file_system = MagicMock()

    # File existence
    file_system.exists = Mock(return_value=True)
    file_system.is_file = Mock(return_value=True)
    file_system.is_dir = Mock(return_value=False)
    file_system.is_symlink = Mock(return_value=False)

    # File reading
    file_system.read_text = Mock(return_value="")
    file_system.read_bytes = Mock(return_value=b"")
    file_system.open = Mock(return_value=MagicMock())

    # File writing
    file_system.write_text = Mock(return_value=None)
    file_system.write_bytes = Mock(return_value=None)

    # Directory operations
    file_system.mkdir = Mock(return_value=None)
    file_system.rmdir = Mock(return_value=None)
    file_system.listdir = Mock(return_value=[])
    file_system.walk = Mock(return_value=[])

    # File operations
    file_system.rename = Mock(return_value=None)
    file_system.remove = Mock(return_value=None)
    file_system.unlink = Mock(return_value=None)
    file_system.copy = Mock(return_value=None)
    file_system.move = Mock(return_value=None)

    # Path operations
    file_system.join = Mock(side_effect=lambda *args: "/".join(args))
    file_system.basename = Mock(side_effect=lambda p: p.split("/")[-1])
    file_system.dirname = Mock(side_effect=lambda p: "/".join(p.split("/")[:-1]))

    # File metadata
    file_system.stat = Mock(return_value=MagicMock())
    file_system.stat.return_value.st_size = 1024
    file_system.stat.return_value.st_mtime = 1234567890

    # Permissions
    file_system.chmod = Mock(return_value=None)
    file_system.chown = Mock(return_value=None)

    return file_system
