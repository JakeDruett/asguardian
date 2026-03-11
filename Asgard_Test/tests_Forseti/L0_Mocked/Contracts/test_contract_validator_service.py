"""
Tests for Contract Validator Service

Unit tests for validating API implementations against contracts.
"""

import pytest
from pathlib import Path

from Asgard.Forseti.Contracts.models.contract_models import ContractConfig
from Asgard.Forseti.Contracts.services.contract_validator_service import ContractValidatorService


class TestContractValidatorServiceInit:
    """Tests for ContractValidatorService initialization."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        service = ContractValidatorService()

        assert service.config is not None
        assert isinstance(service.config, ContractConfig)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = ContractConfig(
            check_parameters=False,
            check_request_body=False,
            check_response_body=False
        )
        service = ContractValidatorService(config)

        assert service.config.check_parameters is False
        assert service.config.check_request_body is False
        assert service.config.check_response_body is False


class TestContractValidatorServiceValidate:
    """Tests for contract validation."""

    def test_validate_matching_contracts(self, tmp_path):
        """Test validation when implementation matches contract."""
        import yaml

        contract = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {"description": "Success"}
                        }
                    }
                }
            }
        }

        contract_file = tmp_path / "contract.yaml"
        impl_file = tmp_path / "impl.yaml"

        with open(contract_file, "w") as f:
            yaml.dump(contract, f)
        with open(impl_file, "w") as f:
            yaml.dump(contract, f)

        service = ContractValidatorService()
        result = service.validate(contract_file, impl_file)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_missing_path_in_implementation(self, tmp_path):
        """Test validation when implementation is missing a path."""
        import yaml

        contract = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {"200": {"description": "Success"}}
                    }
                },
                "/posts": {
                    "get": {
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }

        implementation = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {"200": {"description": "Success"}}
                    }
                }
                # Missing /posts path
            }
        }

        contract_file = tmp_path / "contract.yaml"
        impl_file = tmp_path / "impl.yaml"

        with open(contract_file, "w") as f:
            yaml.dump(contract, f)
        with open(impl_file, "w") as f:
            yaml.dump(implementation, f)

        service = ContractValidatorService()
        result = service.validate(contract_file, impl_file)

        assert result.is_valid is False
        assert any("/posts" in error.message for error in result.errors)

    def test_validate_missing_method_in_implementation(self, tmp_path):
        """Test validation when implementation is missing a method."""
        import yaml

        contract = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {"200": {"description": "Success"}}
                    },
                    "post": {
                        "responses": {"201": {"description": "Created"}}
                    }
                }
            }
        }

        implementation = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {"200": {"description": "Success"}}
                    }
                    # Missing post method
                }
            }
        }

        contract_file = tmp_path / "contract.yaml"
        impl_file = tmp_path / "impl.yaml"

        with open(contract_file, "w") as f:
            yaml.dump(contract, f)
        with open(impl_file, "w") as f:
            yaml.dump(implementation, f)

        service = ContractValidatorService()
        result = service.validate(contract_file, impl_file)

        assert result.is_valid is False
        assert any("post" in error.message.lower() for error in result.errors)


class TestContractValidatorServiceParameters:
    """Tests for parameter validation."""

    def test_validate_parameters_when_enabled(self, tmp_path):
        """Test parameter validation when enabled."""
        import yaml

        contract = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "required": True,
                                "schema": {"type": "integer"}
                            }
                        ],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }

        implementation = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [],  # Missing parameter
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }

        contract_file = tmp_path / "contract.yaml"
        impl_file = tmp_path / "impl.yaml"

        with open(contract_file, "w") as f:
            yaml.dump(contract, f)
        with open(impl_file, "w") as f:
            yaml.dump(implementation, f)

        config = ContractConfig(check_parameters=True)
        service = ContractValidatorService(config)
        result = service.validate(contract_file, impl_file)

        assert result.is_valid is False
        assert any("limit" in error.message for error in result.errors)

    def test_validate_parameters_when_disabled(self, tmp_path):
        """Test that parameter validation can be disabled."""
        import yaml

        contract = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "required": True,
                                "schema": {"type": "integer"}
                            }
                        ],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }

        implementation = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }

        contract_file = tmp_path / "contract.yaml"
        impl_file = tmp_path / "impl.yaml"

        with open(contract_file, "w") as f:
            yaml.dump(contract, f)
        with open(impl_file, "w") as f:
            yaml.dump(implementation, f)

        config = ContractConfig(check_parameters=False)
        service = ContractValidatorService(config)
        result = service.validate(contract_file, impl_file)

        # Should pass because parameter checking is disabled
        assert result.is_valid is True

    def test_validate_required_parameter_mismatch(self, tmp_path):
        """Test validation of required parameter mismatch."""
        import yaml

        contract = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "required": True,
                                "schema": {"type": "integer"}
                            }
                        ],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }

        implementation = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "required": False,  # Should be required
                                "schema": {"type": "integer"}
                            }
                        ],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }

        contract_file = tmp_path / "contract.yaml"
        impl_file = tmp_path / "impl.yaml"

        with open(contract_file, "w") as f:
            yaml.dump(contract, f)
        with open(impl_file, "w") as f:
            yaml.dump(implementation, f)

        service = ContractValidatorService()
        result = service.validate(contract_file, impl_file)

        assert result.is_valid is False
        assert any("required" in error.message.lower() for error in result.errors)


class TestContractValidatorServiceRequestBody:
    """Tests for request body validation."""

    def test_validate_missing_request_body(self, tmp_path):
        """Test validation when request body is missing."""
        import yaml

        contract = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}}
                    }
                }
            }
        }

        implementation = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        # Missing requestBody
                        "responses": {"201": {"description": "Created"}}
                    }
                }
            }
        }

        contract_file = tmp_path / "contract.yaml"
        impl_file = tmp_path / "impl.yaml"

        with open(contract_file, "w") as f:
            yaml.dump(contract, f)
        with open(impl_file, "w") as f:
            yaml.dump(implementation, f)

        service = ContractValidatorService()
        result = service.validate(contract_file, impl_file)

        assert result.is_valid is False
        assert any("request body" in error.message.lower() for error in result.errors)

    def test_validate_missing_content_type(self, tmp_path):
        """Test validation when content type is missing."""
        import yaml

        contract = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {"schema": {"type": "object"}},
                                "application/xml": {"schema": {"type": "object"}}
                            }
                        },
                        "responses": {"201": {"description": "Created"}}
                    }
                }
            }
        }

        implementation = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                                # Missing application/xml
                            }
                        },
                        "responses": {"201": {"description": "Created"}}
                    }
                }
            }
        }

        contract_file = tmp_path / "contract.yaml"
        impl_file = tmp_path / "impl.yaml"

        with open(contract_file, "w") as f:
            yaml.dump(contract, f)
        with open(impl_file, "w") as f:
            yaml.dump(implementation, f)

        service = ContractValidatorService()
        result = service.validate(contract_file, impl_file)

        assert result.is_valid is False
        assert any("application/xml" in error.message for error in result.errors)


class TestContractValidatorServiceResponses:
    """Tests for response validation."""

    def test_validate_missing_response_code(self, tmp_path):
        """Test validation when response code is missing."""
        import yaml

        contract = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {"description": "Success"},
                            "404": {"description": "Not Found"}
                        }
                    }
                }
            }
        }

        implementation = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {"description": "Success"}
                            # Missing 404 response
                        }
                    }
                }
            }
        }

        contract_file = tmp_path / "contract.yaml"
        impl_file = tmp_path / "impl.yaml"

        with open(contract_file, "w") as f:
            yaml.dump(contract, f)
        with open(impl_file, "w") as f:
            yaml.dump(implementation, f)

        service = ContractValidatorService()
        result = service.validate(contract_file, impl_file)

        assert result.is_valid is False
        assert any("404" in error.message for error in result.errors)


class TestContractValidatorServiceFileLoading:
    """Tests for file loading and error handling."""

    def test_validate_invalid_contract_file(self, tmp_path):
        """Test validation with invalid contract file."""
        contract_file = tmp_path / "contract.yaml"
        contract_file.write_text("invalid: yaml: content:")

        impl_file = tmp_path / "impl.yaml"
        impl_file.write_text("openapi: 3.0.0\ninfo:\n  title: Test\n  version: 1.0.0\npaths: {}")

        service = ContractValidatorService()
        result = service.validate(contract_file, impl_file)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_invalid_implementation_file(self, tmp_path):
        """Test validation with invalid implementation file."""
        contract_file = tmp_path / "contract.yaml"
        contract_file.write_text("openapi: 3.0.0\ninfo:\n  title: Test\n  version: 1.0.0\npaths: {}")

        impl_file = tmp_path / "impl.yaml"
        impl_file.write_text("invalid: yaml: content:")

        service = ContractValidatorService()
        result = service.validate(contract_file, impl_file)

        assert result.is_valid is False
        assert len(result.errors) > 0


class TestContractValidatorServiceReportGeneration:
    """Tests for report generation."""

    def test_generate_text_report(self, tmp_path):
        """Test generating a text format report."""
        import yaml

        contract = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }

        contract_file = tmp_path / "contract.yaml"
        impl_file = tmp_path / "impl.yaml"

        with open(contract_file, "w") as f:
            yaml.dump(contract, f)
        with open(impl_file, "w") as f:
            yaml.dump(contract, f)

        service = ContractValidatorService()
        result = service.validate(contract_file, impl_file)

        report = service.generate_report(result, format="text")

        assert "Contract Validation Report" in report
        assert "Valid: Yes" in report

    def test_generate_json_report(self, tmp_path):
        """Test generating a JSON format report."""
        import json
        import yaml

        contract = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {}
        }

        contract_file = tmp_path / "contract.yaml"
        impl_file = tmp_path / "impl.yaml"

        with open(contract_file, "w") as f:
            yaml.dump(contract, f)
        with open(impl_file, "w") as f:
            yaml.dump(contract, f)

        service = ContractValidatorService()
        result = service.validate(contract_file, impl_file)

        report = service.generate_report(result, format="json")
        report_data = json.loads(report)

        assert "is_valid" in report_data

    def test_generate_markdown_report(self, tmp_path):
        """Test generating a markdown format report."""
        import yaml

        contract = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {}
        }

        contract_file = tmp_path / "contract.yaml"
        impl_file = tmp_path / "impl.yaml"

        with open(contract_file, "w") as f:
            yaml.dump(contract, f)
        with open(impl_file, "w") as f:
            yaml.dump(contract, f)

        service = ContractValidatorService()
        result = service.validate(contract_file, impl_file)

        report = service.generate_report(result, format="markdown")

        assert "# Contract Validation Report" in report
        assert "**Valid**:" in report


class TestContractValidatorServiceEdgeCases:
    """Tests for edge cases and error handling."""

    def test_validate_empty_paths(self, tmp_path):
        """Test validation with empty paths."""
        import yaml

        spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {}
        }

        contract_file = tmp_path / "contract.yaml"
        impl_file = tmp_path / "impl.yaml"

        with open(contract_file, "w") as f:
            yaml.dump(spec, f)
        with open(impl_file, "w") as f:
            yaml.dump(spec, f)

        service = ContractValidatorService()
        result = service.validate(contract_file, impl_file)

        assert result.is_valid is True

    def test_validation_result_properties(self, tmp_path):
        """Test validation result properties."""
        import yaml

        contract = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {}
        }

        contract_file = tmp_path / "contract.yaml"
        impl_file = tmp_path / "impl.yaml"

        with open(contract_file, "w") as f:
            yaml.dump(contract, f)
        with open(impl_file, "w") as f:
            yaml.dump(contract, f)

        service = ContractValidatorService()
        result = service.validate(contract_file, impl_file)

        assert result.error_count == 0
        assert result.contract_path is not None
        assert result.implementation_path is not None
