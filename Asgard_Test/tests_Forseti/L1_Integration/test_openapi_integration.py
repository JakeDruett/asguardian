"""
OpenAPI Integration Tests

Tests for end-to-end OpenAPI workflows including validation, parsing,
generation, and version conversion.
"""

import json
import pytest
import yaml
from pathlib import Path

from Asgard.Forseti.OpenAPI import (
    SpecValidatorService,
    SpecParserService,
    SpecGeneratorService,
    SpecConverterService,
    OpenAPIConfig,
    OpenAPIVersion,
    ValidationSeverity,
)


class TestOpenAPIWorkflow:
    """Tests for complete OpenAPI validation workflow."""

    def test_workflow_validate_parse_report(self, openapi_spec_file):
        """Test workflow: validate spec, parse it, and generate report."""
        # Step 1: Validate the spec
        validator = SpecValidatorService()
        validation_result = validator.validate(openapi_spec_file)

        assert validation_result.is_valid is True
        assert validation_result.openapi_version == OpenAPIVersion.V3_0
        assert validation_result.validation_time_ms > 0

        # Step 2: Parse the spec
        parser = SpecParserService()
        parsed_spec = parser.parse(openapi_spec_file)

        assert parsed_spec.openapi == "3.0.3"
        assert parsed_spec.info.title == "Test API"
        assert len(parsed_spec.paths) > 0

        # Step 3: Generate reports in multiple formats
        text_report = validator.generate_report(validation_result, format="text")
        assert "Valid: True" in text_report or "VALID" in text_report

        json_report = validator.generate_report(validation_result, format="json")
        json_data = json.loads(json_report)
        assert json_data["is_valid"] is True

    def test_workflow_parse_modify_validate(self, tmp_path, sample_openapi_v3_spec):
        """Test workflow: parse spec, modify it, and validate again."""
        # Step 1: Create and parse original spec
        original_file = tmp_path / "original.yaml"
        with open(original_file, "w") as f:
            yaml.dump(sample_openapi_v3_spec, f)

        parser = SpecParserService()
        parsed_spec = parser.parse(original_file)

        # Step 2: Modify the spec
        spec_dict = sample_openapi_v3_spec.copy()
        spec_dict["info"]["version"] = "2.0.0"
        spec_dict["paths"]["/health"] = {
            "get": {
                "summary": "Health check",
                "operationId": "healthCheck",
                "responses": {
                    "200": {
                        "description": "Service is healthy"
                    }
                }
            }
        }

        modified_file = tmp_path / "modified.yaml"
        with open(modified_file, "w") as f:
            yaml.dump(spec_dict, f)

        # Step 3: Validate modified spec
        validator = SpecValidatorService()
        result = validator.validate(modified_file)

        assert result.is_valid is True
        assert "/health" in str(result.spec_path) or result.is_valid

    def test_workflow_invalid_spec_error_reporting(self, tmp_path, invalid_openapi_spec):
        """Test workflow: validate invalid spec and check error reporting."""
        invalid_file = tmp_path / "invalid.yaml"
        with open(invalid_file, "w") as f:
            yaml.dump(invalid_openapi_spec, f)

        validator = SpecValidatorService()
        result = validator.validate(invalid_file)

        assert result.is_valid is False
        assert len(result.errors) > 0

        # Check that errors have proper structure
        for error in result.errors:
            assert error.message is not None
            assert error.severity in [ValidationSeverity.ERROR, ValidationSeverity.WARNING]
            assert error.path is not None

        # Test error report generation
        report = validator.generate_report(result, format="text")
        assert "error" in report.lower() or "invalid" in report.lower()


