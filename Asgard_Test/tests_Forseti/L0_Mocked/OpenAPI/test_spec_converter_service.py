"""
Tests for OpenAPI Spec Converter Service

Unit tests for converting between OpenAPI specification versions.
"""

import pytest
from pathlib import Path

from Asgard.Forseti.OpenAPI.models.openapi_models import OpenAPIConfig, OpenAPIVersion
from Asgard.Forseti.OpenAPI.services.spec_converter_service import SpecConverterService


class TestSpecConverterServiceInit:
    """Tests for SpecConverterService initialization."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        service = SpecConverterService()

        assert service.config is not None
        assert isinstance(service.config, OpenAPIConfig)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = OpenAPIConfig(strict_mode=True)
        service = SpecConverterService(config)

        assert service.config.strict_mode is True


class TestSpecConverterServiceConvertFile:
    """Tests for converting specification files."""

    def test_convert_nonexistent_file(self, tmp_path):
        """Test converting a file that doesn't exist."""
        service = SpecConverterService()
        nonexistent_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            service.convert(nonexistent_file, OpenAPIVersion.V3_1)

    def test_convert_swagger_2_file_to_3_0(self, tmp_path):
        """Test converting Swagger 2.0 file to OpenAPI 3.0."""
        import yaml

        swagger_spec = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "host": "api.test.com",
            "basePath": "/",
            "paths": {}
        }
        spec_file = tmp_path / "swagger.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(swagger_spec, f)

        service = SpecConverterService()
        converted = service.convert(spec_file, OpenAPIVersion.V3_0)

        assert converted["openapi"].startswith("3.0")
        assert "swagger" not in converted


class TestSpecConverterServiceConvertData:
    """Tests for converting specification dictionaries."""

    def test_convert_same_version_returns_unchanged(self, sample_openapi_v3_spec):
        """Test converting to same version returns unchanged spec."""
        service = SpecConverterService()

        converted = service.convert_data(sample_openapi_v3_spec, OpenAPIVersion.V3_0)

        assert converted == sample_openapi_v3_spec

    def test_convert_2_to_3_0(self, sample_openapi_v2_spec):
        """Test converting Swagger 2.0 to OpenAPI 3.0."""
        service = SpecConverterService()

        converted = service.convert_data(sample_openapi_v2_spec, OpenAPIVersion.V3_0)

        assert converted["openapi"] == "3.0.3"
        assert "swagger" not in converted
        assert "servers" in converted
        assert "components" in converted

    def test_convert_2_to_3_1(self, sample_openapi_v2_spec):
        """Test converting Swagger 2.0 to OpenAPI 3.1."""
        service = SpecConverterService()

        converted = service.convert_data(sample_openapi_v2_spec, OpenAPIVersion.V3_1)

        assert converted["openapi"] == "3.1.0"

    def test_convert_3_0_to_2_0(self, sample_openapi_v3_spec):
        """Test converting OpenAPI 3.0 to Swagger 2.0."""
        service = SpecConverterService()

        converted = service.convert_data(sample_openapi_v3_spec, OpenAPIVersion.V2_0)

        assert converted["swagger"] == "2.0"
        assert "openapi" not in converted
        assert "host" in converted
        assert "definitions" in converted

    def test_convert_3_0_to_3_1(self):
        """Test converting OpenAPI 3.0 to 3.1."""
        service = SpecConverterService()
        spec_3_0 = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {}
        }

        converted = service.convert_data(spec_3_0, OpenAPIVersion.V3_1)

        assert converted["openapi"] == "3.1.0"

    def test_convert_3_1_to_3_0(self):
        """Test converting OpenAPI 3.1 to 3.0."""
        service = SpecConverterService()
        spec_3_1 = {
            "openapi": "3.1.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {}
        }

        converted = service.convert_data(spec_3_1, OpenAPIVersion.V3_0)

        assert converted["openapi"] == "3.0.3"

    def test_convert_3_1_to_2_0(self):
        """Test converting OpenAPI 3.1 to Swagger 2.0."""
        service = SpecConverterService()
        spec_3_1 = {
            "openapi": "3.1.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "servers": [{"url": "https://api.test.com/v1"}],
            "paths": {}
        }

        converted = service.convert_data(spec_3_1, OpenAPIVersion.V2_0)

        assert converted["swagger"] == "2.0"


