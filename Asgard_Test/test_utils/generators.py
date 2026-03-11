"""
Test Data Generators

Utilities for generating realistic test data including Python code,
OpenAPI specs, GraphQL schemas, and performance metrics.
"""

import random
from typing import Dict, List


def generate_python_class(name: str, methods: int = 5) -> str:
    """
    Generate a Python class with specified number of methods.

    Args:
        name: Class name
        methods: Number of methods to generate (default: 5)

    Returns:
        Python source code as string

    Example:
        >>> code = generate_python_class("UserService", methods=3)
        >>> assert "class UserService:" in code
        >>> assert "def method_1" in code
        >>> assert "def method_2" in code
        >>> assert "def method_3" in code
    """
    lines = [f"class {name}:"]
    lines.append('    """Generated test class."""')
    lines.append("")

    lines.append("    def __init__(self):")
    lines.append('        """Initialize the class."""')
    lines.append("        pass")
    lines.append("")

    for i in range(1, methods + 1):
        lines.append(f"    def method_{i}(self, param1, param2):")
        lines.append(f'        """Method {i} implementation."""')
        lines.append("        result = param1 + param2")
        lines.append("        return result")
        lines.append("")

    return "\n".join(lines)


def generate_python_module(classes: int = 3, functions: int = 5) -> str:
    """
    Generate a Python module with multiple classes and functions.

    Args:
        classes: Number of classes to generate (default: 3)
        functions: Number of module-level functions (default: 5)

    Returns:
        Python source code as string

    Example:
        >>> code = generate_python_module(classes=2, functions=3)
        >>> assert "class Class1:" in code
        >>> assert "class Class2:" in code
        >>> assert "def function_1" in code
        >>> assert "def function_2" in code
        >>> assert "def function_3" in code
    """
    lines = [
        '"""Generated test module."""',
        "",
        "from typing import Any, Dict, List, Optional",
        "",
    ]

    # Generate module-level functions
    for i in range(1, functions + 1):
        lines.append(f"def function_{i}(arg1: str, arg2: int = 0) -> Dict[str, Any]:")
        lines.append(f'    """Module function {i}."""')
        lines.append("    return {")
        lines.append('        "arg1": arg1,')
        lines.append('        "arg2": arg2,')
        lines.append(f'        "result": "function_{i}_result"')
        lines.append("    }")
        lines.append("")

    # Generate classes
    for i in range(1, classes + 1):
        lines.append("")
        lines.append(generate_python_class(f"Class{i}", methods=3))

    return "\n".join(lines)


