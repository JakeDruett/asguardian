"""
MockServer Models - Pydantic models for mock server generation and data.

These models represent mock server configurations, endpoints, and
generated mock data for testing API implementations.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field


class MockResponseType(str, Enum):
    """Types of mock responses."""
    STATIC = "static"
    DYNAMIC = "dynamic"
    RANDOM = "random"
    SEQUENTIAL = "sequential"


class HttpMethod(str, Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"


class DataType(str, Enum):
    """Types of data for mock generation."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    DATE = "date"
    DATETIME = "datetime"
    EMAIL = "email"
    UUID = "uuid"
    URL = "url"
    PHONE = "phone"
    NAME = "name"
    ADDRESS = "address"


class MockServerConfig(BaseModel):
    """Configuration for mock server generation."""

    host: str = Field(
        default="0.0.0.0",
        description="Host to bind the server to"
    )
    port: int = Field(
        default=8080,
        description="Port to run the server on"
    )
    base_path: str = Field(
        default="",
        description="Base path prefix for all endpoints"
    )
    response_delay_ms: int = Field(
        default=0,
        description="Artificial delay for responses in milliseconds"
    )
    enable_cors: bool = Field(
        default=True,
        description="Enable CORS headers"
    )
    enable_logging: bool = Field(
        default=True,
        description="Enable request/response logging"
    )
    validate_requests: bool = Field(
        default=False,
        description="Validate incoming requests against schema"
    )
    use_realistic_data: bool = Field(
        default=True,
        description="Generate realistic mock data"
    )
    random_seed: Optional[int] = Field(
        default=None,
        description="Random seed for reproducible data generation"
    )
    server_framework: str = Field(
        default="flask",
        description="Server framework to generate (flask, fastapi, express)"
    )

    class Config:
        use_enum_values = True


class MockDataConfig(BaseModel):
    """Configuration for mock data generation."""

    use_examples: bool = Field(
        default=True,
        description="Use examples from schema when available"
    )
    use_defaults: bool = Field(
        default=True,
        description="Use default values from schema when available"
    )
    generate_optional: bool = Field(
        default=True,
        description="Generate values for optional fields"
    )
    array_min_items: int = Field(
        default=1,
        description="Minimum items for arrays"
    )
    array_max_items: int = Field(
        default=5,
        description="Maximum items for arrays"
    )
    string_min_length: int = Field(
        default=1,
        description="Minimum length for strings"
    )
    string_max_length: int = Field(
        default=50,
        description="Maximum length for strings"
    )
    number_min: float = Field(
        default=0,
        description="Minimum for numbers"
    )
    number_max: float = Field(
        default=1000,
        description="Maximum for numbers"
    )
    locale: str = Field(
        default="en_US",
        description="Locale for generating realistic data"
    )


class MockHeader(BaseModel):
    """A mock HTTP header."""

    name: str = Field(
        description="Header name"
    )
    value: str = Field(
        description="Header value"
    )
    required: bool = Field(
        default=False,
        description="Whether the header is required"
    )


class MockResponse(BaseModel):
    """Definition of a mock response."""

    status_code: int = Field(
        default=200,
        description="HTTP status code"
    )
    content_type: str = Field(
        default="application/json",
        description="Response content type"
    )
    body: Optional[Any] = Field(
        default=None,
        description="Response body"
    )
    body_schema: Optional[dict[str, Any]] = Field(
        default=None,
        description="JSON Schema for generating response body"
    )
    headers: list[MockHeader] = Field(
        default_factory=list,
        description="Response headers"
    )
    delay_ms: Optional[int] = Field(
        default=None,
        description="Response-specific delay in milliseconds"
    )
    response_type: MockResponseType = Field(
        default=MockResponseType.DYNAMIC,
        description="Type of response generation"
    )
    probability: float = Field(
        default=1.0,
        description="Probability of this response (for random selection)"
    )

    class Config:
        use_enum_values = True


class MockParameter(BaseModel):
    """A mock endpoint parameter."""

    name: str = Field(
        description="Parameter name"
    )
    location: str = Field(
        description="Parameter location (path, query, header)"
    )
    required: bool = Field(
        default=False,
        description="Whether the parameter is required"
    )
    schema_: Optional[dict[str, Any]] = Field(
        default=None,
        alias="schema",
        description="Parameter schema"
    )
    example: Optional[Any] = Field(
        default=None,
        description="Example value"
    )

    class Config:
        populate_by_name = True


