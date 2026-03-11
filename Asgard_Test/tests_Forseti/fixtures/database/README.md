# Database Schema Test Fixtures

This directory contains SQL schema files for testing Forseti's database schema analysis and diff functionality.

## Files

| File | Description |
|------|-------------|
| `schema_v1.sql` | Initial e-commerce database schema |
| `schema_v2.sql` | Modified schema with various changes |

## Schema Overview

### schema_v1.sql (Baseline)

Initial database schema for an e-commerce application:

**Tables:**
- `users` - User accounts with roles and status
- `user_profiles` - Extended user information
- `categories` - Product categories (self-referential)
- `products` - Product catalog
- `product_inventory` - Stock tracking
- `orders` - Customer orders
- `order_items` - Line items in orders
- `addresses` - User shipping/billing addresses
- `order_addresses` - Address snapshot at order time
- `payments` - Payment records
- `product_tags` - Product tagging (many-to-many)

**Key Features:**
- Foreign key relationships
- Unique constraints
- Enum types for status fields
- Composite indexes
- Timestamp tracking (created_at, updated_at)

### schema_v2.sql (Modified)

Schema with various types of changes for diff testing:

## Change Summary

### Added Tables
| Table | Description |
|-------|-------------|
| `shipments` | Order shipping/tracking information |
| `product_images` | Product image gallery |
| `wishlists` | User product wishlists |

### Dropped Tables
| Table | Reason |
|-------|--------|
| `product_tags` | Moved to separate tagging microservice |

### Added Columns
| Table | Column | Type |
|-------|--------|------|
| `users` | `phone` | VARCHAR(20) |
| `users` | `last_login_at` | TIMESTAMP |
| `products` | `compare_at_price` | DECIMAL(10,2) |
| `products` | `weight` | DECIMAL(8,2) |
| `products` | `weight_unit` | ENUM |
| `products` | `deleted_at` | TIMESTAMP (soft delete) |
| `orders` | `shipped_at` | TIMESTAMP |
| `orders` | `delivered_at` | TIMESTAMP |
| `addresses` | `company` | VARCHAR(100) |
| `user_profiles` | `date_of_birth` | DATE |

### Dropped Columns
| Table | Column | Reason |
|-------|--------|--------|
| `user_profiles` | `website` | Moved to social links service |

### Modified Columns
| Table | Column | Change |
|-------|--------|--------|
| `products` | `name` | VARCHAR(200) -> VARCHAR(255) |

### Modified Enums
| Table | Column | Change |
|-------|--------|--------|
| `users` | `role` | Added 'guest', removed 'moderator' |
| `users` | `status` | Added 'suspended' |
| `orders` | `status` | Added 'refunded' |
| `products` | `status` | Added 'archived' |

### Modified Indexes
| Table | Change |
|-------|--------|
| `addresses` | `idx_addresses_type` replaced with `idx_addresses_user_id_type` |
| `addresses` | Added `idx_addresses_is_default` |
| `users` | Added `idx_users_last_login` |
| `products` | Added `idx_products_deleted_at` |

## Usage Examples

### Schema Parsing

```python
from Asgard.Forseti.Database.services.schema_analyzer_service import SchemaAnalyzerService

analyzer = SchemaAnalyzerService()

# Parse schema from SQL file
schema_v1 = analyzer.parse_sql_file("schema_v1.sql")
print(f"Tables: {schema_v1.table_count}")
for table in schema_v1.tables:
    print(f"  {table.name}: {len(table.columns)} columns")
```

### Schema Comparison

```python
from Asgard.Forseti.Database.services.schema_diff_service import SchemaDiffService

differ = SchemaDiffService()

# Compare two schemas
diff = differ.compare("schema_v1.sql", "schema_v2.sql")

print(f"Identical: {diff.is_identical}")
print(f"Added tables: {diff.added_tables}")
print(f"Dropped tables: {diff.dropped_tables}")
print(f"Modified tables: {diff.modified_tables}")

for change in diff.changes:
    print(f"[{change.change_type}] {change.table_name}.{change.object_name}")
```

### Migration Generation

```python
from Asgard.Forseti.Database.services.migration_generator_service import MigrationGeneratorService

generator = MigrationGeneratorService()

# Generate migration SQL
migrations = generator.generate_migrations(
    source="schema_v1.sql",
    target="schema_v2.sql"
)

for migration in migrations:
    print(f"-- {migration.description}")
    print(migration.up_sql)
    print()
```

## Change Types

The `ChangeType` enum covers:

| Type | Description |
|------|-------------|
| `ADD_TABLE` | New table created |
| `DROP_TABLE` | Table removed |
| `ADD_COLUMN` | New column added |
| `DROP_COLUMN` | Column removed |
| `MODIFY_COLUMN` | Column type/constraints changed |
| `ADD_INDEX` | New index created |
| `DROP_INDEX` | Index removed |
| `ADD_FOREIGN_KEY` | New FK constraint |
| `DROP_FOREIGN_KEY` | FK constraint removed |
| `ADD_CONSTRAINT` | New constraint (CHECK, UNIQUE) |
| `DROP_CONSTRAINT` | Constraint removed |
| `RENAME_TABLE` | Table renamed |
| `RENAME_COLUMN` | Column renamed |

## Testing Scenarios

1. **Parse SQL**: Verify correct parsing of DDL statements
2. **Detect Additions**: New tables, columns, indexes
3. **Detect Removals**: Dropped tables, columns, indexes
4. **Detect Modifications**: Type changes, constraint changes
5. **Enum Changes**: Added/removed enum values
6. **Index Changes**: Modified index columns or types
7. **FK Changes**: Foreign key additions/removals
8. **Migration Generation**: SQL for applying changes
9. **Rollback Generation**: SQL for reverting changes
10. **Breaking Change Detection**: Identify destructive changes

## SQL Dialect

These schemas use MySQL/MariaDB syntax:
- `ENGINE=InnoDB`
- `AUTO_INCREMENT`
- `UNSIGNED` integers
- `ENUM` types
- `ON UPDATE CURRENT_TIMESTAMP`

For PostgreSQL or other dialects, the Forseti parser can be configured accordingly.
