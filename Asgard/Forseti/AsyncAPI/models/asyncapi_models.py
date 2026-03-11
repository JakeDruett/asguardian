"""
AsyncAPI Models - Pydantic models for AsyncAPI specification handling.

These models represent AsyncAPI 2.x/3.x specification structures and
validation results for event-driven and message-based APIs.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AsyncAPIVersion(str, Enum):
    """Supported AsyncAPI specification versions."""
    V2_0 = "2.0.0"
    V2_1 = "2.1.0"
    V2_2 = "2.2.0"
    V2_3 = "2.3.0"
    V2_4 = "2.4.0"
    V2_5 = "2.5.0"
    V2_6 = "2.6.0"
    V3_0 = "3.0.0"


class ChannelType(str, Enum):
    """Types of message channels."""
    PUBLISH = "publish"
    SUBSCRIBE = "subscribe"


class ProtocolType(str, Enum):
    """Supported messaging protocols."""
    AMQP = "amqp"
    MQTT = "mqtt"
    KAFKA = "kafka"
    HTTP = "http"
    WEBSOCKET = "ws"
    NATS = "nats"
    REDIS = "redis"
    JMS = "jms"
    STOMP = "stomp"
    MERCURE = "mercure"


class ValidationSeverity(str, Enum):
    """Severity levels for validation errors."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class AsyncAPIConfig(BaseModel):
    """Configuration for AsyncAPI validation and processing."""

    strict_mode: bool = Field(
        default=False,
        description="Enable strict validation mode"
    )
    validate_schemas: bool = Field(
        default=True,
        description="Validate message payload schemas"
    )
    validate_examples: bool = Field(
        default=True,
        description="Validate message examples against schemas"
    )
    allow_deprecated: bool = Field(
        default=True,
        description="Allow deprecated channels and operations"
    )
    include_warnings: bool = Field(
        default=True,
        description="Include warnings in validation results"
    )
    max_errors: int = Field(
        default=100,
        description="Maximum number of errors to report"
    )
    resolve_refs: bool = Field(
        default=True,
        description="Resolve $ref references during parsing"
    )

    class Config:
        use_enum_values = True


class AsyncAPIValidationError(BaseModel):
    """Represents a single validation error or warning."""

    path: str = Field(
        description="JSON path to the error location"
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


class MessageInfo(BaseModel):
    """Information about a message in a channel."""

    name: Optional[str] = Field(
        default=None,
        description="Message name"
    )
    title: Optional[str] = Field(
        default=None,
        description="Message title"
    )
    summary: Optional[str] = Field(
        default=None,
        description="Message summary"
    )
    description: Optional[str] = Field(
        default=None,
        description="Message description"
    )
    content_type: Optional[str] = Field(
        default=None,
        alias="contentType",
        description="Default content type"
    )
    payload: Optional[dict[str, Any]] = Field(
        default=None,
        description="Message payload schema"
    )
    headers: Optional[dict[str, Any]] = Field(
        default=None,
        description="Message headers schema"
    )
    correlation_id: Optional[dict[str, Any]] = Field(
        default=None,
        alias="correlationId",
        description="Correlation ID schema"
    )
    tags: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Message tags"
    )
    bindings: Optional[dict[str, Any]] = Field(
        default=None,
        description="Protocol-specific bindings"
    )
    examples: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Message examples"
    )
    traits: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Message traits"
    )

    class Config:
        populate_by_name = True


class OperationInfo(BaseModel):
    """Information about an operation on a channel."""

    operation_id: Optional[str] = Field(
        default=None,
        alias="operationId",
        description="Operation identifier"
    )
    summary: Optional[str] = Field(
        default=None,
        description="Operation summary"
    )
    description: Optional[str] = Field(
        default=None,
        description="Operation description"
    )
    tags: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Operation tags"
    )
    external_docs: Optional[dict[str, Any]] = Field(
        default=None,
        alias="externalDocs",
        description="External documentation"
    )
    bindings: Optional[dict[str, Any]] = Field(
        default=None,
        description="Protocol-specific bindings"
    )
    traits: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Operation traits"
    )
    message: Optional[MessageInfo | list[MessageInfo]] = Field(
        default=None,
        description="Message(s) for this operation"
    )
    security: Optional[list[dict[str, list[str]]]] = Field(
        default=None,
        description="Security requirements"
    )

    class Config:
        populate_by_name = True


class Channel(BaseModel):
    """Represents an AsyncAPI channel."""

    name: str = Field(
        description="Channel name/path"
    )
    description: Optional[str] = Field(
        default=None,
        description="Channel description"
    )
    subscribe: Optional[OperationInfo] = Field(
        default=None,
        description="Subscribe operation"
    )
    publish: Optional[OperationInfo] = Field(
        default=None,
        description="Publish operation"
    )
    parameters: Optional[dict[str, Any]] = Field(
        default=None,
        description="Channel parameters"
    )
    bindings: Optional[dict[str, Any]] = Field(
        default=None,
        description="Protocol-specific bindings"
    )
    servers: Optional[list[str]] = Field(
        default=None,
        description="Servers this channel is available on"
    )

    @property
    def has_subscribe(self) -> bool:
        """Check if channel has subscribe operation."""
        return self.subscribe is not None

    @property
    def has_publish(self) -> bool:
        """Check if channel has publish operation."""
        return self.publish is not None


