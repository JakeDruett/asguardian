"""
Protobuf Models - Pydantic models for Protocol Buffer schema handling.

These models represent Protobuf specification structures and
validation results for proto2 and proto3 files.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProtobufSyntaxVersion(str, Enum):
    """Supported Protobuf syntax versions."""
    PROTO2 = "proto2"
    PROTO3 = "proto3"


class ValidationSeverity(str, Enum):
    """Severity levels for validation errors."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class BreakingChangeType(str, Enum):
    """Types of breaking changes in Protobuf schemas."""
    REMOVED_FIELD = "removed_field"
    REMOVED_MESSAGE = "removed_message"
    REMOVED_ENUM = "removed_enum"
    REMOVED_ENUM_VALUE = "removed_enum_value"
    REMOVED_SERVICE = "removed_service"
    REMOVED_RPC = "removed_rpc"
    CHANGED_FIELD_TYPE = "changed_field_type"
    CHANGED_FIELD_NUMBER = "changed_field_number"
    CHANGED_FIELD_LABEL = "changed_field_label"
    CHANGED_ENUM_VALUE_NUMBER = "changed_enum_value_number"
    RESERVED_FIELD_REUSED = "reserved_field_reused"
    RESERVED_NUMBER_REUSED = "reserved_number_reused"


class CompatibilityLevel(str, Enum):
    """Compatibility level between schema versions."""
    FULL = "full"
    BACKWARD = "backward"
    FORWARD = "forward"
    NONE = "none"


class ProtobufConfig(BaseModel):
    """Configuration for Protobuf validation and processing."""

    strict_mode: bool = Field(
        default=False,
        description="Enable strict validation mode"
    )
    check_naming_conventions: bool = Field(
        default=True,
        description="Check naming convention best practices"
    )
    check_field_numbers: bool = Field(
        default=True,
        description="Validate field number ranges and recommendations"
    )
    check_reserved_fields: bool = Field(
        default=True,
        description="Validate reserved field declarations"
    )
    allow_proto2: bool = Field(
        default=True,
        description="Allow proto2 syntax files"
    )
    require_package: bool = Field(
        default=True,
        description="Require package declaration"
    )
    max_errors: int = Field(
        default=100,
        description="Maximum number of errors to report"
    )
    include_warnings: bool = Field(
        default=True,
        description="Include warnings in validation results"
    )

    class Config:
        use_enum_values = True


class ProtobufValidationError(BaseModel):
    """Represents a single validation error or warning."""

    path: str = Field(
        description="Path to the error location (e.g., 'Message.field_name')"
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
        description="Line number in the proto file"
    )
    context: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional context about the error"
    )

    class Config:
        use_enum_values = True


class ProtobufField(BaseModel):
    """Represents a field in a Protobuf message."""

    name: str = Field(
        description="Field name"
    )
    number: int = Field(
        description="Field number"
    )
    type: str = Field(
        description="Field type (e.g., 'int32', 'string', 'MyMessage')"
    )
    label: Optional[str] = Field(
        default=None,
        description="Field label (optional, required, repeated)"
    )
    default_value: Optional[str] = Field(
        default=None,
        description="Default value for the field"
    )
    options: Optional[dict[str, Any]] = Field(
        default=None,
        description="Field options"
    )
    oneof_group: Optional[str] = Field(
        default=None,
        description="Name of the oneof group if applicable"
    )
    map_key_type: Optional[str] = Field(
        default=None,
        description="Key type for map fields"
    )
    map_value_type: Optional[str] = Field(
        default=None,
        description="Value type for map fields"
    )


class ProtobufEnum(BaseModel):
    """Represents an enum definition in Protobuf."""

    name: str = Field(
        description="Enum name"
    )
    values: dict[str, int] = Field(
        default_factory=dict,
        description="Enum values mapping name to number"
    )
    options: Optional[dict[str, Any]] = Field(
        default=None,
        description="Enum options"
    )
    allow_alias: bool = Field(
        default=False,
        description="Whether allow_alias option is set"
    )
    reserved_names: list[str] = Field(
        default_factory=list,
        description="Reserved enum value names"
    )
    reserved_numbers: list[int] = Field(
        default_factory=list,
        description="Reserved enum value numbers"
    )


