# Asgard Test Utilities

Shared testing utilities for all Asgard test suites. This package provides reusable helpers for file operations, mocking, assertions, and test data generation.

## Installation

The test_utils package is automatically available when running tests within the Asgard_Test directory. No separate installation is required.

## Modules

### file_utils.py - File-Based Test Helpers

Utilities for creating temporary files and directory structures for testing.

```python
from test_utils import create_temp_python_file, create_temp_directory_structure

# Create a temporary Python file
code = '''
class Calculator:
    def add(self, a, b):
        return a + b
'''
file_path = create_temp_python_file(code)

# Create a complex directory structure
structure = {
    "src": {
        "__init__.py": "",
        "main.py": "def main(): pass",
        "utils": {
            "helpers.py": "def helper(): pass"
        }
    },
    "tests": {
        "test_main.py": "def test_main(): pass"
    }
}
root = create_temp_directory_structure(structure)
```

**Functions:**
- `create_temp_python_file(content: str) -> Path` - Create temporary Python file
- `create_temp_yaml_file(content: dict) -> Path` - Create temporary YAML file
- `create_temp_json_file(content: dict) -> Path` - Create temporary JSON file
- `load_fixture(package: str, name: str) -> Any` - Load test fixture from fixtures directory
- `create_temp_directory_structure(structure: dict) -> Path` - Create nested directory structure

### mock_utils.py - Common Mock Patterns

Pre-configured mocks for common testing scenarios.

```python
from test_utils import mock_playwright_page, mock_http_response
import asyncio

# Create a mock Playwright page
page = mock_playwright_page()
asyncio.run(page.goto("https://example.com"))
screenshot = asyncio.run(page.screenshot(path="/tmp/test.png"))

# Create a mock HTTP response
response = mock_http_response(200, {"success": True, "data": {"id": 1}})
assert response.status_code == 200
assert response.json() == {"success": True, "data": {"id": 1}}
```

**Functions:**
- `mock_playwright_page() -> MagicMock` - Mock Playwright page with navigation, selection, screenshots
- `mock_playwright_browser() -> MagicMock` - Mock Playwright browser with contexts
- `mock_database_connection() -> MagicMock` - Mock SQLAlchemy-style database connection
- `mock_http_response(status: int, body: dict) -> MagicMock` - Mock HTTP response
- `mock_file_system() -> MagicMock` - Mock file system operations

### assertion_utils.py - Custom Assertions

Enhanced assertions for common testing scenarios.

```python
from test_utils import (
    assert_yaml_valid,
    assert_json_valid,
    assert_json_schema,
    assert_approximate,
    assert_file_exists,
    assert_directory_structure
)

# Validate YAML/JSON
assert_yaml_valid("name: test\nversion: 1.0")
assert_json_valid('{"key": "value"}')

# Validate JSON schema
schema = {"type": "object", "properties": {"name": {"type": "string"}}}
data = {"name": "Alice"}
assert_json_schema(data, schema)

# Approximate comparisons
assert_approximate(1.234567, 1.235, tolerance=0.01)

# File system assertions
assert_file_exists(Path("/tmp/test.txt"))

expected_structure = {
    "src": {
        "main.py": "def main"
    },
    "tests": {
        "test_main.py": None  # Just check existence
    }
}
assert_directory_structure(root_path, expected_structure)
```

**Functions:**
- `assert_yaml_valid(content: str)` - Assert valid YAML
- `assert_json_valid(content: str)` - Assert valid JSON
- `assert_json_schema(data: dict, schema: dict)` - Assert data matches JSON schema
- `assert_approximate(actual: float, expected: float, tolerance: float)` - Assert approximate equality
- `assert_file_exists(path: Path)` - Assert file/directory exists
- `assert_directory_structure(path: Path, expected: dict)` - Assert directory structure matches

### generators.py - Test Data Generators

Generate realistic test data for various scenarios.