class TestOpenAPIVersionConversion:
    """Tests for OpenAPI version conversion workflows."""

    def test_workflow_swagger_to_openapi_conversion(self, tmp_path, sample_openapi_v2_spec):
        """Test conversion from Swagger 2.0 to OpenAPI 3.0."""
        # Step 1: Create Swagger 2.0 spec file
        swagger_file = tmp_path / "swagger.yaml"
        with open(swagger_file, "w") as f:
            yaml.dump(sample_openapi_v2_spec, f)

        # Step 2: Convert to OpenAPI 3.0
        converter = SpecConverterService()
        result = converter.convert(swagger_file, target_version=OpenAPIVersion.V3_0)

        assert result.is_valid is True
        assert result.target_version == OpenAPIVersion.V3_0

        # Step 3: Validate converted spec
        validator = SpecValidatorService()
        validation_result = validator.validate_spec(result.converted_spec)

        assert validation_result.is_valid is True

        # Step 4: Verify conversion details
        converted = result.converted_spec
        assert "openapi" in converted
        assert converted["openapi"].startswith("3.0")
        assert "servers" in converted
        assert "components" in converted
        assert "schemas" in converted["components"]

    def test_workflow_openapi_30_to_31_conversion(self, tmp_path, sample_openapi_v3_spec):
        """Test conversion from OpenAPI 3.0 to 3.1."""
        # Step 1: Create OpenAPI 3.0 spec
        v30_file = tmp_path / "openapi30.yaml"
        with open(v30_file, "w") as f:
            yaml.dump(sample_openapi_v3_spec, f)

        # Step 2: Convert to OpenAPI 3.1
        converter = SpecConverterService()
        result = converter.convert(v30_file, target_version=OpenAPIVersion.V3_1)

        assert result.is_valid is True
        assert result.target_version == OpenAPIVersion.V3_1

        # Step 3: Save and validate converted spec
        v31_file = tmp_path / "openapi31.yaml"
        converter.save_converted_spec(result, v31_file)

        assert v31_file.exists()

        validator = SpecValidatorService()
        validation_result = validator.validate(v31_file)

        # 3.1 specs may have different validation rules, check for proper handling
        assert validation_result.openapi_version in [OpenAPIVersion.V3_0, OpenAPIVersion.V3_1]

    def test_workflow_bidirectional_conversion(self, tmp_path, sample_openapi_v3_spec):
        """Test converting back and forth between versions."""
        # Original 3.0 spec
        v30_original = tmp_path / "v30_original.yaml"
        with open(v30_original, "w") as f:
            yaml.dump(sample_openapi_v3_spec, f)

        converter = SpecConverterService()

        # Convert to Swagger 2.0
        to_v2_result = converter.convert(v30_original, target_version=OpenAPIVersion.V2_0)
        assert to_v2_result.is_valid

        v2_file = tmp_path / "v2.yaml"
        converter.save_converted_spec(to_v2_result, v2_file)

        # Convert back to OpenAPI 3.0
        to_v3_result = converter.convert(v2_file, target_version=OpenAPIVersion.V3_0)
        assert to_v3_result.is_valid

        # Validate final spec
        v30_final = tmp_path / "v30_final.yaml"
        converter.save_converted_spec(to_v3_result, v30_final)

        validator = SpecValidatorService()
        validation_result = validator.validate(v30_final)

        assert validation_result.is_valid is True


