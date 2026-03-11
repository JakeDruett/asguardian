"""
CodeGen Models - Pydantic models for API client code generation.

These models represent code generation configurations, generated files,
and generation results for various programming languages.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TargetLanguage(str, Enum):
    """Target programming languages for code generation."""
    TYPESCRIPT = "typescript"
    PYTHON = "python"
    GOLANG = "golang"
    JAVA = "java"
    CSHARP = "csharp"
    RUST = "rust"
    KOTLIN = "kotlin"
    SWIFT = "swift"


class HttpClientType(str, Enum):
    """HTTP client libraries to use in generated code."""
    # TypeScript
    FETCH = "fetch"
    AXIOS = "axios"
    # Python
    REQUESTS = "requests"
    HTTPX = "httpx"
    AIOHTTP = "aiohttp"
    # Go
    NET_HTTP = "net/http"
    RESTY = "resty"
    # Java
    OKHTTP = "okhttp"
    HTTPCLIENT = "httpclient"
    # Rust
    REQWEST = "reqwest"


class CodeStyle(str, Enum):
    """Code style preferences."""
    STANDARD = "standard"
    MINIMAL = "minimal"
    VERBOSE = "verbose"


class CodeGenConfig(BaseModel):
    """Configuration for code generation."""

    target_language: TargetLanguage = Field(
        default=TargetLanguage.TYPESCRIPT,
        description="Target programming language"
    )
    http_client: Optional[HttpClientType] = Field(
        default=None,
        description="HTTP client to use (auto-selected if None)"
    )
    output_dir: Optional[str] = Field(
        default=None,
        description="Output directory for generated files"
    )
    package_name: str = Field(
        default="api_client",
        description="Package/module name for generated code"
    )
    generate_types: bool = Field(
        default=True,
        description="Generate type definitions/interfaces"
    )
    generate_client: bool = Field(
        default=True,
        description="Generate API client class"
    )
    generate_models: bool = Field(
        default=True,
        description="Generate model classes"
    )
    use_async: bool = Field(
        default=True,
        description="Generate async/await code where supported"
    )
    include_validation: bool = Field(
        default=False,
        description="Include runtime validation"
    )
    include_documentation: bool = Field(
        default=True,
        description="Include JSDoc/docstring documentation"
    )
    strict_types: bool = Field(
        default=True,
        description="Use strict type checking"
    )
    code_style: CodeStyle = Field(
        default=CodeStyle.STANDARD,
        description="Code style preference"
    )
    custom_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Custom headers to include in all requests"
    )
    base_url_config: bool = Field(
        default=True,
        description="Make base URL configurable"
    )
    error_handling: bool = Field(
        default=True,
        description="Include error handling utilities"
    )
    retry_logic: bool = Field(
        default=False,
        description="Include retry logic for failed requests"
    )

    class Config:
        use_enum_values = True


class GeneratedFile(BaseModel):
    """A generated source code file."""

    path: str = Field(
        description="Relative path for the file"
    )
    content: str = Field(
        description="File content"
    )
    language: TargetLanguage = Field(
        description="Programming language"
    )
    file_type: str = Field(
        description="Type of file (client, model, types, util)"
    )
    line_count: int = Field(
        default=0,
        description="Number of lines in the file"
    )

    class Config:
        use_enum_values = True

    @property
    def extension(self) -> str:
        """Get file extension based on language."""
        extensions = {
            TargetLanguage.TYPESCRIPT: ".ts",
            TargetLanguage.PYTHON: ".py",
            TargetLanguage.GOLANG: ".go",
            TargetLanguage.JAVA: ".java",
            TargetLanguage.CSHARP: ".cs",
            TargetLanguage.RUST: ".rs",
            TargetLanguage.KOTLIN: ".kt",
            TargetLanguage.SWIFT: ".swift",
        }
        return extensions.get(self.language, ".txt")


class TypeDefinition(BaseModel):
    """A type/interface definition."""

    name: str = Field(
        description="Type name"
    )
    description: Optional[str] = Field(
        default=None,
        description="Type description"
    )
    properties: dict[str, "PropertyDefinition"] = Field(
        default_factory=dict,
        description="Type properties"
    )
    required_properties: list[str] = Field(
        default_factory=list,
        description="Required property names"
    )
    is_enum: bool = Field(
        default=False,
        description="Whether this is an enum type"
    )
    enum_values: list[Any] = Field(
        default_factory=list,
        description="Enum values if is_enum is True"
    )
    extends: Optional[str] = Field(
        default=None,
        description="Parent type to extend"
    )


class PropertyDefinition(BaseModel):
    """A property within a type definition."""

    name: str = Field(
        description="Property name"
    )
    type_name: str = Field(
        description="Type name"
    )
    description: Optional[str] = Field(
        default=None,
        description="Property description"
    )
    required: bool = Field(
        default=False,
        description="Whether the property is required"
    )
    nullable: bool = Field(
        default=False,
        description="Whether the property can be null"
    )
    default_value: Optional[Any] = Field(
        default=None,
        description="Default value"
    )
    format: Optional[str] = Field(
        default=None,
        description="Format hint (date, date-time, etc.)"
    )
    is_array: bool = Field(
        default=False,
        description="Whether this is an array type"
    )
    array_item_type: Optional[str] = Field(
        default=None,
        description="Type of array items"
    )


class MethodDefinition(BaseModel):
    """An API method definition."""

    name: str = Field(
        description="Method name"
    )
    http_method: str = Field(
        description="HTTP method (GET, POST, etc.)"
    )
    path: str = Field(
        description="API path"
    )
    description: Optional[str] = Field(
        default=None,
        description="Method description"
    )
    parameters: list["ParameterDefinition"] = Field(
        default_factory=list,
        description="Method parameters"
    )
    request_body_type: Optional[str] = Field(
        default=None,
        description="Request body type"
    )
    response_type: Optional[str] = Field(
        default=None,
        description="Response type"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="API tags"
    )
    deprecated: bool = Field(
        default=False,
        description="Whether the method is deprecated"
    )
    security: list[str] = Field(
        default_factory=list,
        description="Required security schemes"
    )


class ParameterDefinition(BaseModel):
    """An API parameter definition."""

    name: str = Field(
        description="Parameter name"
    )
    location: str = Field(
        description="Parameter location (path, query, header)"
    )
    type_name: str = Field(
        description="Parameter type"
    )
    description: Optional[str] = Field(
        default=None,
        description="Parameter description"
    )
    required: bool = Field(
        default=False,
        description="Whether the parameter is required"
    )
    default_value: Optional[Any] = Field(
        default=None,
        description="Default value"
    )


class CodeGenReport(BaseModel):
    """Report from code generation."""

    success: bool = Field(
        description="Whether generation was successful"
    )
    source_spec: Optional[str] = Field(
        default=None,
        description="Source specification path"
    )
    target_language: TargetLanguage = Field(
        description="Target language"
    )
    generated_files: list[GeneratedFile] = Field(
        default_factory=list,
        description="List of generated files"
    )
    types_generated: int = Field(
        default=0,
        description="Number of types generated"
    )
    methods_generated: int = Field(
        default=0,
        description="Number of methods generated"
    )
    total_lines: int = Field(
        default=0,
        description="Total lines of code generated"
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
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="Generation timestamp"
    )

    class Config:
        use_enum_values = True

    @property
    def file_count(self) -> int:
        """Get number of generated files."""
        return len(self.generated_files)


# Update forward references
TypeDefinition.model_rebuild()
