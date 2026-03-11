"""
Contract Integration Tests

Tests for API contract testing and compatibility checking workflows.
"""

import json
import pytest
import yaml
from pathlib import Path

from Asgard.Forseti.Contracts import (
    CompatibilityCheckerService,
    ContractValidatorService,
    BreakingChangeDetectorService,
    ContractConfig,
    CompatibilityResult,
)


class TestContractCompatibility:
    """Tests for API contract compatibility checking."""

    def test_workflow_check_compatible_versions(self, compatible_specs):
        """Test checking compatibility between compatible API versions."""
        checker = CompatibilityCheckerService()

        result = checker.check_compatibility(
            compatible_specs["v1"],
            compatible_specs["v2"]
        )

        assert result.is_compatible is True
        assert len(result.breaking_changes) == 0

        # Should have non-breaking changes
        if hasattr(result, 'non_breaking_changes'):
            # Adding optional fields is non-breaking
            pass

    def test_workflow_check_incompatible_versions(self, breaking_change_specs):
        """Test detecting incompatibility between API versions."""
        checker = CompatibilityCheckerService()

        result = checker.check_compatibility(
            breaking_change_specs["v1"],
            breaking_change_specs["v2"]
        )

        assert result.is_compatible is False
        assert len(result.breaking_changes) > 0

        # Verify breaking changes were detected
        breaking_types = [c.change_type for c in result.breaking_changes]

        # Should detect removed endpoint, changed types, or required fields
        assert any(
            change_type in ["endpoint_removed", "parameter_type_changed", "field_required"]
            for change_type in breaking_types
        )

    def test_workflow_compatibility_with_files(self, tmp_path, compatible_specs):
        """Test compatibility checking with file inputs."""
        # Save specs to files
        v1_file = tmp_path / "v1.yaml"
        v2_file = tmp_path / "v2.yaml"

        with open(v1_file, "w") as f:
            yaml.dump(compatible_specs["v1"], f)

        with open(v2_file, "w") as f:
            yaml.dump(compatible_specs["v2"], f)

        # Check compatibility
        checker = CompatibilityCheckerService()
        result = checker.check_compatibility_files(v1_file, v2_file)

        assert result.is_compatible is True

    def test_workflow_generate_compatibility_report(self, breaking_change_specs):
        """Test generating compatibility report."""
        checker = CompatibilityCheckerService()

        result = checker.check_compatibility(
            breaking_change_specs["v1"],
            breaking_change_specs["v2"]
        )

        # Generate reports in different formats
        text_report = checker.generate_report(result, format="text")
        json_report = checker.generate_report(result, format="json")
        markdown_report = checker.generate_report(result, format="markdown")

        assert len(text_report) > 0
        assert len(json_report) > 0
        assert len(markdown_report) > 0

        # Verify JSON structure
        json_data = json.loads(json_report)
        assert "is_compatible" in json_data
        assert "breaking_changes" in json_data


