"""
Protobuf Compatibility Checker Service.

Checks backward compatibility between Protocol Buffer schema versions.
"""

import json
import time
from pathlib import Path
from typing import Any, Optional

from Asgard.Forseti.Protobuf.models.protobuf_models import (
    BreakingChange,
    BreakingChangeType,
    CompatibilityLevel,
    ProtobufCompatibilityResult,
    ProtobufConfig,
    ProtobufEnum,
    ProtobufMessage,
    ProtobufSchema,
)
from Asgard.Forseti.Protobuf.services.protobuf_validator_service import (
    ProtobufValidatorService,
)


class ProtobufCompatibilityService:
    """
    Service for checking Protocol Buffer schema compatibility.

    Checks backward compatibility between schema versions and reports
    breaking changes.

    Usage:
        service = ProtobufCompatibilityService()
        result = service.check("old.proto", "new.proto")
        if not result.is_compatible:
            for change in result.breaking_changes:
                print(f"Breaking: {change.message}")
    """

    def __init__(self, config: Optional[ProtobufConfig] = None):
        """
        Initialize the compatibility checker service.

        Args:
            config: Optional configuration for checking behavior.
        """
        self.config = config or ProtobufConfig()
        self.validator = ProtobufValidatorService(self.config)

    def check(
        self,
        old_proto_path: str | Path,
        new_proto_path: str | Path
    ) -> ProtobufCompatibilityResult:
        """
        Check compatibility between two Protocol Buffer schema versions.

        Args:
            old_proto_path: Path to the old proto file.
            new_proto_path: Path to the new proto file.

        Returns:
            ProtobufCompatibilityResult with compatibility details.
        """
        start_time = time.time()

        breaking_changes: list[BreakingChange] = []
        warnings: list[BreakingChange] = []
        added_messages: list[str] = []
        removed_messages: list[str] = []
        modified_messages: list[str] = []

        # Validate and parse both schemas
        old_result = self.validator.validate_file(old_proto_path)
        new_result = self.validator.validate_file(new_proto_path)

        # Check if parsing succeeded
        if not old_result.parsed_schema:
            return ProtobufCompatibilityResult(
                is_compatible=False,
                compatibility_level=CompatibilityLevel.NONE,
                source_file=str(old_proto_path),
                target_file=str(new_proto_path),
                breaking_changes=[BreakingChange(
                    change_type=BreakingChangeType.REMOVED_MESSAGE,
                    path="/",
                    message=f"Failed to parse old schema: {old_result.errors[0].message if old_result.errors else 'Unknown error'}",
                )],
                check_time_ms=(time.time() - start_time) * 1000,
            )

        if not new_result.parsed_schema:
            return ProtobufCompatibilityResult(
                is_compatible=False,
                compatibility_level=CompatibilityLevel.NONE,
                source_file=str(old_proto_path),
                target_file=str(new_proto_path),
                breaking_changes=[BreakingChange(
                    change_type=BreakingChangeType.REMOVED_MESSAGE,
                    path="/",
                    message=f"Failed to parse new schema: {new_result.errors[0].message if new_result.errors else 'Unknown error'}",
                )],
                check_time_ms=(time.time() - start_time) * 1000,
            )

        old_schema = old_result.parsed_schema
        new_schema = new_result.parsed_schema

        # Check messages
        old_message_names = {msg.name for msg in old_schema.messages}
        new_message_names = {msg.name for msg in new_schema.messages}

        # Find removed messages (breaking)
        for msg_name in old_message_names - new_message_names:
            removed_messages.append(msg_name)
            breaking_changes.append(BreakingChange(
                change_type=BreakingChangeType.REMOVED_MESSAGE,
                path=f"message {msg_name}",
                message=f"Message '{msg_name}' was removed",
                old_value=msg_name,
                severity="error",
                mitigation="Keep the message or mark it as deprecated first",
            ))

        # Find added messages (non-breaking)
        for msg_name in new_message_names - old_message_names:
            added_messages.append(msg_name)

        # Check modified messages
        old_messages_map = {msg.name: msg for msg in old_schema.messages}
        new_messages_map = {msg.name: msg for msg in new_schema.messages}

        for msg_name in old_message_names & new_message_names:
            old_msg = old_messages_map[msg_name]
            new_msg = new_messages_map[msg_name]

            msg_changes = self._check_message_compatibility(old_msg, new_msg)
            if msg_changes:
                modified_messages.append(msg_name)
                for change in msg_changes:
                    if change.severity == "error":
                        breaking_changes.append(change)
                    else:
                        warnings.append(change)

        # Check enums
        enum_changes = self._check_enums_compatibility(
            old_schema.enums,
            new_schema.enums
        )
        for change in enum_changes:
            if change.severity == "error":
                breaking_changes.append(change)
            else:
                warnings.append(change)

        # Check services
        service_changes = self._check_services_compatibility(
            old_schema.services,
            new_schema.services
        )
        for change in service_changes:
            if change.severity == "error":
                breaking_changes.append(change)
            else:
                warnings.append(change)

        # Determine compatibility level
        if not breaking_changes:
            compatibility_level = CompatibilityLevel.FULL
        elif not removed_messages:
            compatibility_level = CompatibilityLevel.BACKWARD
        else:
            compatibility_level = CompatibilityLevel.NONE

        check_time_ms = (time.time() - start_time) * 1000

        return ProtobufCompatibilityResult(
            is_compatible=len(breaking_changes) == 0,
            compatibility_level=compatibility_level,
            source_file=str(old_proto_path),
            target_file=str(new_proto_path),
            breaking_changes=breaking_changes,
            warnings=warnings,
            added_messages=added_messages,
            removed_messages=removed_messages,
            modified_messages=modified_messages,
            check_time_ms=check_time_ms,
        )

    def check_schemas(
        self,
        old_schema: ProtobufSchema,
        new_schema: ProtobufSchema
    ) -> ProtobufCompatibilityResult:
        """
        Check compatibility between two parsed schemas.

        Args:
            old_schema: The old schema.
            new_schema: The new schema.

        Returns:
            ProtobufCompatibilityResult with compatibility details.
        """
        start_time = time.time()

        breaking_changes: list[BreakingChange] = []
        warnings: list[BreakingChange] = []
        added_messages: list[str] = []
        removed_messages: list[str] = []
        modified_messages: list[str] = []

        # Check messages
        old_message_names = {msg.name for msg in old_schema.messages}
        new_message_names = {msg.name for msg in new_schema.messages}

        # Find removed messages
        for msg_name in old_message_names - new_message_names:
            removed_messages.append(msg_name)
            breaking_changes.append(BreakingChange(
                change_type=BreakingChangeType.REMOVED_MESSAGE,
                path=f"message {msg_name}",
                message=f"Message '{msg_name}' was removed",
                old_value=msg_name,
                severity="error",
            ))

        # Find added messages
        for msg_name in new_message_names - old_message_names:
            added_messages.append(msg_name)

        # Check modified messages
        old_messages_map = {msg.name: msg for msg in old_schema.messages}
        new_messages_map = {msg.name: msg for msg in new_schema.messages}

        for msg_name in old_message_names & new_message_names:
            old_msg = old_messages_map[msg_name]
            new_msg = new_messages_map[msg_name]

            msg_changes = self._check_message_compatibility(old_msg, new_msg)
            if msg_changes:
                modified_messages.append(msg_name)
                for change in msg_changes:
                    if change.severity == "error":
                        breaking_changes.append(change)
                    else:
                        warnings.append(change)

        # Determine compatibility level
        if not breaking_changes:
            compatibility_level = CompatibilityLevel.FULL
        elif not removed_messages:
            compatibility_level = CompatibilityLevel.BACKWARD
        else:
            compatibility_level = CompatibilityLevel.NONE

        return ProtobufCompatibilityResult(
            is_compatible=len(breaking_changes) == 0,
            compatibility_level=compatibility_level,
            source_file=old_schema.file_path,
            target_file=new_schema.file_path,
            breaking_changes=breaking_changes,
            warnings=warnings,
            added_messages=added_messages,
            removed_messages=removed_messages,
            modified_messages=modified_messages,
            check_time_ms=(time.time() - start_time) * 1000,
        )

    def _check_message_compatibility(
        self,
        old_msg: ProtobufMessage,
        new_msg: ProtobufMessage
    ) -> list[BreakingChange]:
        """Check compatibility for a single message."""
        changes: list[BreakingChange] = []
        base_path = f"message {old_msg.name}"

        old_fields_by_number = {f.number: f for f in old_msg.fields}
        new_fields_by_number = {f.number: f for f in new_msg.fields}
        old_fields_by_name = {f.name: f for f in old_msg.fields}
        new_fields_by_name = {f.name: f for f in new_msg.fields}

        # Check for removed fields (breaking)
        for field_number, old_field in old_fields_by_number.items():
            if field_number not in new_fields_by_number:
                # Check if field number is now reserved
                is_reserved = (
                    field_number in new_msg.reserved_numbers or
                    any(start <= field_number <= end for start, end in new_msg.reserved_ranges)
                )
                if not is_reserved:
                    changes.append(BreakingChange(
                        change_type=BreakingChangeType.REMOVED_FIELD,
                        path=f"{base_path}.{old_field.name}",
                        message=f"Field '{old_field.name}' (number {field_number}) was removed without being reserved",
                        old_value=f"{old_field.name} = {field_number}",
                        severity="error",
                        mitigation="Add field number to reserved list to prevent reuse",
                    ))
                else:
                    changes.append(BreakingChange(
                        change_type=BreakingChangeType.REMOVED_FIELD,
                        path=f"{base_path}.{old_field.name}",
                        message=f"Field '{old_field.name}' (number {field_number}) was removed (properly reserved)",
                        old_value=f"{old_field.name} = {field_number}",
                        severity="warning",
                    ))

        # Check for type changes (breaking)
        for field_number in old_fields_by_number.keys() & new_fields_by_number.keys():
            old_field = old_fields_by_number[field_number]
            new_field = new_fields_by_number[field_number]

            if old_field.type != new_field.type:
                changes.append(BreakingChange(
                    change_type=BreakingChangeType.CHANGED_FIELD_TYPE,
                    path=f"{base_path}.{old_field.name}",
                    message=f"Field type changed from '{old_field.type}' to '{new_field.type}'",
                    old_value=old_field.type,
                    new_value=new_field.type,
                    severity="error",
                    mitigation="Create a new field with the new type instead",
                ))

            # Check label changes
            if old_field.label != new_field.label:
                # Some label changes are more severe than others
                severity = "error"
                if old_field.label == "repeated" and new_field.label != "repeated":
                    severity = "error"
                elif new_field.label == "repeated" and old_field.label != "repeated":
                    severity = "error"
                else:
                    severity = "warning"

                changes.append(BreakingChange(
                    change_type=BreakingChangeType.CHANGED_FIELD_LABEL,
                    path=f"{base_path}.{old_field.name}",
                    message=f"Field label changed from '{old_field.label or 'singular'}' to '{new_field.label or 'singular'}'",
                    old_value=old_field.label or "singular",
                    new_value=new_field.label or "singular",
                    severity=severity,
                ))

        # Check for field number changes (breaking - same name, different number)
        for field_name in old_fields_by_name.keys() & new_fields_by_name.keys():
            old_field = old_fields_by_name[field_name]
            new_field = new_fields_by_name[field_name]

            if old_field.number != new_field.number:
                changes.append(BreakingChange(
                    change_type=BreakingChangeType.CHANGED_FIELD_NUMBER,
                    path=f"{base_path}.{field_name}",
                    message=f"Field number changed from {old_field.number} to {new_field.number}",
                    old_value=str(old_field.number),
                    new_value=str(new_field.number),
                    severity="error",
                    mitigation="Field numbers must remain stable",
                ))

        # Check reserved field reuse (breaking)
        for field_number in new_fields_by_number.keys():
            if field_number in old_msg.reserved_numbers:
                changes.append(BreakingChange(
                    change_type=BreakingChangeType.RESERVED_NUMBER_REUSED,
                    path=f"{base_path}",
                    message=f"Reserved field number {field_number} is now being used",
                    new_value=str(field_number),
                    severity="error",
                    mitigation="Reserved field numbers must never be reused",
                ))
            for start, end in old_msg.reserved_ranges:
                if start <= field_number <= end:
                    if field_number not in old_fields_by_number:
                        changes.append(BreakingChange(
                            change_type=BreakingChangeType.RESERVED_NUMBER_REUSED,
                            path=f"{base_path}",
                            message=f"Field number {field_number} from reserved range {start}-{end} is now being used",
                            new_value=str(field_number),
                            severity="error",
                        ))

        for new_field in new_msg.fields:
            if new_field.name in old_msg.reserved_names:
                changes.append(BreakingChange(
                    change_type=BreakingChangeType.RESERVED_FIELD_REUSED,
                    path=f"{base_path}.{new_field.name}",
                    message=f"Reserved field name '{new_field.name}' is now being used",
                    new_value=new_field.name,
                    severity="error",
                    mitigation="Reserved field names must never be reused",
                ))

        # Check nested messages
        old_nested_map = {m.name: m for m in old_msg.nested_messages}
        new_nested_map = {m.name: m for m in new_msg.nested_messages}

        for nested_name in old_nested_map.keys() - new_nested_map.keys():
            changes.append(BreakingChange(
                change_type=BreakingChangeType.REMOVED_MESSAGE,
                path=f"{base_path}.{nested_name}",
                message=f"Nested message '{nested_name}' was removed",
                old_value=nested_name,
                severity="error",
            ))

        for nested_name in old_nested_map.keys() & new_nested_map.keys():
            nested_changes = self._check_message_compatibility(
                old_nested_map[nested_name],
                new_nested_map[nested_name]
            )
            changes.extend(nested_changes)

        # Check nested enums
        old_enum_map = {e.name: e for e in old_msg.nested_enums}
        new_enum_map = {e.name: e for e in new_msg.nested_enums}

        for enum_name in old_enum_map.keys() - new_enum_map.keys():
            changes.append(BreakingChange(
                change_type=BreakingChangeType.REMOVED_ENUM,
                path=f"{base_path}.{enum_name}",
                message=f"Nested enum '{enum_name}' was removed",
                old_value=enum_name,
                severity="error",
            ))

        for enum_name in old_enum_map.keys() & new_enum_map.keys():
            enum_changes = self._check_enum_compatibility(
                old_enum_map[enum_name],
                new_enum_map[enum_name],
                f"{base_path}.{enum_name}"
            )
            changes.extend(enum_changes)

        return changes

    def _check_enums_compatibility(
        self,
        old_enums: list[ProtobufEnum],
        new_enums: list[ProtobufEnum]
    ) -> list[BreakingChange]:
        """Check compatibility for top-level enums."""
        changes: list[BreakingChange] = []

        old_enum_map = {e.name: e for e in old_enums}
        new_enum_map = {e.name: e for e in new_enums}

        # Check for removed enums
        for enum_name in old_enum_map.keys() - new_enum_map.keys():
            changes.append(BreakingChange(
                change_type=BreakingChangeType.REMOVED_ENUM,
                path=f"enum {enum_name}",
                message=f"Enum '{enum_name}' was removed",
                old_value=enum_name,
                severity="error",
                mitigation="Keep the enum or deprecate it first",
            ))

        # Check modified enums
        for enum_name in old_enum_map.keys() & new_enum_map.keys():
            enum_changes = self._check_enum_compatibility(
                old_enum_map[enum_name],
                new_enum_map[enum_name],
                f"enum {enum_name}"
            )
            changes.extend(enum_changes)

        return changes

    def _check_enum_compatibility(
        self,
        old_enum: ProtobufEnum,
        new_enum: ProtobufEnum,
        base_path: str
    ) -> list[BreakingChange]:
        """Check compatibility for a single enum."""
        changes: list[BreakingChange] = []

        # Check for removed enum values
        for value_name, value_number in old_enum.values.items():
            if value_name not in new_enum.values:
                is_reserved = (
                    value_name in new_enum.reserved_names or
                    value_number in new_enum.reserved_numbers
                )
                if not is_reserved:
                    changes.append(BreakingChange(
                        change_type=BreakingChangeType.REMOVED_ENUM_VALUE,
                        path=f"{base_path}.{value_name}",
                        message=f"Enum value '{value_name}' (= {value_number}) was removed without being reserved",
                        old_value=f"{value_name} = {value_number}",
                        severity="error",
                        mitigation="Add value name/number to reserved list",
                    ))
                else:
                    changes.append(BreakingChange(
                        change_type=BreakingChangeType.REMOVED_ENUM_VALUE,
                        path=f"{base_path}.{value_name}",
                        message=f"Enum value '{value_name}' was removed (properly reserved)",
                        old_value=f"{value_name} = {value_number}",
                        severity="warning",
                    ))

        # Check for value number changes
        for value_name in old_enum.values.keys() & new_enum.values.keys():
            old_number = old_enum.values[value_name]
            new_number = new_enum.values[value_name]

            if old_number != new_number:
                changes.append(BreakingChange(
                    change_type=BreakingChangeType.CHANGED_ENUM_VALUE_NUMBER,
                    path=f"{base_path}.{value_name}",
                    message=f"Enum value number changed from {old_number} to {new_number}",
                    old_value=str(old_number),
                    new_value=str(new_number),
                    severity="error",
                    mitigation="Enum value numbers must remain stable",
                ))

        return changes

    def _check_services_compatibility(
        self,
        old_services: list[Any],
        new_services: list[Any]
    ) -> list[BreakingChange]:
        """Check compatibility for services."""
        changes: list[BreakingChange] = []

        old_service_map = {s.name: s for s in old_services}
        new_service_map = {s.name: s for s in new_services}

        # Check for removed services
        for service_name in old_service_map.keys() - new_service_map.keys():
            changes.append(BreakingChange(
                change_type=BreakingChangeType.REMOVED_SERVICE,
                path=f"service {service_name}",
                message=f"Service '{service_name}' was removed",
                old_value=service_name,
                severity="error",
                mitigation="Keep the service or deprecate it first",
            ))

        # Check modified services
        for service_name in old_service_map.keys() & new_service_map.keys():
            old_service = old_service_map[service_name]
            new_service = new_service_map[service_name]

            old_rpcs = set(old_service.rpcs.keys())
            new_rpcs = set(new_service.rpcs.keys())

            # Check removed RPCs
            for rpc_name in old_rpcs - new_rpcs:
                changes.append(BreakingChange(
                    change_type=BreakingChangeType.REMOVED_RPC,
                    path=f"service {service_name}.{rpc_name}",
                    message=f"RPC '{rpc_name}' was removed from service '{service_name}'",
                    old_value=rpc_name,
                    severity="error",
                ))

            # Check modified RPCs
            for rpc_name in old_rpcs & new_rpcs:
                old_rpc = old_service.rpcs[rpc_name]
                new_rpc = new_service.rpcs[rpc_name]

                if old_rpc.get("input") != new_rpc.get("input"):
                    changes.append(BreakingChange(
                        change_type=BreakingChangeType.CHANGED_FIELD_TYPE,
                        path=f"service {service_name}.{rpc_name}",
                        message=f"RPC input type changed from '{old_rpc.get('input')}' to '{new_rpc.get('input')}'",
                        old_value=old_rpc.get("input"),
                        new_value=new_rpc.get("input"),
                        severity="error",
                    ))

                if old_rpc.get("output") != new_rpc.get("output"):
                    changes.append(BreakingChange(
                        change_type=BreakingChangeType.CHANGED_FIELD_TYPE,
                        path=f"service {service_name}.{rpc_name}",
                        message=f"RPC output type changed from '{old_rpc.get('output')}' to '{new_rpc.get('output')}'",
                        old_value=old_rpc.get("output"),
                        new_value=new_rpc.get("output"),
                        severity="error",
                    ))

        return changes

    def generate_report(
        self,
        result: ProtobufCompatibilityResult,
        format: str = "text"
    ) -> str:
        """
        Generate a compatibility report.

        Args:
            result: Compatibility result to report.
            format: Output format (text, json, markdown).

        Returns:
            Formatted report string.
        """
        if format == "json":
            return json.dumps(result.model_dump(), indent=2, default=str)
        elif format == "markdown":
            return self._generate_markdown_report(result)
        else:
            return self._generate_text_report(result)

    def _generate_text_report(self, result: ProtobufCompatibilityResult) -> str:
        """Generate a text format report."""
        lines = []
        lines.append("=" * 60)
        lines.append("Protobuf Compatibility Report")
        lines.append("=" * 60)
        lines.append(f"Old Schema: {result.source_file or 'N/A'}")
        lines.append(f"New Schema: {result.target_file or 'N/A'}")
        lines.append(f"Compatible: {'Yes' if result.is_compatible else 'No'}")
        lines.append(f"Compatibility Level: {result.compatibility_level}")
        lines.append(f"Breaking Changes: {result.breaking_change_count}")
        lines.append(f"Time: {result.check_time_ms:.2f}ms")
        lines.append("-" * 60)

        if result.added_messages:
            lines.append(f"\nAdded Messages: {', '.join(result.added_messages)}")
        if result.removed_messages:
            lines.append(f"Removed Messages: {', '.join(result.removed_messages)}")
        if result.modified_messages:
            lines.append(f"Modified Messages: {', '.join(result.modified_messages)}")

        if result.breaking_changes:
            lines.append("\nBreaking Changes:")
            for change in result.breaking_changes:
                lines.append(f"  [{change.change_type}] {change.path}")
                lines.append(f"    {change.message}")
                if change.mitigation:
                    lines.append(f"    Mitigation: {change.mitigation}")

        if result.warnings:
            lines.append("\nWarnings:")
            for warning in result.warnings:
                lines.append(f"  [{warning.change_type}] {warning.message}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_markdown_report(self, result: ProtobufCompatibilityResult) -> str:
        """Generate a markdown format report."""
        lines = []
        lines.append("# Protobuf Compatibility Report\n")
        lines.append(f"- **Old Schema**: {result.source_file or 'N/A'}")
        lines.append(f"- **New Schema**: {result.target_file or 'N/A'}")
        lines.append(f"- **Compatible**: {'Yes' if result.is_compatible else 'No'}")
        lines.append(f"- **Compatibility Level**: {result.compatibility_level}")
        lines.append(f"- **Breaking Changes**: {result.breaking_change_count}\n")

        if result.breaking_changes:
            lines.append("## Breaking Changes\n")
            lines.append("| Type | Path | Message | Mitigation |")
            lines.append("|------|------|---------|------------|")
            for change in result.breaking_changes:
                mitigation = change.mitigation or "-"
                lines.append(f"| {change.change_type} | `{change.path}` | {change.message} | {mitigation} |")

        if result.added_messages:
            lines.append("\n## Added Messages\n")
            for msg in result.added_messages:
                lines.append(f"- `{msg}`")

        if result.removed_messages:
            lines.append("\n## Removed Messages\n")
            for msg in result.removed_messages:
                lines.append(f"- `{msg}`")

        if result.modified_messages:
            lines.append("\n## Modified Messages\n")
            for msg in result.modified_messages:
                lines.append(f"- `{msg}`")

        if result.warnings:
            lines.append("\n## Warnings\n")
            for warning in result.warnings:
                lines.append(f"- [{warning.change_type}] {warning.message}")

        return "\n".join(lines)
