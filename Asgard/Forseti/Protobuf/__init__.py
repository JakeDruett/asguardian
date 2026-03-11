"""
Forseti Protobuf Module - Protocol Buffer Schema Management

This module provides comprehensive Protocol Buffer specification handling including:
- Specification validation against Protobuf syntax standards
- Best practices checking for proto files
- Backward compatibility checking between proto versions
- Support for proto2 and proto3 syntax

Usage:
    from Asgard.Forseti.Protobuf import ProtobufValidatorService, ProtobufConfig

    # Validate a proto file
    service = ProtobufValidatorService()
    result = service.validate("schema.proto")
    print(f"Valid: {result.is_valid}")
    for error in result.errors:
        print(f"  - {error.message}")

    # Check compatibility between versions
    from Asgard.Forseti.Protobuf import ProtobufCompatibilityService
    compat_service = ProtobufCompatibilityService()
    result = compat_service.check("old.proto", "new.proto")
    print(f"Compatible: {result.is_compatible}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

# Import models
from Asgard.Forseti.Protobuf.models import (
    ProtobufConfig,
    ProtobufSchema,
    ProtobufValidationError,
    ProtobufValidationResult,
    ProtobufCompatibilityResult,
    ProtobufSyntaxVersion,
    ProtobufField,
    ProtobufMessage,
    ProtobufEnum,
    ProtobufService,
    BreakingChange,
    BreakingChangeType,
    CompatibilityLevel,
    ValidationSeverity,
)

# Import services
from Asgard.Forseti.Protobuf.services import (
    ProtobufValidatorService,
    ProtobufCompatibilityService,
)

__all__ = [
    # Models
    "ProtobufConfig",
    "ProtobufSchema",
    "ProtobufValidationError",
    "ProtobufValidationResult",
    "ProtobufCompatibilityResult",
    "ProtobufSyntaxVersion",
    "ProtobufField",
    "ProtobufMessage",
    "ProtobufEnum",
    "ProtobufService",
    "BreakingChange",
    "BreakingChangeType",
    "CompatibilityLevel",
    "ValidationSeverity",
    # Services
    "ProtobufValidatorService",
    "ProtobufCompatibilityService",
]
