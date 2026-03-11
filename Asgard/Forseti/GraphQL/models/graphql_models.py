"""
GraphQL Models - Pydantic models for GraphQL schema handling.

These models represent GraphQL schema structures and validation results.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class GraphQLTypeKind(str, Enum):
    """GraphQL type kinds."""
    SCALAR = "SCALAR"
    OBJECT = "OBJECT"
    INTERFACE = "INTERFACE"
    UNION = "UNION"
    ENUM = "ENUM"
    INPUT_OBJECT = "INPUT_OBJECT"
    LIST = "LIST"
    NON_NULL = "NON_NULL"


class ValidationSeverity(str, Enum):
    """Severity levels for validation errors."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class GraphQLDirectiveLocation(str, Enum):
    """Locations where directives can be applied."""
    QUERY = "QUERY"
    MUTATION = "MUTATION"
    SUBSCRIPTION = "SUBSCRIPTION"
    FIELD = "FIELD"
    FRAGMENT_DEFINITION = "FRAGMENT_DEFINITION"
    FRAGMENT_SPREAD = "FRAGMENT_SPREAD"
    INLINE_FRAGMENT = "INLINE_FRAGMENT"
    VARIABLE_DEFINITION = "VARIABLE_DEFINITION"
    SCHEMA = "SCHEMA"
    SCALAR = "SCALAR"
    OBJECT = "OBJECT"
    FIELD_DEFINITION = "FIELD_DEFINITION"
    ARGUMENT_DEFINITION = "ARGUMENT_DEFINITION"
    INTERFACE = "INTERFACE"
    UNION = "UNION"
    ENUM = "ENUM"
    ENUM_VALUE = "ENUM_VALUE"
    INPUT_OBJECT = "INPUT_OBJECT"
    INPUT_FIELD_DEFINITION = "INPUT_FIELD_DEFINITION"


class GraphQLConfig(BaseModel):
    """Configuration for GraphQL validation and processing."""

    strict_mode: bool = Field(
        default=False,
        description="Enable strict validation mode"
    )
    validate_deprecation: bool = Field(
        default=True,
        description="Check for deprecated fields usage"
    )
    allow_introspection: bool = Field(
        default=True,
        description="Allow introspection queries"
    )
    max_depth: int = Field(
        default=10,
        description="Maximum query depth for validation"
    )
    max_complexity: int = Field(
        default=1000,
        description="Maximum query complexity score"
    )
    include_warnings: bool = Field(
        default=True,
        description="Include warnings in validation results"
    )

    class Config:
        use_enum_values = True


class GraphQLValidationError(BaseModel):
    """Represents a single validation error or warning."""

    location: Optional[str] = Field(
        default=None,
        description="Location in the schema"
    )
    message: str = Field(
        description="Human-readable error message"
    )
    severity: ValidationSeverity = Field(
        default=ValidationSeverity.ERROR,
        description="Severity level of the error"
    )
    rule: Optional[str] = Field(
        default=None,
        description="Validation rule that triggered the error"
    )
    line: Optional[int] = Field(
        default=None,
        description="Line number in source"
    )
    column: Optional[int] = Field(
        default=None,
        description="Column number in source"
    )

    class Config:
        use_enum_values = True


class GraphQLValidationResult(BaseModel):
    """Result of GraphQL schema validation."""

    is_valid: bool = Field(
        description="Whether the schema is valid"
    )
    schema_path: Optional[str] = Field(
        default=None,
        description="Path to the validated schema file"
    )
    errors: list[GraphQLValidationError] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    warnings: list[GraphQLValidationError] = Field(
        default_factory=list,
        description="List of validation warnings"
    )
    type_count: int = Field(
        default=0,
        description="Number of types in schema"
    )
    field_count: int = Field(
        default=0,
        description="Number of fields in schema"
    )
    validated_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of validation"
    )
    validation_time_ms: float = Field(
        default=0.0,
        description="Time taken to validate in milliseconds"
    )

    class Config:
        use_enum_values = True

    @property
    def error_count(self) -> int:
        """Return the number of errors."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Return the number of warnings."""
        return len(self.warnings)


class GraphQLArgument(BaseModel):
    """GraphQL field or directive argument."""

    name: str = Field(description="Argument name")
    type_name: str = Field(description="Argument type")
    description: Optional[str] = Field(default=None, description="Argument description")
    default_value: Optional[Any] = Field(default=None, description="Default value")
    is_required: bool = Field(default=False, description="Whether argument is required")


class GraphQLField(BaseModel):
    """GraphQL field definition."""

    name: str = Field(description="Field name")
    type_name: str = Field(description="Field type")
    description: Optional[str] = Field(default=None, description="Field description")
    arguments: list[GraphQLArgument] = Field(
        default_factory=list,
        description="Field arguments"
    )
    is_deprecated: bool = Field(default=False, description="Deprecated flag")
    deprecation_reason: Optional[str] = Field(
        default=None,
        description="Deprecation reason"
    )


class GraphQLType(BaseModel):
    """GraphQL type definition."""

    name: str = Field(description="Type name")
    kind: GraphQLTypeKind = Field(description="Type kind")
    description: Optional[str] = Field(default=None, description="Type description")
    fields: list[GraphQLField] = Field(
        default_factory=list,
        description="Type fields (for object/interface types)"
    )
    interfaces: list[str] = Field(
        default_factory=list,
        description="Implemented interfaces"
    )
    possible_types: list[str] = Field(
        default_factory=list,
        description="Possible types (for union/interface)"
    )
    enum_values: list[str] = Field(
        default_factory=list,
        description="Enum values (for enum types)"
    )
    input_fields: list[GraphQLField] = Field(
        default_factory=list,
        description="Input fields (for input object types)"
    )

    class Config:
        use_enum_values = True


class GraphQLDirective(BaseModel):
    """GraphQL directive definition."""

    name: str = Field(description="Directive name")
    description: Optional[str] = Field(default=None, description="Directive description")
    locations: list[GraphQLDirectiveLocation] = Field(
        default_factory=list,
        description="Valid locations"
    )
    arguments: list[GraphQLArgument] = Field(
        default_factory=list,
        description="Directive arguments"
    )
    is_repeatable: bool = Field(default=False, description="Can be applied multiple times")

    class Config:
        use_enum_values = True


class GraphQLSchema(BaseModel):
    """Complete GraphQL schema."""

    query_type: Optional[str] = Field(
        default="Query",
        description="Query type name"
    )
    mutation_type: Optional[str] = Field(
        default=None,
        description="Mutation type name"
    )
    subscription_type: Optional[str] = Field(
        default=None,
        description="Subscription type name"
    )
    types: list[GraphQLType] = Field(
        default_factory=list,
        description="All types in schema"
    )
    directives: list[GraphQLDirective] = Field(
        default_factory=list,
        description="All directives in schema"
    )
    sdl: Optional[str] = Field(
        default=None,
        description="Original SDL source"
    )

    @property
    def type_count(self) -> int:
        """Return the number of types (excluding built-ins)."""
        return len([t for t in self.types if not t.name.startswith("__")])

    @property
    def custom_types(self) -> list[GraphQLType]:
        """Return custom types (excluding built-ins)."""
        return [t for t in self.types if not t.name.startswith("__")]

    def get_type(self, name: str) -> Optional[GraphQLType]:
        """Get a type by name."""
        for t in self.types:
            if t.name == name:
                return t
        return None
