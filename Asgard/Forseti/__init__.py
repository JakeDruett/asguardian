"""
Forseti - API and Schema Specification Library

Named after the Norse god of justice and reconciliation who presides over
contracts and agreements. Like its namesake, Forseti validates and enforces
the contracts between systems through schema validation, API specification
checking, and compatibility verification.

Subpackages:
- OpenAPI: OpenAPI/Swagger specification generation and validation
- GraphQL: GraphQL schema generation and validation
- Database: Database schema analysis and migration generation
- Contracts: API contract testing and compatibility checking
- JSONSchema: JSON Schema generation and validation
- AsyncAPI: AsyncAPI specification parsing and validation
- MockServer: Mock server generation from API specifications
- CodeGen: API client code generation for multiple languages
- Documentation: API documentation generation
- Protobuf: Protocol Buffer schema validation and compatibility checking
- Avro: Apache Avro schema validation and compatibility checking

Usage:
    python -m Forseti --help
    python -m Forseti openapi validate spec.yaml
    python -m Forseti asyncapi validate asyncapi.yaml
    python -m Forseti contract breaking-changes v1.yaml v2.yaml
    python -m Forseti mock generate api.yaml --output ./mock-server
    python -m Forseti codegen typescript api.yaml --output ./client
    python -m Forseti docs generate api.yaml --output ./docs
    python -m Forseti protobuf validate schema.proto
    python -m Forseti protobuf check-compat old.proto new.proto
    python -m Forseti avro validate schema.avsc
    python -m Forseti avro check-compat old.avsc new.avsc
    python -m Forseti audit ./api

Programmatic Usage:
    from Asgard.Forseti.OpenAPI import SpecValidatorService, OpenAPIConfig
    from Asgard.Forseti.AsyncAPI import AsyncAPIValidatorService, AsyncAPIConfig
    from Asgard.Forseti.MockServer import MockServerGeneratorService
    from Asgard.Forseti.CodeGen import TypeScriptGeneratorService
    from Asgard.Forseti.Documentation import DocsGeneratorService

    # OpenAPI Validation
    openapi_service = SpecValidatorService()
    result = openapi_service.validate("openapi.yaml")
    print(f"Valid: {result.is_valid}")

    # AsyncAPI Validation
    asyncapi_service = AsyncAPIValidatorService()
    result = asyncapi_service.validate("asyncapi.yaml")
    print(f"Valid: {result.is_valid}")

    # Generate Mock Server
    mock_service = MockServerGeneratorService()
    result = mock_service.generate_from_openapi("api.yaml", "./mock-server")

    # Generate TypeScript Client
    codegen_service = TypeScriptGeneratorService()
    result = codegen_service.generate("api.yaml", "./client")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

# Package metadata
PACKAGE_INFO = {
    "name": "Forseti",
    "version": __version__,
    "description": "API and schema specification library",
    "author": __author__,
    "sub_packages": [
        "OpenAPI - OpenAPI/Swagger specification generation and validation",
        "GraphQL - GraphQL schema generation and validation",
        "Database - Database schema analysis and migration generation",
        "Contracts - API contract testing and compatibility checking",
        "JSONSchema - JSON Schema generation and validation",
        "AsyncAPI - AsyncAPI specification parsing and validation",
        "MockServer - Mock server generation from API specifications",
        "CodeGen - API client code generation for multiple languages",
        "Documentation - API documentation generation",
        "Protobuf - Protocol Buffer schema validation and compatibility checking",
        "Avro - Apache Avro schema validation and compatibility checking",
    ]
}

# Import subpackages
from . import OpenAPI
from . import GraphQL
from . import Database
from . import Contracts
from . import JSONSchema
from . import AsyncAPI
from . import MockServer
from . import CodeGen
from . import Documentation
from . import Protobuf
from . import Avro

# Re-export commonly used items from OpenAPI for convenience
from Asgard.Forseti.OpenAPI import (
    OpenAPIConfig,
    OpenAPIValidationResult,
    SpecValidatorService,
)

# Re-export commonly used items from GraphQL for convenience
from Asgard.Forseti.GraphQL import (
    GraphQLConfig,
    GraphQLValidationResult,
    SchemaValidatorService,
)

# Re-export commonly used items from Database for convenience
from Asgard.Forseti.Database import (
    DatabaseConfig,
    SchemaDiffResult,
    SchemaDiffService,
)

# Re-export commonly used items from Contracts for convenience
from Asgard.Forseti.Contracts import (
    ContractConfig,
    CompatibilityResult,
    CompatibilityCheckerService,
)

# Re-export commonly used items from JSONSchema for convenience
from Asgard.Forseti.JSONSchema import (
    JSONSchemaConfig,
    JSONSchemaValidationResult,
    SchemaValidatorService as JSONSchemaValidatorService,
)

# Re-export commonly used items from AsyncAPI for convenience
from Asgard.Forseti.AsyncAPI import (
    AsyncAPIConfig,
    AsyncAPIValidationResult,
    AsyncAPIValidatorService,
    AsyncAPIParserService,
)

# Re-export commonly used items from MockServer for convenience
from Asgard.Forseti.MockServer import (
    MockServerConfig,
    MockServerGeneratorService,
    MockDataGeneratorService,
)

# Re-export commonly used items from CodeGen for convenience
from Asgard.Forseti.CodeGen import (
    CodeGenConfig,
    CodeGenReport,
    TypeScriptGeneratorService,
    PythonGeneratorService,
    GolangGeneratorService,
)

# Re-export commonly used items from Documentation for convenience
from Asgard.Forseti.Documentation import (
    APIDocConfig,
    DocumentationReport,
    DocsGeneratorService,
)

# Re-export commonly used items from Protobuf for convenience
from Asgard.Forseti.Protobuf import (
    ProtobufConfig,
    ProtobufValidationResult,
    ProtobufCompatibilityResult,
    ProtobufValidatorService,
    ProtobufCompatibilityService,
)

# Re-export commonly used items from Avro for convenience
from Asgard.Forseti.Avro import (
    AvroConfig,
    AvroValidationResult,
    AvroCompatibilityResult,
    AvroValidatorService,
    AvroCompatibilityService,
)

__all__ = [
    # Subpackages
    "OpenAPI",
    "GraphQL",
    "Database",
    "Contracts",
    "JSONSchema",
    "AsyncAPI",
    "MockServer",
    "CodeGen",
    "Documentation",
    "Protobuf",
    "Avro",
    # OpenAPI exports
    "OpenAPIConfig",
    "OpenAPIValidationResult",
    "SpecValidatorService",
    # GraphQL exports
    "GraphQLConfig",
    "GraphQLValidationResult",
    "SchemaValidatorService",
    # Database exports
    "DatabaseConfig",
    "SchemaDiffResult",
    "SchemaDiffService",
    # Contracts exports
    "ContractConfig",
    "CompatibilityResult",
    "CompatibilityCheckerService",
    # JSONSchema exports
    "JSONSchemaConfig",
    "JSONSchemaValidationResult",
    "JSONSchemaValidatorService",
    # AsyncAPI exports
    "AsyncAPIConfig",
    "AsyncAPIValidationResult",
    "AsyncAPIValidatorService",
    "AsyncAPIParserService",
    # MockServer exports
    "MockServerConfig",
    "MockServerGeneratorService",
    "MockDataGeneratorService",
    # CodeGen exports
    "CodeGenConfig",
    "CodeGenReport",
    "TypeScriptGeneratorService",
    "PythonGeneratorService",
    "GolangGeneratorService",
    # Documentation exports
    "APIDocConfig",
    "DocumentationReport",
    "DocsGeneratorService",
    # Protobuf exports
    "ProtobufConfig",
    "ProtobufValidationResult",
    "ProtobufCompatibilityResult",
    "ProtobufValidatorService",
    "ProtobufCompatibilityService",
    # Avro exports
    "AvroConfig",
    "AvroValidationResult",
    "AvroCompatibilityResult",
    "AvroValidatorService",
    "AvroCompatibilityService",
]
