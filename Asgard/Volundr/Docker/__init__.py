"""
Volundr Docker Module

Provides template-based generation of Docker configurations including:
- Dockerfile optimization (multi-stage builds, security best practices)
- docker-compose.yml generation
- Container security configurations
- Image optimization patterns
"""

from Asgard.Volundr.Docker.models.docker_models import (
    BaseImage,
    BuildStage,
    DockerfileConfig,
    ComposeServiceConfig,
    ComposeConfig,
    GeneratedDockerConfig,
)
from Asgard.Volundr.Docker.services.dockerfile_generator import DockerfileGenerator
from Asgard.Volundr.Docker.services.compose_generator import ComposeGenerator

__all__ = [
    "BaseImage",
    "BuildStage",
    "DockerfileConfig",
    "ComposeServiceConfig",
    "ComposeConfig",
    "GeneratedDockerConfig",
    "DockerfileGenerator",
    "ComposeGenerator",
]
