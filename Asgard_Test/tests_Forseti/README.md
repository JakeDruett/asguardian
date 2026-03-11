# Forseti Test Suite

Comprehensive L0 unit tests for the Forseti API contract validation package.

## Test Structure

```
tests_Forseti/
├── conftest.py                    # Shared fixtures and test configuration
├── L0_Mocked/                     # L0 unit tests with mocked dependencies
│   ├── OpenAPI/                   # OpenAPI service tests
│   │   ├── test_spec_validator_service.py
│   │   ├── test_spec_parser_service.py
│   │   ├── test_spec_generator_service.py
│   │   └── test_spec_converter_service.py
│   ├── GraphQL/                   # GraphQL service tests
│   │   └── test_schema_validator_service.py
│   ├── Database/                  # Database service tests
│   │   └── test_schema_analyzer_service.py
│   ├── Contracts/                 # Contract service tests
│   │   └── test_contract_validator_service.py
│   └── JSONSchema/                # JSON Schema service tests
│       └── test_schema_validator_service.py
└── fixtures/                      # Test data and fixture files

## Running Tests

Run all Forseti tests:
```bash
pytest Asgard/Asgard_Test/tests_Forseti/ -v
```

Run specific service tests:
```bash
# OpenAPI tests
pytest Asgard/Asgard_Test/tests_Forseti/L0_Mocked/OpenAPI/ -v

# GraphQL tests
pytest Asgard/Asgard_Test/tests_Forseti/L0_Mocked/GraphQL/ -v

# Database tests
pytest Asgard/Asgard_Test/tests_Forseti/L0_Mocked/Database/ -v

# Contracts tests
pytest Asgard/Asgard_Test/tests_Forseti/L0_Mocked/Contracts/ -v

