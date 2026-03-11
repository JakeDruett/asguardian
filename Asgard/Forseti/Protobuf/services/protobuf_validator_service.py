"""
Protobuf Specification Validator Service.

Validates Protocol Buffer files against syntax and best practices.
Uses regex-based parsing to avoid requiring external protoc installation.
"""

import json
import re
import time
from pathlib import Path
from typing import Any, Optional

from Asgard.Forseti.Protobuf.models.protobuf_models import (
    ProtobufConfig,
    ProtobufEnum,
    ProtobufField,
    ProtobufMessage,
    ProtobufSchema,
    ProtobufService,
    ProtobufSyntaxVersion,
    ProtobufValidationError,
    ProtobufValidationResult,
    ValidationSeverity,
)


class ProtobufValidatorService:
    """
    Service for validating Protocol Buffer specifications.

    Validates proto files against syntax standards and reports
    errors, warnings, and informational messages.

    Usage:
        service = ProtobufValidatorService()
        result = service.validate("schema.proto")
        if not result.is_valid:
            for error in result.errors:
                print(f"Error: {error.message}")
    """

    # Protobuf scalar types
    SCALAR_TYPES = {
        "double", "float", "int32", "int64", "uint32", "uint64",
        "sint32", "sint64", "fixed32", "fixed64", "sfixed32", "sfixed64",
        "bool", "string", "bytes"
    }

    # Reserved field numbers
    RESERVED_FIELD_NUMBERS = range(19000, 20000)  # 19000-19999 reserved by Google

    # Regex patterns for parsing
    SYNTAX_PATTERN = re.compile(r'syntax\s*=\s*["\']([^"\']+)["\'];')
    PACKAGE_PATTERN = re.compile(r'package\s+([\w.]+)\s*;')
    IMPORT_PATTERN = re.compile(r'import\s+(public\s+)?["\']([^"\']+)["\'];')
    OPTION_PATTERN = re.compile(r'option\s+([\w.]+)\s*=\s*([^;]+);')
    MESSAGE_PATTERN = re.compile(r'message\s+(\w+)\s*\{')
    ENUM_PATTERN = re.compile(r'enum\s+(\w+)\s*\{')
    SERVICE_PATTERN = re.compile(r'service\s+(\w+)\s*\{')
    FIELD_PATTERN = re.compile(
        r'(optional|required|repeated)?\s*([\w.]+)\s+(\w+)\s*=\s*(\d+)'
        r'(?:\s*\[(.*?)\])?;'
    )
    MAP_FIELD_PATTERN = re.compile(
        r'map\s*<\s*([\w.]+)\s*,\s*([\w.]+)\s*>\s+(\w+)\s*=\s*(\d+)\s*;'
    )
    ONEOF_PATTERN = re.compile(r'oneof\s+(\w+)\s*\{')
    RESERVED_PATTERN = re.compile(r'reserved\s+([^;]+);')
    ENUM_VALUE_PATTERN = re.compile(r'(\w+)\s*=\s*(-?\d+)(?:\s*\[.*?\])?;')
    RPC_PATTERN = re.compile(
        r'rpc\s+(\w+)\s*\(\s*(stream\s+)?(\w+)\s*\)\s*returns\s*\(\s*(stream\s+)?(\w+)\s*\)'
    )

    def __init__(self, config: Optional[ProtobufConfig] = None):
        """
        Initialize the validator service.

        Args:
            config: Optional configuration for validation behavior.
        """
        self.config = config or ProtobufConfig()

    def validate(self, proto_path: str | Path) -> ProtobufValidationResult:
        """
        Validate a Protocol Buffer file.

        Args:
            proto_path: Path to the proto file.

        Returns:
            ProtobufValidationResult with validation details.
        """
        return self.validate_file(proto_path)

    def validate_file(self, proto_path: str | Path) -> ProtobufValidationResult:
        """
        Validate a Protocol Buffer file.

        Args:
            proto_path: Path to the proto file.

        Returns:
            ProtobufValidationResult with validation details.
        """
        start_time = time.time()
        proto_path = Path(proto_path)

        errors: list[ProtobufValidationError] = []
        warnings: list[ProtobufValidationError] = []
        info_messages: list[ProtobufValidationError] = []

        # Check file exists
        if not proto_path.exists():
            errors.append(ProtobufValidationError(
                path="",
                message=f"Proto file not found: {proto_path}",
                severity=ValidationSeverity.ERROR,
                rule="file-exists",
            ))
            return ProtobufValidationResult(
                is_valid=False,
                file_path=str(proto_path),
                errors=errors,
                validation_time_ms=(time.time() - start_time) * 1000,
            )

        # Read file content
        try:
            content = proto_path.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(ProtobufValidationError(
                path="",
                message=f"Failed to read proto file: {str(e)}",
                severity=ValidationSeverity.ERROR,
                rule="readable-file",
            ))
            return ProtobufValidationResult(
                is_valid=False,
                file_path=str(proto_path),
                errors=errors,
                validation_time_ms=(time.time() - start_time) * 1000,
            )

        # Parse and validate
        return self._validate_content(content, str(proto_path), start_time)

    def validate_content(self, content: str) -> ProtobufValidationResult:
        """
        Validate Protocol Buffer content directly.

        Args:
            content: Proto file content as string.

        Returns:
            ProtobufValidationResult with validation details.
        """
        return self._validate_content(content, None, time.time())

    def _validate_content(
        self,
        content: str,
        file_path: Optional[str],
        start_time: float
    ) -> ProtobufValidationResult:
        """Internal method to validate proto content."""
        errors: list[ProtobufValidationError] = []
        warnings: list[ProtobufValidationError] = []
        info_messages: list[ProtobufValidationError] = []

        # Remove comments for parsing
        cleaned_content = self._remove_comments(content)

        # Parse syntax
        syntax_version = self._parse_syntax(cleaned_content)
        if syntax_version is None:
            # Default to proto3 if not specified
            syntax_version = ProtobufSyntaxVersion.PROTO3
            warnings.append(ProtobufValidationError(
                path="/",
                message="No syntax declaration found, defaulting to proto3",
                severity=ValidationSeverity.WARNING,
                rule="syntax-declaration",
            ))
        elif syntax_version == ProtobufSyntaxVersion.PROTO2 and not self.config.allow_proto2:
            errors.append(ProtobufValidationError(
                path="/syntax",
                message="proto2 syntax is not allowed by configuration",
                severity=ValidationSeverity.ERROR,
                rule="proto2-allowed",
            ))

        # Parse package
        package = self._parse_package(cleaned_content)
        if not package and self.config.require_package:
            errors.append(ProtobufValidationError(
                path="/",
                message="Package declaration is required",
                severity=ValidationSeverity.ERROR,
                rule="package-required",
            ))

        # Parse imports
        imports, public_imports = self._parse_imports(cleaned_content)

        # Parse options
        options = self._parse_options(cleaned_content)

        # Parse messages
        messages = self._parse_messages(cleaned_content, syntax_version)

        # Parse top-level enums
        enums = self._parse_enums(cleaned_content)

        # Parse services
        services = self._parse_services(cleaned_content)

        # Validate messages
        for msg in messages:
            msg_errors = self._validate_message(msg, syntax_version)
            for err in msg_errors:
                if err.severity == ValidationSeverity.ERROR:
                    errors.append(err)
                elif err.severity == ValidationSeverity.WARNING:
                    warnings.append(err)
                else:
                    info_messages.append(err)

        # Validate enums
        for enum in enums:
            enum_errors = self._validate_enum(enum, syntax_version)
            for err in enum_errors:
                if err.severity == ValidationSeverity.ERROR:
                    errors.append(err)
                elif err.severity == ValidationSeverity.WARNING:
                    warnings.append(err)
                else:
                    info_messages.append(err)

        # Validate services
        for service in services:
            service_errors = self._validate_service(service, messages)
            for err in service_errors:
                if err.severity == ValidationSeverity.ERROR:
                    errors.append(err)
                elif err.severity == ValidationSeverity.WARNING:
                    warnings.append(err)
                else:
                    info_messages.append(err)

        # Check naming conventions
        if self.config.check_naming_conventions:
            naming_issues = self._check_naming_conventions(messages, enums, services)
            warnings.extend(naming_issues)

        # Limit errors if configured
        if self.config.max_errors > 0:
            errors = errors[:self.config.max_errors]

        # Create schema
        schema = ProtobufSchema(
            syntax=syntax_version,
            package=package,
            imports=imports,
            public_imports=public_imports,
            messages=messages,
            enums=enums,
            services=services,
            options=options,
            file_path=file_path,
        )

        validation_time_ms = (time.time() - start_time) * 1000

        return ProtobufValidationResult(
            is_valid=len(errors) == 0,
            file_path=file_path,
            syntax_version=syntax_version,
            parsed_schema=schema if len(errors) == 0 else None,
            errors=errors,
            warnings=warnings if self.config.include_warnings else [],
            info_messages=info_messages,
            validation_time_ms=validation_time_ms,
        )

    def _remove_comments(self, content: str) -> str:
        """Remove single-line and multi-line comments."""
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        return content

    def _parse_syntax(self, content: str) -> Optional[ProtobufSyntaxVersion]:
        """Parse the syntax declaration."""
        match = self.SYNTAX_PATTERN.search(content)
        if match:
            syntax_str = match.group(1)
            if syntax_str == "proto2":
                return ProtobufSyntaxVersion.PROTO2
            elif syntax_str == "proto3":
                return ProtobufSyntaxVersion.PROTO3
        return None

    def _parse_package(self, content: str) -> Optional[str]:
        """Parse the package declaration."""
        match = self.PACKAGE_PATTERN.search(content)
        return match.group(1) if match else None

    def _parse_imports(self, content: str) -> tuple[list[str], list[str]]:
        """Parse import statements."""
        imports = []
        public_imports = []
        for match in self.IMPORT_PATTERN.finditer(content):
            is_public = match.group(1) is not None
            import_path = match.group(2)
            if is_public:
                public_imports.append(import_path)
            else:
                imports.append(import_path)
        return imports, public_imports

    def _parse_options(self, content: str) -> dict[str, Any]:
        """Parse file-level options."""
        options = {}
        # Only parse options outside of message/enum/service blocks
        # This is a simplified version - real parsing would be more complex
        lines = content.split('\n')
        brace_depth = 0
        for line in lines:
            brace_depth += line.count('{') - line.count('}')
            if brace_depth == 0:
                match = self.OPTION_PATTERN.search(line)
                if match:
                    name = match.group(1)
                    value = match.group(2).strip()
                    # Try to parse value as appropriate type
                    if value.startswith('"') and value.endswith('"'):
                        options[name] = value[1:-1]
                    elif value.lower() == 'true':
                        options[name] = True
                    elif value.lower() == 'false':
                        options[name] = False
                    elif value.isdigit():
                        options[name] = int(value)
                    else:
                        options[name] = value
        return options

    def _parse_messages(
        self,
        content: str,
        syntax_version: ProtobufSyntaxVersion
    ) -> list[ProtobufMessage]:
        """Parse message definitions."""
        messages = []
        # Find all top-level message blocks
        for match in self.MESSAGE_PATTERN.finditer(content):
            name = match.group(1)
            start = match.end()
            block_content = self._extract_block(content, start)
            if block_content:
                message = self._parse_message_block(name, block_content, syntax_version)
                messages.append(message)
        return messages

    def _extract_block(self, content: str, start: int) -> Optional[str]:
        """Extract content between matching braces."""
        brace_count = 1
        end = start
        while end < len(content) and brace_count > 0:
            if content[end] == '{':
                brace_count += 1
            elif content[end] == '}':
                brace_count -= 1
            end += 1
        if brace_count == 0:
            return content[start:end-1]
        return None

    def _parse_message_block(
        self,
        name: str,
        block_content: str,
        syntax_version: ProtobufSyntaxVersion
    ) -> ProtobufMessage:
        """Parse a message block."""
        fields = []
        nested_messages = []
        nested_enums = []
        oneofs: dict[str, list[str]] = {}
        reserved_names: list[str] = []
        reserved_numbers: list[int] = []
        reserved_ranges: list[tuple[int, int]] = []

        # Parse nested messages first (to exclude from field parsing)
        for match in self.MESSAGE_PATTERN.finditer(block_content):
            nested_name = match.group(1)
            start = match.end()
            nested_block = self._extract_block(block_content, start)
            if nested_block:
                nested_msg = self._parse_message_block(nested_name, nested_block, syntax_version)
                nested_messages.append(nested_msg)

        # Parse nested enums
        for match in self.ENUM_PATTERN.finditer(block_content):
            enum_name = match.group(1)
            start = match.end()
            enum_block = self._extract_block(block_content, start)
            if enum_block:
                enum = self._parse_enum_block(enum_name, enum_block)
                nested_enums.append(enum)

        # Parse oneofs
        for match in self.ONEOF_PATTERN.finditer(block_content):
            oneof_name = match.group(1)
            start = match.end()
            oneof_block = self._extract_block(block_content, start)
            if oneof_block:
                oneof_fields = []
                for field_match in self.FIELD_PATTERN.finditer(oneof_block):
                    field_name = field_match.group(3)
                    oneof_fields.append(field_name)
                    field = self._parse_field_match(field_match, syntax_version, oneof_name)
                    fields.append(field)
                oneofs[oneof_name] = oneof_fields

        # Parse reserved declarations
        for match in self.RESERVED_PATTERN.finditer(block_content):
            reserved_str = match.group(1)
            names, numbers, ranges = self._parse_reserved(reserved_str)
            reserved_names.extend(names)
            reserved_numbers.extend(numbers)
            reserved_ranges.extend(ranges)

        # Parse regular fields
        for match in self.FIELD_PATTERN.finditer(block_content):
            # Skip fields that are inside nested structures or oneofs
            field = self._parse_field_match(match, syntax_version)
            if field.oneof_group is None:  # Not already added from oneof
                fields.append(field)

        # Parse map fields
        for match in self.MAP_FIELD_PATTERN.finditer(block_content):
            key_type = match.group(1)
            value_type = match.group(2)
            field_name = match.group(3)
            field_number = int(match.group(4))
            fields.append(ProtobufField(
                name=field_name,
                number=field_number,
                type="map",
                label="repeated",
                map_key_type=key_type,
                map_value_type=value_type,
            ))

        return ProtobufMessage(
            name=name,
            fields=fields,
            nested_messages=nested_messages,
            nested_enums=nested_enums,
            oneofs=oneofs,
            reserved_names=reserved_names,
            reserved_numbers=reserved_numbers,
            reserved_ranges=reserved_ranges,
        )

    def _parse_field_match(
        self,
        match: re.Match,
        syntax_version: ProtobufSyntaxVersion,
        oneof_group: Optional[str] = None
    ) -> ProtobufField:
        """Parse a field from a regex match."""
        label = match.group(1)
        field_type = match.group(2)
        name = match.group(3)
        number = int(match.group(4))
        options_str = match.group(5) if len(match.groups()) > 4 else None

        # Parse options
        options = {}
        default_value = None
        if options_str:
            for opt_match in re.finditer(r'(\w+)\s*=\s*([^,\]]+)', options_str):
                opt_name = opt_match.group(1)
                opt_value = opt_match.group(2).strip()
                if opt_name == 'default':
                    default_value = opt_value
                else:
                    options[opt_name] = opt_value

        return ProtobufField(
            name=name,
            number=number,
            type=field_type,
            label=label,
            default_value=default_value,
            options=options if options else None,
            oneof_group=oneof_group,
        )

    def _parse_reserved(
        self,
        reserved_str: str
    ) -> tuple[list[str], list[int], list[tuple[int, int]]]:
        """Parse reserved declaration."""
        names: list[str] = []
        numbers: list[int] = []
        ranges: list[tuple[int, int]] = []

        parts = [p.strip() for p in reserved_str.split(',')]
        for part in parts:
            if part.startswith('"') and part.endswith('"'):
                names.append(part[1:-1])
            elif ' to ' in part:
                range_parts = part.split(' to ')
                start = int(range_parts[0])
                end_str = range_parts[1]
                end = 536870911 if end_str == 'max' else int(end_str)
                ranges.append((start, end))
            elif part.isdigit():
                numbers.append(int(part))

        return names, numbers, ranges

    def _parse_enums(self, content: str) -> list[ProtobufEnum]:
        """Parse top-level enum definitions."""
        enums = []
        for match in self.ENUM_PATTERN.finditer(content):
            name = match.group(1)
            start = match.end()
            block_content = self._extract_block(content, start)
            if block_content:
                enum = self._parse_enum_block(name, block_content)
                enums.append(enum)
        return enums

    def _parse_enum_block(self, name: str, block_content: str) -> ProtobufEnum:
        """Parse an enum block."""
        values: dict[str, int] = {}
        allow_alias = False
        reserved_names: list[str] = []
        reserved_numbers: list[int] = []

        # Check for allow_alias option
        if 'allow_alias' in block_content and 'true' in block_content:
            allow_alias = True

        # Parse reserved
        for match in self.RESERVED_PATTERN.finditer(block_content):
            reserved_str = match.group(1)
            names, numbers, _ = self._parse_reserved(reserved_str)
            reserved_names.extend(names)
            reserved_numbers.extend(numbers)

        # Parse enum values
        for match in self.ENUM_VALUE_PATTERN.finditer(block_content):
            value_name = match.group(1)
            value_number = int(match.group(2))
            values[value_name] = value_number

        return ProtobufEnum(
            name=name,
            values=values,
            allow_alias=allow_alias,
            reserved_names=reserved_names,
            reserved_numbers=reserved_numbers,
        )

    def _parse_services(self, content: str) -> list[ProtobufService]:
        """Parse service definitions."""
        services = []
        for match in self.SERVICE_PATTERN.finditer(content):
            name = match.group(1)
            start = match.end()
            block_content = self._extract_block(content, start)
            if block_content:
                service = self._parse_service_block(name, block_content)
                services.append(service)
        return services

    def _parse_service_block(self, name: str, block_content: str) -> ProtobufService:
        """Parse a service block."""
        rpcs: dict[str, dict[str, str]] = {}

        for match in self.RPC_PATTERN.finditer(block_content):
            rpc_name = match.group(1)
            input_stream = match.group(2) is not None
            input_type = match.group(3)
            output_stream = match.group(4) is not None
            output_type = match.group(5)

            rpcs[rpc_name] = {
                "input": input_type,
                "output": output_type,
                "input_stream": str(input_stream).lower(),
                "output_stream": str(output_stream).lower(),
            }

        return ProtobufService(
            name=name,
            rpcs=rpcs,
        )

    def _validate_message(
        self,
        message: ProtobufMessage,
        syntax_version: ProtobufSyntaxVersion
    ) -> list[ProtobufValidationError]:
        """Validate a message definition."""
        errors: list[ProtobufValidationError] = []
        base_path = f"message {message.name}"

        # Check for duplicate field numbers
        field_numbers: dict[int, str] = {}
        for field in message.fields:
            if field.number in field_numbers:
                errors.append(ProtobufValidationError(
                    path=f"{base_path}.{field.name}",
                    message=f"Duplicate field number {field.number} (also used by '{field_numbers[field.number]}')",
                    severity=ValidationSeverity.ERROR,
                    rule="unique-field-numbers",
                ))
            else:
                field_numbers[field.number] = field.name

        # Validate field numbers
        if self.config.check_field_numbers:
            for field in message.fields:
                if field.number < 1:
                    errors.append(ProtobufValidationError(
                        path=f"{base_path}.{field.name}",
                        message=f"Field number must be positive, got {field.number}",
                        severity=ValidationSeverity.ERROR,
                        rule="valid-field-number",
                    ))
                elif field.number in self.RESERVED_FIELD_NUMBERS:
                    errors.append(ProtobufValidationError(
                        path=f"{base_path}.{field.name}",
                        message=f"Field number {field.number} is in reserved range 19000-19999",
                        severity=ValidationSeverity.ERROR,
                        rule="reserved-range",
                    ))
                elif field.number > 536870911:
                    errors.append(ProtobufValidationError(
                        path=f"{base_path}.{field.name}",
                        message=f"Field number {field.number} exceeds maximum (536870911)",
                        severity=ValidationSeverity.ERROR,
                        rule="max-field-number",
                    ))
                elif field.number > 15 and field.number <= 2047:
                    # Numbers 1-15 use one byte, 16-2047 use two bytes
                    errors.append(ProtobufValidationError(
                        path=f"{base_path}.{field.name}",
                        message=f"Consider using field numbers 1-15 for frequently used fields (better encoding)",
                        severity=ValidationSeverity.INFO,
                        rule="efficient-field-number",
                    ))

        # Check reserved fields
        if self.config.check_reserved_fields:
            for field in message.fields:
                if field.name in message.reserved_names:
                    errors.append(ProtobufValidationError(
                        path=f"{base_path}.{field.name}",
                        message=f"Field name '{field.name}' is reserved",
                        severity=ValidationSeverity.ERROR,
                        rule="reserved-name",
                    ))
                if field.number in message.reserved_numbers:
                    errors.append(ProtobufValidationError(
                        path=f"{base_path}.{field.name}",
                        message=f"Field number {field.number} is reserved",
                        severity=ValidationSeverity.ERROR,
                        rule="reserved-number",
                    ))
                for start, end in message.reserved_ranges:
                    if start <= field.number <= end:
                        errors.append(ProtobufValidationError(
                            path=f"{base_path}.{field.name}",
                            message=f"Field number {field.number} is in reserved range {start}-{end}",
                            severity=ValidationSeverity.ERROR,
                            rule="reserved-range",
                        ))

        # Proto3 specific validations
        if syntax_version == ProtobufSyntaxVersion.PROTO3:
            for field in message.fields:
                if field.label == "required":
                    errors.append(ProtobufValidationError(
                        path=f"{base_path}.{field.name}",
                        message="'required' label is not allowed in proto3",
                        severity=ValidationSeverity.ERROR,
                        rule="proto3-no-required",
                    ))

        # Validate nested messages
        for nested in message.nested_messages:
            nested_errors = self._validate_message(nested, syntax_version)
            errors.extend(nested_errors)

        # Validate nested enums
        for nested_enum in message.nested_enums:
            enum_errors = self._validate_enum(nested_enum, syntax_version)
            errors.extend(enum_errors)

        return errors

    def _validate_enum(
        self,
        enum: ProtobufEnum,
        syntax_version: ProtobufSyntaxVersion
    ) -> list[ProtobufValidationError]:
        """Validate an enum definition."""
        errors: list[ProtobufValidationError] = []
        base_path = f"enum {enum.name}"

        # Check for duplicate values (unless allow_alias is set)
        if not enum.allow_alias:
            value_numbers: dict[int, str] = {}
            for value_name, value_number in enum.values.items():
                if value_number in value_numbers:
                    errors.append(ProtobufValidationError(
                        path=f"{base_path}.{value_name}",
                        message=f"Duplicate enum value {value_number} (also used by '{value_numbers[value_number]}'). Use allow_alias = true to allow aliases.",
                        severity=ValidationSeverity.ERROR,
                        rule="unique-enum-values",
                    ))
                else:
                    value_numbers[value_number] = value_name

        # Proto3 requires first enum value to be 0
        if syntax_version == ProtobufSyntaxVersion.PROTO3:
            if enum.values:
                first_value = min(enum.values.values())
                if first_value != 0:
                    errors.append(ProtobufValidationError(
                        path=base_path,
                        message="First enum value must be 0 in proto3",
                        severity=ValidationSeverity.ERROR,
                        rule="proto3-enum-zero",
                    ))

        # Check reserved values
        for value_name, value_number in enum.values.items():
            if value_name in enum.reserved_names:
                errors.append(ProtobufValidationError(
                    path=f"{base_path}.{value_name}",
                    message=f"Enum value name '{value_name}' is reserved",
                    severity=ValidationSeverity.ERROR,
                    rule="reserved-enum-name",
                ))
            if value_number in enum.reserved_numbers:
                errors.append(ProtobufValidationError(
                    path=f"{base_path}.{value_name}",
                    message=f"Enum value number {value_number} is reserved",
                    severity=ValidationSeverity.ERROR,
                    rule="reserved-enum-number",
                ))

        return errors

    def _validate_service(
        self,
        service: ProtobufService,
        messages: list[ProtobufMessage]
    ) -> list[ProtobufValidationError]:
        """Validate a service definition."""
        errors: list[ProtobufValidationError] = []
        base_path = f"service {service.name}"

        # Get all message names for type checking
        message_names = set()
        for msg in messages:
            message_names.add(msg.name)
            for nested in msg.nested_messages:
                message_names.add(f"{msg.name}.{nested.name}")

        # Validate RPC methods
        for rpc_name, rpc_def in service.rpcs.items():
            input_type = rpc_def.get("input", "")
            output_type = rpc_def.get("output", "")

            # Check if types exist (basic check - could be external imports)
            if input_type not in message_names and input_type not in self.SCALAR_TYPES:
                errors.append(ProtobufValidationError(
                    path=f"{base_path}.{rpc_name}",
                    message=f"RPC input type '{input_type}' may not be defined (could be an import)",
                    severity=ValidationSeverity.INFO,
                    rule="rpc-type-exists",
                ))
            if output_type not in message_names and output_type not in self.SCALAR_TYPES:
                errors.append(ProtobufValidationError(
                    path=f"{base_path}.{rpc_name}",
                    message=f"RPC output type '{output_type}' may not be defined (could be an import)",
                    severity=ValidationSeverity.INFO,
                    rule="rpc-type-exists",
                ))

        return errors

    def _check_naming_conventions(
        self,
        messages: list[ProtobufMessage],
        enums: list[ProtobufEnum],
        services: list[ProtobufService]
    ) -> list[ProtobufValidationError]:
        """Check naming convention best practices."""
        warnings: list[ProtobufValidationError] = []

        # Message names should be PascalCase
        for msg in messages:
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', msg.name):
                warnings.append(ProtobufValidationError(
                    path=f"message {msg.name}",
                    message=f"Message name '{msg.name}' should be PascalCase",
                    severity=ValidationSeverity.WARNING,
                    rule="naming-convention",
                ))

            # Field names should be snake_case
            for field in msg.fields:
                if not re.match(r'^[a-z][a-z0-9_]*$', field.name):
                    warnings.append(ProtobufValidationError(
                        path=f"message {msg.name}.{field.name}",
                        message=f"Field name '{field.name}' should be snake_case",
                        severity=ValidationSeverity.WARNING,
                        rule="naming-convention",
                    ))

        # Enum names should be PascalCase
        for enum in enums:
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', enum.name):
                warnings.append(ProtobufValidationError(
                    path=f"enum {enum.name}",
                    message=f"Enum name '{enum.name}' should be PascalCase",
                    severity=ValidationSeverity.WARNING,
                    rule="naming-convention",
                ))

            # Enum values should be SCREAMING_SNAKE_CASE
            for value_name in enum.values:
                if not re.match(r'^[A-Z][A-Z0-9_]*$', value_name):
                    warnings.append(ProtobufValidationError(
                        path=f"enum {enum.name}.{value_name}",
                        message=f"Enum value '{value_name}' should be SCREAMING_SNAKE_CASE",
                        severity=ValidationSeverity.WARNING,
                        rule="naming-convention",
                    ))

        # Service names should be PascalCase
        for service in services:
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', service.name):
                warnings.append(ProtobufValidationError(
                    path=f"service {service.name}",
                    message=f"Service name '{service.name}' should be PascalCase",
                    severity=ValidationSeverity.WARNING,
                    rule="naming-convention",
                ))

        return warnings

    def generate_report(
        self,
        result: ProtobufValidationResult,
        format: str = "text"
    ) -> str:
        """
        Generate a validation report.

        Args:
            result: Validation result to report.
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

    def _generate_text_report(self, result: ProtobufValidationResult) -> str:
        """Generate a text format report."""
        lines = []
        lines.append("=" * 60)
        lines.append("Protobuf Validation Report")
        lines.append("=" * 60)
        lines.append(f"File: {result.file_path or 'N/A'}")
        lines.append(f"Syntax: {result.syntax_version or 'Unknown'}")
        lines.append(f"Valid: {'Yes' if result.is_valid else 'No'}")
        lines.append(f"Errors: {result.error_count}")
        lines.append(f"Warnings: {result.warning_count}")
        lines.append(f"Time: {result.validation_time_ms:.2f}ms")
        lines.append("-" * 60)

        if result.parsed_schema:
            lines.append(f"Package: {result.parsed_schema.package or 'N/A'}")
            lines.append(f"Messages: {result.parsed_schema.message_count}")
            lines.append(f"Enums: {result.parsed_schema.enum_count}")
            lines.append(f"Services: {result.parsed_schema.service_count}")
            lines.append("-" * 60)

        if result.errors:
            lines.append("\nErrors:")
            for error in result.errors:
                line_info = f" (line {error.line})" if error.line else ""
                lines.append(f"  [{error.rule or 'error'}] {error.path}{line_info}: {error.message}")

        if result.warnings:
            lines.append("\nWarnings:")
            for warning in result.warnings:
                lines.append(f"  [{warning.rule or 'warning'}] {warning.path}: {warning.message}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_markdown_report(self, result: ProtobufValidationResult) -> str:
        """Generate a markdown format report."""
        lines = []
        lines.append("# Protobuf Validation Report\n")
        lines.append(f"- **File**: {result.file_path or 'N/A'}")
        lines.append(f"- **Syntax**: {result.syntax_version or 'Unknown'}")
        lines.append(f"- **Valid**: {'Yes' if result.is_valid else 'No'}")
        lines.append(f"- **Errors**: {result.error_count}")
        lines.append(f"- **Warnings**: {result.warning_count}")
        lines.append(f"- **Time**: {result.validation_time_ms:.2f}ms\n")

        if result.parsed_schema:
            lines.append("## Schema Summary\n")
            lines.append(f"- **Package**: {result.schema.package or 'N/A'}")
            lines.append(f"- **Messages**: {result.schema.message_count}")
            lines.append(f"- **Enums**: {result.schema.enum_count}")
            lines.append(f"- **Services**: {result.schema.service_count}\n")

        if result.errors:
            lines.append("## Errors\n")
            lines.append("| Path | Rule | Message |")
            lines.append("|------|------|---------|")
            for error in result.errors:
                lines.append(f"| `{error.path}` | {error.rule or 'error'} | {error.message} |")

        if result.warnings:
            lines.append("\n## Warnings\n")
            lines.append("| Path | Rule | Message |")
            lines.append("|------|------|---------|")
            for warning in result.warnings:
                lines.append(f"| `{warning.path}` | {warning.rule or 'warning'} | {warning.message} |")

        return "\n".join(lines)
