"""
Forseti Documentation Module - API Documentation Generation

This module provides API documentation generation from OpenAPI specifications:
- Generate HTML documentation with customizable themes
- Generate Markdown documentation
- Include authentication, schemas, and examples

Usage:
    from Asgard.Forseti.Documentation import DocsGeneratorService, APIDocConfig

    # Generate HTML documentation
    config = APIDocConfig(output_format="html", theme="modern")
    generator = DocsGeneratorService(config)
    result = generator.generate("api.yaml", output_dir="./docs")

    for doc in result.generated_documents:
        print(f"Generated: {doc.path}")

    # Generate Markdown documentation
    config = APIDocConfig(output_format="markdown")
    generator = DocsGeneratorService(config)
    result = generator.generate("api.yaml")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

# Import models
from Asgard.Forseti.Documentation.models import (
    APIDocConfig,
    DocumentationFormat,
    DocumentationReport,
    DocumentationStructure,
    DocumentationTheme,
    EndpointInfo,
    GeneratedDocument,
    SchemaInfo,
    TagGroup,
)

# Import services
from Asgard.Forseti.Documentation.services import (
    DocsGeneratorService,
)

__all__ = [
    # Models
    "APIDocConfig",
    "DocumentationFormat",
    "DocumentationReport",
    "DocumentationStructure",
    "DocumentationTheme",
    "EndpointInfo",
    "GeneratedDocument",
    "SchemaInfo",
    "TagGroup",
    # Services
    "DocsGeneratorService",
]
