"""
Forseti GraphQL Module - GraphQL Schema Management

This module provides comprehensive GraphQL schema handling including:
- Schema validation against GraphQL specification
- Schema parsing and introspection
- Schema generation from code

Usage:
    from Asgard.Forseti.GraphQL import SchemaValidatorService, GraphQLConfig

    # Validate a GraphQL schema
    service = SchemaValidatorService()
    result = service.validate("schema.graphql")
    print(f"Valid: {result.is_valid}")
    for error in result.errors:
        print(f"  - {error.message}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

# Import models
from Asgard.Forseti.GraphQL.models import (
    GraphQLConfig,
    GraphQLSchema,
    GraphQLType,
    GraphQLField,
    GraphQLDirective,
    GraphQLValidationResult,
    GraphQLValidationError,
    GraphQLTypeKind,
    ValidationSeverity,
)

# Import services
from Asgard.Forseti.GraphQL.services import (
    SchemaValidatorService,
    SchemaGeneratorService,
    IntrospectionService,
)

# Import utilities
from Asgard.Forseti.GraphQL.utilities import (
    load_schema_file,
    save_schema_file,
    parse_sdl,
    merge_schemas,
)

__all__ = [
    # Models
    "GraphQLConfig",
    "GraphQLSchema",
    "GraphQLType",
    "GraphQLField",
    "GraphQLDirective",
    "GraphQLValidationResult",
    "GraphQLValidationError",
    "GraphQLTypeKind",
    "ValidationSeverity",
    # Services
    "SchemaValidatorService",
    "SchemaGeneratorService",
    "IntrospectionService",
    # Utilities
    "load_schema_file",
    "save_schema_file",
    "parse_sdl",
    "merge_schemas",
]
