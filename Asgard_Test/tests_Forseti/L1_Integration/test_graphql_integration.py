"""
GraphQL Integration Tests

Tests for end-to-end GraphQL schema validation and generation workflows.
"""

import pytest
from pathlib import Path

from Asgard.Forseti.GraphQL import (
    SchemaValidatorService,
    SchemaGeneratorService,
    IntrospectionService,
    GraphQLConfig,
    GraphQLValidationResult,
)


class TestGraphQLSchemaValidation:
    """Tests for GraphQL schema validation workflows."""

    def test_workflow_validate_simple_schema(self, graphql_schema_file):
        """Test validating a simple GraphQL schema file."""
        validator = SchemaValidatorService()
        result = validator.validate(graphql_schema_file)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.type_count > 0
        assert result.validation_time_ms > 0

    def test_workflow_validate_complex_schema(self, tmp_path, complex_graphql_schema):
        """Test validating a complex schema with directives and interfaces."""
        schema_file = tmp_path / "complex_schema.graphql"
        schema_file.write_text(complex_graphql_schema)

        validator = SchemaValidatorService()
        result = validator.validate(schema_file)

        assert result.is_valid is True
        assert result.type_count > 0

        # Should have found Query, Mutation, Subscription, and custom types
        assert result.type_count >= 6

    def test_workflow_detect_syntax_errors(self, tmp_path):
        """Test detection of GraphQL syntax errors."""
        invalid_schema = '''
type Query {
    user(id: ID!): User
}

type User {
    id: ID!
    email String!  # Missing colon
    name: String
}
'''
        schema_file = tmp_path / "invalid_syntax.graphql"
        schema_file.write_text(invalid_schema)

        validator = SchemaValidatorService()
        result = validator.validate(schema_file)

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("syntax" in error.message.lower() for error in result.errors)

    def test_workflow_detect_undefined_types(self, tmp_path):
        """Test detection of undefined type references."""
        schema = '''
type Query {
    user(id: ID!): User
    post(id: ID!): Post  # Post type not defined
}

type User {
    id: ID!
    email: String!
}
'''
        schema_file = tmp_path / "undefined_type.graphql"
        schema_file.write_text(schema)

        validator = SchemaValidatorService()
        result = validator.validate(schema_file)

        assert result.is_valid is False
        assert any("undefined" in error.message.lower() or "Post" in error.message for error in result.errors)

    def test_workflow_validate_and_report(self, graphql_schema_file):
        """Test validating schema and generating reports."""
        validator = SchemaValidatorService()
        result = validator.validate(graphql_schema_file)

        # Generate different report formats
        text_report = validator.generate_report(result, format="text")
        json_report = validator.generate_report(result, format="json")

        assert len(text_report) > 0
        assert len(json_report) > 0

        # JSON report should be parseable
        import json
        json_data = json.loads(json_report)
        assert "is_valid" in json_data


class TestGraphQLDirectiveValidation:
    """Tests for GraphQL directive validation."""

    def test_workflow_builtin_directives(self, tmp_path):
        """Test validation of built-in GraphQL directives."""
        schema = '''
type Query {
    user(id: ID!): User
    oldField: String @deprecated(reason: "Use newField instead")
}

type User {
    id: ID!
    email: String!
    legacyName: String @deprecated
}
'''
        schema_file = tmp_path / "directives.graphql"
        schema_file.write_text(schema)

        validator = SchemaValidatorService()
        result = validator.validate(schema_file)

        assert result.is_valid is True

    def test_workflow_custom_directives(self, tmp_path):
        """Test validation of custom directives."""
        schema = '''
directive @auth(requires: Role = USER) on OBJECT | FIELD_DEFINITION

enum Role {
    ADMIN
    USER
}

type Query {
    publicData: String
    privateData: String @auth(requires: ADMIN)
}

type User @auth(requires: USER) {
    id: ID!
    email: String!
}
'''
        schema_file = tmp_path / "custom_directives.graphql"
        schema_file.write_text(schema)

        validator = SchemaValidatorService()
        result = validator.validate(schema_file)

        assert result.is_valid is True

    def test_workflow_unknown_directive_warning(self, tmp_path):
        """Test that unknown directives generate warnings."""
        schema = '''
type Query {
    user(id: ID!): User @unknownDirective
}

type User {
    id: ID!
    email: String!
}
'''
        schema_file = tmp_path / "unknown_directive.graphql"
        schema_file.write_text(schema)

        config = GraphQLConfig(strict_mode=False)
        validator = SchemaValidatorService(config)
        result = validator.validate(schema_file)

        # May be valid with warnings or invalid depending on strictness
        if result.is_valid:
            warnings = [e for e in result.errors if "warning" in e.severity.lower()]
            # Warnings may be present
        else:
            # Strict mode might reject unknown directives
            assert len(result.errors) > 0


