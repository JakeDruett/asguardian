# Forseti L1 Integration Tests

Comprehensive L1 integration tests for the Forseti API/schema validation package. These tests validate end-to-end workflows and integration between Forseti services without mocking internal dependencies.

## Test Structure

```
L1_Integration/
├── conftest.py                          # Integration test fixtures
├── test_openapi_integration.py          # OpenAPI workflow tests
├── test_graphql_integration.py          # GraphQL workflow tests
├── test_database_integration.py         # Database schema tests
├── test_contract_integration.py         # API contract tests
└── test_jsonschema_integration.py       # JSON Schema tests
```

## Test Philosophy

L1 integration tests follow these principles:

1. **No Internal Mocking**: Tests use real service instances and validate actual functionality
2. **Workflow-Based**: Tests validate complete workflows from start to finish
3. **Real Data**: Tests use realistic schemas, specs, and data samples
4. **Cross-Service**: Tests validate integration between multiple Forseti services
5. **File-Based**: Tests work with actual files and databases (in-memory SQLite)

## Running Tests

Run all L1 integration tests:
```bash
pytest Asgard/Asgard_Test/tests_Forseti/L1_Integration/ -v
```

Run specific test file:
```bash
# OpenAPI tests
pytest Asgard/Asgard_Test/tests_Forseti/L1_Integration/test_openapi_integration.py -v

# GraphQL tests
pytest Asgard/Asgard_Test/tests_Forseti/L1_Integration/test_graphql_integration.py -v

# Database tests
pytest Asgard/Asgard_Test/tests_Forseti/L1_Integration/test_database_integration.py -v

# Contract tests
pytest Asgard/Asgard_Test/tests_Forseti/L1_Integration/test_contract_integration.py -v

# JSON Schema tests
pytest Asgard/Asgard_Test/tests_Forseti/L1_Integration/test_jsonschema_integration.py -v
```

Run with coverage:
```bash
pytest Asgard/Asgard_Test/tests_Forseti/L1_Integration/ --cov=Asgard.Forseti --cov-report=html
```

## Test Coverage

### OpenAPI Integration Tests (test_openapi_integration.py)

**TestOpenAPIWorkflow**
- Validate, parse, and generate reports workflow
- Parse, modify, and re-validate workflow
- Invalid spec error reporting workflow

**TestOpenAPIVersionConversion**
- Swagger 2.0 to OpenAPI 3.0 conversion
- OpenAPI 3.0 to 3.1 conversion
- Bidirectional conversion (3.0 -> 2.0 -> 3.0)
- Version detection and validation

**TestOpenAPIGeneration**
- Generate specs from FastAPI source code
- Generate and validate workflow
- Pydantic model schema extraction
- Generate, convert, and validate workflow

**TestOpenAPIParsingWorkflows**
- Parse and extract endpoints
- Parse and extract schemas
- Parse multiple OpenAPI versions

**TestOpenAPIErrorDetection**
- Detect missing responses
- Detect undefined schema references
- Detect deprecated operations

**TestOpenAPIComplexScenarios**
- Large specs with many endpoints
- Security schemes validation
- Multi-format report generation

### GraphQL Integration Tests (test_graphql_integration.py)

**TestGraphQLSchemaValidation**
- Simple schema validation
- Complex schema with directives and interfaces
- Syntax error detection
- Undefined type detection
- Validation and reporting workflow

**TestGraphQLDirectiveValidation**
- Built-in directives (@deprecated)
- Custom directives (@auth)
- Unknown directive warnings

**TestGraphQLInterfaceAndUnion**
- Interface implementation validation
- Incomplete interface detection
- Union type validation

**TestGraphQLSchemaGeneration**
- Generate from Python types
- Generate with mutations
- Generate, validate, and save workflow

**TestGraphQLIntrospection**
- Schema introspection
- Type information extraction
- Introspect and validate workflow

**TestGraphQLComplexScenarios**
- Large schemas with many types
- Enum types
- Input types
- Subscription types
- Error reporting formats