class ProtobufMessage(BaseModel):
    """Represents a message definition in Protobuf."""

    name: str = Field(
        description="Message name"
    )
    fields: list[ProtobufField] = Field(
        default_factory=list,
        description="Message fields"
    )
    nested_messages: list["ProtobufMessage"] = Field(
        default_factory=list,
        description="Nested message definitions"
    )
    nested_enums: list[ProtobufEnum] = Field(
        default_factory=list,
        description="Nested enum definitions"
    )
    oneofs: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Oneof definitions mapping name to field names"
    )
    reserved_names: list[str] = Field(
        default_factory=list,
        description="Reserved field names"
    )
    reserved_numbers: list[int] = Field(
        default_factory=list,
        description="Reserved field numbers"
    )
    reserved_ranges: list[tuple[int, int]] = Field(
        default_factory=list,
        description="Reserved field number ranges"
    )
    options: Optional[dict[str, Any]] = Field(
        default=None,
        description="Message options"
    )


class ProtobufService(BaseModel):
    """Represents a service definition in Protobuf."""

    name: str = Field(
        description="Service name"
    )
    rpcs: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="RPC definitions mapping name to input/output types"
    )
    options: Optional[dict[str, Any]] = Field(
        default=None,
        description="Service options"
    )


class ProtobufSchema(BaseModel):
    """Complete parsed Protobuf schema."""

    syntax: ProtobufSyntaxVersion = Field(
        default=ProtobufSyntaxVersion.PROTO3,
        description="Protobuf syntax version"
    )
    package: Optional[str] = Field(
        default=None,
        description="Package name"
    )
    imports: list[str] = Field(
        default_factory=list,
        description="Import statements"
    )
    public_imports: list[str] = Field(
        default_factory=list,
        description="Public import statements"
    )
    messages: list[ProtobufMessage] = Field(
        default_factory=list,
        description="Top-level message definitions"
    )
    enums: list[ProtobufEnum] = Field(
        default_factory=list,
        description="Top-level enum definitions"
    )
    services: list[ProtobufService] = Field(
        default_factory=list,
        description="Service definitions"
    )
    options: Optional[dict[str, Any]] = Field(
        default=None,
        description="File-level options"
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Path to the proto file"
    )

    class Config:
        use_enum_values = True

    @property
    def message_count(self) -> int:
        """Return the number of messages (including nested)."""
        count = len(self.messages)
        for msg in self.messages:
            count += self._count_nested_messages(msg)
        return count

    def _count_nested_messages(self, message: ProtobufMessage) -> int:
        """Count nested messages recursively."""
        count = len(message.nested_messages)
        for nested in message.nested_messages:
            count += self._count_nested_messages(nested)
        return count

    @property
    def enum_count(self) -> int:
        """Return the number of enums."""
        return len(self.enums)

    @property
    def service_count(self) -> int:
        """Return the number of services."""
        return len(self.services)


class ProtobufValidationResult(BaseModel):
    """Result of Protobuf schema validation."""

    is_valid: bool = Field(
        description="Whether the schema is valid"
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Path to the validated proto file"
    )
    syntax_version: Optional[ProtobufSyntaxVersion] = Field(
        default=None,
        description="Detected syntax version"
    )
    parsed_schema: Optional[ProtobufSchema] = Field(
        default=None,
        description="Parsed schema if validation succeeded"
    )
    errors: list[ProtobufValidationError] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    warnings: list[ProtobufValidationError] = Field(
        default_factory=list,
        description="List of validation warnings"
    )
    info_messages: list[ProtobufValidationError] = Field(
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


class ProtobufCompatibilityResult(BaseModel):
    """Result of Protobuf schema compatibility check."""

    is_compatible: bool = Field(
        description="Whether the schemas are compatible"
    )
    compatibility_level: CompatibilityLevel = Field(
        description="Level of compatibility"
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
    added_messages: list[str] = Field(
        default_factory=list,
        description="List of added message types"
    )
    removed_messages: list[str] = Field(
        default_factory=list,
        description="List of removed message types"
    )
    modified_messages: list[str] = Field(
        default_factory=list,
        description="List of modified message types"
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
