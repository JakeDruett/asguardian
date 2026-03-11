# Forseti - API and Schema Specification Validation

Named after the Norse god of justice and reconciliation who presides over contracts and agreements, Forseti validates and enforces the contracts between systems through schema validation, API specification checking, and compatibility verification.

## Overview

Forseti is an API and schema specification library that validates OpenAPI/Swagger specifications, GraphQL schemas, database schemas, JSON Schemas, and API contracts. Like its namesake who ensures fair agreements and resolves disputes, Forseti ensures that system contracts are valid, compatible, and properly enforced.

## Features

- **OpenAPI/Swagger**: Specification validation, generation from code, version conversion (2.0, 3.0, 3.1)
- **GraphQL**: Schema validation, SDL generation, endpoint introspection
- **Database Schemas**: Schema analysis, diff generation, migration scripts
- **API Contracts**: Contract validation, backward compatibility checking, breaking change detection
- **JSON Schema**: Schema generation from types, validation, inference from samples

## Installation

```bash
pip install -e /path/to/Asgard
```

Or install directly:

```bash
cd /path/to/Asgard
pip install .
```

## Quick Start

### CLI Usage

```bash
# OpenAPI validation and tools
python -m Forseti openapi validate api.yaml
python -m Forseti openapi validate api.yaml --strict
python -m Forseti openapi generate ./src --output openapi.yaml
python -m Forseti openapi convert api-v2.yaml --target-version 3.1 -o api-v3.yaml
python -m Forseti openapi diff old-api.yaml new-api.yaml

# GraphQL validation and tools
python -m Forseti graphql validate schema.graphql
python -m Forseti graphql introspect https://api.example.com/graphql -o schema.graphql
python -m Forseti graphql introspect https://api.example.com/graphql -H "Authorization: Bearer TOKEN"

# Database schema tools
python -m Forseti database analyze schema.sql -o schema.json
python -m Forseti database diff old-schema.sql new-schema.sql
python -m Forseti database migrate diff.json -o migration.sql --dialect postgresql

# API contract testing
python -m Forseti contract validate contract.yaml implementation.yaml
python -m Forseti contract check-compat old-api.yaml new-api.yaml
python -m Forseti contract breaking-changes old-api.yaml new-api.yaml --version 2.0.0

# JSON Schema tools
python -m Forseti jsonschema validate schema.json data.json
python -m Forseti jsonschema validate schema.json data.json --strict
python -m Forseti jsonschema infer samples.json -o schema.json
python -m Forseti jsonschema generate source.py --class User -o user-schema.json

# Audit all specifications
python -m Forseti audit ./api --format json -o audit-report.json
```

### Python API Usage

```python
from Asgard.Forseti import (
    SpecValidatorService,
    OpenAPIConfig,
    SchemaValidatorService,
    GraphQLConfig,
    CompatibilityCheckerService,
    BreakingChangeDetectorService,
)

# OpenAPI Validation
openapi_config = OpenAPIConfig(strict_mode=True)
validator = SpecValidatorService(openapi_config)
result = validator.validate_file("openapi.yaml")

if result.is_valid:
    print("Specification is valid!")
else:
    print(f"Found {result.error_count} errors:")
    for error in result.errors:
        print(f"  - {error.message}")

# GraphQL Validation
graphql_config = GraphQLConfig(strict_mode=True)
validator = SchemaValidatorService(graphql_config)
result = validator.validate_file("schema.graphql")

print(f"Valid: {result.is_valid}")
print(f"Errors: {len(result.errors)}")

# API Compatibility Checking
compat_checker = CompatibilityCheckerService()
result = compat_checker.check("old-api.yaml", "new-api.yaml")

if result.is_compatible:
    print("APIs are backward compatible!")
else:
    print(f"Found {len(result.breaking_changes)} breaking changes:")
    for change in result.breaking_changes:
        print(f"  - {change.description}")

# Breaking Change Detection
detector = BreakingChangeDetectorService()
changes = detector.detect("old-api.yaml", "new-api.yaml")

print(f"Breaking changes: {len(changes)}")
for change in changes:
    print(f"  {change.type}: {change.description}")
    print(f"    Location: {change.path}")
    print(f"    Impact: {change.impact}")

# Generate Changelog
changelog = detector.generate_changelog(changes, version="2.0.0")
print(changelog)
```

## Submodules

### OpenAPI Module

OpenAPI/Swagger specification validation and generation.

**Services:**
- `SpecValidatorService`: Validate OpenAPI 2.0/3.0/3.1 specifications
- `SpecGeneratorService`: Generate specs from FastAPI/Flask applications
- `SpecParserService`: Parse and extract specification information
- `SpecConverterService`: Convert between OpenAPI versions

**Key Features:**
- Support for OpenAPI 2.0 (Swagger), 3.0, and 3.1
- Strict and permissive validation modes
- Component reference validation
- Security scheme validation
- Parameter and response schema validation

### GraphQL Module

GraphQL schema validation and introspection.

**Services:**
- `SchemaValidatorService`: Validate GraphQL SDL schemas
- `SchemaGeneratorService`: Generate schemas from Python types
- `IntrospectionService`: Introspect GraphQL endpoints

**Key Features:**
- SDL (Schema Definition Language) validation
- Type system validation
- Directive validation
- Schema introspection with authentication
- SDL generation from introspection

### Database Module

Database schema analysis and migration generation.

**Services:**
- `SchemaAnalyzerService`: Analyze database schemas from SQL
- `SchemaDiffService`: Compare two database schemas
- `MigrationGeneratorService`: Generate migration scripts from diffs

**Key Features:**
- Support for MySQL, PostgreSQL, SQLite
- Table, column, index, constraint analysis
- Foreign key relationship detection
- Migration script generation
- Schema change impact analysis

