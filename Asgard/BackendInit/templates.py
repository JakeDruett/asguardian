"""
Templates for backend project initialization.
"""

APIS_INIT = """\
\"\"\"
API route definitions for this service.
\"\"\"
"""

MODELS_INIT = """\
\"\"\"
Data models for this service.
\"\"\"
"""

MODELS_ENUMS = """\
\"\"\"
Enumeration types for this service.
\"\"\"

from enum import Enum
"""

SERVICES_INIT = """\
\"\"\"
Business logic services for this service.
\"\"\"
"""

PROMPTS_INIT = """\
\"\"\"
Prompt templates and definitions for AI/LLM interactions.
\"\"\"
"""

TESTS_INIT = """\
\"\"\"
Test suite for this service.
\"\"\"
"""

UTILITIES_INIT = """\
\"\"\"
Shared utility functions and helpers for this service.
\"\"\"
"""

README = """\
# Service Name

## Overview

Brief description of what this service does.

## Getting Started

### Prerequisites

- Python 3.11+
- Dependencies listed in requirements.txt or pyproject.toml

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and fill in the required values.

```bash
cp .env.example .env
```

## Structure

```
apis/         - API route definitions
models/       - Data models and enums
services/     - Business logic
prompts/      - AI/LLM prompt templates
tests/        - Test suite
utilities/    - Shared helpers and utilities
```

## Running Tests

```bash
pytest tests/
```
"""

ENV_EXAMPLE = """\
# Environment variable definitions for this service.
# Copy this file to .env and fill in the required values.
# Do NOT commit .env to version control.

# Application
# APP_ENV=
# APP_PORT=

# Database
# DB_HOST=
# DB_PORT=
# DB_NAME=
# DB_USER=
# DB_PASSWORD=
"""

CODING_STANDARDS = """\
# Coding Standards

This document defines the coding standards for this service.
These standards are enforced by [Asgard](https://github.com/your-org/asgard).

---

## General

- All imports MUST be at the top of the file. No lazy imports inside functions,
  methods, or conditional blocks. Exception: `if TYPE_CHECKING:` blocks are
  allowed for type hints.
- NEVER set fallback or default values for environment variables.
- Do not use relative file imports between modules. Shared packages should be
  imported like any other installed package.
- Never use emojis in comments, docstrings, print statements, or any other text.

---

## Models

- Use Pydantic v2 for all data models.
- Enumerations belong in `models/enums.py`.
- Models that are not unique to this service MUST live in a shared package
  (e.g. Aether).

---

## Services

Services are files contained in the `services/` directory.

- Services MUST be instantiated with required dependencies (e.g. logger) in
  their constructor.
- Service method calls from routers MUST pass `correlation_id` as the first
  parameter (excluding `__init__`).
- Services MUST log entry and exit for all public methods.
- Services MUST NOT use `info` log messages.
- Services MUST have at minimum a `trace` message as the first line of each
  function and a `trace` message immediately before the return statement (or as
  the last line if not returning).
- Services MUST use `try`/`except`, raising an error log for any exception.
- Log payload structure:
  ```python
  trace(correlation_id,
        f'{{"message":"MESSAGE", "details":{{"function_name":"NAME", "field":"{value}"}}}}',
        datetime.now())
  ```

---

## Routers

Routers are files contained in the `apis/` directory.

- Routers MUST log an `info` message as each endpoint's first task, stating the
  endpoint method and path:
  ```python
  logger.info(correlation_id,
              f'{{"message":"DESCRIPTION", "details":{{"endpoint":"[GET] /prefix/path"}}}}',
              datetime.now())
  ```
- Routers MUST log an `error` when an exception would crash the application or
  prevent a function from completing.
- Routers MUST log a `warning` when an issue results in a graceful exit or when
  a default value must be used.
- Routers SHOULD use `trace` messages to log subsequent activities.

---

## Logging

- All logging calls in `async` functions MUST use `await` with async logger
  methods.
- `message` fields describe the specific action being performed.
- `details` fields contain contextual data for debugging and monitoring.
- Avoid generic messages such as "Starting process" or "Operation complete".
- Services SHOULD log execution time for operations that may impact performance.
- External API calls MUST be logged before and after execution with timing
  information.
- Error logs MUST include the function name, sanitized input parameters, and
  full error details.
- HTTP errors MUST include the status code, response content (if available),
  and request details.

---

## Testing

- Run the test suite with `pytest tests/`.
- Test coverage is tracked via the Asgard test coverage matrix.
- Use the relevant test engineer agent from `.claude/` when creating tests.

---

## Code Quality

Run Asgard quality checks before committing:

```bash
asgard heimdall quality lazy-imports .
asgard heimdall quality typing .
asgard heimdall security scan .
```
"""

GITIGNORE_ENTRIES = [
    ".claude",
    "Claude Team",
    ".env",
]

GITIGNORE_FULL = """\
# Asgard / Claude
.claude
Claude Team/

# Environment
.env

# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
.Python
*.egg
*.egg-info/
dist/
build/
eggs/
parts/
var/
sdist/
wheels/
*.egg-link
.installed.cfg
lib/
lib64/
pip-wheel-metadata/
.eggs/

# Virtual environments
.venv/
venv/
env/
ENV/
.env.local
.env.*.local

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/
coverage.xml
*.cover
nosetests.xml
test-results/

# Type checking
.mypy_cache/
.dmypy.json
dmypy.json
.pytype/

# Linting
.ruff_cache/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
Thumbs.db

# Distribution / packaging
MANIFEST
*.manifest
*.spec

# Logs
*.log
logs/

# Node (if applicable)
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Secrets
*.pem
*.key
*.p12
*.pfx
"""
