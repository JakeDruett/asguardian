# OpenAPI Test Fixtures

This directory contains OpenAPI specification files for testing the Forseti OpenAPI validation and parsing functionality.

## Files

### Valid Specifications

| File | Description | Version |
|------|-------------|---------|
| `valid_v2.yaml` | Valid Swagger 2.0 specification for User Management API | Swagger 2.0 |
| `valid_v3.yaml` | Valid OpenAPI 3.0 specification for Product Catalog API | OpenAPI 3.0.3 |
| `valid_v3_1.yaml` | Valid OpenAPI 3.1 specification for Order Management API | OpenAPI 3.1.0 |
| `petstore.yaml` | Standard Petstore API (comprehensive example) | OpenAPI 3.0.3 |
| `complex_spec.yaml` | Advanced features: OAuth2, callbacks, webhooks, discriminators | OpenAPI 3.1.0 |

### Invalid Specifications

| File | Description | Expected Errors |
|------|-------------|-----------------|
| `invalid_missing_paths.yaml` | Missing required `paths` field | Schema validation error |
| `invalid_bad_refs.yaml` | Contains broken `$ref` references | Reference resolution errors |

## Usage

### Testing Valid Specifications

```python
from Asgard.Forseti.OpenAPI.services.spec_validator_service import SpecValidatorService

validator = SpecValidatorService()
result = validator.validate_file("valid_v3.yaml")
assert result.is_valid == True
assert result.error_count == 0
```

### Testing Invalid Specifications

```python
result = validator.validate_file("invalid_missing_paths.yaml")
assert result.is_valid == False
assert "paths" in str(result.errors[0].message).lower()
```

### Version Detection

```python
from Asgard.Forseti.OpenAPI.services.spec_parser_service import SpecParserService

parser = SpecParserService()
spec = parser.parse_file("valid_v3_1.yaml")
assert spec.version == OpenAPIVersion.V3_1
```

## Features Covered

### valid_v2.yaml (Swagger 2.0)
- `swagger` version field
- `host`, `basePath`, `schemes`
- `consumes`, `produces`
- `securityDefinitions` (apiKey, basic)
- `definitions` for schemas
- Parameter types: query, path, body, header

### valid_v3.yaml (OpenAPI 3.0)
- `openapi` version field
- `servers` with variables
- `components/schemas` with `$ref`
- `components/parameters` (reusable)
- `components/responses` (reusable)
- `components/examples`
- `requestBody` with media types
- `security` (Bearer, API Key)
- Response headers

### valid_v3_1.yaml (OpenAPI 3.1)
- JSON Schema 2020-12 dialect
- `webhooks` section
- `type` as array (nullable types)
- `const` keyword
- `exclusiveMinimum` as number
- OAuth2 with all flow types
- Server variables with enums

### complex_spec.yaml (Advanced Features)
- `callbacks` for async operations
- `links` for HATEOAS
- `discriminator` for polymorphism
- `oneOf`, `allOf` compositions
- Multiple security schemes
- OAuth2 with scopes
- Webhook definitions

## Data Relationships

The specifications are designed to represent realistic APIs:

1. **User Management** (v2): Basic CRUD for users
2. **Product Catalog** (v3): Products, categories, inventory
3. **Order Management** (v3.1): Orders, payments, shipping
4. **Complex API** (advanced): Subscriptions with callbacks

These can be used together to test contract compatibility between services.
