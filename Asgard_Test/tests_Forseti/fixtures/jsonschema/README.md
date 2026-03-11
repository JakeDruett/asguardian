# JSON Schema Test Fixtures

This directory contains JSON Schema files and sample data for testing Forseti JSON Schema validation functionality.

## Files

### Schema Files

| File | Description | Draft Version |
|------|-------------|---------------|
| `draft4_schema.json` | User schema demonstrating Draft 4 features | Draft 4 |
| `draft7_schema.json` | Order schema with conditional schemas | Draft 7 |
| `draft2020_schema.json` | Product catalog with advanced 2020-12 features | 2020-12 |

### Sample Data

| File | Description |
|------|-------------|
| `sample_data_valid.json` | Valid data matching all three schema drafts |
| `sample_data_invalid.json` | Invalid data demonstrating various violation types |

## Schema Details

### draft4_schema.json (Draft 4)

User data validation schema featuring:

- **Basic Types**: string, integer, boolean, array, object
- **String Constraints**: pattern, minLength, maxLength, format (email, uri, date-time)
- **Numeric Constraints**: minimum, maximum
- **Array Constraints**: items, uniqueItems, maxItems
- **Object Properties**: required, additionalProperties: false
- **References**: `$ref` to `#/definitions/address`
- **Format Validation**: UUID pattern, email format

**Key Fields:**
```json
{
  "id": "UUID v4 pattern",
  "email": "format: email",
  "name": "1-100 chars",
  "role": "enum: user/admin/moderator/guest",
  "profile": { "nested object" },
  "addresses": [{ "$ref": "#/definitions/address" }]
}
```

### draft7_schema.json (Draft 7)

Order data validation with conditional schemas:

- **New Keywords**: `if/then/else`, `readOnly`, `writeOnly`
- **Exclusive Limits**: `exclusiveMinimum` as boolean
- **Multi-type**: `type: ["string", "null"]`
- **Definitions**: Complex nested `$ref` structures
- **Conditional Validation**: Different rules based on status

**Conditional Example:**
```json
{
  "if": { "properties": { "status": { "const": "shipped" } } },
  "then": { "required": ["shipment"] }
}
```

### draft2020_schema.json (Draft 2020-12)

Product catalog with latest JSON Schema features:

- **$defs**: Replaces `definitions`
- **$id**: Schema identification
- **unevaluatedProperties**: Strict property control
- **dependentRequired**: Conditional requirements
- **dependentSchemas**: Conditional schema application
- **prefixItems**: Tuple validation
- **propertyNames**: Key validation
- **oneOf/anyOf/allOf**: Schema composition
- **Discriminated Unions**: Product type variants

**Product Types (oneOf):**
- `physicalProduct`: weight, dimensions, variants
- `digitalProduct`: downloadUrl, fileSize, licenseType
- `subscriptionProduct`: billingInterval, features
- `bundleProduct`: bundleItems (min 2), bundlePrice

## Sample Data Structure

### sample_data_valid.json

Contains three validated examples:

```json
{
  "draft4_user": { /* Valid user matching draft4_schema */ },
  "draft7_order": { /* Valid order with payment & shipment */ },
  "draft2020_catalog": { /* Catalog with multiple product types */ }
}
```

### sample_data_invalid.json

Organized by violation category:

```json
{
  "draft4_user_invalid": {
    "_violations": ["Missing email", "Invalid UUID", "..."],
    /* Invalid user data */
  },
  "draft7_order_invalid": {
    "_violations": ["Empty items", "Negative total", "..."],
    /* Invalid order data */
  },
  "additional_invalid_cases": {
    "type_mismatch": { /* Wrong types */ },
    "format_violations": { /* Invalid formats */ },
    "numeric_constraints": { /* Out of range */ },
    "string_constraints": { /* Length/pattern issues */ },
    "array_constraints": { /* Size/uniqueness issues */ }
  }
}
```

## Usage Examples

### Schema Validation

```python
from Asgard.Forseti.JSONSchema.services.schema_validator_service import SchemaValidatorService
import json

validator = SchemaValidatorService()

# Load schema and data
with open("draft7_schema.json") as f:
    schema = json.load(f)

with open("sample_data_valid.json") as f:
    data = json.load(f)["draft7_order"]

# Validate
result = validator.validate(data, schema)
assert result.is_valid
```

### Testing Invalid Data

```python
with open("sample_data_invalid.json") as f:
    invalid_data = json.load(f)["draft7_order_invalid"]

result = validator.validate(invalid_data, schema)
assert not result.is_valid
assert result.error_count > 0

for error in result.errors:
    print(f"{error.path}: {error.message}")
```

### Schema Inference

```python
from Asgard.Forseti.JSONSchema.services.schema_inference_service import SchemaInferenceService

inferrer = SchemaInferenceService()

with open("sample_data_valid.json") as f:
    sample = json.load(f)["draft4_user"]

inferred = inferrer.infer_schema([sample])
print(json.dumps(inferred.schema, indent=2))
```

## Testing Scenarios

1. **Draft Compatibility**: Verify each draft version is correctly parsed
2. **Validation Accuracy**: Test valid data passes, invalid data fails
3. **Error Messages**: Verify helpful error paths and messages
4. **Conditional Schemas**: Test if/then/else evaluation
5. **Reference Resolution**: Test `$ref` and `$defs` resolution
6. **Format Validation**: Test email, uri, date-time, uuid formats
7. **Schema Composition**: Test oneOf, anyOf, allOf behavior
