# Contributing to Asgard

Thank you for your interest in contributing to Asgard. This document provides guidelines and instructions for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- pip with support for PEP 621 (pip >= 21.3)

### Installation

1. Clone the repository and navigate to the Asgard directory:

```bash
cd Asgard
```

2. Install the package in editable mode with test dependencies:

```bash
pip install -e ".[all]"
pip install -e ".[test]"
```

3. Verify the installation:

```bash
asgard --help
```

### Running Tests

Tests live in the `Asgard_Test/` directory and are organized by module and test level:

```bash
# Run all tests
pytest Asgard_Test/

# Run tests for a specific module
pytest Asgard_Test/tests_Heimdall/
pytest Asgard_Test/tests_Freya/
pytest Asgard_Test/tests_Forseti/
pytest Asgard_Test/tests_Verdandi/
pytest Asgard_Test/tests_Volundr/

# Run only L0 unit tests
pytest Asgard_Test/L0_unit/

# Run cross-package integration tests
pytest Asgard_Test/L2_CrossPackage/
```

## Code Style

### General Rules

- All imports must be at the top of the file. No imports inside functions, methods, or conditional blocks. The only exception is `if TYPE_CHECKING:` blocks for type hints.
- Never set fallback or default values for environment variables.
- Never use emojis in comments, prints, documentation, or any other text.
- Use Pydantic v2 models for data validation and configuration.
- Use type hints throughout the codebase.
- Follow PEP 8 naming conventions.

### Module Structure

Each module within Asgard follows a consistent internal structure:

```
Module/
├── __init__.py          # Package exports and metadata
├── cli.py               # CLI entry point (if applicable)
├── SubFeature/
│   ├── __init__.py
│   ├── models/          # Pydantic models
│   │   └── *.py
│   └── services/        # Business logic
│       └── *.py
```

- **Models** define data structures using Pydantic. Place them in a `models/` directory within the relevant subfeature.
- **Services** contain the business logic. Each service should focus on a single responsibility.
- **CLI** modules wire services together and expose them as command-line tools.

### Detecting Code Quality Issues

Asgard includes built-in tools to check your own code quality:

```bash
# Detect lazy import violations
python -m Heimdall quality lazy-imports <path>

# Run full quality analysis
asgard heimdall analyze <path>
```

## Project Architecture

Asgard is a monorepo containing five independent modules under a unified namespace:

| Module | Purpose | Named After |
|--------|---------|-------------|
| Heimdall | Code quality control and static analysis | The Norse watchman god |
| Freya | Visual and UI testing | The Norse goddess of beauty |
| Forseti | API and schema specification | The Norse god of justice |
| Verdandi | Runtime performance metrics | The Norn of the present |
| Volundr | Infrastructure generation | The legendary Norse smith |

Each module can be used independently or through the unified `asgard` CLI. Modules are designed to have minimal coupling to each other. Cross-module functionality belongs in `Asgard/common/` or `Asgard/config/`.

### Dependency Groups

The project uses optional dependency groups defined in `pyproject.toml`. When adding a dependency:

1. If it is needed by only one module, add it to that module's optional dependency group.
2. If it is needed by all modules, add it to the core `dependencies` list.
3. Keep the total dependency count low. Prefer standard library solutions or lightweight custom implementations over heavy third-party packages.

## Pull Request Process

1. **Branch naming**: Use descriptive branch names (e.g., `feature/heimdall-complexity-metrics`, `fix/freya-crawl-timeout`).

2. **Scope**: Keep PRs focused. One logical change per pull request. If a change touches multiple modules, explain why in the PR description.

3. **Tests**: All new features must include tests. Bug fixes should include a test that reproduces the issue. Tests go in the appropriate `Asgard_Test/tests_<Module>/` directory.

4. **Documentation**: Update the module's README.md if you are adding or changing public-facing functionality.

5. **Changelog**: Add an entry to the `[Unreleased]` section of `CHANGELOG.md` describing your change.

6. **Review**: All PRs require review before merging. Address review feedback with additional commits rather than force-pushing over history.

## Adding a New Module

If you are adding an entirely new module to Asgard:

1. Create the module directory under `Asgard/Asgard/` following the standard structure.
2. Add the module to `PACKAGE_INFO["sub_packages"]` in `Asgard/Asgard/__init__.py`.
3. Add the module to `__all__` in `Asgard/Asgard/__init__.py`.
4. Register a CLI entry point in `pyproject.toml` under `[project.scripts]`.
5. Wire the module into the unified CLI in `Asgard/Asgard/cli.py`.
6. Create a test directory at `Asgard_Test/tests_<Module>/`.
7. Add an optional dependency group in `pyproject.toml` if the module has unique dependencies.
8. Update the README.md with the new module's description.

## Reporting Issues

When reporting a bug, include:

- The module and version affected
- Steps to reproduce the issue
- Expected vs actual behavior
- Python version and operating system
- Relevant error output or logs
