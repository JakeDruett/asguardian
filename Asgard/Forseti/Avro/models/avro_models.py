"""
Avro Models - Pydantic models for Apache Avro schema handling.

These models represent Avro schema structures and
validation results for .avsc files.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class AvroSchemaType(str, Enum):
    """Avro primitive and complex types."""
    # Primitive types
    NULL = "null"
    BOOLEAN = "boolean"
    INT = "int"
    LONG = "long"
    FLOAT = "float"
    DOUBLE = "double"
    BYTES = "bytes"
    STRING = "string"
    # Complex types
    RECORD = "record"
    ENUM = "enum"
    ARRAY = "array"
    MAP = "map"
    UNION = "union"
    FIXED = "fixed"


class ValidationSeverity(str, Enum):
    """Severity levels for validation errors."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class BreakingChangeType(str, Enum):
    """Types of breaking changes in Avro schemas."""
    REMOVED_FIELD = "removed_field"
    REMOVED_TYPE = "removed_type"
    REMOVED_ENUM_SYMBOL = "removed_enum_symbol"
    CHANGED_FIELD_TYPE = "changed_field_type"
    CHANGED_FIELD_DEFAULT = "changed_field_default"
    ADDED_REQUIRED_FIELD = "added_required_field"
    CHANGED_NAMESPACE = "changed_namespace"
    CHANGED_NAME = "changed_name"
    CHANGED_SIZE = "changed_size"
    CHANGED_ENUM_ORDER = "changed_enum_order"
    INCOMPATIBLE_UNION = "incompatible_union"


class CompatibilityLevel(str, Enum):
    """Compatibility level between schema versions."""
    FULL = "full"
    BACKWARD = "backward"
    FORWARD = "forward"
    NONE = "none"


class CompatibilityMode(str, Enum):
    """Compatibility checking mode."""
    BACKWARD = "backward"  # New schema can read old data
    FORWARD = "forward"    # Old schema can read new data
    FULL = "full"          # Both directions compatible
    NONE = "none"          # No compatibility guarantee


class AvroConfig(BaseModel):
    """Configuration for Avro validation and processing."""

    strict_mode: bool = Field(
        default=False,
        description="Enable strict validation mode"
    )
    check_naming_conventions: bool = Field(
        default=True,
        description="Check naming convention best practices"
    )
    require_doc: bool = Field(
        default=False,
        description="Require documentation on all types and fields"
    )
    require_default: bool = Field(
        default=False,
        description="Require default values on optional fields"
    )
    compatibility_mode: CompatibilityMode = Field(
        default=CompatibilityMode.BACKWARD,
        description="Default compatibility checking mode"
    )
    max_errors: int = Field(
        default=100,
        description="Maximum number of errors to report"
    )
    include_warnings: bool = Field(
        default=True,
        description="Include warnings in validation results"
    )
    allow_unknown_logical_types: bool = Field(
        default=True,
        description="Allow unknown logical types (treat as base type)"
    )

    class Config:
        use_enum_values = True


class AvroValidationError(BaseModel):
    """Represents a single validation error or warning."""

    path: str = Field(
        description="Path to the error location (e.g., 'Record.field_name')"
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
    context: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional context about the error"
    )

    class Config:
        use_enum_values = True


class AvroField(BaseModel):
    """Represents a field in an Avro record."""

    name: str = Field(
        description="Field name"
    )
    type: Any = Field(
        description="Field type (can be string, dict, or list for unions)"
    )
    default: Optional[Any] = Field(
        default=None,
        description="Default value for the field"
    )
    doc: Optional[str] = Field(
        default=None,
        description="Documentation for the field"
    )
    order: Optional[str] = Field(
        default=None,
        description="Sort order (ascending, descending, ignore)"
    )
    aliases: Optional[list[str]] = Field(
        default=None,
        description="Aliases for this field"
    )

    @property
    def is_optional(self) -> bool:
        """Check if the field is optional (has null in union)."""
        if isinstance(self.type, list):
            return "null" in self.type
        return False

    @property
    def has_default(self) -> bool:
        """Check if the field has a default value."""
        return self.default is not None


