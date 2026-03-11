"""
Docker Models for Configuration Generation

Provides Pydantic models for configuring and generating Dockerfiles
and docker-compose configurations with best practices.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BaseImage(str, Enum):
    """Common base images with security best practices."""
    PYTHON_SLIM = "python:3.12-slim"
    PYTHON_ALPINE = "python:3.12-alpine"
    NODE_SLIM = "node:20-slim"
    NODE_ALPINE = "node:20-alpine"
    GOLANG_ALPINE = "golang:1.22-alpine"
    RUST_SLIM = "rust:1.75-slim"
    DISTROLESS_PYTHON = "gcr.io/distroless/python3"
    DISTROLESS_STATIC = "gcr.io/distroless/static-debian12"
    UBUNTU = "ubuntu:22.04"
    ALPINE = "alpine:3.19"


class BuildStage(BaseModel):
    """Configuration for a Docker build stage."""
    name: str = Field(description="Stage name")
    base_image: str = Field(description="Base image for this stage")
    workdir: str = Field(default="/app", description="Working directory")
    user: Optional[str] = Field(default=None, description="User to run as")
    copy_from: Optional[str] = Field(default=None, description="Stage to copy from")
    copy_src: Optional[str] = Field(default=None, description="Source path to copy")
    copy_dst: Optional[str] = Field(default=None, description="Destination path")
    run_commands: List[str] = Field(default_factory=list, description="RUN commands")
    copy_commands: List[Dict[str, str]] = Field(default_factory=list, description="COPY commands")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    expose_ports: List[int] = Field(default_factory=list, description="Ports to expose")
    entrypoint: Optional[List[str]] = Field(default=None, description="ENTRYPOINT command")
    cmd: Optional[List[str]] = Field(default=None, description="CMD command")


class DockerfileConfig(BaseModel):
    """Configuration for generating a Dockerfile."""
    name: str = Field(description="Application name")
    stages: List[BuildStage] = Field(description="Build stages (multi-stage support)")
    labels: Dict[str, str] = Field(default_factory=dict, description="Image labels")
    args: Dict[str, str] = Field(default_factory=dict, description="Build arguments")
    healthcheck: Optional[Dict[str, Any]] = Field(default=None, description="Healthcheck configuration")
    use_non_root: bool = Field(default=True, description="Run as non-root user")
    optimize_layers: bool = Field(default=True, description="Optimize layer caching")


class ComposeServiceConfig(BaseModel):
    """Configuration for a docker-compose service."""
    name: str = Field(description="Service name")
    image: Optional[str] = Field(default=None, description="Image to use (if not building)")
    build: Optional[Dict[str, Any]] = Field(default=None, description="Build configuration")
    ports: List[str] = Field(default_factory=list, description="Port mappings")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    env_file: List[str] = Field(default_factory=list, description="Environment files")
    volumes: List[str] = Field(default_factory=list, description="Volume mounts")
    depends_on: List[str] = Field(default_factory=list, description="Service dependencies")
    networks: List[str] = Field(default_factory=list, description="Networks to join")
    restart: str = Field(default="unless-stopped", description="Restart policy")
    healthcheck: Optional[Dict[str, Any]] = Field(default=None, description="Healthcheck configuration")
    deploy: Optional[Dict[str, Any]] = Field(default=None, description="Deploy configuration")
    labels: Dict[str, str] = Field(default_factory=dict, description="Service labels")
    command: Optional[List[str]] = Field(default=None, description="Override command")


class NetworkConfig(BaseModel):
    """Docker network configuration."""
    name: str = Field(description="Network name")
    driver: str = Field(default="bridge", description="Network driver")
    external: bool = Field(default=False, description="Is external network")
    ipam: Optional[Dict[str, Any]] = Field(default=None, description="IPAM configuration")


class VolumeConfig(BaseModel):
    """Docker volume configuration."""
    name: str = Field(description="Volume name")
    driver: str = Field(default="local", description="Volume driver")
    external: bool = Field(default=False, description="Is external volume")
    driver_opts: Dict[str, str] = Field(default_factory=dict, description="Driver options")


class ComposeConfig(BaseModel):
    """Configuration for generating docker-compose.yml."""
    version: str = Field(default="3.8", description="Compose file version")
    services: List[ComposeServiceConfig] = Field(description="Services to define")
    networks: List[NetworkConfig] = Field(default_factory=list, description="Networks to define")
    volumes: List[VolumeConfig] = Field(default_factory=list, description="Volumes to define")
    configs: Dict[str, Any] = Field(default_factory=dict, description="Docker configs")
    secrets: Dict[str, Any] = Field(default_factory=dict, description="Docker secrets")


class GeneratedDockerConfig(BaseModel):
    """Result of Docker configuration generation."""
    id: str = Field(description="Unique configuration ID")
    config_hash: str = Field(description="Hash of the configuration")
    dockerfile_content: Optional[str] = Field(default=None, description="Generated Dockerfile content")
    compose_content: Optional[str] = Field(default=None, description="Generated docker-compose.yml content")
    validation_results: List[str] = Field(default_factory=list, description="Validation issues found")
    best_practice_score: float = Field(ge=0, le=100, description="Best practice compliance score")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    file_path: Optional[str] = Field(default=None, description="Path where config was saved")

    @property
    def has_issues(self) -> bool:
        """Check if there are validation issues."""
        return len(self.validation_results) > 0