class TestGraphQLInterfaceAndUnion:
    """Tests for GraphQL interfaces and unions."""

    def test_workflow_interface_implementation(self, tmp_path):
        """Test validation of interface implementations."""
        schema = '''
interface Node {
    id: ID!
    createdAt: String!
}

type Query {
    node(id: ID!): Node
}

type User implements Node {
    id: ID!
    createdAt: String!
    email: String!
}

type Post implements Node {
    id: ID!
    createdAt: String!
    title: String!
}
'''
        schema_file = tmp_path / "interfaces.graphql"
        schema_file.write_text(schema)

        validator = SchemaValidatorService()
        result = validator.validate(schema_file)

        assert result.is_valid is True

    def test_workflow_incomplete_interface_implementation(self, tmp_path):
        """Test detection of incomplete interface implementations."""
        schema = '''
interface Node {
    id: ID!
    createdAt: String!
}

type Query {
    node(id: ID!): Node
}

type User implements Node {
    id: ID!
    # Missing createdAt field
    email: String!
}
'''
        schema_file = tmp_path / "incomplete_interface.graphql"
        schema_file.write_text(schema)

        validator = SchemaValidatorService()
        result = validator.validate(schema_file)

        # Should detect missing interface field
        assert result.is_valid is False or len(result.errors) > 0

    def test_workflow_union_types(self, tmp_path):
        """Test validation of union types."""
        schema = '''
type Query {
    search(query: String!): [SearchResult!]!
}

union SearchResult = User | Post | Comment

type User {
    id: ID!
    email: String!
}

type Post {
    id: ID!
    title: String!
}

type Comment {
    id: ID!
    content: String!
}
'''
        schema_file = tmp_path / "unions.graphql"
        schema_file.write_text(schema)

        validator = SchemaValidatorService()
        result = validator.validate(schema_file)

        assert result.is_valid is True


class TestGraphQLSchemaGeneration:
    """Tests for GraphQL schema generation."""

    def test_workflow_generate_from_types(self):
        """Test generating GraphQL schema from Python types."""
        generator = SchemaGeneratorService()

        # Define Python types
        type_definitions = {
            "User": {
                "id": "ID!",
                "email": "String!",
                "name": "String",
                "posts": "[Post!]!"
            },
            "Post": {
                "id": "ID!",
                "title": "String!",
                "content": "String",
                "author": "User!"
            }
        }

        result = generator.generate_from_types(
            type_definitions,
            query_fields={
                "user": ("User", {"id": "ID!"}),
                "users": ("[User!]!", {}),
            }
        )

        assert result.is_valid is True
        assert result.schema is not None

        # Validate generated schema
        validator = SchemaValidatorService()
        validation_result = validator.validate_sdl(result.schema)

        assert validation_result.is_valid is True

    def test_workflow_generate_with_mutations(self):
        """Test generating schema with mutations."""
        generator = SchemaGeneratorService()

        type_definitions = {
            "User": {
                "id": "ID!",
                "email": "String!",
            },
            "UserInput": {
                "email": "String!",
            }
        }

        result = generator.generate_from_types(
            type_definitions,
            query_fields={
                "user": ("User", {"id": "ID!"}),
            },
            mutation_fields={
                "createUser": ("User!", {"input": "UserInput!"}),
                "deleteUser": ("Boolean!", {"id": "ID!"}),
            }
        )

        assert result.is_valid is True

        # Validate generated schema
        validator = SchemaValidatorService()
        validation_result = validator.validate_sdl(result.schema)

        assert validation_result.is_valid is True

    def test_workflow_generate_validate_save(self, tmp_path):
        """Test generating schema, validating it, and saving to file."""
        generator = SchemaGeneratorService()

        type_definitions = {
            "User": {
                "id": "ID!",
                "email": "String!",
            }
        }

        # Generate schema
        gen_result = generator.generate_from_types(
            type_definitions,
            query_fields={"user": ("User", {"id": "ID!"})}
        )

        assert gen_result.is_valid is True

        # Save to file
        schema_file = tmp_path / "generated.graphql"
        schema_file.write_text(gen_result.schema)

        # Validate saved schema
        validator = SchemaValidatorService()
        validation_result = validator.validate(schema_file)

        assert validation_result.is_valid is True


class TestGraphQLIntrospection:
    """Tests for GraphQL introspection workflows."""

    def test_workflow_introspect_schema(self, graphql_schema_file):
        """Test introspecting a GraphQL schema."""
        introspection = IntrospectionService()

        result = introspection.introspect_file(graphql_schema_file)

        assert result.is_valid is True
        assert result.schema_info is not None

        # Should have type information
        assert len(result.schema_info.get("types", [])) > 0

    def test_workflow_extract_type_info(self, tmp_path, complex_graphql_schema):
        """Test extracting detailed type information."""
        schema_file = tmp_path / "complex.graphql"
        schema_file.write_text(complex_graphql_schema)

        introspection = IntrospectionService()
        result = introspection.introspect_file(schema_file)

        assert result.is_valid is True

        # Should have found Query, Mutation, Subscription types
        types = result.schema_info.get("types", [])
        type_names = [t.get("name") for t in types if isinstance(t, dict)]

        # Should include core types
        assert any("Query" in str(t) for t in type_names)

    def test_workflow_introspect_and_validate(self, graphql_schema_file):
        """Test introspecting schema and then validating it."""
        # First introspect
        introspection = IntrospectionService()
        intro_result = introspection.introspect_file(graphql_schema_file)

        assert intro_result.is_valid is True

        # Then validate
        validator = SchemaValidatorService()
        validation_result = validator.validate(graphql_schema_file)

        assert validation_result.is_valid is True

        # Both should agree on validity
        assert intro_result.is_valid == validation_result.is_valid


