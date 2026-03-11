"""
Mock Data Generator Service.

Generates realistic mock data based on JSON schemas and specifications.
"""

import hashlib
import random
import re
import string
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from Asgard.Forseti.MockServer.models.mock_models import (
    DataType,
    MockDataConfig,
    MockDataResult,
)


class MockDataGeneratorService:
    """
    Service for generating realistic mock data from JSON schemas.

    Generates data that matches schema constraints while providing
    realistic values based on field names and formats.

    Usage:
        generator = MockDataGeneratorService()
        data = generator.generate_from_schema(schema)
        print(data)
    """

    def __init__(self, config: Optional[MockDataConfig] = None):
        """
        Initialize the mock data generator.

        Args:
            config: Optional configuration for data generation.
        """
        self.config = config or MockDataConfig()
        self._random = random.Random()
        if config and config.locale:
            # Seed based on locale for consistency
            self._random.seed(hash(config.locale))

        # Common realistic data patterns
        self._first_names = [
            "James", "John", "Robert", "Michael", "David", "William", "Richard",
            "Joseph", "Thomas", "Charles", "Mary", "Patricia", "Jennifer", "Linda",
            "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen"
        ]
        self._last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
            "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
            "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"
        ]
        self._domains = [
            "example.com", "test.org", "sample.net", "demo.io", "mock.dev"
        ]
        self._street_types = ["St", "Ave", "Blvd", "Dr", "Ln", "Rd", "Way", "Ct"]
        self._cities = [
            "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
            "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"
        ]
        self._countries = ["USA", "Canada", "UK", "Australia", "Germany", "France"]

    def set_seed(self, seed: int) -> None:
        """
        Set the random seed for reproducible data generation.

        Args:
            seed: Random seed value.
        """
        self._random.seed(seed)

    def generate_from_schema(
        self,
        schema: dict[str, Any],
        property_name: Optional[str] = None
    ) -> MockDataResult:
        """
        Generate mock data based on a JSON schema.

        Args:
            schema: JSON Schema definition.
            property_name: Optional property name for context-aware generation.

        Returns:
            MockDataResult with generated data.
        """
        warnings: list[str] = []

        # Use example if available and configured
        if self.config.use_examples and "example" in schema:
            return MockDataResult(
                data=schema["example"],
                schema_used=schema,
                generation_strategy="example",
            )

        if self.config.use_examples and "examples" in schema:
            examples = schema["examples"]
            if examples:
                return MockDataResult(
                    data=self._random.choice(examples),
                    schema_used=schema,
                    generation_strategy="examples",
                )

        # Use default if available and configured
        if self.config.use_defaults and "default" in schema:
            return MockDataResult(
                data=schema["default"],
                schema_used=schema,
                generation_strategy="default",
            )

        # Check for enum
        if "enum" in schema:
            return MockDataResult(
                data=self._random.choice(schema["enum"]),
                schema_used=schema,
                generation_strategy="enum",
            )

        # Check for const
        if "const" in schema:
            return MockDataResult(
                data=schema["const"],
                schema_used=schema,
                generation_strategy="const",
            )

        # Handle composition keywords
        if "oneOf" in schema:
            selected = self._random.choice(schema["oneOf"])
            return self.generate_from_schema(selected, property_name)

        if "anyOf" in schema:
            selected = self._random.choice(schema["anyOf"])
            return self.generate_from_schema(selected, property_name)

        if "allOf" in schema:
            # Merge all schemas and generate
            merged = self._merge_all_of(schema["allOf"])
            return self.generate_from_schema(merged, property_name)

        # Generate based on type
        schema_type = schema.get("type", "object")
        schema_format = schema.get("format")

        if isinstance(schema_type, list):
            # Handle multiple types - pick the first non-null
            for t in schema_type:
                if t != "null":
                    schema_type = t
                    break
            else:
                schema_type = "null"

        data = self._generate_by_type(
            schema_type,
            schema,
            schema_format,
            property_name,
            warnings
        )

        return MockDataResult(
            data=data,
            schema_used=schema,
            generation_strategy=f"generated_{schema_type}",
            warnings=warnings,
        )

    def generate_value(
        self,
        data_type: DataType,
        constraints: Optional[dict[str, Any]] = None
    ) -> Any:
        """
        Generate a single value of a specific type.

        Args:
            data_type: Type of data to generate.
            constraints: Optional constraints (min, max, pattern, etc.).

        Returns:
            Generated value.
        """
        constraints = constraints or {}

        if data_type == DataType.STRING:
            return self._generate_string(constraints)
        elif data_type == DataType.INTEGER:
            return self._generate_integer(constraints)
        elif data_type == DataType.NUMBER:
            return self._generate_number(constraints)
        elif data_type == DataType.BOOLEAN:
            return self._random.choice([True, False])
        elif data_type == DataType.DATE:
            return self._generate_date()
        elif data_type == DataType.DATETIME:
            return self._generate_datetime()
        elif data_type == DataType.EMAIL:
            return self._generate_email()
        elif data_type == DataType.UUID:
            return str(uuid.uuid4())
        elif data_type == DataType.URL:
            return self._generate_url()
        elif data_type == DataType.PHONE:
            return self._generate_phone()
        elif data_type == DataType.NAME:
            return self._generate_name()
        elif data_type == DataType.ADDRESS:
            return self._generate_address()
        elif data_type == DataType.ARRAY:
            return []
        elif data_type == DataType.OBJECT:
            return {}
        else:
            return None

    def _generate_by_type(
        self,
        schema_type: str,
        schema: dict[str, Any],
        schema_format: Optional[str],
        property_name: Optional[str],
        warnings: list[str]
    ) -> Any:
        """Generate data based on schema type."""
        if schema_type == "string":
            return self._generate_string_from_schema(schema, schema_format, property_name)
        elif schema_type == "integer":
            return self._generate_integer(schema)
        elif schema_type == "number":
            return self._generate_number(schema)
        elif schema_type == "boolean":
            return self._random.choice([True, False])
        elif schema_type == "array":
            return self._generate_array(schema, warnings)
        elif schema_type == "object":
            return self._generate_object(schema, warnings)
        elif schema_type == "null":
            return None
        else:
            warnings.append(f"Unknown type: {schema_type}, defaulting to null")
            return None

    def _generate_string_from_schema(
        self,
        schema: dict[str, Any],
        schema_format: Optional[str],
        property_name: Optional[str]
    ) -> str:
        """Generate a string value based on schema and format."""
        # Check format first
        if schema_format:
            return self._generate_formatted_string(schema_format)

        # Check pattern
        if "pattern" in schema:
            return self._generate_from_pattern(schema["pattern"])

        # Infer from property name
        if property_name:
            inferred = self._infer_from_property_name(property_name)
            if inferred is not None:
                return inferred

        # Generate random string within constraints
        return self._generate_string(schema)

    def _generate_formatted_string(self, format_type: str) -> str:
        """Generate a string based on format type."""
        if format_type == "email":
            return self._generate_email()
        elif format_type == "uri" or format_type == "url":
            return self._generate_url()
        elif format_type == "uuid":
            return str(uuid.uuid4())
        elif format_type == "date":
            return self._generate_date()
        elif format_type == "date-time":
            return self._generate_datetime()
        elif format_type == "time":
            return self._generate_time()
        elif format_type == "hostname":
            return self._random.choice(self._domains)
        elif format_type == "ipv4":
            return self._generate_ipv4()
        elif format_type == "ipv6":
            return self._generate_ipv6()
        elif format_type == "phone":
            return self._generate_phone()
        else:
            return self._generate_string({})

    def _infer_from_property_name(self, property_name: str) -> Optional[str]:
        """Infer data type and generate based on property name."""
        name_lower = property_name.lower()

        if any(x in name_lower for x in ["email", "mail"]):
            return self._generate_email()
        elif any(x in name_lower for x in ["phone", "tel", "mobile"]):
            return self._generate_phone()
        elif any(x in name_lower for x in ["url", "uri", "link", "href", "website"]):
            return self._generate_url()
        elif any(x in name_lower for x in ["uuid", "guid", "id"]) and "id" in name_lower:
            return str(uuid.uuid4())
        elif any(x in name_lower for x in ["first_name", "firstname", "given_name"]):
            return self._random.choice(self._first_names)
        elif any(x in name_lower for x in ["last_name", "lastname", "surname", "family_name"]):
            return self._random.choice(self._last_names)
        elif "name" in name_lower and "user" in name_lower:
            return self._generate_username()
        elif "name" in name_lower:
            return self._generate_name()
        elif any(x in name_lower for x in ["address", "street"]):
            return self._generate_street()
        elif "city" in name_lower:
            return self._random.choice(self._cities)
        elif "country" in name_lower:
            return self._random.choice(self._countries)
        elif any(x in name_lower for x in ["zip", "postal"]):
            return self._generate_zip()
        elif any(x in name_lower for x in ["date", "created", "updated", "timestamp"]):
            return self._generate_datetime()
        elif any(x in name_lower for x in ["description", "bio", "summary", "about"]):
            return self._generate_lorem(2, 4)
        elif any(x in name_lower for x in ["title", "subject", "headline"]):
            return self._generate_lorem(1, 1).rstrip(".")
        elif "password" in name_lower:
            return self._generate_password()
        elif "token" in name_lower:
            return self._generate_token()
        elif "ip" in name_lower:
            return self._generate_ipv4()

        return None

    def _generate_string(self, constraints: dict[str, Any]) -> str:
        """Generate a random string within constraints."""
        min_length = constraints.get("minLength", self.config.string_min_length)
        max_length = constraints.get("maxLength", self.config.string_max_length)
        length = self._random.randint(min_length, max_length)

        chars = string.ascii_letters + string.digits
        return "".join(self._random.choice(chars) for _ in range(length))

    def _generate_integer(self, constraints: dict[str, Any]) -> int:
        """Generate a random integer within constraints."""
        minimum = constraints.get("minimum", int(self.config.number_min))
        maximum = constraints.get("maximum", int(self.config.number_max))

        if constraints.get("exclusiveMinimum"):
            minimum = constraints["exclusiveMinimum"] + 1
        if constraints.get("exclusiveMaximum"):
            maximum = constraints["exclusiveMaximum"] - 1

        return self._random.randint(minimum, maximum)

    def _generate_number(self, constraints: dict[str, Any]) -> float:
        """Generate a random number within constraints."""
        minimum = constraints.get("minimum", self.config.number_min)
        maximum = constraints.get("maximum", self.config.number_max)

        if constraints.get("exclusiveMinimum"):
            minimum = constraints["exclusiveMinimum"] + 0.001
        if constraints.get("exclusiveMaximum"):
            maximum = constraints["exclusiveMaximum"] - 0.001

        return round(self._random.uniform(minimum, maximum), 2)

    def _generate_array(
        self,
        schema: dict[str, Any],
        warnings: list[str]
    ) -> list:
        """Generate an array based on schema."""
        min_items = schema.get("minItems", self.config.array_min_items)
        max_items = schema.get("maxItems", self.config.array_max_items)
        count = self._random.randint(min_items, max_items)

        items_schema = schema.get("items", {})
        if not items_schema:
            warnings.append("Array schema has no items definition")
            return []

        result = []
        for _ in range(count):
            item_result = self.generate_from_schema(items_schema)
            result.append(item_result.data)
            warnings.extend(item_result.warnings)

        return result

    def _generate_object(
        self,
        schema: dict[str, Any],
        warnings: list[str]
    ) -> dict:
        """Generate an object based on schema."""
        result = {}
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        for prop_name, prop_schema in properties.items():
            is_required = prop_name in required
            if is_required or self.config.generate_optional:
                prop_result = self.generate_from_schema(prop_schema, prop_name)
                result[prop_name] = prop_result.data
                warnings.extend(prop_result.warnings)

        return result

    def _generate_from_pattern(self, pattern: str) -> str:
        """Generate a string matching a regex pattern (basic implementation)."""
        # Basic pattern handling - covers common cases
        if pattern == r"^\d+$":
            return str(self._random.randint(0, 99999))
        elif pattern == r"^[a-zA-Z]+$":
            return "".join(self._random.choices(string.ascii_letters, k=10))
        elif pattern == r"^[a-z]+$":
            return "".join(self._random.choices(string.ascii_lowercase, k=10))
        elif pattern == r"^[A-Z]+$":
            return "".join(self._random.choices(string.ascii_uppercase, k=10))
        else:
            # Fallback to generic string
            return self._generate_string({})

    def _merge_all_of(self, schemas: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge multiple schemas from allOf."""
        merged: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

        for schema in schemas:
            if "properties" in schema:
                merged["properties"].update(schema["properties"])
            if "required" in schema:
                merged["required"].extend(schema["required"])
            if "type" in schema:
                merged["type"] = schema["type"]

        return merged

    # Helper generators for specific data types

    def _generate_email(self) -> str:
        """Generate a realistic email address."""
        first = self._random.choice(self._first_names).lower()
        last = self._random.choice(self._last_names).lower()
        domain = self._random.choice(self._domains)
        return f"{first}.{last}@{domain}"

    def _generate_url(self) -> str:
        """Generate a realistic URL."""
        domain = self._random.choice(self._domains)
        path = "/".join(
            "".join(self._random.choices(string.ascii_lowercase, k=6))
            for _ in range(self._random.randint(1, 3))
        )
        return f"https://{domain}/{path}"

    def _generate_phone(self) -> str:
        """Generate a realistic phone number."""
        area = self._random.randint(200, 999)
        prefix = self._random.randint(200, 999)
        line = self._random.randint(1000, 9999)
        return f"+1-{area}-{prefix}-{line}"

    def _generate_name(self) -> str:
        """Generate a full name."""
        first = self._random.choice(self._first_names)
        last = self._random.choice(self._last_names)
        return f"{first} {last}"

    def _generate_username(self) -> str:
        """Generate a username."""
        first = self._random.choice(self._first_names).lower()
        num = self._random.randint(1, 999)
        return f"{first}{num}"

    def _generate_street(self) -> str:
        """Generate a street address."""
        num = self._random.randint(1, 9999)
        name = self._random.choice(self._last_names)
        street_type = self._random.choice(self._street_types)
        return f"{num} {name} {street_type}"

    def _generate_address(self) -> str:
        """Generate a full address."""
        street = self._generate_street()
        city = self._random.choice(self._cities)
        country = self._random.choice(self._countries)
        return f"{street}, {city}, {country}"

    def _generate_zip(self) -> str:
        """Generate a ZIP code."""
        return str(self._random.randint(10000, 99999))

    def _generate_date(self) -> str:
        """Generate a random date."""
        days_offset = self._random.randint(-365, 365)
        date = datetime.now() + timedelta(days=days_offset)
        return date.strftime("%Y-%m-%d")

    def _generate_datetime(self) -> str:
        """Generate a random datetime."""
        days_offset = self._random.randint(-365, 365)
        hours_offset = self._random.randint(0, 23)
        dt = datetime.now() + timedelta(days=days_offset, hours=hours_offset)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _generate_time(self) -> str:
        """Generate a random time."""
        hour = self._random.randint(0, 23)
        minute = self._random.randint(0, 59)
        second = self._random.randint(0, 59)
        return f"{hour:02d}:{minute:02d}:{second:02d}"

    def _generate_ipv4(self) -> str:
        """Generate a random IPv4 address."""
        return ".".join(str(self._random.randint(0, 255)) for _ in range(4))

    def _generate_ipv6(self) -> str:
        """Generate a random IPv6 address."""
        return ":".join(
            "".join(self._random.choices("0123456789abcdef", k=4))
            for _ in range(8)
        )

    def _generate_password(self) -> str:
        """Generate a random password."""
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(self._random.choices(chars, k=16))

    def _generate_token(self) -> str:
        """Generate a random token."""
        return hashlib.sha256(
            str(self._random.random()).encode()
        ).hexdigest()[:32]

    def _generate_lorem(self, min_sentences: int, max_sentences: int) -> str:
        """Generate lorem ipsum-style text."""
        words = [
            "lorem", "ipsum", "dolor", "sit", "amet", "consectetur",
            "adipiscing", "elit", "sed", "do", "eiusmod", "tempor",
            "incididunt", "ut", "labore", "et", "dolore", "magna", "aliqua"
        ]

        sentences = []
        for _ in range(self._random.randint(min_sentences, max_sentences)):
            length = self._random.randint(5, 12)
            sentence_words = self._random.choices(words, k=length)
            sentence_words[0] = sentence_words[0].capitalize()
            sentences.append(" ".join(sentence_words) + ".")

        return " ".join(sentences)