### Database Integration Tests (test_database_integration.py)

**TestDatabaseSchemaAnalysis**
- Analyze SQL schema files
- Analyze SQLAlchemy models in database
- Extract table dependencies
- Analyze indexes and constraints

**TestDatabaseSchemaDiff**
- Compare schema versions
- Detect breaking changes
- Compare SQLAlchemy schemas
- Identical schema comparison
- Diff report generation

**TestMigrationGeneration**
- Generate migration from diff
- Generate migration for new tables
- Save migration files (upgrade/downgrade)
- Generate Alembic-compatible migrations

**TestDatabaseComplexScenarios**
- Complex relationships analysis
- Circular dependency detection
- Composite primary keys
- Data preservation during migration
- Full schema lifecycle (analyze -> diff -> migrate -> validate)

### Contract Integration Tests (test_contract_integration.py)

**TestContractCompatibility**
- Check compatible API versions
- Detect incompatible versions
- File-based compatibility checking
- Compatibility report generation

**TestBreakingChangeDetection**
- Detect removed endpoints
- Detect parameter type changes
- Detect required parameter additions
- Detect response schema changes
- Severity classification (major/minor/patch)

**TestContractValidation**
- Validate contract against spec
- Detect missing endpoints
- Validate response schemas
- File-based validation

**TestCompatibilityComplexScenarios**
- Multiple version comparison (v1 -> v2 -> v3)
- Cross-format compatibility (Swagger 2.0 vs OpenAPI 3.0)
- Subtle breaking change detection
- Comprehensive compatibility checks

### JSON Schema Integration Tests (test_jsonschema_integration.py)

**TestJSONSchemaValidation**
- Validate data against schema
- Detect validation errors
- File-based validation
- Multiple JSON Schema drafts (4, 7, 2020-12)
- Validation report generation

**TestJSONSchemaInference**
- Infer schema from simple data
- Infer schema from nested data
- Infer schema from array data
- Infer and validate workflow
- Infer from multiple samples
- Save inferred schemas

**TestJSONSchemaGeneration**
- Generate from Python types
- Generate with nested objects
- Generate with arrays
- Generate and validate workflow

**TestJSONSchemaComplexScenarios**
- Schema references ($ref)
- Pattern constraints
- oneOf/anyOf/allOf constraints
- Infer, validate, refine cycle
- Large schema validation
- Schema evolution (backward compatibility)
- Cross-format validation

## Fixtures

The `conftest.py` provides comprehensive fixtures for integration testing:

### Database Fixtures
- `in_memory_db` - SQLite in-memory database with tables
- `sqlalchemy_models` - SQLAlchemy model classes (User, Post)
- `database_versions` - Two schema versions for migration testing

### OpenAPI Fixtures
- `sample_openapi_v3_1_spec` - OpenAPI 3.1 specification
- `breaking_change_specs` - Two specs with breaking changes
- `compatible_specs` - Two backward-compatible specs

### GraphQL Fixtures
- `complex_graphql_schema` - Schema with directives, interfaces, unions
- Includes Query, Mutation, Subscription types
- Custom directives and enum types

### JSON Schema Fixtures
- `jsonschema_draft_7` - JSON Schema draft 7 example
- `jsonschema_draft_2020_12` - JSON Schema draft 2020-12 example
- `json_data_samples` - Various JSON data for inference testing

### FastAPI Fixtures
- `fastapi_source_with_models` - Realistic FastAPI source with Pydantic models
- Includes models.py and routes.py files

## Test Patterns

### Workflow Testing
Integration tests follow complete workflows:

```python
def test_workflow_validate_parse_report(self, openapi_spec_file):
    # Step 1: Validate
    validator = SpecValidatorService()
    validation_result = validator.validate(openapi_spec_file)
    assert validation_result.is_valid is True

    # Step 2: Parse
    parser = SpecParserService()
    parsed_spec = parser.parse(openapi_spec_file)
    assert parsed_spec.openapi == "3.0.3"

    # Step 3: Generate report
    report = validator.generate_report(validation_result, format="text")
    assert "Valid" in report
```

