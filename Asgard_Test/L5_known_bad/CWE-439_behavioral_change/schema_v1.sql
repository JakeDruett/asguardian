-- CWE-439: Behavioral Change in New Version — baseline schema
-- Expected scanner: Forseti SchemaDiffService (paired with schema_v2_dropped_column.sql)
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL
);
