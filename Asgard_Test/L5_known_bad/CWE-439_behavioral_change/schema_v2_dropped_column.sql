-- CWE-439: Behavioral Change in New Version — destructive migration target
-- Drops the email column: breaking change (DROP COLUMN)
-- Expected scanner: Forseti SchemaDiffService (has_breaking_changes = True)
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);
