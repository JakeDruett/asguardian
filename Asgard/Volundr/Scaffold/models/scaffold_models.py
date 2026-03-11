"""
Scaffold Models for Project Generation

Provides Pydantic models for configuring and generating
project structures with best practices.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProjectType(str, Enum):
    """Project types."""
    MICROSERVICE = "microservice"
    LIBRARY = "library"
    CLI = "cli"
    WEB_APP = "web-app"
    API = "api"
    WORKER = "worker"


class Language(str, Enum):
    """Programming languages."""
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"


class Framework(str, Enum):
    """Frameworks/libraries."""
    FASTAPI = "fastapi"
    FLASK = "flask"
    DJANGO = "django"
    EXPRESS = "express"
    NESTJS = "nestjs"
    GIN = "gin"
    ECHO = "echo"
    ACTIX = "actix"
    SPRING = "spring"
    NONE = "none"


class DatabaseType(str, Enum):
    """Database types."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    REDIS = "redis"
    SQLITE = "sqlite"
    NONE = "none"


class MessageBroker(str, Enum):
    """Message broker types."""
    RABBITMQ = "rabbitmq"
    KAFKA = "kafka"
    REDIS = "redis"
    NATS = "nats"
    NONE = "none"


class CICDPlatform(str, Enum):
    """CI/CD platforms."""
    GITHUB_ACTIONS = "github-actions"
    GITLAB_CI = "gitlab-ci"
    AZURE_DEVOPS = "azure-devops"
    JENKINS = "jenkins"
    NONE = "none"


class ContainerOrchestration(str, Enum):
    """Container orchestration platforms."""
    KUBERNETES = "kubernetes"
    DOCKER_COMPOSE = "docker-compose"
    DOCKER_SWARM = "docker-swarm"
    NONE = "none"


class DependencyConfig(BaseModel):
    """Dependency configuration."""
    name: str = Field(description="Dependency name")
    version: Optional[str] = Field(default=None, description="Version constraint")
    dev: bool = Field(default=False, description="Is development dependency")


class DatabaseConfig(BaseModel):
    """Database configuration for service."""
    type: DatabaseType = Field(description="Database type")
    orm: Optional[str] = Field(default=None, description="ORM to use")
    migrations: bool = Field(default=True, description="Include migration support")


class MessagingConfig(BaseModel):
    """Messaging configuration for service."""
    broker: MessageBroker = Field(description="Message broker")
    publish: List[str] = Field(default_factory=list, description="Topics/queues to publish to")
    subscribe: List[str] = Field(default_factory=list, description="Topics/queues to subscribe to")


class ServiceConfig(BaseModel):
    """Configuration for a single service in a project."""
    name: str = Field(description="Service name")
    description: str = Field(default="", description="Service description")
    project_type: ProjectType = Field(default=ProjectType.MICROSERVICE, description="Project type")
    language: Language = Field(description="Programming language")
    framework: Framework = Field(default=Framework.NONE, description="Framework to use")
    port: int = Field(default=8080, description="Service port")
    database: Optional[DatabaseConfig] = Field(default=None, description="Database configuration")
    messaging: Optional[MessagingConfig] = Field(default=None, description="Messaging configuration")
    dependencies: List[DependencyConfig] = Field(default_factory=list, description="Dependencies")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    include_tests: bool = Field(default=True, description="Include test files")
    include_docker: bool = Field(default=True, description="Include Dockerfile")
    include_cicd: bool = Field(default=True, description="Include CI/CD configuration")
    include_docs: bool = Field(default=True, description="Include documentation")
    include_healthcheck: bool = Field(default=True, description="Include health check endpoint")
    include_logging: bool = Field(default=True, description="Include structured logging")
    include_metrics: bool = Field(default=False, description="Include metrics endpoint")
    include_tracing: bool = Field(default=False, description="Include distributed tracing")


class ProjectConfig(BaseModel):
    """Configuration for generating a project."""
    name: str = Field(description="Project name")
    description: str = Field(default="", description="Project description")
    version: str = Field(default="0.1.0", description="Initial version")
    author: str = Field(default="", description="Author name")
    license: str = Field(default="MIT", description="License type")
    services: List[ServiceConfig] = Field(default_factory=list, description="Services in project")
    monorepo: bool = Field(default=False, description="Is monorepo structure")
    cicd_platform: CICDPlatform = Field(default=CICDPlatform.GITHUB_ACTIONS, description="CI/CD platform")
    orchestration: ContainerOrchestration = Field(
        default=ContainerOrchestration.KUBERNETES, description="Container orchestration"
    )
    include_makefile: bool = Field(default=True, description="Include Makefile")
    include_pre_commit: bool = Field(default=True, description="Include pre-commit hooks")
    include_devcontainer: bool = Field(default=False, description="Include VS Code devcontainer")
    git_init: bool = Field(default=True, description="Initialize git repository")
    custom_templates: Dict[str, str] = Field(default_factory=dict, description="Custom template overrides")


class FileEntry(BaseModel):
    """Generated file entry."""
    path: str = Field(description="File path relative to project root")
    content: str = Field(description="File content")
    executable: bool = Field(default=False, description="Is executable")


class ScaffoldReport(BaseModel):
    """Result of project scaffolding."""
    id: str = Field(description="Unique scaffold ID")
    project_name: str = Field(description="Project name")
    project_type: str = Field(description="Project type")
    files: List[FileEntry] = Field(default_factory=list, description="Generated files")
    directories: List[str] = Field(default_factory=list, description="Created directories")
    total_files: int = Field(default=0, description="Total files created")
    total_directories: int = Field(default=0, description="Total directories created")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    output_path: Optional[str] = Field(default=None, description="Output path")
    messages: List[str] = Field(default_factory=list, description="Status messages")
    next_steps: List[str] = Field(default_factory=list, description="Suggested next steps")

    @property
    def file_count(self) -> int:
        """Get the number of generated files."""
        return len(self.files)