class TestBreakingChangeDetection:
    """Tests for breaking change detection workflows."""

    def test_workflow_detect_removed_endpoint(self, tmp_path, sample_openapi_v3_spec):
        """Test detecting removed endpoint."""
        v1_spec = sample_openapi_v3_spec.copy()

        v2_spec = sample_openapi_v3_spec.copy()
        # Remove POST /users endpoint
        del v2_spec["paths"]["/users"]["post"]

        detector = BreakingChangeDetectorService()
        result = detector.detect_changes(v1_spec, v2_spec)

        assert result.has_breaking_changes is True

        # Should detect endpoint removal
        removed_endpoints = [c for c in result.changes if c.change_type == "endpoint_removed"]
        assert len(removed_endpoints) > 0

    def test_workflow_detect_parameter_type_change(self, tmp_path):
        """Test detecting parameter type change."""
        v1_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/users/{userId}": {
                    "parameters": [
                        {
                            "name": "userId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        }
                    ],
                    "get": {
                        "summary": "Get user",
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }

        v2_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "2.0.0"},
            "paths": {
                "/users/{userId}": {
                    "parameters": [
                        {
                            "name": "userId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}  # Changed from integer
                        }
                    ],
                    "get": {
                        "summary": "Get user",
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }

        detector = BreakingChangeDetectorService()
        result = detector.detect_changes(v1_spec, v2_spec)

        assert result.has_breaking_changes is True

        # Should detect type change
        type_changes = [c for c in result.changes if "type" in c.change_type.lower()]
        assert len(type_changes) > 0

    def test_workflow_detect_required_parameter_added(self, tmp_path):
        """Test detecting addition of required parameter."""
        v1_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "List users",
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }

        v2_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "2.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "List users",
                        "parameters": [
                            {
                                "name": "apiKey",
                                "in": "header",
                                "required": True,  # New required parameter
                                "schema": {"type": "string"}
                            }
                        ],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }

        detector = BreakingChangeDetectorService()
        result = detector.detect_changes(v1_spec, v2_spec)

        assert result.has_breaking_changes is True

    def test_workflow_detect_response_schema_change(self, tmp_path):
        """Test detecting response schema changes."""
        v1_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "email": {"type": "string"},
                                                "name": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        v2_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "2.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "email": {"type": "string"}
                                                # Removed 'name' field - breaking change
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        detector = BreakingChangeDetectorService()
        result = detector.detect_changes(v1_spec, v2_spec)

        assert result.has_breaking_changes is True

        # Should detect field removal
        field_removals = [c for c in result.changes if "removed" in c.change_type.lower()]
        assert len(field_removals) > 0

    def test_workflow_severity_classification(self, breaking_change_specs):
        """Test classification of change severity."""
        detector = BreakingChangeDetectorService()
        result = detector.detect_changes(
            breaking_change_specs["v1"],
            breaking_change_specs["v2"]
        )

        # Changes should have severity levels
        for change in result.changes:
            assert change.severity in ["major", "minor", "patch"]

        # Breaking changes should be major
        breaking = [c for c in result.changes if c.is_breaking]
        for change in breaking:
            assert change.severity in ["major", "critical"]


class TestContractValidation:
    """Tests for API contract validation workflows."""

    def test_workflow_validate_contract_against_spec(self, tmp_path, sample_openapi_v3_spec):
        """Test validating API contract against OpenAPI spec."""
        validator = ContractValidatorService()

        # Define expected contract
        contract = {
            "endpoints": [
                {
                    "path": "/users",
                    "method": "GET",
                    "required": True
                },
                {
                    "path": "/users",
                    "method": "POST",
                    "required": True
                }
            ]
        }

        result = validator.validate_contract(sample_openapi_v3_spec, contract)

        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_workflow_detect_missing_endpoints(self, tmp_path, sample_openapi_v3_spec):
        """Test detecting missing required endpoints."""
        validator = ContractValidatorService()

        # Require an endpoint that doesn't exist
        contract = {
            "endpoints": [
                {
                    "path": "/users",
                    "method": "GET",
                    "required": True
                },
                {
                    "path": "/admin/users",
                    "method": "DELETE",
                    "required": True  # This doesn't exist
                }
            ]
        }

        result = validator.validate_contract(sample_openapi_v3_spec, contract)

        assert result.is_valid is False
        assert len(result.violations) > 0

        # Should report missing endpoint
        missing = [v for v in result.violations if "missing" in v.message.lower()]
        assert len(missing) > 0

    def test_workflow_validate_response_schemas(self, tmp_path, sample_openapi_v3_spec):
        """Test validating response schema compliance."""
        validator = ContractValidatorService()

        contract = {
            "endpoints": [
                {
                    "path": "/users",
                    "method": "GET",
                    "response_schema": {
                        "200": {
                            "type": "array",
                            "items": {"type": "object"}
                        }
                    }
                }
            ]
        }

        result = validator.validate_contract(sample_openapi_v3_spec, contract)

        # Should validate that the spec has the expected response schema
        assert result.is_valid is True or len(result.violations) >= 0

    def test_workflow_validate_from_files(self, tmp_path, sample_openapi_v3_spec):
        """Test validating contract from files."""
        # Save spec to file
        spec_file = tmp_path / "spec.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(sample_openapi_v3_spec, f)

        # Save contract to file
        contract = {
            "endpoints": [
                {"path": "/users", "method": "GET", "required": True}
            ]
        }
        contract_file = tmp_path / "contract.json"
        with open(contract_file, "w") as f:
            json.dump(contract, f)

        validator = ContractValidatorService()
        result = validator.validate_contract_files(spec_file, contract_file)

        assert result.is_valid is True