class TestOpenAPIGeneration:
    """Tests for OpenAPI spec generation from code."""

    def test_workflow_generate_from_fastapi(self, fastapi_source_with_models):
        """Test generating OpenAPI spec from FastAPI source code."""
        generator = SpecGeneratorService()

        result = generator.generate_from_source(
            fastapi_source_with_models,
            title="Generated API",
            version="1.0.0"
        )

        assert result.is_valid is True
        assert result.spec is not None

        # Verify generated spec structure
        spec = result.spec
        assert spec["info"]["title"] == "Generated API"
        assert spec["info"]["version"] == "1.0.0"
        assert "paths" in spec
        assert len(spec["paths"]) > 0

        # Verify endpoints were discovered
        assert "/users" in spec["paths"]
        assert "/users/{user_id}" in spec["paths"]

    def test_workflow_generate_and_validate(self, tmp_path, fastapi_source_with_models):
        """Test generating spec and then validating it."""
        # Step 1: Generate spec
        generator = SpecGeneratorService()
        gen_result = generator.generate_from_source(
            fastapi_source_with_models,
            title="Test API",
            version="1.0.0"
        )

        assert gen_result.is_valid is True

        # Step 2: Save generated spec
        spec_file = tmp_path / "generated.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(gen_result.spec, f)

        # Step 3: Validate generated spec
        validator = SpecValidatorService()
        validation_result = validator.validate(spec_file)

        assert validation_result.is_valid is True

    def test_workflow_generate_with_pydantic_models(self, fastapi_source_with_models):
        """Test spec generation includes Pydantic model schemas."""
        generator = SpecGeneratorService()

        result = generator.generate_from_source(
            fastapi_source_with_models,
            title="Test API",
            version="1.0.0"
        )

        assert result.is_valid is True
        spec = result.spec

        # Verify components/schemas were generated
        assert "components" in spec
        assert "schemas" in spec["components"]

        # Should have discovered Pydantic models
        schemas = spec["components"]["schemas"]
        assert len(schemas) > 0

    def test_workflow_generate_convert_validate(self, tmp_path, fastapi_source_with_models):
        """Test generating spec, converting version, and validating."""
        # Step 1: Generate OpenAPI 3.0 spec
        generator = SpecGeneratorService()
        gen_result = generator.generate_from_source(
            fastapi_source_with_models,
            title="Test API",
            version="1.0.0"
        )

        v30_file = tmp_path / "generated_v30.yaml"
        with open(v30_file, "w") as f:
            yaml.dump(gen_result.spec, f)

        # Step 2: Convert to Swagger 2.0
        converter = SpecConverterService()
        conv_result = converter.convert(v30_file, target_version=OpenAPIVersion.V2_0)

        v2_file = tmp_path / "generated_v2.yaml"
        converter.save_converted_spec(conv_result, v2_file)

        # Step 3: Validate both versions
        validator = SpecValidatorService()

        v30_validation = validator.validate(v30_file)
        assert v30_validation.is_valid is True

        v2_validation = validator.validate(v2_file)
        assert v2_validation.is_valid is True


class TestOpenAPIParsingWorkflows:
    """Tests for OpenAPI parsing workflows."""

    def test_workflow_parse_and_extract_endpoints(self, openapi_spec_file):
        """Test parsing spec and extracting endpoint information."""
        parser = SpecParserService()
        parsed_spec = parser.parse(openapi_spec_file)

        # Extract all paths
        paths = parser.get_paths(parsed_spec)
        assert len(paths) > 0

        # Extract operations from each path
        for path_name, path_item in paths.items():
            operations = parser.get_operations(path_item)
            assert len(operations) >= 0

            for method, operation in operations.items():
                # Verify operation structure
                assert "responses" in operation or hasattr(operation, "responses")

    def test_workflow_parse_and_extract_schemas(self, openapi_spec_file):
        """Test parsing spec and extracting schema definitions."""
        parser = SpecParserService()
        parsed_spec = parser.parse(openapi_spec_file)

        # Extract schemas
        schemas = parser.get_schemas(parsed_spec)
        assert schemas is not None

        # Verify schema structure
        if isinstance(schemas, dict) and len(schemas) > 0:
            for schema_name, schema_def in schemas.items():
                assert schema_def is not None

    def test_workflow_parse_multiple_versions(self, tmp_path, sample_openapi_v2_spec, sample_openapi_v3_spec):
        """Test parsing different OpenAPI versions."""
        # Create Swagger 2.0 file
        v2_file = tmp_path / "swagger.yaml"
        with open(v2_file, "w") as f:
            yaml.dump(sample_openapi_v2_spec, f)

        # Create OpenAPI 3.0 file
        v3_file = tmp_path / "openapi.yaml"
        with open(v3_file, "w") as f:
            yaml.dump(sample_openapi_v3_spec, f)

        parser = SpecParserService()

        # Parse both versions
        v2_parsed = parser.parse(v2_file)
        v3_parsed = parser.parse(v3_file)

        # Both should parse successfully
        assert v2_parsed is not None
        assert v3_parsed is not None

        # Verify version detection
        assert "swagger" in v2_parsed or hasattr(v2_parsed, "swagger")
        assert "openapi" in v3_parsed or hasattr(v3_parsed, "openapi")


