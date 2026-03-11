"""
Forseti AsyncAPI Module - AsyncAPI Specification Management

This module provides comprehensive AsyncAPI specification handling including:
- Specification validation against AsyncAPI standards
- Specification parsing and normalization
- Support for AsyncAPI 2.x and 3.x versions

Usage:
    from Asgard.Forseti.AsyncAPI import AsyncAPIValidatorService, AsyncAPIConfig

    # Validate an AsyncAPI specification
    service = AsyncAPIValidatorService()
    result = service.validate("asyncapi.yaml")
    print(f"Valid: {result.is_valid}")
    for error in result.errors:
        print(f"  - {error.message}")

    # Parse a specification
    from Asgard.Forseti.AsyncAPI import AsyncAPIParserService
    parser = AsyncAPIParserService()
    spec = parser.parse("asyncapi.yaml")
    print(f"Title: {spec.info.title}")
    for channel in parser.get_channels():
        print(f"Channel: {channel.name}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

# Import models
from Asgard.Forseti.AsyncAPI.models import (
    AsyncAPIConfig,
    AsyncAPIInfo,
    AsyncAPIReport,
    AsyncAPISpec,
    AsyncAPIValidationError,
    AsyncAPIValidationResult,
    AsyncAPIVersion,
    Channel,
    ChannelType,
    MessageInfo,
    OperationInfo,
    ProtocolType,
    ServerInfo,
    ValidationSeverity,
)

# Import services
from Asgard.Forseti.AsyncAPI.services import (
    AsyncAPIParserService,
    AsyncAPIValidatorService,
)

__all__ = [
    # Models
    "AsyncAPIConfig",
    "AsyncAPIInfo",
    "AsyncAPIReport",
    "AsyncAPISpec",
    "AsyncAPIValidationError",
    "AsyncAPIValidationResult",
    "AsyncAPIVersion",
    "Channel",
    "ChannelType",
    "MessageInfo",
    "OperationInfo",
    "ProtocolType",
    "ServerInfo",
    "ValidationSeverity",
    # Services
    "AsyncAPIParserService",
    "AsyncAPIValidatorService",
]
