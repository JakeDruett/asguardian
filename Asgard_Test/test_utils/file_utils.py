"""
File-Based Test Helpers

Utilities for creating temporary files and directory structures for testing.
Provides helpers for Python, YAML, JSON files and complex directory hierarchies.
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict

import yaml


def create_temp_python_file(content: str, suffix: str = ".py") -> Path:
    """
    Create a temporary Python file with the given content.

    Args:
        content: Python source code to write to the file
        suffix: File suffix (default: ".py")

    Returns:
        Path to the created temporary file

    Example:
        >>> code = '''
        ... class Calculator:
        ...     def add(self, a, b):
        ...         return a + b
        ... '''
        >>> file_path = create_temp_python_file(code)
        >>> assert file_path.exists()
        >>> assert file_path.suffix == ".py"
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=suffix,
        delete=False,
        encoding="utf-8"
    ) as tmp_file:
        tmp_file.write(content)
        return Path(tmp_file.name)


def create_temp_yaml_file(content: Dict[str, Any], suffix: str = ".yaml") -> Path:
    """
    Create a temporary YAML file with the given content.

    Args:
        content: Dictionary to serialize as YAML
        suffix: File suffix (default: ".yaml")

    Returns:
        Path to the created temporary file

    Example:
        >>> data = {
        ...     "name": "test_service",
        ...     "version": "1.0.0",
        ...     "dependencies": ["requests", "pyyaml"]
        ... }
        >>> file_path = create_temp_yaml_file(data)
        >>> assert file_path.exists()
        >>> with open(file_path) as f:
        ...     loaded = yaml.safe_load(f)
        >>> assert loaded["name"] == "test_service"
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=suffix,
        delete=False,
        encoding="utf-8"
    ) as tmp_file:
        yaml.dump(content, tmp_file, default_flow_style=False)
        return Path(tmp_file.name)


def create_temp_json_file(content: Dict[str, Any], suffix: str = ".json") -> Path:
    """
    Create a temporary JSON file with the given content.

    Args:
        content: Dictionary to serialize as JSON
        suffix: File suffix (default: ".json")

    Returns:
        Path to the created temporary file

    Example:
        >>> data = {
        ...     "test_id": "test_001",
        ...     "status": "passed",
        ...     "metrics": {"duration": 1.23, "memory": 1024}
        ... }
        >>> file_path = create_temp_json_file(data)
        >>> assert file_path.exists()
        >>> with open(file_path) as f:
        ...     loaded = json.load(f)
        >>> assert loaded["test_id"] == "test_001"
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=suffix,
        delete=False,
        encoding="utf-8"
    ) as tmp_file:
        json.dump(content, tmp_file, indent=2)
        return Path(tmp_file.name)


def load_fixture(package: str, name: str) -> Any:
    """
    Load a test fixture from the fixtures directory.

    Args:
        package: Package name (e.g., "heimdall", "freya")
        name: Fixture name without extension

    Returns:
        Loaded fixture data (type depends on file extension)

    Example:
        >>> # Load JSON fixture
        >>> data = load_fixture("heimdall", "sample_coverage_report")
        >>> assert isinstance(data, dict)
        >>>
        >>> # Load YAML fixture
        >>> config = load_fixture("freya", "test_config")
        >>> assert "browser_type" in config
    """
    fixtures_dir = Path(__file__).parent.parent / f"tests_{package.capitalize()}" / "fixtures"

    # Try common file extensions
    for ext in [".json", ".yaml", ".yml", ".txt", ".py"]:
        fixture_path = fixtures_dir / f"{name}{ext}"
        if fixture_path.exists():
            if ext == ".json":
                with open(fixture_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            elif ext in [".yaml", ".yml"]:
                with open(fixture_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
            else:
                with open(fixture_path, "r", encoding="utf-8") as f:
                    return f.read()

    raise FileNotFoundError(f"Fixture '{name}' not found in package '{package}'")


def create_temp_directory_structure(structure: Dict[str, Any], base_path: Path = None) -> Path:
    """
    Create a temporary directory structure from a nested dictionary.

    Args:
        structure: Dictionary where keys are file/dir names and values are:
                  - str: file content
                  - dict: nested directory structure
                  - None: empty file
        base_path: Base path for the structure (creates temp dir if None)

    Returns:
        Path to the root of the created structure

    Example:
        >>> structure = {
        ...     "src": {
        ...         "__init__.py": "",
        ...         "main.py": "def main(): pass",
        ...         "utils": {
        ...             "__init__.py": "",
        ...             "helpers.py": "def helper(): pass"
        ...         }
        ...     },
        ...     "tests": {
        ...         "test_main.py": "def test_main(): pass"
        ...     },
        ...     "README.md": "# Test Project"
        ... }
        >>> root = create_temp_directory_structure(structure)
        >>> assert (root / "src" / "main.py").exists()
        >>> assert (root / "src" / "utils" / "helpers.py").exists()
        >>> assert (root / "tests" / "test_main.py").exists()
    """
    if base_path is None:
        base_path = Path(tempfile.mkdtemp())
    else:
        base_path = Path(base_path)
        base_path.mkdir(parents=True, exist_ok=True)

    for name, content in structure.items():
        path = base_path / name

        if isinstance(content, dict):
            # Create directory and recurse
            path.mkdir(parents=True, exist_ok=True)
            create_temp_directory_structure(content, path)
        else:
            # Create file
            path.parent.mkdir(parents=True, exist_ok=True)
            if content is None:
                content = ""
            path.write_text(str(content), encoding="utf-8")

    return base_path