class TestSpecConverterServiceSwagger2To3:
    """Tests for Swagger 2.0 to OpenAPI 3.0 conversion specifics."""

    def test_convert_host_basepath_to_servers(self):
        """Test conversion of host and basePath to servers."""
        service = SpecConverterService()
        swagger = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "host": "api.example.com",
            "basePath": "/v2",
            "schemes": ["https"],
            "paths": {}
        }

        converted = service.convert_data(swagger, OpenAPIVersion.V3_0)

        assert "servers" in converted
        assert converted["servers"][0]["url"] == "https://api.example.com/v2"

    def test_convert_multiple_schemes(self):
        """Test conversion with multiple schemes."""
        service = SpecConverterService()
        swagger = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "host": "api.test.com",
            "basePath": "/",
            "schemes": ["http", "https"],
            "paths": {}
        }

        converted = service.convert_data(swagger, OpenAPIVersion.V3_0)

        assert len(converted["servers"]) == 2

    def test_convert_definitions_to_schemas(self):
        """Test conversion of definitions to components/schemas."""
        service = SpecConverterService()
        swagger = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "host": "api.test.com",
            "paths": {},
            "definitions": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"}
                    }
                }
            }
        }

        converted = service.convert_data(swagger, OpenAPIVersion.V3_0)

        assert "components" in converted
        assert "schemas" in converted["components"]
        assert "User" in converted["components"]["schemas"]

    def test_convert_ref_paths(self):
        """Test conversion of $ref paths."""
        service = SpecConverterService()
        swagger = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "host": "api.test.com",
            "paths": {},
            "definitions": {
                "User": {
                    "type": "object",
                    "properties": {
                        "related": {"$ref": "#/definitions/Related"}
                    }
                },
                "Related": {"type": "object"}
            }
        }

        converted = service.convert_data(swagger, OpenAPIVersion.V3_0)

        user_schema = converted["components"]["schemas"]["User"]
        assert "$ref" in user_schema["properties"]["related"]
        assert "#/components/schemas/" in user_schema["properties"]["related"]["$ref"]

    def test_convert_body_parameter_to_request_body(self):
        """Test conversion of body parameters to requestBody."""
        service = SpecConverterService()
        swagger = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "host": "api.test.com",
            "paths": {
                "/users": {
                    "post": {
                        "parameters": [
                            {
                                "name": "body",
                                "in": "body",
                                "required": True,
                                "schema": {"$ref": "#/definitions/User"}
                            }
                        ],
                        "responses": {"201": {"description": "Created"}}
                    }
                }
            },
            "definitions": {"User": {"type": "object"}}
        }

        converted = service.convert_data(swagger, OpenAPIVersion.V3_0)

        post_op = converted["paths"]["/users"]["post"]
        assert "requestBody" in post_op
        assert post_op["requestBody"]["required"] is True
        assert "content" in post_op["requestBody"]

    def test_convert_formdata_to_request_body(self):
        """Test conversion of formData parameters."""
        service = SpecConverterService()
        swagger = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "host": "api.test.com",
            "paths": {
                "/upload": {
                    "post": {
                        "consumes": ["multipart/form-data"],
                        "parameters": [
                            {
                                "name": "file",
                                "in": "formData",
                                "type": "file",
                                "required": True
                            },
                            {
                                "name": "description",
                                "in": "formData",
                                "type": "string"
                            }
                        ],
                        "responses": {"200": {"description": "OK"}}
                    }
                }
            }
        }

        converted = service.convert_data(swagger, OpenAPIVersion.V3_0)

        post_op = converted["paths"]["/upload"]["post"]
        assert "requestBody" in post_op

    def test_convert_query_parameter(self):
        """Test conversion of query parameters."""
        service = SpecConverterService()
        swagger = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "host": "api.test.com",
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 100
                            }
                        ],
                        "responses": {"200": {"description": "OK"}}
                    }
                }
            }
        }

        converted = service.convert_data(swagger, OpenAPIVersion.V3_0)

        get_op = converted["paths"]["/users"]["get"]
        param = get_op["parameters"][0]
        assert "schema" in param
        assert param["schema"]["type"] == "integer"

    def test_convert_response_with_schema(self):
        """Test conversion of responses with schemas."""
        service = SpecConverterService()
        swagger = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "host": "api.test.com",
            "paths": {
                "/users": {
                    "get": {
                        "produces": ["application/json"],
                        "responses": {
                            "200": {
                                "description": "Success",
                                "schema": {"type": "array"}
                            }
                        }
                    }
                }
            }
        }

        converted = service.convert_data(swagger, OpenAPIVersion.V3_0)

        response = converted["paths"]["/users"]["get"]["responses"]["200"]
        assert "content" in response
        assert "application/json" in response["content"]


