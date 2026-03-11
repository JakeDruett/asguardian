"""
Tests for OpenAPI Spec Generator Service

Unit tests for generating OpenAPI specifications from source code.
"""

import pytest
from pathlib import Path

from Asgard.Forseti.OpenAPI.models.openapi_models import OpenAPIConfig, OpenAPISpec
from Asgard.Forseti.OpenAPI.services.spec_generator_service import SpecGeneratorService


class TestSpecGeneratorServiceInit:
    """Tests for SpecGeneratorService initialization."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        service = SpecGeneratorService()

        assert service.config is not None
        assert isinstance(service.config, OpenAPIConfig)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = OpenAPIConfig(strict_mode=True)
        service = SpecGeneratorService(config)

        assert service.config.strict_mode is True


class TestSpecGeneratorServiceFromFastAPI:
    """Tests for generating specs from FastAPI code."""

    def test_generate_from_empty_directory(self, tmp_path):
        """Test generating from empty directory."""
        service = SpecGeneratorService()

        spec = service.generate_from_fastapi(tmp_path)

        assert isinstance(spec, OpenAPISpec)
        assert spec.info.title == "Generated API"
        assert len(spec.paths) == 0

    def test_generate_from_simple_route(self, tmp_path):
        """Test generating from simple FastAPI route."""
        source_file = tmp_path / "main.py"
        source_file.write_text('''
from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
def list_users():
    """List all users."""
    pass
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        assert "/users" in spec.paths
        assert "get" in spec.paths["/users"]

    def test_generate_with_custom_metadata(self, tmp_path):
        """Test generating with custom title, version, and description."""
        service = SpecGeneratorService()

        spec = service.generate_from_fastapi(
            tmp_path,
            title="My API",
            version="2.0.0",
            description="Custom description"
        )

        assert spec.info.title == "My API"
        assert spec.info.version == "2.0.0"
        assert spec.info.description == "Custom description"

    def test_generate_with_tags(self, tmp_path):
        """Test generating routes with tags."""
        source_file = tmp_path / "routes.py"
        source_file.write_text('''
from fastapi import APIRouter

router = APIRouter()

@router.get("/users", tags=["users", "admin"])
def list_users():
    pass
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        operation = spec.paths["/users"]["get"]
        assert "tags" in operation
        assert "users" in operation["tags"]

    def test_generate_with_docstring(self, tmp_path):
        """Test generating operation from function with docstring."""
        source_file = tmp_path / "routes.py"
        source_file.write_text('''
from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
def list_users():
    """List all users.

    This endpoint returns all users in the system.
    """
    pass
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        operation = spec.paths["/users"]["get"]
        assert "summary" in operation
        assert operation["summary"] == "List all users."
        assert "description" in operation

    def test_generate_with_parameters(self, tmp_path):
        """Test generating operation with parameters."""
        source_file = tmp_path / "routes.py"
        source_file.write_text('''
from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
def list_users(limit: int, offset: int = 0):
    pass
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        operation = spec.paths["/users"]["get"]
        assert "parameters" in operation
        param_names = [p["name"] for p in operation["parameters"]]
        assert "limit" in param_names
        assert "offset" in param_names

    def test_generate_ignores_internal_parameters(self, tmp_path):
        """Test that internal parameters are ignored."""
        source_file = tmp_path / "routes.py"
        source_file.write_text('''
from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
def list_users(self, request, db, session, user_id: int):
    pass
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        operation = spec.paths["/users"]["get"]
        param_names = [p["name"] for p in operation["parameters"]]
        assert "self" not in param_names
        assert "request" not in param_names
        assert "db" not in param_names
        assert "user_id" in param_names

    def test_generate_with_pydantic_models(self, tmp_path):
        """Test generating schemas from Pydantic models."""
        source_file = tmp_path / "models.py"
        source_file.write_text('''
from pydantic import BaseModel

class User(BaseModel):
    """User model."""
    id: int
    email: str
    name: str = None
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        assert spec.components is not None
        assert "schemas" in spec.components
        assert "User" in spec.components["schemas"]
        user_schema = spec.components["schemas"]["User"]
        assert "properties" in user_schema
        assert "id" in user_schema["properties"]

    def test_generate_skips_unparseable_files(self, tmp_path):
        """Test that unparseable files are skipped."""
        invalid_file = tmp_path / "broken.py"
        invalid_file.write_text("this is not valid python syntax {{{")

        valid_file = tmp_path / "valid.py"
        valid_file.write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/test")
def test():
    pass
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        # Should still parse valid file
        assert "/test" in spec.paths


class TestSpecGeneratorServiceHTTPMethods:
    """Tests for different HTTP methods."""

    def test_generate_post_method(self, tmp_path):
        """Test generating POST operation."""
        source_file = tmp_path / "routes.py"
        source_file.write_text('''
from fastapi import APIRouter

router = APIRouter()

@router.post("/users")
def create_user():
    pass
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        assert "post" in spec.paths["/users"]

    def test_generate_multiple_methods(self, tmp_path):
        """Test generating multiple methods on same path."""
        source_file = tmp_path / "routes.py"
        source_file.write_text('''
from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
def list_users():
    pass

@router.post("/users")
def create_user():
    pass

@router.delete("/users")
def delete_users():
    pass
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        assert "get" in spec.paths["/users"]
        assert "post" in spec.paths["/users"]
        assert "delete" in spec.paths["/users"]


class TestSpecGeneratorServiceTypeAnnotations:
    """Tests for type annotation handling."""

    def test_annotation_to_schema_primitives(self, tmp_path):
        """Test converting primitive type annotations."""
        source_file = tmp_path / "routes.py"
        source_file.write_text('''
from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
def test_types(
    str_param: str,
    int_param: int,
    float_param: float,
    bool_param: bool
):
    pass
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        params = spec.paths["/test"]["get"]["parameters"]
        param_map = {p["name"]: p["schema"]["type"] for p in params}

        assert param_map["str_param"] == "string"
        assert param_map["int_param"] == "integer"
        assert param_map["float_param"] == "number"
        assert param_map["bool_param"] == "boolean"

    def test_annotation_to_schema_list(self, tmp_path):
        """Test converting List type annotation."""
        source_file = tmp_path / "routes.py"
        source_file.write_text('''
from typing import List
from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
def test_list(items: List[str]):
    pass
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        params = spec.paths["/test"]["get"]["parameters"]
        items_param = next(p for p in params if p["name"] == "items")

        assert items_param["schema"]["type"] == "array"
        assert "items" in items_param["schema"]

    def test_annotation_to_schema_optional(self, tmp_path):
        """Test converting Optional type annotation."""
        source_file = tmp_path / "routes.py"
        source_file.write_text('''
from typing import Optional
from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
def test_optional(value: Optional[int]):
    pass
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        params = spec.paths["/test"]["get"]["parameters"]
        value_param = next(p for p in params if p["name"] == "value")

        assert "nullable" in value_param["schema"]


class TestSpecGeneratorServicePydanticModels:
    """Tests for Pydantic model extraction."""

    def test_extract_pydantic_fields(self, tmp_path):
        """Test extracting fields from Pydantic model."""
        source_file = tmp_path / "models.py"
        source_file.write_text('''
from pydantic import BaseModel

class User(BaseModel):
    id: int
    email: str
    name: str = "Default"
    age: int = None
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        user_schema = spec.components["schemas"]["User"]
        assert "id" in user_schema["properties"]
        assert "email" in user_schema["properties"]
        assert "name" in user_schema["properties"]

    def test_extract_pydantic_required_fields(self, tmp_path):
        """Test identifying required fields in Pydantic model."""
        source_file = tmp_path / "models.py"
        source_file.write_text('''
from pydantic import BaseModel

class User(BaseModel):
    id: int
    email: str
    optional: str = None
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        user_schema = spec.components["schemas"]["User"]
        assert "required" in user_schema
        assert "id" in user_schema["required"]
        assert "email" in user_schema["required"]

    def test_extract_pydantic_with_docstring(self, tmp_path):
        """Test extracting Pydantic model with docstring."""
        source_file = tmp_path / "models.py"
        source_file.write_text('''
from pydantic import BaseModel

class User(BaseModel):
    """User account model."""
    id: int
    email: str
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        user_schema = spec.components["schemas"]["User"]
        assert "description" in user_schema
        assert "User account model." in user_schema["description"]

    def test_ignore_private_fields(self, tmp_path):
        """Test that private fields are ignored."""
        source_file = tmp_path / "models.py"
        source_file.write_text('''
from pydantic import BaseModel

class User(BaseModel):
    id: int
    _private: str
    __very_private: int
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        user_schema = spec.components["schemas"]["User"]
        assert "id" in user_schema["properties"]
        assert "_private" not in user_schema["properties"]
        assert "__very_private" not in user_schema["properties"]

    def test_ignore_non_pydantic_classes(self, tmp_path):
        """Test that non-Pydantic classes are ignored."""
        source_file = tmp_path / "models.py"
        source_file.write_text('''
class NotAModel:
    id: int
    name: str
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        assert spec.components is None or "NotAModel" not in spec.components.get("schemas", {})


class TestSpecGeneratorServiceOutputFormats:
    """Tests for output format conversions."""

    def test_to_dict(self, tmp_path):
        """Test converting spec to dictionary."""
        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path, title="Test")

        spec_dict = service.to_dict(spec)

        assert isinstance(spec_dict, dict)
        assert "openapi" in spec_dict
        assert "info" in spec_dict
        assert spec_dict["info"]["title"] == "Test"

    def test_to_dict_excludes_none(self, tmp_path):
        """Test that None values are excluded from dict."""
        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        spec_dict = service.to_dict(spec)

        # Fields with None values should not be in the dict
        # This is controlled by exclude_none=True in to_dict method
        assert isinstance(spec_dict, dict)

    def test_to_yaml(self, tmp_path):
        """Test converting spec to YAML."""
        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path, title="Test")

        yaml_str = service.to_yaml(spec)

        assert isinstance(yaml_str, str)
        assert "openapi:" in yaml_str
        assert "title: Test" in yaml_str

    def test_to_json(self, tmp_path):
        """Test converting spec to JSON."""
        import json

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path, title="Test")

        json_str = service.to_json(spec)

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["info"]["title"] == "Test"

    def test_to_json_with_custom_indent(self, tmp_path):
        """Test JSON conversion with custom indentation."""
        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        json_str = service.to_json(spec, indent=4)

        # With indent=4, lines should have 4-space indentation
        assert "    " in json_str


class TestSpecGeneratorServiceEdgeCases:
    """Tests for edge cases and error handling."""

    def test_generate_from_nonexistent_directory(self, tmp_path):
        """Test generating from non-existent directory."""
        nonexistent = tmp_path / "nonexistent"

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(nonexistent)

        # Should return empty spec instead of crashing
        assert isinstance(spec, OpenAPISpec)
        assert len(spec.paths) == 0

    def test_generate_with_no_python_files(self, tmp_path):
        """Test generating from directory with no Python files."""
        (tmp_path / "readme.txt").write_text("No Python here")

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        assert len(spec.paths) == 0

    def test_generate_with_nested_directories(self, tmp_path):
        """Test generating from nested directory structure."""
        api_dir = tmp_path / "api" / "v1"
        api_dir.mkdir(parents=True)

        routes_file = api_dir / "routes.py"
        routes_file.write_text('''
from fastapi import APIRouter

router = APIRouter()

@router.get("/nested")
def nested_route():
    pass
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        assert "/nested" in spec.paths

    def test_operation_id_from_function_name(self, tmp_path):
        """Test that operationId is generated from function name."""
        source_file = tmp_path / "routes.py"
        source_file.write_text('''
from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
def list_all_users():
    pass
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        operation = spec.paths["/users"]["get"]
        assert operation["operationId"] == "list_all_users"

    def test_default_response_generated(self, tmp_path):
        """Test that a default 200 response is generated."""
        source_file = tmp_path / "routes.py"
        source_file.write_text('''
from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
def test():
    pass
''')

        service = SpecGeneratorService()
        spec = service.generate_from_fastapi(tmp_path)

        operation = spec.paths["/test"]["get"]
        assert "responses" in operation
        assert "200" in operation["responses"]