class MockRequestBody(BaseModel):
    """A mock request body definition."""

    content_type: str = Field(
        default="application/json",
        description="Request content type"
    )
    required: bool = Field(
        default=False,
        description="Whether the request body is required"
    )
    schema_: Optional[dict[str, Any]] = Field(
        default=None,
        alias="schema",
        description="Request body schema"
    )
    example: Optional[Any] = Field(
        default=None,
        description="Example request body"
    )

    class Config:
        populate_by_name = True


class MockEndpoint(BaseModel):
    """Definition of a mock API endpoint."""

    path: str = Field(
        description="Endpoint path (may include path parameters)"
    )
    method: HttpMethod = Field(
        description="HTTP method"
    )
    operation_id: Optional[str] = Field(
        default=None,
        description="Operation identifier"
    )
    summary: Optional[str] = Field(
        default=None,
        description="Endpoint summary"
    )
    description: Optional[str] = Field(
        default=None,
        description="Endpoint description"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Endpoint tags"
    )
    parameters: list[MockParameter] = Field(
        default_factory=list,
        description="Endpoint parameters"
    )
    request_body: Optional[MockRequestBody] = Field(
        default=None,
        description="Request body definition"
    )
    responses: dict[str, MockResponse] = Field(
        default_factory=dict,
        description="Response definitions by status code"
    )
    default_response: Optional[str] = Field(
        default=None,
        description="Default response status code"
    )
    security: list[dict[str, list[str]]] = Field(
        default_factory=list,
        description="Security requirements"
    )

    class Config:
        use_enum_values = True

    @property
    def path_parameters(self) -> list[MockParameter]:
        """Get path parameters."""
        return [p for p in self.parameters if p.location == "path"]

    @property
    def query_parameters(self) -> list[MockParameter]:
        """Get query parameters."""
        return [p for p in self.parameters if p.location == "query"]

    @property
    def header_parameters(self) -> list[MockParameter]:
        """Get header parameters."""
        return [p for p in self.parameters if p.location == "header"]


class MockServerDefinition(BaseModel):
    """Complete mock server definition."""

    title: str = Field(
        description="Server title"
    )
    description: Optional[str] = Field(
        default=None,
        description="Server description"
    )
    version: str = Field(
        default="1.0.0",
        description="API version"
    )
    base_url: str = Field(
        default="",
        description="Base URL for the API"
    )
    endpoints: list[MockEndpoint] = Field(
        default_factory=list,
        description="List of mock endpoints"
    )
    config: MockServerConfig = Field(
        default_factory=MockServerConfig,
        description="Server configuration"
    )
    global_headers: list[MockHeader] = Field(
        default_factory=list,
        description="Headers to add to all responses"
    )
    source_spec: Optional[str] = Field(
        default=None,
        description="Path to source specification"
    )
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="Generation timestamp"
    )

    @property
    def endpoint_count(self) -> int:
        """Return the number of endpoints."""
        return len(self.endpoints)

    def get_endpoints_by_tag(self) -> dict[str, list[MockEndpoint]]:
        """Group endpoints by tag."""
        result: dict[str, list[MockEndpoint]] = {}
        for endpoint in self.endpoints:
            tags = endpoint.tags or ["untagged"]
            for tag in tags:
                if tag not in result:
                    result[tag] = []
                result[tag].append(endpoint)
        return result


class GeneratedFile(BaseModel):
    """A generated file from mock server generation."""

    path: str = Field(
        description="Relative path for the file"
    )
    content: str = Field(
        description="File content"
    )
    file_type: str = Field(
        description="File type (python, javascript, json, etc.)"
    )
    is_entry_point: bool = Field(
        default=False,
        description="Whether this is the main entry point"
    )


class MockServerGenerationResult(BaseModel):
    """Result of mock server generation."""

    success: bool = Field(
        description="Whether generation was successful"
    )
    server_definition: MockServerDefinition = Field(
        description="The mock server definition"
    )
    generated_files: list[GeneratedFile] = Field(
        default_factory=list,
        description="Generated server files"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Generation warnings"
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Generation errors"
    )
    generation_time_ms: float = Field(
        default=0.0,
        description="Time taken for generation in milliseconds"
    )


class MockDataResult(BaseModel):
    """Result of mock data generation."""

    data: Any = Field(
        description="Generated mock data"
    )
    schema_used: Optional[dict[str, Any]] = Field(
        default=None,
        description="Schema used for generation"
    )
    generation_strategy: str = Field(
        description="Strategy used for generation"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Generation warnings"
    )