class TestSpecConverterServiceOpenAPI3To2:
    """Tests for OpenAPI 3.0 to Swagger 2.0 conversion."""

    def test_convert_servers_to_host_basepath(self):
        """Test conversion of servers to host and basePath."""
        service = SpecConverterService()
        spec_3 = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com/v1"}],
            "paths": {}
        }

        converted = service.convert_data(spec_3, OpenAPIVersion.V2_0)

        assert converted["host"] == "api.example.com"
        assert converted["basePath"] == "/v1"
        assert converted["schemes"] == ["https"]

    def test_convert_components_to_definitions(self):
        """Test conversion of components/schemas to definitions."""
        service = SpecConverterService()
        spec_3 = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "User": {"type": "object"}
                }
            }
        }

        converted = service.convert_data(spec_3, OpenAPIVersion.V2_0)

        assert "definitions" in converted
        assert "User" in converted["definitions"]

    def test_convert_request_body_to_parameter(self):
        """Test conversion of requestBody to body parameter."""
        service = SpecConverterService()
        spec_3 = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
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

        converted = service.convert_data(spec_3, OpenAPIVersion.V2_0)

        post_op = converted["paths"]["/users"]["post"]
        assert "parameters" in post_op
        body_param = next(p for p in post_op["parameters"] if p["in"] == "body")
        assert body_param["required"] is True


class TestSpecConverterServiceOpenAPI30To31:
    """Tests for OpenAPI 3.0 to 3.1 conversion."""

    def test_convert_nullable_to_type_array(self):
        """Test conversion of nullable: true to type arrays."""
        service = SpecConverterService()
        spec_30 = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "nullable": True
                            }
                        }
                    }
                }
            }
        }

        converted = service.convert_data(spec_30, OpenAPIVersion.V3_1)

        name_prop = converted["components"]["schemas"]["User"]["properties"]["name"]
        assert isinstance(name_prop["type"], list)
        assert "null" in name_prop["type"]
        assert "nullable" not in name_prop


class TestSpecConverterServiceOpenAPI31To30:
    """Tests for OpenAPI 3.1 to 3.0 conversion."""

    def test_convert_type_array_to_nullable(self):
        """Test conversion of type arrays to nullable: true."""
        service = SpecConverterService()
        spec_31 = {
            "openapi": "3.1.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": ["string", "null"]
                            }
                        }
                    }
                }
            }
        }

        converted = service.convert_data(spec_31, OpenAPIVersion.V3_0)

        name_prop = converted["components"]["schemas"]["User"]["properties"]["name"]
        assert name_prop["type"] == "string"
        assert name_prop["nullable"] is True


class TestSpecConverterServiceSave:
    """Tests for saving converted specifications."""

    def test_save_converted_spec(self, tmp_path, sample_openapi_v2_spec):
        """Test saving a converted specification to file."""
        service = SpecConverterService()
        converted = service.convert_data(sample_openapi_v2_spec, OpenAPIVersion.V3_0)

        output_file = tmp_path / "converted.yaml"
        service.save(output_file, converted)

        assert output_file.exists()

    def test_save_as_json(self, tmp_path, sample_openapi_v3_spec):
        """Test saving as JSON file."""
        import json

        service = SpecConverterService()

        output_file = tmp_path / "spec.json"
        service.save(output_file, sample_openapi_v3_spec)

        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
        assert data["openapi"] == sample_openapi_v3_spec["openapi"]


class TestSpecConverterServiceEdgeCases:
    """Tests for edge cases and error handling."""

    def test_convert_empty_spec(self):
        """Test converting empty specification."""
        service = SpecConverterService()
        with pytest.raises(Exception):
            service.convert_data({}, OpenAPIVersion.V3_0)

    def test_convert_preserves_metadata(self):
        """Test that conversion preserves metadata like tags."""
        service = SpecConverterService()
        swagger = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "host": "api.test.com",
            "paths": {},
            "tags": [{"name": "users", "description": "User ops"}],
            "externalDocs": {"url": "https://docs.test.com"}
        }

        converted = service.convert_data(swagger, OpenAPIVersion.V3_0)

        assert "tags" in converted
        assert "externalDocs" in converted

    def test_convert_preserves_security(self):
        """Test that global security is preserved."""
        service = SpecConverterService()
        swagger = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "host": "api.test.com",
            "paths": {},
            "security": [{"apiKey": []}],
            "securityDefinitions": {
                "apiKey": {"type": "apiKey", "name": "X-API-Key", "in": "header"}
            }
        }

        converted = service.convert_data(swagger, OpenAPIVersion.V3_0)

        assert "security" in converted
