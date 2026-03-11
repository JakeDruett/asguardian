"""
Kubernetes Models for Manifest Generation

Provides Pydantic models for configuring and generating Kubernetes manifests
with best practices, security configurations, and operational readiness.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkloadType(str, Enum):
    """Kubernetes workload types."""
    DEPLOYMENT = "Deployment"
    STATEFULSET = "StatefulSet"
    DAEMONSET = "DaemonSet"
    JOB = "Job"
    CRONJOB = "CronJob"


class SecurityProfile(str, Enum):
    """Security profile levels for generated manifests."""
    BASIC = "basic"
    ENHANCED = "enhanced"
    STRICT = "strict"
    ZERO_TRUST = "zero-trust"


class EnvironmentType(str, Enum):
    """Deployment environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ResourceRequirements(BaseModel):
    """Container resource requirements."""
    cpu_request: str = Field(default="100m", description="CPU request")
    cpu_limit: str = Field(default="500m", description="CPU limit")
    memory_request: str = Field(default="128Mi", description="Memory request")
    memory_limit: str = Field(default="512Mi", description="Memory limit")
    storage_request: Optional[str] = Field(default=None, description="Storage request for PVCs")


class SecurityContext(BaseModel):
    """Container security context configuration."""
    run_as_user: Optional[int] = Field(default=1000, description="UID to run as")
    run_as_group: Optional[int] = Field(default=3000, description="GID to run as")
    run_as_non_root: bool = Field(default=True, description="Require non-root user")
    read_only_root_filesystem: bool = Field(default=True, description="Read-only root filesystem")
    allow_privilege_escalation: bool = Field(default=False, description="Allow privilege escalation")
    drop_capabilities: List[str] = Field(default_factory=lambda: ["ALL"], description="Capabilities to drop")
    add_capabilities: List[str] = Field(default_factory=list, description="Capabilities to add")


class ProbeConfig(BaseModel):
    """Health probe configuration."""
    enabled: bool = Field(default=True, description="Enable the probe")
    initial_delay_seconds: int = Field(default=10, description="Initial delay before probing")
    period_seconds: int = Field(default=10, description="Probe interval")
    timeout_seconds: int = Field(default=5, description="Probe timeout")
    failure_threshold: int = Field(default=3, description="Failures before unhealthy")
    success_threshold: int = Field(default=1, description="Successes before healthy")
    http_path: Optional[str] = Field(default="/health", description="HTTP probe path")
    http_port: Optional[int] = Field(default=8080, description="HTTP probe port")


class PortConfig(BaseModel):
    """Container port configuration."""
    name: str = Field(default="http", description="Port name")
    container_port: int = Field(description="Container port number")
    service_port: Optional[int] = Field(default=None, description="Service port (defaults to container_port)")
    protocol: str = Field(default="TCP", description="Protocol (TCP/UDP)")


class ManifestConfig(BaseModel):
    """Configuration for generating Kubernetes manifests."""
    name: str = Field(description="Application/workload name")
    namespace: str = Field(default="default", description="Kubernetes namespace")
    workload_type: WorkloadType = Field(default=WorkloadType.DEPLOYMENT, description="Workload type")
    image: str = Field(description="Container image")
    replicas: int = Field(default=1, ge=0, description="Number of replicas")
    environment: EnvironmentType = Field(default=EnvironmentType.DEVELOPMENT, description="Environment type")
    security_profile: SecurityProfile = Field(default=SecurityProfile.BASIC, description="Security profile")
    resources: ResourceRequirements = Field(default_factory=ResourceRequirements, description="Resource requirements")
    security_context: SecurityContext = Field(default_factory=SecurityContext, description="Security context")
    liveness_probe: ProbeConfig = Field(default_factory=ProbeConfig, description="Liveness probe config")
    readiness_probe: ProbeConfig = Field(default_factory=ProbeConfig, description="Readiness probe config")
    labels: Dict[str, str] = Field(default_factory=dict, description="Additional labels")
    annotations: Dict[str, str] = Field(default_factory=dict, description="Annotations")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    config_maps: List[str] = Field(default_factory=list, description="ConfigMaps to mount")
    secrets: List[str] = Field(default_factory=list, description="Secrets to mount")
    volumes: List[Dict[str, Any]] = Field(default_factory=list, description="Volume definitions")
    service_account: Optional[str] = Field(default=None, description="Service account name")
    ports: List[PortConfig] = Field(
        default_factory=lambda: [PortConfig(container_port=8080)],
        description="Container ports"
    )
    cron_schedule: Optional[str] = Field(default=None, description="Cron schedule for CronJob workloads")


class GeneratedManifest(BaseModel):
    """Result of manifest generation."""
    id: str = Field(description="Unique manifest ID")
    config_hash: str = Field(description="Hash of the configuration")
    manifests: Dict[str, Dict[str, Any]] = Field(description="Generated manifest objects")
    yaml_content: str = Field(description="Combined YAML content")
    validation_results: List[str] = Field(default_factory=list, description="Validation issues found")
    best_practice_score: float = Field(ge=0, le=100, description="Best practice compliance score")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    file_path: Optional[str] = Field(default=None, description="Path where manifest was saved")

    @property
    def has_issues(self) -> bool:
        """Check if there are validation issues."""
        return len(self.validation_results) > 0

    @property
    def is_production_ready(self) -> bool:
        """Check if manifest meets production readiness criteria."""
        return self.best_practice_score >= 80 and not self.has_issues
