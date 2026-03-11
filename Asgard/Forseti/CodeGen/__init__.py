"""
Forseti CodeGen Module - API Client Code Generation

This module provides API client code generation from OpenAPI specifications:
- Generate TypeScript clients with fetch or axios
- Generate Python clients with requests, httpx, or aiohttp
- Generate Go clients with net/http
- Generate type-safe models and interfaces

Usage:
    from Asgard.Forseti.CodeGen import TypeScriptGeneratorService, CodeGenConfig

    # Generate TypeScript client
    config = CodeGenConfig(target_language="typescript")
    generator = TypeScriptGeneratorService(config)
    result = generator.generate("api.yaml", output_dir="./client")

    for file in result.generated_files:
        print(f"Generated: {file.path}")

    # Generate Python client
    from Asgard.Forseti.CodeGen import PythonGeneratorService
    generator = PythonGeneratorService()
    result = generator.generate("api.yaml")

    # Generate Go client
    from Asgard.Forseti.CodeGen import GolangGeneratorService
    generator = GolangGeneratorService()
    result = generator.generate("api.yaml")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

# Import models
from Asgard.Forseti.CodeGen.models import (
    CodeGenConfig,
    CodeGenReport,
    CodeStyle,
    GeneratedFile,
    HttpClientType,
    MethodDefinition,
    ParameterDefinition,
    PropertyDefinition,
    TargetLanguage,
    TypeDefinition,
)

# Import services
from Asgard.Forseti.CodeGen.services import (
    GolangGeneratorService,
    PythonGeneratorService,
    TypeScriptGeneratorService,
)

__all__ = [
    # Models
    "CodeGenConfig",
    "CodeGenReport",
    "CodeStyle",
    "GeneratedFile",
    "HttpClientType",
    "MethodDefinition",
    "ParameterDefinition",
    "PropertyDefinition",
    "TargetLanguage",
    "TypeDefinition",
    # Services
    "GolangGeneratorService",
    "PythonGeneratorService",
    "TypeScriptGeneratorService",
]