class AvroSchema(BaseModel):
    """Complete parsed Avro schema."""

    type: str = Field(
        description="Schema type"
    )
    name: Optional[str] = Field(
        default=None,
        description="Schema name (for named types)"
    )
    namespace: Optional[str] = Field(
        default=None,
        description="Namespace"
    )
    doc: Optional[str] = Field(
        default=None,
        description="Documentation"
    )
    fields: Optional[list[AvroField]] = Field(
        default=None,
        description="Fields (for record types)"
    )
    symbols: Optional[list[str]] = Field(
        default=None,
        description="Enum symbols"
    )
    items: Optional[Any] = Field(
        default=None,
        description="Array item type"
    )
    values: Optional[Any] = Field(
        default=None,
        description="Map value type"
    )
    size: Optional[int] = Field(
        default=None,
        description="Fixed type size"
    )
    aliases: Optional[list[str]] = Field(
        default=None,
        description="Aliases for this type"
    )
    logical_type: Optional[str] = Field(
        default=None,
        alias="logicalType",
        description="Logical type annotation"
    )
    raw_schema: Optional[dict[str, Any]] = Field(
        default=None,
        description="Original raw schema"
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Path to the schema file"
    )

    class Config:
        populate_by_name = True

    @property
    def full_name(self) -> str:
        """Return the fully qualified name."""
        if self.namespace and self.name:
            return f"{self.namespace}.{self.name}"
        return self.name or self.type

    @property
    def field_count(self) -> int:
        """Return the number of fields."""
        return len(self.fields) if self.fields else 0


class AvroValidationResult(BaseModel):
    """Result of Avro schema validation."""

    is_valid: bool = Field(
        description="Whether the schema is valid"
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Path to the validated schema file"
    )
    schema_type: Optional[str] = Field(
        default=None,
        description="Detected schema type"
    )
    parsed_schema: Optional[AvroSchema] = Field(
        default=None,
        description="Parsed schema if validation succeeded"
    )
    errors: list[AvroValidationError] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    warnings: list[AvroValidationError] = Field(
        default_factory=list,
        description="List of validation warnings"
    )
    info_messages: list[AvroValidationError] = Field(
        default_factory=list,
        description="List of informational messages"
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

    @property
    def total_issues(self) -> int:
        """Return total number of issues (errors + warnings)."""
        return self.error_count + self.warning_count


class BreakingChange(BaseModel):
    """Represents a breaking change between schema versions."""

    change_type: BreakingChangeType = Field(
        description="Type of breaking change"
    )
    path: str = Field(
        description="Path to the changed element"
    )
    message: str = Field(
        description="Human-readable description of the change"
    )
    old_value: Optional[str] = Field(
        default=None,
        description="Old value before the change"
    )
    new_value: Optional[str] = Field(
        default=None,
        description="New value after the change"
    )
    severity: str = Field(
        default="error",
        description="Severity of the breaking change"
    )
    mitigation: Optional[str] = Field(
        default=None,
        description="Suggested mitigation for the breaking change"
    )

    class Config:
        use_enum_values = True


class AvroCompatibilityResult(BaseModel):
    """Result of Avro schema compatibility check."""

    is_compatible: bool = Field(
        description="Whether the schemas are compatible"
    )
    compatibility_level: CompatibilityLevel = Field(
        description="Level of compatibility"
    )
    compatibility_mode: CompatibilityMode = Field(
        default=CompatibilityMode.BACKWARD,
        description="Mode of compatibility check performed"
    )
    source_file: Optional[str] = Field(
        default=None,
        description="Path to the old schema file"
    )
    target_file: Optional[str] = Field(
        default=None,
        description="Path to the new schema file"
    )
    breaking_changes: list[BreakingChange] = Field(
        default_factory=list,
        description="List of breaking changes"
    )
    warnings: list[BreakingChange] = Field(
        default_factory=list,
        description="List of compatibility warnings"
    )
    added_fields: list[str] = Field(
        default_factory=list,
        description="List of added fields"
    )
    removed_fields: list[str] = Field(
        default_factory=list,
        description="List of removed fields"
    )
    modified_fields: list[str] = Field(
        default_factory=list,
        description="List of modified fields"
    )
    check_time_ms: float = Field(
        default=0.0,
        description="Time taken for compatibility check in milliseconds"
    )
    checked_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of compatibility check"
    )

    class Config:
        use_enum_values = True

    @property
    def breaking_change_count(self) -> int:
        """Return the number of breaking changes."""
        return len(self.breaking_changes)

    @property
    def warning_count(self) -> int:
        """Return the number of warnings."""
        return len(self.warnings)