class ServerInfo(BaseModel):
    """Information about a server."""

    url: str = Field(
        description="Server URL"
    )
    protocol: str = Field(
        description="Protocol to use"
    )
    protocol_version: Optional[str] = Field(
        default=None,
        alias="protocolVersion",
        description="Protocol version"
    )
    description: Optional[str] = Field(
        default=None,
        description="Server description"
    )
    variables: Optional[dict[str, Any]] = Field(
        default=None,
        description="Server variables"
    )
    security: Optional[list[dict[str, list[str]]]] = Field(
        default=None,
        description="Security requirements"
    )
    bindings: Optional[dict[str, Any]] = Field(
        default=None,
        description="Protocol-specific bindings"
    )

    class Config:
        populate_by_name = True


class AsyncAPIInfo(BaseModel):
    """API information object."""

    title: str = Field(
        description="API title"
    )
    version: str = Field(
        description="API version"
    )
    description: Optional[str] = Field(
        default=None,
        description="API description"
    )
    terms_of_service: Optional[str] = Field(
        default=None,
        alias="termsOfService",
        description="Terms of service URL"
    )
    contact: Optional[dict[str, Any]] = Field(
        default=None,
        description="Contact information"
    )
    license: Optional[dict[str, Any]] = Field(
        default=None,
        description="License information"
    )

    class Config:
        populate_by_name = True


class AsyncAPISpec(BaseModel):
    """Complete AsyncAPI specification."""

    asyncapi: str = Field(
        description="AsyncAPI version string"
    )
    id: Optional[str] = Field(
        default=None,
        description="Application identifier"
    )
    info: AsyncAPIInfo = Field(
        description="API information"
    )
    servers: Optional[dict[str, ServerInfo]] = Field(
        default=None,
        description="Server definitions"
    )
    channels: dict[str, Any] = Field(
        default_factory=dict,
        description="Channel definitions"
    )
    components: Optional[dict[str, Any]] = Field(
        default=None,
        description="Reusable components"
    )
    tags: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="API tags"
    )
    external_docs: Optional[dict[str, Any]] = Field(
        default=None,
        alias="externalDocs",
        description="External documentation"
    )
    default_content_type: Optional[str] = Field(
        default=None,
        alias="defaultContentType",
        description="Default content type for messages"
    )

    class Config:
        populate_by_name = True

    @property
    def version(self) -> AsyncAPIVersion:
        """Return the AsyncAPI version as an enum."""
        if self.asyncapi.startswith("3."):
            return AsyncAPIVersion.V3_0
        elif self.asyncapi.startswith("2.6"):
            return AsyncAPIVersion.V2_6
        elif self.asyncapi.startswith("2.5"):
            return AsyncAPIVersion.V2_5
        elif self.asyncapi.startswith("2.4"):
            return AsyncAPIVersion.V2_4
        elif self.asyncapi.startswith("2.3"):
            return AsyncAPIVersion.V2_3
        elif self.asyncapi.startswith("2.2"):
            return AsyncAPIVersion.V2_2
        elif self.asyncapi.startswith("2.1"):
            return AsyncAPIVersion.V2_1
        elif self.asyncapi.startswith("2.0"):
            return AsyncAPIVersion.V2_0
        return AsyncAPIVersion.V2_6

    @property
    def channel_count(self) -> int:
        """Return the number of channels."""
        return len(self.channels)

    @property
    def server_count(self) -> int:
        """Return the number of servers."""
        return len(self.servers) if self.servers else 0


class AsyncAPIValidationResult(BaseModel):
    """Result of AsyncAPI specification validation."""

    is_valid: bool = Field(
        description="Whether the specification is valid"
    )
    spec_path: Optional[str] = Field(
        default=None,
        description="Path to the validated specification file"
    )
    asyncapi_version: Optional[AsyncAPIVersion] = Field(
        default=None,
        description="Detected AsyncAPI version"
    )
    errors: list[AsyncAPIValidationError] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    warnings: list[AsyncAPIValidationError] = Field(
        default_factory=list,
        description="List of validation warnings"
    )
    info_messages: list[AsyncAPIValidationError] = Field(
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


class AsyncAPIReport(BaseModel):
    """Comprehensive report for AsyncAPI specification analysis."""

    spec_path: Optional[str] = Field(
        default=None,
        description="Path to the specification file"
    )
    validation_result: AsyncAPIValidationResult = Field(
        description="Validation result"
    )
    spec: Optional[AsyncAPISpec] = Field(
        default=None,
        description="Parsed specification"
    )
    channels: list[Channel] = Field(
        default_factory=list,
        description="Parsed channels"
    )
    message_count: int = Field(
        default=0,
        description="Total number of messages"
    )
    protocol_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Count of channels by protocol"
    )
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="Report generation timestamp"
    )