### Contracts Module

API contract testing and compatibility verification.

**Services:**
- `ContractValidatorService`: Validate implementations against contracts
- `CompatibilityCheckerService`: Check backward compatibility
- `BreakingChangeDetectorService`: Detect breaking changes

**Key Features:**
- Consumer-driven contract testing
- Semantic versioning compliance
- Breaking change classification
- Compatibility report generation
- Changelog generation

### JSONSchema Module

JSON Schema generation, validation, and inference.

**Services:**
- `SchemaValidatorService`: Validate data against JSON Schema
- `SchemaGeneratorService`: Generate schemas from Pydantic models
- `SchemaInferenceService`: Infer schemas from sample data

**Key Features:**
- JSON Schema Draft 7 support
- Pydantic model integration
- Type inference from samples
- Schema confidence scoring
- Strict and permissive validation

## CLI Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `openapi validate` | Validate OpenAPI spec | `python -m Forseti openapi validate api.yaml` |
| `openapi generate` | Generate spec from code | `python -m Forseti openapi generate ./src -o api.yaml` |
| `openapi convert` | Convert spec version | `python -m Forseti openapi convert api.yaml --target-version 3.1` |
| `openapi diff` | Compare two specs | `python -m Forseti openapi diff old.yaml new.yaml` |
| `graphql validate` | Validate GraphQL schema | `python -m Forseti graphql validate schema.graphql` |
| `graphql generate` | Generate schema | `python -m Forseti graphql generate ./src -o schema.graphql` |
| `graphql introspect` | Introspect endpoint | `python -m Forseti graphql introspect https://api.com/graphql` |
| `database analyze` | Analyze database schema | `python -m Forseti database analyze schema.sql` |
| `database diff` | Compare schemas | `python -m Forseti database diff old.sql new.sql` |
| `database migrate` | Generate migration | `python -m Forseti database migrate diff.json --dialect mysql` |
| `contract validate` | Validate contract | `python -m Forseti contract validate contract.yaml impl.yaml` |
| `contract check-compat` | Check compatibility | `python -m Forseti contract check-compat old.yaml new.yaml` |
| `contract breaking-changes` | Detect breaking changes | `python -m Forseti contract breaking-changes old.yaml new.yaml` |
| `jsonschema validate` | Validate data | `python -m Forseti jsonschema validate schema.json data.json` |
| `jsonschema generate` | Generate schema | `python -m Forseti jsonschema generate models.py --class User` |
| `jsonschema infer` | Infer from samples | `python -m Forseti jsonschema infer samples.json -o schema.json` |
| `audit` | Audit all specs | `python -m Forseti audit ./api` |

## Configuration Options

### Common Options

- `--format`: Output format (text, json, markdown) - default: text
- `--verbose, -v`: Verbose output
- `--output, -o`: Output file path
- `--strict`: Enable strict validation mode

### OpenAPI Options

- `--target-version`: Target OpenAPI version (2.0, 3.0, 3.1)
- `--title`: API title
- `--version`: API version

### GraphQL Options

- `--header, -H`: HTTP headers for introspection (can be repeated)

### Database Options

- `--dialect`: SQL dialect (mysql, postgresql, sqlite)

### JSON Schema Options

- `--class`: Class name to generate schema from
- `--title`: Schema title

## Troubleshooting

### Common Issues

**Issue: "Invalid specification"**
- Check YAML/JSON syntax
- Verify all $ref references are valid
- Ensure required fields are present
- Use `--verbose` for detailed error messages

**Issue: "Cannot parse schema"**
- Verify file encoding (UTF-8)
- Check for special characters
- Validate YAML/JSON syntax separately

**Issue: "Introspection failed"**
- Check endpoint URL is correct
- Verify authentication headers
- Ensure GraphQL introspection is enabled
- Test endpoint with curl first

**Issue: "Breaking changes not detected"**
- Ensure both specs use same format
- Check that spec versions are correct
- Verify semantic versioning compliance

### Performance Tips

- Use specific validators instead of audit for single files
- Cache validation results for unchanged specs
- Run compatibility checks in CI/CD on spec changes
- Use strict mode in development, permissive in testing

## Output Formats

### Text Output
Human-readable output with error messages and locations.

### JSON Output
Machine-readable JSON for tool integration:
```json
{
  "is_valid": false,
  "error_count": 3,
  "errors": [
    {
      "type": "validation_error",
      "message": "Missing required field 'info'",
      "path": "/",
      "severity": "error"
    }
  ]
}
```

### Markdown Output
Documentation-friendly markdown with tables and lists.

## Integration with CI/CD

```yaml
# GitHub Actions example
- name: Validate OpenAPI Specification
  run: |
    python -m Forseti openapi validate api/openapi.yaml --strict

- name: Check API Compatibility
  run: |
    python -m Forseti contract check-compat \
      api/v1/openapi.yaml \
      api/v2/openapi.yaml

- name: Detect Breaking Changes
  if: failure()
  run: |
    python -m Forseti contract breaking-changes \
      api/v1/openapi.yaml \
      api/v2/openapi.yaml \
      --version ${{ github.ref_name }}
```

## Best Practices

1. **Validate Early**: Validate specs in pre-commit hooks
2. **Version Control**: Track specs in version control
3. **Compatibility Checks**: Always check backward compatibility before releasing
4. **Documentation**: Generate documentation from validated specs
5. **Strict Mode**: Use strict validation in CI/CD
6. **Schema First**: Design schemas before implementation
7. **Contract Testing**: Use contract validation in integration tests

## Version

Version: 1.0.0

## Author

Asgard Contributors
