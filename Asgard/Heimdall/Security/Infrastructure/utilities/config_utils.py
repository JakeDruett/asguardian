"""
Heimdall Security Infrastructure Config Utilities

Helper functions for parsing and analyzing configuration files.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def parse_env_file(content: str) -> Dict[str, str]:
    """
    Parse a .env file content into a dictionary.

    Args:
        content: Content of the .env file

    Returns:
        Dictionary of environment variable key-value pairs
    """
    env_vars: Dict[str, str] = {}
    lines = content.split("\n")

    for line in lines:
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()

        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]

        if key:
            env_vars[key] = value

    return env_vars


def parse_yaml_simple(content: str) -> Dict[str, Any]:
    """
    Simple YAML parser for basic key-value extraction.
    Does not handle complex YAML structures - use for security scanning only.

    Args:
        content: YAML content to parse

    Returns:
        Dictionary of extracted key-value pairs
    """
    result: Dict[str, Any] = {}
    lines = content.split("\n")

    for line in lines:
        line_stripped = line.strip()

        if not line_stripped or line_stripped.startswith("#"):
            continue

        if ":" not in line_stripped:
            continue

        key, _, value = line_stripped.partition(":")
        key = key.strip()
        value = value.strip()

        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]

        if key:
            result[key] = value

    return result


def parse_properties_file(content: str) -> Dict[str, str]:
    """
    Parse a .properties file (Java-style) into a dictionary.

    Args:
        content: Content of the properties file

    Returns:
        Dictionary of property key-value pairs
    """
    properties: Dict[str, str] = {}
    lines = content.split("\n")
    current_value = ""
    current_key = ""

    for line in lines:
        if line.rstrip().endswith("\\"):
            if current_key:
                current_value += line.rstrip()[:-1]
            else:
                key_part, _, value_part = line.rstrip()[:-1].partition("=")
                current_key = key_part.strip()
                current_value = value_part.strip()
            continue

        if current_key:
            current_value += line.strip()
            properties[current_key] = current_value
            current_key = ""
            current_value = ""
            continue

        line = line.strip()

        if not line or line.startswith("#") or line.startswith("!"):
            continue

        if "=" in line:
            key, _, value = line.partition("=")
        elif ":" in line:
            key, _, value = line.partition(":")
        else:
            continue

        key = key.strip()
        value = value.strip()

        if key:
            properties[key] = value

    return properties


def parse_ini_file(content: str) -> Dict[str, Dict[str, str]]:
    """
    Parse an INI file into a nested dictionary.

    Args:
        content: Content of the INI file

    Returns:
        Dictionary with sections as keys and dictionaries of values
    """
    result: Dict[str, Dict[str, str]] = {}
    current_section = "DEFAULT"
    result[current_section] = {}

    lines = content.split("\n")

    for line in lines:
        line = line.strip()

        if not line or line.startswith("#") or line.startswith(";"):
            continue

        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip()
            if current_section not in result:
                result[current_section] = {}
            continue

        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]

            if key:
                result[current_section][key] = value

    return result


def extract_config_value(
    content: str,
    key_pattern: str,
) -> List[Tuple[int, str, str]]:
    """
    Extract configuration values matching a key pattern from content.

    Args:
        content: File content to search
        key_pattern: Regex pattern for the configuration key

    Returns:
        List of (line_number, key, value) tuples
    """
    results: List[Tuple[int, str, str]] = []
    lines = content.split("\n")

    pattern = re.compile(
        rf"""({key_pattern})\s*[=:]\s*(['"]?)([^'"#\n]+)\2""",
        re.IGNORECASE | re.MULTILINE
    )

    for i, line in enumerate(lines, start=1):
        match = pattern.search(line)
        if match:
            key = match.group(1)
            value = match.group(3).strip()
            results.append((i, key, value))

    return results


def find_sensitive_keys(content: str) -> List[Tuple[int, str]]:
    """
    Find configuration keys that typically contain sensitive values.

    Args:
        content: File content to search

    Returns:
        List of (line_number, key_name) tuples
    """
    sensitive_patterns = [
        r"(?:API[_-]?KEY)",
        r"(?:SECRET[_-]?KEY)",
        r"(?:PASSWORD|PASSWD|PWD)",
        r"(?:TOKEN|AUTH[_-]?TOKEN|ACCESS[_-]?TOKEN)",
        r"(?:PRIVATE[_-]?KEY)",
        r"(?:CREDENTIALS?)",
        r"(?:DATABASE[_-]?URL|DB[_-]?URL)",
        r"(?:CONNECTION[_-]?STRING)",
        r"(?:AWS[_-]?(?:ACCESS|SECRET))",
        r"(?:AZURE[_-]?(?:KEY|SECRET))",
        r"(?:GCP[_-]?(?:KEY|CREDENTIALS))",
        r"(?:ENCRYPTION[_-]?KEY)",
        r"(?:SIGNING[_-]?KEY)",
        r"(?:OAUTH[_-]?(?:SECRET|TOKEN))",
        r"(?:JWT[_-]?SECRET)",
    ]

    combined_pattern = re.compile(
        rf"""({'|'.join(sensitive_patterns)})\s*[=:]""",
        re.IGNORECASE
    )

    results: List[Tuple[int, str]] = []
    lines = content.split("\n")

    for i, line in enumerate(lines, start=1):
        match = combined_pattern.search(line)
        if match:
            results.append((i, match.group(1)))

    return results


def is_production_config(file_path: Path) -> bool:
    """
    Determine if a configuration file is likely for production.

    Args:
        file_path: Path to the configuration file

    Returns:
        True if the file appears to be a production configuration
    """
    name_lower = file_path.name.lower()
    parent_lower = file_path.parent.name.lower() if file_path.parent else ""

    prod_indicators = [
        "prod",
        "production",
        "live",
        "deploy",
    ]

    non_prod_indicators = [
        "dev",
        "development",
        "local",
        "test",
        "staging",
        "example",
        "sample",
        "template",
    ]

    for indicator in non_prod_indicators:
        if indicator in name_lower or indicator in parent_lower:
            return False

    for indicator in prod_indicators:
        if indicator in name_lower or indicator in parent_lower:
            return True

    if name_lower in ["settings.py", "config.py", ".env", "application.yml"]:
        return True

    return False


def detect_config_format(file_path: Path, content: Optional[str] = None) -> str:
    """
    Detect the format of a configuration file.

    Args:
        file_path: Path to the configuration file
        content: Optional file content (if already read)

    Returns:
        Format identifier: 'env', 'yaml', 'json', 'ini', 'properties', 'python', 'xml', 'unknown'
    """
    ext = file_path.suffix.lower()

    format_map = {
        ".env": "env",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".ini": "ini",
        ".cfg": "ini",
        ".conf": "ini",
        ".properties": "properties",
        ".py": "python",
        ".xml": "xml",
        ".config": "xml",
    }

    if ext in format_map:
        return format_map[ext]

    if file_path.name == ".env" or file_path.name.startswith(".env"):
        return "env"

    if content:
        if content.strip().startswith("{"):
            try:
                json.loads(content)
                return "json"
            except json.JSONDecodeError:
                pass

        if content.strip().startswith("<?xml") or content.strip().startswith("<"):
            return "xml"

        if "import " in content or "from " in content or "def " in content:
            return "python"

    return "unknown"


def extract_debug_settings(content: str) -> List[Tuple[int, str, bool]]:
    """
    Extract debug-related settings from configuration content.

    Args:
        content: Configuration file content

    Returns:
        List of (line_number, setting_name, is_enabled) tuples
    """
    debug_patterns = [
        (r"DEBUG\s*[=:]\s*(True|true|1|yes|on)", True),
        (r"DEBUG\s*[=:]\s*(False|false|0|no|off)", False),
        (r"\.debug\s*=\s*(True|true|1)", True),
        (r"\.debug\s*=\s*(False|false|0)", False),
        (r"debug_mode\s*[=:]\s*(True|true|1|yes|on)", True),
        (r"debug_mode\s*[=:]\s*(False|false|0|no|off)", False),
    ]

    results: List[Tuple[int, str, bool]] = []
    lines = content.split("\n")

    for i, line in enumerate(lines, start=1):
        for pattern, is_enabled in debug_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                results.append((i, "DEBUG", is_enabled))
                break

    return results


def get_config_security_recommendations(
    file_path: Path,
    issues_found: List[str],
) -> List[str]:
    """
    Generate security recommendations based on configuration issues found.

    Args:
        file_path: Path to the configuration file
        issues_found: List of issue types found

    Returns:
        List of security recommendations
    """
    recommendations: List[str] = []

    if "debug_enabled" in issues_found:
        recommendations.append(
            "Disable debug mode in production. Use environment variables to control this setting."
        )

    if "default_credentials" in issues_found:
        recommendations.append(
            "Change default credentials immediately. Use strong, unique passwords "
            "and store them in environment variables or a secrets manager."
        )

    if "hardcoded_secret" in issues_found:
        recommendations.append(
            "Move hardcoded secrets to environment variables or a secrets manager like HashiCorp Vault."
        )

    if "permissive_hosts" in issues_found:
        recommendations.append(
            "Restrict ALLOWED_HOSTS to specific hostnames for your application."
        )

    if "cors_allow_all" in issues_found:
        recommendations.append(
            "Configure CORS with specific allowed origins instead of allowing all origins."
        )

    if "insecure_transport" in issues_found:
        recommendations.append(
            "Ensure all communications use HTTPS. Enable SSL redirect and HSTS."
        )

    if "missing_security_headers" in issues_found:
        recommendations.append(
            "Add security headers: X-Content-Type-Options, X-Frame-Options, "
            "Content-Security-Policy, and Strict-Transport-Security."
        )

    if not recommendations:
        recommendations.append(
            "Review configuration files regularly and ensure security best practices are followed."
        )

    return recommendations