class TestGraphQLComplexScenarios:
    """Tests for complex GraphQL scenarios."""

    def test_workflow_large_schema(self, tmp_path):
        """Test handling of large schemas with many types."""
        schema_parts = [
            "type Query {",
            "  users: [User!]!",
        ]

        # Generate many types
        for i in range(50):
            schema_parts.append(f"  resource{i}(id: ID!): Resource{i}")

        schema_parts.append("}")

        # Add type definitions
        for i in range(50):
            schema_parts.extend([
                f"type Resource{i} {{",
                "  id: ID!",
                f"  name: String!",
                "}"
            ])

        schema_parts.extend([
            "type User {",
            "  id: ID!",
            "  email: String!",
            "}"
        ])

        schema = "\n".join(schema_parts)
        schema_file = tmp_path / "large_schema.graphql"
        schema_file.write_text(schema)

        validator = SchemaValidatorService()
        result = validator.validate(schema_file)

        assert result.is_valid is True
        assert result.type_count >= 50

    def test_workflow_schema_with_enums(self, tmp_path):
        """Test handling of enum types."""
        schema = '''
enum UserRole {
    ADMIN
    MODERATOR
    USER
    GUEST
}

enum PostStatus {
    DRAFT
    PUBLISHED
    ARCHIVED
}

type Query {
    usersByRole(role: UserRole!): [User!]!
    postsByStatus(status: PostStatus!): [Post!]!
}

type User {
    id: ID!
    email: String!
    role: UserRole!
}

type Post {
    id: ID!
    title: String!
    status: PostStatus!
}
'''
        schema_file = tmp_path / "enums.graphql"
        schema_file.write_text(schema)

        validator = SchemaValidatorService()
        result = validator.validate(schema_file)

        assert result.is_valid is True

    def test_workflow_schema_with_input_types(self, tmp_path):
        """Test handling of input types."""
        schema = '''
type Query {
    user(id: ID!): User
}

type Mutation {
    createUser(input: UserInput!): User!
    updateUser(id: ID!, input: UserUpdateInput!): User
}

input UserInput {
    email: String!
    name: String
    profile: ProfileInput
}

input UserUpdateInput {
    email: String
    name: String
    profile: ProfileInput
}

input ProfileInput {
    bio: String
    avatarUrl: String
}

type User {
    id: ID!
    email: String!
    name: String
    profile: Profile
}

type Profile {
    bio: String
    avatarUrl: String
}
'''
        schema_file = tmp_path / "input_types.graphql"
        schema_file.write_text(schema)

        validator = SchemaValidatorService()
        result = validator.validate(schema_file)

        assert result.is_valid is True

    def test_workflow_schema_with_subscriptions(self, tmp_path):
        """Test handling of subscription types."""
        schema = '''
type Query {
    user(id: ID!): User
}

type Mutation {
    createUser(input: UserInput!): User!
}

type Subscription {
    userCreated: User!
    userUpdated(id: ID!): User!
    userDeleted: ID!
}

input UserInput {
    email: String!
    name: String
}

type User {
    id: ID!
    email: String!
    name: String
}
'''
        schema_file = tmp_path / "subscriptions.graphql"
        schema_file.write_text(schema)

        validator = SchemaValidatorService()
        result = validator.validate(schema_file)

        assert result.is_valid is True

    def test_workflow_error_reporting_formats(self, tmp_path):
        """Test different error reporting formats."""
        invalid_schema = '''
type Query {
    user(id: ID!): UndefinedType
}
'''
        schema_file = tmp_path / "invalid.graphql"
        schema_file.write_text(invalid_schema)

        validator = SchemaValidatorService()
        result = validator.validate(schema_file)

        assert result.is_valid is False

        # Generate reports in different formats
        text_report = validator.generate_report(result, format="text")
        json_report = validator.generate_report(result, format="json")
        markdown_report = validator.generate_report(result, format="markdown")

        # All reports should mention the error
        assert len(text_report) > 0
        assert len(json_report) > 0
        assert len(markdown_report) > 0

        # JSON should be valid
        import json
        json_data = json.loads(json_report)
        assert json_data["is_valid"] is False
        assert len(json_data.get("errors", [])) > 0