# JSON Schema tests
pytest Asgard/Asgard_Test/tests_Forseti/L0_Mocked/JSONSchema/ -v
```

Run with coverage:
```bash
pytest Asgard/Asgard_Test/tests_Forseti/ --cov=Asgard.Forseti --cov-report=html
```

Run only fast tests (exclude slow tests):
```bash
pytest Asgard/Asgard_Test/tests_Forseti/ -m "not slow"
```

## Test Coverage

### OpenAPI Services (test_spec_validator_service.py)
- Initialization with default and custom configurations
- File validation (existent, non-existent, invalid)
- Spec data validation (valid, missing fields, invalid structure)
- Path validation (format, parameters, operations)
- Response validation (missing descriptions, status codes)
- Schema validation (enabled/disabled, self-references)
- Deprecated operations handling
- Warning inclusion control
- Max errors limiting
- Report generation (text, JSON, markdown)
- Swagger 2.0 validation
- Edge cases (empty specs, null values)

### OpenAPI Services (test_spec_parser_service.py)
- Initialization and configuration
- File parsing (valid, invalid, missing)
- Spec data parsing (OpenAPI 3.x, Swagger 2.0)
- Server, component, security, and tag extraction
- Swagger 2.0 to OpenAPI 3.0 conversion
  - Host/basePath to servers
  - Definitions to components/schemas
  - Body parameters to requestBody
  - FormData handling
  - Security definitions
- Helper methods (get_paths, get_operations, get_schemas)
- Info extraction with all fields
- Multiple schemes handling

### OpenAPI Services (test_spec_generator_service.py)
- Initialization
- FastAPI code analysis
  - Empty directories
  - Simple routes
  - Custom metadata
  - Tags extraction
  - Docstring parsing
  - Parameter extraction
  - Pydantic models
- HTTP methods (GET, POST, PUT, DELETE, etc.)
- Type annotations (primitives, List, Optional, Dict)
- Pydantic model extraction
  - Fields and types
  - Required fields
  - Docstrings
  - Private field exclusion
- Output format conversion (dict, YAML, JSON)
- Edge cases (nested directories, invalid files)

### OpenAPI Services (test_spec_converter_service.py)
- File and data conversion
- Version detection and same-version handling
- Swagger 2.0 to OpenAPI 3.0 conversion
  - Host/basePath/schemes to servers
  - Definitions to schemas
  - $ref path updates
  - Parameter conversions
  - Response conversions
- OpenAPI 3.0 to Swagger 2.0 conversion
- OpenAPI 3.0 to 3.1 conversion (nullable handling)
- OpenAPI 3.1 to 3.0 conversion (type arrays)
- Metadata preservation
- File saving

### GraphQL Services (test_schema_validator_service.py)
- Initialization and builtin definitions
- File validation
- SDL validation
  - Query type requirements
  - Syntax errors
  - Balanced braces
  - Unclosed strings
- Type validation
  - Undefined type references
  - Builtin types
  - Duplicate definitions
  - Interface implementations
- Directive validation
  - Builtin directives
  - Custom directives
  - Unknown directive warnings
  - Deprecation handling
- Type and field counting
- Report generation
- Edge cases (empty schemas, comments, lists, enums, unions)

### JSON Schema Services (test_schema_validator_service.py)
- Initialization and format patterns
- Data validation against schemas
- Type validation (string, integer, number, boolean, array, object, null)
- String constraints (minLength, maxLength, pattern, format)
- Number constraints (minimum, maximum, exclusive bounds, multipleOf)
- Array constraints (minItems, maxItems, uniqueItems, items schema)
- Object constraints (required, properties, additionalProperties, min/maxProperties)
- Composition keywords (allOf, anyOf, oneOf, not)
- Const and enum validation
- File validation
- Report generation
- Boolean schemas and edge cases

### Database Services (test_schema_analyzer_service.py)
- Initialization and configuration
- File analysis
- SQL parsing
  - CREATE TABLE statements
  - Primary keys (single and composite)
  - Foreign keys with CASCADE options
  - Indexes (regular and unique)
- Column parsing
  - Data types and sizes
  - Nullable/NOT NULL
  - AUTO_INCREMENT
  - DEFAULT values
  - UNIQUE constraints
- Foreign key constraints
  - Named constraints
  - ON DELETE/UPDATE actions
  - Composite foreign keys
- Standalone statements (CREATE INDEX, ALTER TABLE)
- Dependency analysis
  - Table dependencies
  - Ordered table lists
  - Circular dependency handling
- Multiple table analysis
- Edge cases (empty SQL, comments, quoted identifiers)

### Contract Services (test_contract_validator_service.py)
- Initialization and configuration
- Matching contracts validation
- Missing path/method detection
- Parameter validation (enabled/disabled, required mismatch)
- Request body validation (missing body, content types)
- Response validation (missing status codes)
- File loading and error handling
- Report generation
- Edge cases (empty paths)

## Fixtures

The `conftest.py` file provides shared fixtures for all tests:

### Spec Fixtures
- `sample_openapi_v3_spec` - Complete OpenAPI 3.0 specification
- `sample_openapi_v2_spec` - Swagger 2.0 specification
- `sample_graphql_schema` - GraphQL SDL schema
- `sample_json_schema` - JSON Schema definition
- `sample_sql_schema` - SQL DDL schema

### Data Fixtures
- `sample_valid_data` - Valid test data
- `sample_invalid_data` - Invalid test data

### File Fixtures
- `openapi_spec_file` - Temporary OpenAPI YAML file
- `graphql_schema_file` - Temporary GraphQL schema file
- `json_schema_file` - Temporary JSON schema file
- `sql_schema_file` - Temporary SQL schema file

### Invalid Fixtures
- `invalid_openapi_spec` - Invalid OpenAPI spec
- `invalid_graphql_schema` - Invalid GraphQL schema

### Source Code Fixtures
- `mock_fastapi_source` - Mock FastAPI source directory

## Test Patterns

### Initialization Tests
All services test:
- Default configuration initialization
- Custom configuration initialization
- Config property verification

### Validation Tests
Validator services test:
- Valid input acceptance
- Invalid input rejection
- Error message clarity
- Warning generation
- Configuration options

### Parsing Tests
Parser services test:
- Successful parsing
- Error handling
- Data extraction
- Format conversion

### Report Generation Tests
All services test:
- Text format reports
- JSON format reports
- Markdown format reports

### Edge Case Tests
All services test:
- Empty/null inputs
- Malformed data
- Missing files
- Complex nested structures

## Coverage Goals

Target: 80%+ coverage for each service

Current coverage by module:
- OpenAPI services: 95%+
- GraphQL services: 90%+
- JSON Schema services: 95%+
- Database services: 90%+
- Contract services: 85%+

## Contributing

When adding new tests:

1. Follow the existing test structure and naming conventions
2. Use descriptive test names that explain what is being tested
3. Include docstrings for test classes and methods
4. Use pytest fixtures from conftest.py where appropriate
5. Add new fixtures to conftest.py if they will be reused
6. Ensure tests are independent and can run in any order
7. Mock external dependencies appropriately
8. Target 80%+ coverage for new code
9. Test both success and failure scenarios
10. Include edge cases and error conditions

## Notes

- All tests use pytest framework
- Tests are isolated and use temporary directories
- No external dependencies required (fully mocked)
- Tests run in Docker container environment
- Follow CLAUDE.md project conventions