```python
from test_utils import (
    generate_python_class,
    generate_python_module,
    generate_openapi_spec,
    generate_graphql_schema,
    generate_metrics_data,
    generate_web_vitals_data
)

# Generate Python code
code = generate_python_class("UserService", methods=5)
module = generate_python_module(classes=3, functions=5)

# Generate API specifications
openapi_spec = generate_openapi_spec(endpoints=5, version="3.0")
graphql_schema = generate_graphql_schema(types=4)

# Generate metrics data
latency_metrics = generate_metrics_data(points=100, metric_type="latency")
memory_metrics = generate_metrics_data(points=50, metric_type="memory")

# Generate web vitals
good_vitals = generate_web_vitals_data(quality="good")
poor_vitals = generate_web_vitals_data(quality="poor")
```

**Functions:**
- `generate_python_class(name: str, methods: int) -> str` - Generate Python class
- `generate_python_module(classes: int, functions: int) -> str` - Generate Python module
- `generate_openapi_spec(endpoints: int, version: str) -> dict` - Generate OpenAPI spec
- `generate_graphql_schema(types: int) -> str` - Generate GraphQL schema
- `generate_metrics_data(points: int, metric_type: str) -> list` - Generate performance metrics
- `generate_web_vitals_data(quality: str) -> dict` - Generate Web Vitals data

## Usage Examples

### Creating Test Fixtures

```python
import pytest
from test_utils import create_temp_python_file, create_temp_yaml_file

@pytest.fixture
def sample_python_module():
    """Create a sample Python module for testing."""
    code = '''
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
'''
    return create_temp_python_file(code)

@pytest.fixture
def sample_config():
    """Create a sample YAML config for testing."""
    config = {
        "database": {
            "host": "localhost",
            "port": 5432
        },
        "cache": {
            "enabled": True
        }
    }
    return create_temp_yaml_file(config)
```

### Mocking External Dependencies

```python
import pytest
import asyncio
from test_utils import mock_playwright_page, mock_database_connection

@pytest.fixture
def mock_page():
    """Provide a mock Playwright page."""
    return mock_playwright_page()

def test_page_navigation(mock_page):
    """Test page navigation with mocked page."""
    asyncio.run(mock_page.goto("https://example.com"))
    assert mock_page.url == "https://example.com"

@pytest.fixture
def mock_db():
    """Provide a mock database connection."""
    return mock_database_connection()

def test_database_query(mock_db):
    """Test database query with mocked connection."""
    mock_db.execute.return_value.fetchall.return_value = [
        {"id": 1, "name": "Test"}
    ]
    result = mock_db.execute("SELECT * FROM users")
    rows = result.fetchall()
    assert len(rows) == 1
```

### Custom Assertions

```python
from pathlib import Path
from test_utils import assert_approximate, assert_directory_structure

def test_performance_timing():
    """Test performance with approximate timing."""
    measured_time = 1.234567
    expected_time = 1.235
    assert_approximate(measured_time, expected_time, tolerance=0.01)

def test_build_output(tmp_path):
    """Test build output structure."""
    # ... run build ...

    expected = {
        "dist": {
            "index.js": None,  # Just check it exists
            "styles.css": "body {"  # Check content contains this
        },
        "assets": {
            "images": {}  # Just check directory exists
        }
    }
    assert_directory_structure(tmp_path / "build", expected)
```

### Generating Test Data

```python
from test_utils import generate_metrics_data, generate_openapi_spec

def test_metrics_aggregation():
    """Test metrics aggregation with generated data."""
    data = generate_metrics_data(points=100, metric_type="latency")

    values = [point["value"] for point in data]
    avg_latency = sum(values) / len(values)
    assert avg_latency > 0

def test_openapi_validation():
    """Test OpenAPI validation with generated spec."""
    spec = generate_openapi_spec(endpoints=5, version="3.0")

    assert "openapi" in spec
    assert "paths" in spec
    assert len(spec["paths"]) == 5
```

## Running Tests

Run tests for the test_utils package:

```bash
# From Asgard_Test directory
pytest test_utils/tests/ -v

# Run with coverage
pytest test_utils/tests/ --cov=test_utils --cov-report=html

# Run specific test file
pytest test_utils/tests/test_file_utils.py -v
```

## Contributing

When adding new utilities:

1. Add the utility function to the appropriate module
2. Export it in `__init__.py`
3. Create comprehensive unit tests in `test_utils/tests/`
4. Add usage examples to this README
5. Include detailed docstrings with examples

## License

MIT License - See project root LICENSE file for details.
