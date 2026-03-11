"""
Heimdall Security Container - Container Security Analysis

This module provides container security analysis including:
- Dockerfile security scanning
- docker-compose.yml security scanning
- Privileged container detection
- Secrets in container configuration detection
- Exposed sensitive ports detection

Usage:
    python -m Heimdall security container ./src

Example:
    from Asgard.Heimdall.Security.Container import ContainerAnalyzer, ContainerConfig

    analyzer = ContainerAnalyzer(ContainerConfig(scan_path="./src"))
    report = analyzer.analyze()
    print(f"Container Issues: {report.total_issues}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Heimdall.Security.Container.models.container_models import (
    ContainerConfig,
    ContainerFinding,
    ContainerFindingType,
    ContainerReport,
)
from Asgard.Heimdall.Security.Container.services.compose_analyzer import ComposeAnalyzer
from Asgard.Heimdall.Security.Container.services.container_analyzer import ContainerAnalyzer
from Asgard.Heimdall.Security.Container.services.dockerfile_analyzer import DockerfileAnalyzer

__all__ = [
    "ComposeAnalyzer",
    "ContainerAnalyzer",
    "ContainerConfig",
    "ContainerFinding",
    "ContainerFindingType",
    "ContainerReport",
    "DockerfileAnalyzer",
]