### Cross-Service Integration
Tests validate integration between services:

```python
def test_workflow_generate_convert_validate(self, tmp_path, fastapi_source):
    # Generate OpenAPI spec from code
    generator = SpecGeneratorService()
    gen_result = generator.generate_from_source(fastapi_source)

    # Convert to different version
    converter = SpecConverterService()
    conv_result = converter.convert(gen_result.spec, OpenAPIVersion.V2_0)

    # Validate converted spec
    validator = SpecValidatorService()
    validation_result = validator.validate_spec(conv_result.converted_spec)
    assert validation_result.is_valid is True
```

### Real File Operations
Tests work with actual files and databases:

```python
def test_workflow_save_migration_files(self, tmp_path, database_versions):
    # Generate migration
    diff_service = SchemaDiffService()
    diff_result = diff_service.diff(database_versions["v1"], database_versions["v2"])

    migration_service = MigrationGeneratorService()
    migration_result = migration_service.generate_migration(diff_result)

    # Save to files
    migration_dir = tmp_path / "migrations"
    migration_dir.mkdir()
    migration_service.save_migration(migration_result, migration_dir, version="001")

    # Verify files exist
    assert (migration_dir / "001_migration_upgrade.sql").exists()
    assert (migration_dir / "001_migration_downgrade.sql").exists()
```

## Key Differences from L0 Tests

| Aspect | L0 Tests | L1 Tests |
|--------|----------|----------|
| **Mocking** | Mock external dependencies | No mocking, real services |
| **Scope** | Single service method | Complete workflows |
| **Data** | Simple test data | Realistic, complex data |
| **Integration** | Isolated units | Cross-service integration |
| **Files** | In-memory only | Real file I/O |
| **Database** | Mocked | In-memory SQLite |
| **Focus** | Method behavior | End-to-end functionality |

## Coverage Goals

Target: 85%+ integration test coverage

Coverage areas:
- Complete workflows from input to output
- Service-to-service integration points
- File format conversions (YAML, JSON, SQL)
- Error handling and recovery
- Report generation in multiple formats
- Schema evolution and compatibility

## Best Practices

When adding new L1 integration tests:

1. **Test Complete Workflows**: Each test should cover a full user workflow
2. **Use Realistic Data**: Use complex, realistic schemas and data samples
3. **Test Integration Points**: Validate how services work together
4. **Include Error Paths**: Test error handling and recovery
5. **Verify File Operations**: Test actual file reading/writing
6. **Test Multiple Formats**: Validate different output formats (text, JSON, markdown)
7. **Use Temporary Files**: Always use pytest's tmp_path fixture
8. **Assert Meaningful Results**: Verify actual functionality, not just success
9. **Test Edge Cases**: Include boundary conditions and complex scenarios
10. **Document Workflows**: Use descriptive test names and docstrings

## Common Issues

### SQLAlchemy Version Compatibility
If database tests fail, ensure SQLAlchemy version is compatible:
```bash
pip install sqlalchemy>=1.4,<2.0
```

### JSON Schema Draft Support
Different JSON Schema drafts have different validation rules. Tests should handle multiple draft versions.

### File Path Issues
Always use absolute paths or pytest's tmp_path fixture for file operations.

## Contributing

When contributing new integration tests:

1. Follow existing test structure and naming conventions
2. Use fixtures from conftest.py where possible
3. Add new fixtures to conftest.py if they're reusable
4. Document complex workflows in docstrings
5. Ensure tests are independent and can run in any order
6. Test both success and failure scenarios
7. Include realistic, production-like data
8. Target 85%+ coverage for new functionality

## Notes

- All tests use pytest framework
- Tests use temporary directories for file operations
- Database tests use in-memory SQLite for speed
- No external services required
- Tests run in Docker container environment
- Follow CLAUDE.md project conventions
- Integration tests complement L0 unit tests
- L1 tests validate that services work together correctly
