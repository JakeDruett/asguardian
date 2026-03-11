# Asgard Test Suite

Unit and integration tests for all Asgard subpackages.

## Structure

```
Asgard_Test/
├── __init__.py
├── conftest.py           # Shared pytest configuration and fixtures
├── pytest.ini            # Pytest settings
├── README.md
└── tests_Volundr/        # Volundr infrastructure generation tests
    ├── __init__.py
    ├── test_kubernetes.py  # Kubernetes manifest generation tests
    ├── test_terraform.py   # Terraform module generation tests
    ├── test_docker.py      # Docker/Compose generation tests
    └── test_cicd.py        # CI/CD pipeline generation tests
```

## Running Tests

### All Asgard Tests

```bash
# From Asgard root directory
cd Asgard/Asgard_Test
python -m pytest -v

# Or from Asgard root
python -m pytest Asgard/Asgard_Test -v
```

### Volundr Tests Only

```bash
# Run all Volundr tests
python -m pytest Asgard/Asgard_Test/tests_Volundr -v

# Run with marker
python -m pytest Asgard/Asgard_Test -m volundr -v
```

### Specific Module Tests

```bash
# Kubernetes tests
python -m pytest Asgard/Asgard_Test/tests_Volundr/test_kubernetes.py -v

# Terraform tests
python -m pytest Asgard/Asgard_Test/tests_Volundr/test_terraform.py -v

# Docker tests
python -m pytest Asgard/Asgard_Test/tests_Volundr/test_docker.py -v

# CICD tests
python -m pytest Asgard/Asgard_Test/tests_Volundr/test_cicd.py -v
```

## Test Markers

| Marker | Description |
|--------|-------------|
| `unit` | Unit tests (no external dependencies) |
| `integration` | Integration tests |
| `slow` | Slow-running tests |
| `volundr` | Volundr package tests |
| `heimdall` | Heimdall package tests |
| `freya` | Freya package tests |
| `verdandi` | Verdandi package tests |
| `forseti` | Forseti package tests |

### Using Markers

```bash
# Run only unit tests
python -m pytest -m unit -v

# Run only Volundr tests
python -m pytest -m volundr -v

# Skip slow tests
python -m pytest -m "not slow" -v
```

## Test Coverage

To run tests with coverage:

```bash
python -m pytest Asgard/Asgard_Test --cov=Asgard --cov-report=html
```

## Adding New Tests

1. Create test file in appropriate `tests_<Package>/` directory
2. Follow naming convention: `test_<module>.py`
3. Use pytest fixtures from `conftest.py`
4. Add appropriate markers to test classes/functions

### Example Test

```python
import pytest
from Volundr.Kubernetes import ManifestConfig, ManifestGenerator

class TestMyFeature:
    """Tests for my feature."""

    @pytest.fixture
    def generator(self):
        return ManifestGenerator()

    def test_feature_works(self, generator):
        config = ManifestConfig(name="test", image="nginx:latest")
        result = generator.generate(config)
        assert result is not None
```