def generate_openapi_spec(endpoints: int = 3, version: str = "3.0") -> Dict:
    """
    Generate an OpenAPI specification with specified number of endpoints.

    Args:
        endpoints: Number of endpoints to generate (default: 3)
        version: OpenAPI version (default: "3.0")

    Returns:
        OpenAPI specification as dictionary

    Example:
        >>> spec = generate_openapi_spec(endpoints=2)
        >>> assert spec["openapi"].startswith("3.0")
        >>> assert "paths" in spec
        >>> assert len(spec["paths"]) == 2
        >>> assert "/api/endpoint_1" in spec["paths"]
    """
    spec = {
        "openapi": f"{version}.0" if version == "3.0" else version,
        "info": {
            "title": "Generated Test API",
            "description": "Auto-generated OpenAPI specification for testing",
            "version": "1.0.0",
            "contact": {
                "name": "Test Team",
                "email": "test@example.com"
            }
        },
        "servers": [
            {
                "url": "https://api.example.com/v1",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.example.com/v1",
                "description": "Staging server"
            }
        ],
        "paths": {},
        "components": {
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "integer"},
                        "message": {"type": "string"}
                    },
                    "required": ["code", "message"]
                }
            }
        }
    }

    # Generate endpoints
    for i in range(1, endpoints + 1):
        endpoint_path = f"/api/endpoint_{i}"
        spec["paths"][endpoint_path] = {
            "get": {
                "summary": f"Get endpoint {i} data",
                "description": f"Retrieve data from endpoint {i}",
                "operationId": f"getEndpoint{i}",
                "parameters": [
                    {
                        "name": "id",
                        "in": "query",
                        "description": f"ID for endpoint {i}",
                        "required": False,
                        "schema": {"type": "integer"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "name": {"type": "string"},
                                        "data": {"type": "object"}
                                    }
                                }
                            }
                        }
                    },
                    "404": {
                        "description": "Not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            },
            "post": {
                "summary": f"Create endpoint {i} data",
                "description": f"Create new data at endpoint {i}",
                "operationId": f"createEndpoint{i}",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "value": {"type": "integer"}
                                },
                                "required": ["name"]
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Created successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "name": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

    return spec


def generate_graphql_schema(types: int = 3) -> str:
    """
    Generate a GraphQL schema with specified number of types.

    Args:
        types: Number of types to generate (default: 3)

    Returns:
        GraphQL schema as string

    Example:
        >>> schema = generate_graphql_schema(types=2)
        >>> assert "type Type1" in schema
        >>> assert "type Type2" in schema
        >>> assert "type Query" in schema
    """
    lines = [
        '"""Generated GraphQL schema for testing."""',
        "",
        "scalar DateTime",
        "",
    ]

    # Generate types
    for i in range(1, types + 1):
        lines.append(f'"""Type {i} description."""')
        lines.append(f"type Type{i} {{")
        lines.append("  id: ID!")
        lines.append("  name: String!")
        lines.append("  value: Int")
        lines.append("  active: Boolean")
        lines.append("  createdAt: DateTime!")
        lines.append("}")
        lines.append("")

    # Generate Query type
    lines.append("type Query {")
    for i in range(1, types + 1):
        lines.append(f"  type{i}(id: ID!): Type{i}")
        lines.append(f"  allType{i}s: [Type{i}!]!")
    lines.append("}")
    lines.append("")

    # Generate Mutation type
    lines.append("type Mutation {")
    for i in range(1, types + 1):
        lines.append(f"  createType{i}(name: String!, value: Int): Type{i}!")
        lines.append(f"  updateType{i}(id: ID!, name: String, value: Int): Type{i}")
        lines.append(f"  deleteType{i}(id: ID!): Boolean!")
    lines.append("}")

    return "\n".join(lines)


def generate_metrics_data(points: int = 100, metric_type: str = "latency") -> List[Dict]:
    """
    Generate realistic performance metrics data.

    Args:
        points: Number of data points to generate (default: 100)
        metric_type: Type of metric ("latency", "throughput", "memory", "cpu")

    Returns:
        List of metric data points

    Example:
        >>> data = generate_metrics_data(points=50, metric_type="latency")
        >>> assert len(data) == 50
        >>> assert all("timestamp" in point for point in data)
        >>> assert all("value" in point for point in data)
        >>> assert all("metric_type" in point for point in data)
    """
    base_values = {
        "latency": 100.0,  # milliseconds
        "throughput": 1000.0,  # requests/sec
        "memory": 512.0,  # MB
        "cpu": 50.0,  # percent
    }

    base_value = base_values.get(metric_type, 100.0)
    data = []

    for i in range(points):
        # Add some realistic variance
        variance = random.uniform(-0.2, 0.3)
        value = base_value * (1 + variance)

        # Add occasional spikes
        if random.random() < 0.05:  # 5% chance of spike
            value *= random.uniform(2.0, 4.0)

        data.append({
            "timestamp": 1704067200 + (i * 60),  # 1-minute intervals
            "value": round(value, 2),
            "metric_type": metric_type,
            "labels": {
                "service": "test_service",
                "environment": "production",
                "region": "us-west-1"
            }
        })

    return data


def generate_web_vitals_data(quality: str = "mixed") -> Dict:
    """
    Generate Web Vitals performance data.

    Args:
        quality: Overall quality level ("good", "poor", "mixed")

    Returns:
        Web Vitals data dictionary with LCP, FID, CLS, etc.

    Example:
        >>> vitals = generate_web_vitals_data(quality="good")
        >>> assert "lcp" in vitals
        >>> assert "fid" in vitals
        >>> assert "cls" in vitals
        >>> assert vitals["lcp"] < 2500  # Good LCP threshold
        >>>
        >>> poor_vitals = generate_web_vitals_data(quality="poor")
        >>> assert poor_vitals["lcp"] > 4000  # Poor LCP threshold
    """
    if quality == "good":
        lcp_range = (1000, 2500)  # Largest Contentful Paint
        fid_range = (50, 100)  # First Input Delay
        cls_range = (0.01, 0.1)  # Cumulative Layout Shift
        ttfb_range = (200, 800)  # Time to First Byte
        fcp_range = (800, 1800)  # First Contentful Paint
    elif quality == "poor":
        lcp_range = (4000, 8000)
        fid_range = (300, 500)
        cls_range = (0.25, 0.5)
        ttfb_range = (1500, 3000)
        fcp_range = (3000, 5000)
    else:  # mixed
        lcp_range = (2500, 4000)
        fid_range = (100, 300)
        cls_range = (0.1, 0.25)
        ttfb_range = (800, 1500)
        fcp_range = (1800, 3000)

    return {
        "lcp": round(random.uniform(*lcp_range), 2),
        "fid": round(random.uniform(*fid_range), 2),
        "cls": round(random.uniform(*cls_range), 4),
        "ttfb": round(random.uniform(*ttfb_range), 2),
        "fcp": round(random.uniform(*fcp_range), 2),
        "tti": round(random.uniform(*fcp_range) * 1.5, 2),  # Time to Interactive
        "tbt": round(random.uniform(*fid_range) * 2, 2),  # Total Blocking Time
        "si": round(random.uniform(*fcp_range) * 1.2, 2),  # Speed Index
        "metadata": {
            "timestamp": 1704067200,
            "url": "https://example.com/test-page",
            "device": "desktop",
            "connection": "4g",
            "quality_rating": quality
        }
    }
