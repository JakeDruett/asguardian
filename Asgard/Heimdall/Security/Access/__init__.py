"""
Heimdall Security Access - Access Control Analysis

This module provides access control pattern verification including:
- RBAC/ABAC pattern validation
- Permission misconfiguration detection
- Privilege escalation path identification
- Authorization bypass detection

Usage:
    python -m Heimdall security access ./src

Example:
    from Asgard.Heimdall.Security.Access import AccessAnalyzer, AccessConfig

    analyzer = AccessAnalyzer(AccessConfig(scan_path="./src"))
    report = analyzer.analyze()
    print(f"Access Issues: {report.total_issues}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Heimdall.Security.Access.models.access_models import (
    AccessConfig,
    AccessFinding,
    AccessFindingType,
    AccessReport,
)
from Asgard.Heimdall.Security.Access.services.access_analyzer import AccessAnalyzer
from Asgard.Heimdall.Security.Access.services.control_analyzer import ControlAnalyzer
from Asgard.Heimdall.Security.Access.services.permission_analyzer import PermissionAnalyzer

__all__ = [
    "AccessAnalyzer",
    "AccessConfig",
    "AccessFinding",
    "AccessFindingType",
    "AccessReport",
    "ControlAnalyzer",
    "PermissionAnalyzer",
]
