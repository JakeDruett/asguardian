"""
Comprehensive L0 unit tests for Protobuf Compatibility Service.

Tests the ProtobufCompatibilityService for:
- Backward compatibility checking
- Detection of breaking changes (removed fields, changed types)
- Field number reuse detection
- Message, enum, and service compatibility
- Reserved field handling
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from Asgard.Forseti.Protobuf.models.protobuf_models import (
    ProtobufConfig,
    ProtobufSchema,
    ProtobufMessage,
    ProtobufField,
    ProtobufEnum,
    ProtobufService,
    ProtobufSyntaxVersion,
    BreakingChangeType,
    CompatibilityLevel,
)
from Asgard.Forseti.Protobuf.services.protobuf_compatibility_service import (
    ProtobufCompatibilityService,
)


class TestProtobufCompatibilityServiceInit:
    """Test ProtobufCompatibilityService initialization."""

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        service = ProtobufCompatibilityService()

        assert service.config is not None
        assert service.validator is not None

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = ProtobufConfig(strict_mode=True)
        service = ProtobufCompatibilityService(config)

        assert service.config.strict_mode is True


class TestProtobufCompatibilityServiceCheckFiles:
    """Test file-based compatibility checking."""

    def test_check_compatible_schemas(self):
        """Test checking two compatible schemas."""
        service = ProtobufCompatibilityService()

        old_content = '''
syntax = "proto3";
package test;
message User {
  string name = 1;
  int32 age = 2;
}
'''

        new_content = '''
syntax = "proto3";
package test;
message User {
  string name = 1;
  int32 age = 2;
  string email = 3;
}
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.proto', delete=False) as f:
            f.write(old_content)
            old_path = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.proto', delete=False) as f:
            f.write(new_content)
            new_path = f.name

        try:
            result = service.check(old_path, new_path)

            assert result.is_compatible is True
            assert result.compatibility_level == CompatibilityLevel.FULL
            assert len(result.breaking_changes) == 0
        finally:
            Path(old_path).unlink()
            Path(new_path).unlink()

    def test_check_with_old_schema_parse_error(self):
        """Test checking when old schema fails to parse."""
        service = ProtobufCompatibilityService()

        old_content = "invalid proto content"
        new_content = '''
syntax = "proto3";
message Test {
  string field = 1;
}
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.proto', delete=False) as f:
            f.write(old_content)
            old_path = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.proto', delete=False) as f:
            f.write(new_content)
            new_path = f.name

        try:
            result = service.check(old_path, new_path)

            assert result.is_compatible is False
            assert result.compatibility_level == CompatibilityLevel.NONE
            assert len(result.breaking_changes) >= 1
        finally:
            Path(old_path).unlink()
            Path(new_path).unlink()


class TestProtobufCompatibilityServiceRemovedMessages:
    """Test detection of removed messages."""

    def test_detect_removed_message(self):
        """Test detection of removed message type."""
        service = ProtobufCompatibilityService()

        old_schema = ProtobufSchema(
            messages=[
                ProtobufMessage(name="User"),
                ProtobufMessage(name="Product")
            ]
        )

        new_schema = ProtobufSchema(
            messages=[ProtobufMessage(name="User")]
        )

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert "Product" in result.removed_messages
        assert any(
            c.change_type == BreakingChangeType.REMOVED_MESSAGE
            for c in result.breaking_changes
        )

    def test_detect_multiple_removed_messages(self):
        """Test detection of multiple removed messages."""
        service = ProtobufCompatibilityService()

        old_schema = ProtobufSchema(
            messages=[
                ProtobufMessage(name="M1"),
                ProtobufMessage(name="M2"),
                ProtobufMessage(name="M3")
            ]
        )

        new_schema = ProtobufSchema(messages=[])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert len(result.removed_messages) == 3
        assert len(result.breaking_changes) >= 3


class TestProtobufCompatibilityServiceAddedMessages:
    """Test detection of added messages."""

    def test_detect_added_message(self):
        """Test detection of added message (non-breaking)."""
        service = ProtobufCompatibilityService()

        old_schema = ProtobufSchema(
            messages=[ProtobufMessage(name="User")]
        )

        new_schema = ProtobufSchema(
            messages=[
                ProtobufMessage(name="User"),
                ProtobufMessage(name="Product")
            ]
        )

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is True
        assert "Product" in result.added_messages
        assert len(result.breaking_changes) == 0


class TestProtobufCompatibilityServiceRemovedFields:
    """Test detection of removed fields."""

    def test_detect_removed_field_not_reserved(self):
        """Test detection of removed field without reservation (breaking)."""
        service = ProtobufCompatibilityService()

        old_msg = ProtobufMessage(
            name="User",
            fields=[
                ProtobufField(name="name", number=1, type="string"),
                ProtobufField(name="email", number=2, type="string")
            ]
        )

        new_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="name", number=1, type="string")]
        )

        old_schema = ProtobufSchema(messages=[old_msg])
        new_schema = ProtobufSchema(messages=[new_msg])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert any(
            c.change_type == BreakingChangeType.REMOVED_FIELD and
            "email" in c.message
            for c in result.breaking_changes
        )

    def test_detect_removed_field_with_reservation(self):
        """Test detection of removed field with reservation (warning)."""
        service = ProtobufCompatibilityService()

        old_msg = ProtobufMessage(
            name="User",
            fields=[
                ProtobufField(name="name", number=1, type="string"),
                ProtobufField(name="email", number=2, type="string")
            ]
        )

        new_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="name", number=1, type="string")],
            reserved_numbers=[2]
        )

        old_schema = ProtobufSchema(messages=[old_msg])
        new_schema = ProtobufSchema(messages=[new_msg])

        result = service.check_schemas(old_schema, new_schema)

        assert any(
            c.change_type == BreakingChangeType.REMOVED_FIELD and
            c.severity == "warning"
            for c in result.warnings
        )


class TestProtobufCompatibilityServiceFieldTypeChanges:
    """Test detection of field type changes."""

    def test_detect_field_type_change(self):
        """Test detection of field type change (breaking)."""
        service = ProtobufCompatibilityService()

        old_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="age", number=1, type="int32")]
        )

        new_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="age", number=1, type="string")]
        )

        old_schema = ProtobufSchema(messages=[old_msg])
        new_schema = ProtobufSchema(messages=[new_msg])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert any(
            c.change_type == BreakingChangeType.CHANGED_FIELD_TYPE and
            c.old_value == "int32" and
            c.new_value == "string"
            for c in result.breaking_changes
        )


class TestProtobufCompatibilityServiceFieldNumberChanges:
    """Test detection of field number changes."""

    def test_detect_field_number_change(self):
        """Test detection of field number change (breaking)."""
        service = ProtobufCompatibilityService()

        old_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="name", number=1, type="string")]
        )

        new_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="name", number=2, type="string")]
        )

        old_schema = ProtobufSchema(messages=[old_msg])
        new_schema = ProtobufSchema(messages=[new_msg])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert any(
            c.change_type == BreakingChangeType.CHANGED_FIELD_NUMBER
            for c in result.breaking_changes
        )


class TestProtobufCompatibilityServiceFieldLabelChanges:
    """Test detection of field label changes."""

    def test_detect_repeated_to_singular_change(self):
        """Test detection of repeated to singular change (breaking)."""
        service = ProtobufCompatibilityService()

        old_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="tags", number=1, type="string", label="repeated")]
        )

        new_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="tags", number=1, type="string")]
        )

        old_schema = ProtobufSchema(messages=[old_msg])
        new_schema = ProtobufSchema(messages=[new_msg])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert any(
            c.change_type == BreakingChangeType.CHANGED_FIELD_LABEL
            for c in result.breaking_changes
        )

    def test_detect_singular_to_repeated_change(self):
        """Test detection of singular to repeated change (breaking)."""
        service = ProtobufCompatibilityService()

        old_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="tag", number=1, type="string")]
        )

        new_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="tag", number=1, type="string", label="repeated")]
        )

        old_schema = ProtobufSchema(messages=[old_msg])
        new_schema = ProtobufSchema(messages=[new_msg])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert any(
            c.change_type == BreakingChangeType.CHANGED_FIELD_LABEL
            for c in result.breaking_changes
        )


class TestProtobufCompatibilityServiceReservedFieldReuse:
    """Test detection of reserved field reuse."""

    def test_detect_reserved_number_reuse(self):
        """Test detection of reserved field number reuse (breaking)."""
        service = ProtobufCompatibilityService()

        old_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="name", number=1, type="string")],
            reserved_numbers=[5]
        )

        new_msg = ProtobufMessage(
            name="User",
            fields=[
                ProtobufField(name="name", number=1, type="string"),
                ProtobufField(name="new_field", number=5, type="string")
            ]
        )

        old_schema = ProtobufSchema(messages=[old_msg])
        new_schema = ProtobufSchema(messages=[new_msg])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert any(
            c.change_type == BreakingChangeType.RESERVED_NUMBER_REUSED
            for c in result.breaking_changes
        )

    def test_detect_reserved_name_reuse(self):
        """Test detection of reserved field name reuse (breaking)."""
        service = ProtobufCompatibilityService()

        old_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="name", number=1, type="string")],
            reserved_names=["old_field"]
        )

        new_msg = ProtobufMessage(
            name="User",
            fields=[
                ProtobufField(name="name", number=1, type="string"),
                ProtobufField(name="old_field", number=2, type="string")
            ]
        )

        old_schema = ProtobufSchema(messages=[old_msg])
        new_schema = ProtobufSchema(messages=[new_msg])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert any(
            c.change_type == BreakingChangeType.RESERVED_FIELD_REUSED
            for c in result.breaking_changes
        )

    def test_detect_reserved_range_reuse(self):
        """Test detection of reserved field range reuse (breaking)."""
        service = ProtobufCompatibilityService()

        old_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="name", number=1, type="string")],
            reserved_ranges=[(10, 20)]
        )

        new_msg = ProtobufMessage(
            name="User",
            fields=[
                ProtobufField(name="name", number=1, type="string"),
                ProtobufField(name="new_field", number=15, type="string")
            ]
        )

        old_schema = ProtobufSchema(messages=[old_msg])
        new_schema = ProtobufSchema(messages=[new_msg])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert any(
            c.change_type == BreakingChangeType.RESERVED_NUMBER_REUSED
            for c in result.breaking_changes
        )


class TestProtobufCompatibilityServiceNestedMessages:
    """Test nested message compatibility checking."""

    def test_detect_removed_nested_message(self):
        """Test detection of removed nested message."""
        service = ProtobufCompatibilityService()

        nested = ProtobufMessage(name="Address")
        old_msg = ProtobufMessage(name="User", nested_messages=[nested])

        new_msg = ProtobufMessage(name="User", nested_messages=[])

        old_schema = ProtobufSchema(messages=[old_msg])
        new_schema = ProtobufSchema(messages=[new_msg])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert any(
            c.change_type == BreakingChangeType.REMOVED_MESSAGE and
            "Address" in c.message
            for c in result.breaking_changes
        )

    def test_nested_message_field_changes(self):
        """Test detection of field changes in nested messages."""
        service = ProtobufCompatibilityService()

        old_nested = ProtobufMessage(
            name="Address",
            fields=[ProtobufField(name="street", number=1, type="string")]
        )
        old_msg = ProtobufMessage(name="User", nested_messages=[old_nested])

        new_nested = ProtobufMessage(name="Address", fields=[])
        new_msg = ProtobufMessage(name="User", nested_messages=[new_nested])

        old_schema = ProtobufSchema(messages=[old_msg])
        new_schema = ProtobufSchema(messages=[new_msg])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False


class TestProtobufCompatibilityServiceEnums:
    """Test enum compatibility checking."""

    def test_detect_removed_enum(self):
        """Test detection of removed enum."""
        service = ProtobufCompatibilityService()

        old_schema = ProtobufSchema(
            enums=[ProtobufEnum(name="Status", values={"ACTIVE": 0})]
        )

        new_schema = ProtobufSchema(enums=[])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert any(
            c.change_type == BreakingChangeType.REMOVED_ENUM
            for c in result.breaking_changes
        )

    def test_detect_removed_enum_value_without_reservation(self):
        """Test detection of removed enum value without reservation."""
        service = ProtobufCompatibilityService()

        old_enum = ProtobufEnum(name="Status", values={"ACTIVE": 0, "INACTIVE": 1})
        new_enum = ProtobufEnum(name="Status", values={"ACTIVE": 0})

        old_schema = ProtobufSchema(enums=[old_enum])
        new_schema = ProtobufSchema(enums=[new_enum])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert any(
            c.change_type == BreakingChangeType.REMOVED_ENUM_VALUE
            for c in result.breaking_changes
        )

    def test_detect_removed_enum_value_with_reservation(self):
        """Test detection of removed enum value with reservation (warning)."""
        service = ProtobufCompatibilityService()

        old_enum = ProtobufEnum(name="Status", values={"ACTIVE": 0, "INACTIVE": 1})
        new_enum = ProtobufEnum(
            name="Status",
            values={"ACTIVE": 0},
            reserved_names=["INACTIVE"],
            reserved_numbers=[1]
        )

        old_schema = ProtobufSchema(enums=[old_enum])
        new_schema = ProtobufSchema(enums=[new_enum])

        result = service.check_schemas(old_schema, new_schema)

        assert any(
            c.change_type == BreakingChangeType.REMOVED_ENUM_VALUE and
            c.severity == "warning"
            for c in result.warnings
        )

    def test_detect_enum_value_number_change(self):
        """Test detection of enum value number change."""
        service = ProtobufCompatibilityService()

        old_enum = ProtobufEnum(name="Status", values={"ACTIVE": 0})
        new_enum = ProtobufEnum(name="Status", values={"ACTIVE": 1})

        old_schema = ProtobufSchema(enums=[old_enum])
        new_schema = ProtobufSchema(enums=[new_enum])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert any(
            c.change_type == BreakingChangeType.CHANGED_ENUM_VALUE_NUMBER
            for c in result.breaking_changes
        )


class TestProtobufCompatibilityServiceNestedEnums:
    """Test nested enum compatibility checking."""

    def test_detect_removed_nested_enum(self):
        """Test detection of removed nested enum."""
        service = ProtobufCompatibilityService()

        nested_enum = ProtobufEnum(name="Type", values={"UNKNOWN": 0})
        old_msg = ProtobufMessage(name="User", nested_enums=[nested_enum])
        new_msg = ProtobufMessage(name="User", nested_enums=[])

        old_schema = ProtobufSchema(messages=[old_msg])
        new_schema = ProtobufSchema(messages=[new_msg])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert any(
            c.change_type == BreakingChangeType.REMOVED_ENUM
            for c in result.breaking_changes
        )


class TestProtobufCompatibilityServiceServices:
    """Test service compatibility checking."""

    def test_detect_removed_service(self):
        """Test detection of removed service."""
        service = ProtobufCompatibilityService()

        old_schema = ProtobufSchema(
            services=[ProtobufService(name="UserService")]
        )

        new_schema = ProtobufSchema(services=[])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert any(
            c.change_type == BreakingChangeType.REMOVED_SERVICE
            for c in result.breaking_changes
        )

    def test_detect_removed_rpc(self):
        """Test detection of removed RPC method."""
        service = ProtobufCompatibilityService()

        old_service = ProtobufService(
            name="UserService",
            rpcs={
                "GetUser": {"input": "Request", "output": "Response"},
                "DeleteUser": {"input": "Request", "output": "Response"}
            }
        )

        new_service = ProtobufService(
            name="UserService",
            rpcs={"GetUser": {"input": "Request", "output": "Response"}}
        )

        old_schema = ProtobufSchema(services=[old_service])
        new_schema = ProtobufSchema(services=[new_service])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False
        assert any(
            c.change_type == BreakingChangeType.REMOVED_RPC
            for c in result.breaking_changes
        )

    def test_detect_rpc_input_type_change(self):
        """Test detection of RPC input type change."""
        service = ProtobufCompatibilityService()

        old_service = ProtobufService(
            name="UserService",
            rpcs={"GetUser": {"input": "Request", "output": "Response"}}
        )

        new_service = ProtobufService(
            name="UserService",
            rpcs={"GetUser": {"input": "NewRequest", "output": "Response"}}
        )

        old_schema = ProtobufSchema(services=[old_service])
        new_schema = ProtobufSchema(services=[new_service])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False

    def test_detect_rpc_output_type_change(self):
        """Test detection of RPC output type change."""
        service = ProtobufCompatibilityService()

        old_service = ProtobufService(
            name="UserService",
            rpcs={"GetUser": {"input": "Request", "output": "Response"}}
        )

        new_service = ProtobufService(
            name="UserService",
            rpcs={"GetUser": {"input": "Request", "output": "NewResponse"}}
        )

        old_schema = ProtobufSchema(services=[old_service])
        new_schema = ProtobufSchema(services=[new_service])

        result = service.check_schemas(old_schema, new_schema)

        assert result.is_compatible is False


class TestProtobufCompatibilityServiceCompatibilityLevels:
    """Test compatibility level determination."""

    def test_full_compatibility(self):
        """Test full compatibility (no breaking changes)."""
        service = ProtobufCompatibilityService()

        old_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="name", number=1, type="string")]
        )

        new_msg = ProtobufMessage(
            name="User",
            fields=[
                ProtobufField(name="name", number=1, type="string"),
                ProtobufField(name="email", number=2, type="string")
            ]
        )

        old_schema = ProtobufSchema(messages=[old_msg])
        new_schema = ProtobufSchema(messages=[new_msg])

        result = service.check_schemas(old_schema, new_schema)

        assert result.compatibility_level == CompatibilityLevel.FULL

    def test_backward_compatibility(self):
        """Test backward compatibility (fields added)."""
        service = ProtobufCompatibilityService()

        old_schema = ProtobufSchema(
            messages=[ProtobufMessage(name="User")]
        )

        new_schema = ProtobufSchema(
            messages=[
                ProtobufMessage(name="User"),
                ProtobufMessage(name="Product")
            ]
        )

        result = service.check_schemas(old_schema, new_schema)

        assert result.compatibility_level == CompatibilityLevel.FULL

    def test_no_compatibility(self):
        """Test no compatibility (breaking changes)."""
        service = ProtobufCompatibilityService()

        old_schema = ProtobufSchema(
            messages=[ProtobufMessage(name="User")]
        )

        new_schema = ProtobufSchema(messages=[])

        result = service.check_schemas(old_schema, new_schema)

        assert result.compatibility_level == CompatibilityLevel.NONE


class TestProtobufCompatibilityServiceReportGeneration:
    """Test report generation functionality."""

    def test_generate_text_report(self):
        """Test generation of text format report."""
        service = ProtobufCompatibilityService()

        old_schema = ProtobufSchema(messages=[ProtobufMessage(name="User")])
        new_schema = ProtobufSchema(messages=[])

        result = service.check_schemas(old_schema, new_schema)
        report = service.generate_report(result, format="text")

        assert "Protobuf Compatibility Report" in report
        assert "Breaking Changes:" in report

    def test_generate_json_report(self):
        """Test generation of JSON format report."""
        service = ProtobufCompatibilityService()

        old_schema = ProtobufSchema(messages=[ProtobufMessage(name="User")])
        new_schema = ProtobufSchema(messages=[])

        result = service.check_schemas(old_schema, new_schema)
        report = service.generate_report(result, format="json")

        assert "is_compatible" in report
        assert "compatibility_level" in report

    def test_generate_markdown_report(self):
        """Test generation of markdown format report."""
        service = ProtobufCompatibilityService()

        old_schema = ProtobufSchema(messages=[ProtobufMessage(name="User")])
        new_schema = ProtobufSchema(messages=[])

        result = service.check_schemas(old_schema, new_schema)
        report = service.generate_report(result, format="markdown")

        assert "# Protobuf Compatibility Report" in report
        assert "## Breaking Changes" in report


class TestProtobufCompatibilityServiceModifiedMessages:
    """Test modified message tracking."""

    def test_track_modified_messages(self):
        """Test that modified messages are tracked."""
        service = ProtobufCompatibilityService()

        old_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="name", number=1, type="string")]
        )

        new_msg = ProtobufMessage(
            name="User",
            fields=[ProtobufField(name="name", number=1, type="int32")]
        )

        old_schema = ProtobufSchema(messages=[old_msg])
        new_schema = ProtobufSchema(messages=[new_msg])

        result = service.check_schemas(old_schema, new_schema)

        assert "User" in result.modified_messages


class TestProtobufCompatibilityServiceTimingAndMetadata:
    """Test timing and metadata tracking."""

    def test_check_time_recorded(self):
        """Test that compatibility check time is recorded."""
        service = ProtobufCompatibilityService()

        old_schema = ProtobufSchema(messages=[])
        new_schema = ProtobufSchema(messages=[])

        result = service.check_schemas(old_schema, new_schema)

        assert result.check_time_ms >= 0.0

    def test_file_paths_recorded(self):
        """Test that file paths are recorded."""
        service = ProtobufCompatibilityService()

        old_content = '''
syntax = "proto3";
message Test {
  string field = 1;
}
'''

        new_content = '''
syntax = "proto3";
message Test {
  string field = 1;
}
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.proto', delete=False) as f:
            f.write(old_content)
            old_path = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.proto', delete=False) as f:
            f.write(new_content)
            new_path = f.name

        try:
            result = service.check(old_path, new_path)

            assert result.source_file == old_path
            assert result.target_file == new_path
        finally:
            Path(old_path).unlink()
            Path(new_path).unlink()
