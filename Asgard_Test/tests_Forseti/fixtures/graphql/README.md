# GraphQL Test Fixtures

This directory contains GraphQL schema files for testing the Forseti GraphQL validation and parsing functionality.

## Files

| File | Description | Use Case |
|------|-------------|----------|
| `valid_schema.graphql` | Complete e-commerce schema with types, queries, mutations, subscriptions | Basic validation, type introspection |
| `complex_types.graphql` | Advanced types: interfaces, unions, nested types, recursive structures | Complex type handling |
| `invalid_syntax.graphql` | Intentional syntax errors | Error detection testing |
| `with_directives.graphql` | Custom directives for auth, validation, caching | Directive parsing |

## Schema Details

### valid_schema.graphql

A comprehensive e-commerce GraphQL schema featuring:

**Custom Scalars:**
- `DateTime`, `UUID`, `Email`, `URL`, `Money`

**Enumerations:**
- `UserRole`, `OrderStatus`, `PaymentStatus`, `ProductStatus`, `SortOrder`

**Object Types:**
- `User`, `Product`, `Order`, `Cart`, `Review`, `Category`, `Inventory`
- Connection types for pagination (`ProductConnection`, `OrderConnection`, etc.)

**Input Types:**
- `CreateUserInput`, `CreateProductInput`, `CreateOrderInput`
- `PaginationInput`, `ProductFilterInput`, `ProductSortInput`

**Root Types:**
- `Query`: User, product, category, order, and cart queries
- `Mutation`: CRUD operations for all entities
- `Subscription`: Real-time order status, inventory updates

### complex_types.graphql

Demonstrates advanced GraphQL type system features:

**Interfaces:**
- `Node` (relay-style)
- `Timestamped`, `Auditable`, `Searchable`, `Publishable`

**Unions:**
- `SearchResult = User | Project | Task | Document`
- `ActivityTarget = Task | Project | Milestone | Comment | Document`
- `NotificationContent` (polymorphic notifications)

**Complex Nesting:**
- `Organization -> Department -> Project -> Task -> Comment`
- `DocumentFolder` (recursive tree structure)

**Federation Directives:**
- `@key`, `@external`, `@requires`, `@provides`, `@extends`

### invalid_syntax.graphql

Contains intentional errors for testing error detection:

| Error Type | Example |
|------------|---------|
| Missing closing brace | `type User { ... ` |
| Missing field type | `name` without type |
| Empty enum | `enum OrderStatus { }` |
| Invalid keyword | `typo InvalidType` |
| Duplicate fields | `name: String!` twice |
| Invalid input inheritance | `input X implements Y` |
| Missing interface fields | `type Post implements Entity` without `createdAt` |
| Undefined type references | `UndefinedScalar`, `UndefinedMutation` |

### with_directives.graphql

Custom directive definitions and usage:

**Authorization:**
```graphql
directive @auth(requires: [Role!]!, allowSelf: Boolean = false) on FIELD_DEFINITION | OBJECT
```

**Validation:**
```graphql
directive @constraint(minLength: Int, maxLength: Int, pattern: String, ...) on INPUT_FIELD_DEFINITION
```

**Performance:**
```graphql
directive @cacheControl(maxAge: Int, scope: CacheScope) on FIELD_DEFINITION
directive @complexity(value: Int!, multipliers: [String!]) on FIELD_DEFINITION
directive @rateLimit(max: Int!, window: String!) on FIELD_DEFINITION
```

**Feature Flags:**
```graphql
directive @feature(flag: String!, default: Boolean = false) on FIELD_DEFINITION
```

**Auditing:**
```graphql
directive @audit(action: String!, level: AuditLevel) on FIELD_DEFINITION
```

## Usage Examples

### Schema Validation

```python
from Asgard.Forseti.GraphQL.services.schema_validator_service import SchemaValidatorService

validator = SchemaValidatorService()

# Valid schema
result = validator.validate_file("valid_schema.graphql")
assert result.is_valid

# Invalid schema
result = validator.validate_file("invalid_syntax.graphql")
assert not result.is_valid
assert len(result.errors) > 0
```

### Schema Introspection

```python
from Asgard.Forseti.GraphQL.services.introspection_service import IntrospectionService

service = IntrospectionService()
schema = service.parse_schema("valid_schema.graphql")

# Get all types
types = schema.types
print(f"Type count: {schema.type_count}")

# Get specific type
user_type = schema.get_type("User")
print(f"User fields: {[f.name for f in user_type.fields]}")
```

### Directive Analysis

```python
schema = service.parse_schema("with_directives.graphql")

# Find all directives
directives = schema.directives
for d in directives:
    print(f"{d.name}: {d.locations}")
```

## Testing Scenarios

1. **Basic Validation**: Use `valid_schema.graphql` to verify parser accepts valid schemas
2. **Error Detection**: Use `invalid_syntax.graphql` to test error messages and locations
3. **Type Resolution**: Use `complex_types.graphql` for interface/union type handling
4. **Directive Parsing**: Use `with_directives.graphql` for custom directive support
5. **Schema Comparison**: Compare `valid_schema.graphql` and `complex_types.graphql` for diff testing