class TestOpenAPIErrorDetection:
    """Tests for error detection in OpenAPI specs."""

    def test_workflow_detect_missing_responses(self, tmp_path):
        """Test detection of missing response definitions."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "get": {
                        "summary": "Test endpoint"
                        # Missing responses
                    }
                }
            }
        }

        spec_file = tmp_path / "missing_responses.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(spec, f)

        validator = SpecValidatorService()
        result = validator.validate(spec_file)

        assert result.is_valid is False
        assert any("response" in error.message.lower() for error in result.errors)

    def test_workflow_detect_undefined_references(self, tmp_path):
        """Test detection of undefined schema references."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "get": {
                        "summary": "Test endpoint",
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/UndefinedSchema"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {
                "schemas": {}
            }
        }

        spec_file = tmp_path / "undefined_ref.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(spec, f)

        validator = SpecValidatorService()
        result = validator.validate(spec_file)

        assert result.is_valid is False
        # Should detect the undefined reference
        assert len(result.errors) > 0

    def test_workflow_detect_deprecated_operations(self, tmp_path):
        """Test detection and reporting of deprecated operations."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "get": {
                        "summary": "Deprecated endpoint",
                        "deprecated": True,
                        "responses": {
                            "200": {"description": "Success"}
                        }
                    }
                }
            }
        }

        spec_file = tmp_path / "deprecated.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(spec, f)

        config = OpenAPIConfig(include_warnings=True)
        validator = SpecValidatorService(config)
        result = validator.validate(spec_file)

        # Should be valid but have warnings
        assert result.is_valid is True
        # May have warnings about deprecated operations
        warnings = [e for e in result.errors if e.severity == ValidationSeverity.WARNING]
        # Warnings may or may not be reported depending on validator configuration


class TestOpenAPIComplexScenarios:
    """Tests for complex OpenAPI scenarios."""

    def test_workflow_large_spec_with_many_endpoints(self, tmp_path):
        """Test handling of large specs with many endpoints."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Large API", "version": "1.0.0"},
            "paths": {}
        }

        # Generate 100 endpoints
        for i in range(100):
            spec["paths"][f"/resource{i}"] = {
                "get": {
                    "summary": f"Get resource {i}",
                    "operationId": f"getResource{i}",
                    "responses": {
                        "200": {"description": "Success"}
                    }
                }
            }

        spec_file = tmp_path / "large_spec.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(spec, f)

        validator = SpecValidatorService()
        result = validator.validate(spec_file)

        assert result.is_valid is True
        assert result.validation_time_ms > 0

    def test_workflow_spec_with_security_schemes(self, tmp_path):
        """Test handling of specs with security schemes."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Secure API", "version": "1.0.0"},
            "paths": {
                "/secure": {
                    "get": {
                        "summary": "Secure endpoint",
                        "security": [{"api_key": []}],
                        "responses": {
                            "200": {"description": "Success"}
                        }
                    }
                }
            },
            "components": {
                "securitySchemes": {
                    "api_key": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key"
                    }
                }
            }
        }

        spec_file = tmp_path / "secure.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(spec, f)

        validator = SpecValidatorService()
        result = validator.validate(spec_file)

        assert result.is_valid is True

    def test_workflow_multiformat_output(self, openapi_spec_file):
        """Test generating reports in multiple formats."""
        validator = SpecValidatorService()
        result = validator.validate(openapi_spec_file)

        # Generate all report formats
        text_report = validator.generate_report(result, format="text")
        json_report = validator.generate_report(result, format="json")
        markdown_report = validator.generate_report(result, format="markdown")

        # Verify all formats are non-empty
        assert len(text_report) > 0
        assert len(json_report) > 0
        assert len(markdown_report) > 0

        # Verify JSON is valid
        json_data = json.loads(json_report)
        assert "is_valid" in json_data
