"""
Forseti Avro Module - Apache Avro Schema Management

This module provides comprehensive Avro schema handling including:
- Schema validation against Avro specification standards
- Best practices checking for Avro schemas
- Backward/forward compatibility checking between schema versions
- Support for all Avro schema types

Usage:
    from Asgard.Forseti.Avro import AvroValidatorService, AvroConfig

    # Validate an Avro schema
    service = AvroValidatorService()
    result = service.validate("schema.avsc")
    print(f"Valid: {result.is_valid}")
    for error in result.errors:
        print(f"  - {error.message}")

    # Check compatibility between versions
    from Asgard.Forseti.Avro import AvroCompatibilityService
    compat_service = AvroCompatibilityService()
    result = compat_service.check("old.avsc", "new.avsc")
    print(f"Compatible: {result.is_compatible}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

# Import models
from Asgard.Forseti.Avro.models import (
    AvroCompatibilityResult,
    AvroConfig,
    AvroField,
    AvroSchema,
    AvroSchemaType,
    AvroValidationError,
    AvroValidationResult,
    BreakingChange,
    BreakingChangeType,
    CompatibilityLevel,
    CompatibilityMode,
    ValidationSeverity,
)

# Import services
from Asgard.Forseti.Avro.services import (
    AvroCompatibilityService,
    AvroValidatorService,
)

__all__ = [
    # Models
    "AvroCompatibilityResult",
    "AvroConfig",
    "AvroField",
    "AvroSchema",
    "AvroSchemaType",
    "AvroValidationError",
    "AvroValidationResult",
    "BreakingChange",
    "BreakingChangeType",
    "CompatibilityLevel",
    "CompatibilityMode",
    "ValidationSeverity",
    # Services
    "AvroCompatibilityService",
    "AvroValidatorService",
]