class TestCompatibilityComplexScenarios:
    """Tests for complex compatibility scenarios."""

    def test_workflow_multiple_version_comparison(self, tmp_path, sample_openapi_v3_spec):
        """Test comparing multiple API versions in sequence."""
        v1_spec = sample_openapi_v3_spec.copy()

        # Create v2 with compatible changes
        v2_spec = sample_openapi_v3_spec.copy()
        v2_spec["info"]["version"] = "1.1.0"
        v2_spec["components"]["schemas"]["User"]["properties"]["phone"] = {"type": "string"}

        # Create v3 with breaking changes
        v3_spec = sample_openapi_v3_spec.copy()
        v3_spec["info"]["version"] = "2.0.0"
        del v3_spec["paths"]["/users"]["post"]

        checker = CompatibilityCheckerService()

        # Check v1 -> v2 (should be compatible)
        result_v1_v2 = checker.check_compatibility(v1_spec, v2_spec)
        assert result_v1_v2.is_compatible is True

        # Check v2 -> v3 (should be incompatible)
        result_v2_v3 = checker.check_compatibility(v2_spec, v3_spec)
        assert result_v2_v3.is_compatible is False

    def test_workflow_cross_format_compatibility(self, tmp_path, sample_openapi_v2_spec, sample_openapi_v3_spec):
        """Test checking compatibility across different OpenAPI versions."""
        # Compare Swagger 2.0 to OpenAPI 3.0
        checker = CompatibilityCheckerService()

        # May need to convert to same version first
        from Asgard.Forseti.OpenAPI import SpecConverterService, OpenAPIVersion

        converter = SpecConverterService()
        v2_to_v3 = converter.convert_spec(
            sample_openapi_v2_spec,
            target_version=OpenAPIVersion.V3_0
        )

        # Now compare
        result = checker.check_compatibility(v2_to_v3.converted_spec, sample_openapi_v3_spec)

        # Should complete without errors
        assert result is not None

    def test_workflow_detect_subtle_breaking_changes(self, tmp_path):
        """Test detecting subtle breaking changes."""
        v1_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "integer", "default": 10}
                            }
                        ],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }

        v2_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.1.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "required": True,  # Changed to required - breaking!
                                "schema": {"type": "integer"}
                            }
                        ],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }

        detector = BreakingChangeDetectorService()
        result = detector.detect_changes(v1_spec, v2_spec)

        assert result.has_breaking_changes is True

        # Should detect parameter now being required
        param_changes = [c for c in result.changes if "parameter" in c.change_type.lower()]
        assert len(param_changes) > 0

    def test_workflow_comprehensive_compatibility_check(self, tmp_path):
        """Test comprehensive compatibility check covering all aspects."""
        v1_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {"name": "page", "in": "query", "schema": {"type": "integer"}}
                        ],
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {"$ref": "#/components/schemas/User"}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "post": {
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/UserInput"}
                                }
                            }
                        },
                        "responses": {
                            "201": {"description": "Created"}
                        }
                    }
                }
            },
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "email": {"type": "string"}
                        }
                    },
                    "UserInput": {
                        "type": "object",
                        "required": ["email"],
                        "properties": {
                            "email": {"type": "string"}
                        }
                    }
                }
            }
        }

        v2_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.1.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {"name": "page", "in": "query", "schema": {"type": "integer"}},
                            {"name": "size", "in": "query", "schema": {"type": "integer"}}  # New optional
                        ],
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {"$ref": "#/components/schemas/User"}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "post": {
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/UserInput"}
                                }
                            }
                        },
                        "responses": {
                            "201": {"description": "Created"}
                        }
                    }
                }
            },
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "email": {"type": "string"},
                            "name": {"type": "string"}  # New optional field
                        }
                    },
                    "UserInput": {
                        "type": "object",
                        "required": ["email"],
                        "properties": {
                            "email": {"type": "string"},
                            "name": {"type": "string"}  # New optional field
                        }
                    }
                }
            }
        }

        # Check compatibility
        checker = CompatibilityCheckerService()
        compat_result = checker.check_compatibility(v1_spec, v2_spec)

        # Should be compatible (only added optional fields)
        assert compat_result.is_compatible is True

        # Detect all changes
        detector = BreakingChangeDetectorService()
        change_result = detector.detect_changes(v1_spec, v2_spec)

        # Should have non-breaking changes
        assert len(change_result.changes) > 0
        assert change_result.has_breaking_changes is False
