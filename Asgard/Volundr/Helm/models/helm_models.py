"""
Helm Models for Chart Generation

Provides Pydantic models for configuring and generating Helm charts
with best practices, security configurations, and operational readiness.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChartType(str, Enum):
    """Helm chart types."""
    APPLICATION = "application"
    LIBRARY = "library"


class HelmMaintainer(BaseModel):
    """Helm chart maintainer information."""
    name: str = Field(description="Maintainer name")
    email: Optional[str] = Field(default=None, description="Maintainer email")
    url: Optional[str] = Field(default=None, description="Maintainer URL")


class HelmDependency(BaseModel):
    """Helm chart dependency configuration."""
    name: str = Field(description="Dependency name")
    version: str = Field(description="Dependency version")
    repository: str = Field(description="Chart repository URL")
    condition: Optional[str] = Field(default=None, description="Condition to enable dependency")
    tags: List[str] = Field(default_factory=list, description="Tags for grouping")
    alias: Optional[str] = Field(default=None, description="Alias for the dependency")
    import_values: List[Any] = Field(default_factory=list, description="Values to import")


class HelmChart(BaseModel):
    """Helm Chart.yaml configuration."""
    api_version: str = Field(default="v2", description="Chart API version")
    name: str = Field(description="Chart name")
    version: str = Field(default="0.1.0", description="Chart version")
    app_version: str = Field(default="1.0.0", description="Application version")
    description: str = Field(default="", description="Chart description")
    type: ChartType = Field(default=ChartType.APPLICATION, description="Chart type")
    keywords: List[str] = Field(default_factory=list, description="Chart keywords")
    home: Optional[str] = Field(default=None, description="Project home URL")
    sources: List[str] = Field(default_factory=list, description="Source code URLs")
    maintainers: List[HelmMaintainer] = Field(default_factory=list, description="Chart maintainers")
    icon: Optional[str] = Field(default=None, description="Icon URL")
    deprecated: bool = Field(default=False, description="Is chart deprecated")
    annotations: Dict[str, str] = Field(default_factory=dict, description="Chart annotations")
    kube_version: Optional[str] = Field(default=None, description="Kubernetes version constraint")
    dependencies: List[HelmDependency] = Field(default_factory=list, description="Chart dependencies")


class ResourceSpec(BaseModel):
    """Container resource specification."""
    cpu: str = Field(default="100m", description="CPU amount")
    memory: str = Field(default="128Mi", description="Memory amount")


class ResourceRequirements(BaseModel):
    """Container resource requirements."""
    limits: ResourceSpec = Field(default_factory=ResourceSpec, description="Resource limits")
    requests: ResourceSpec = Field(default_factory=ResourceSpec, description="Resource requests")


class ProbeConfig(BaseModel):
    """Health probe configuration."""
    enabled: bool = Field(default=True, description="Enable probe")
    path: str = Field(default="/health", description="HTTP probe path")
    port: str = Field(default="http", description="Port name or number")
    initial_delay_seconds: int = Field(default=10, description="Initial delay")
    period_seconds: int = Field(default=10, description="Probe period")
    timeout_seconds: int = Field(default=5, description="Probe timeout")
    failure_threshold: int = Field(default=3, description="Failure threshold")
    success_threshold: int = Field(default=1, description="Success threshold")


class AutoscalingConfig(BaseModel):
    """Horizontal Pod Autoscaler configuration."""
    enabled: bool = Field(default=False, description="Enable HPA")
    min_replicas: int = Field(default=1, description="Minimum replicas")
    max_replicas: int = Field(default=10, description="Maximum replicas")
    target_cpu_utilization: int = Field(default=80, description="Target CPU utilization")
    target_memory_utilization: Optional[int] = Field(default=None, description="Target memory utilization")


class ServiceConfig(BaseModel):
    """Kubernetes Service configuration."""
    type: str = Field(default="ClusterIP", description="Service type")
    port: int = Field(default=80, description="Service port")
    target_port: str = Field(default="http", description="Target port")
    node_port: Optional[int] = Field(default=None, description="Node port (for NodePort type)")


class IngressConfig(BaseModel):
    """Kubernetes Ingress configuration."""
    enabled: bool = Field(default=False, description="Enable Ingress")
    class_name: Optional[str] = Field(default=None, description="Ingress class name")
    annotations: Dict[str, str] = Field(default_factory=dict, description="Ingress annotations")
    hosts: List[Dict[str, Any]] = Field(default_factory=list, description="Ingress hosts")
    tls: List[Dict[str, Any]] = Field(default_factory=list, description="TLS configuration")


class SecurityContextConfig(BaseModel):
    """Pod/Container security context."""
    run_as_non_root: bool = Field(default=True, description="Run as non-root")
    run_as_user: Optional[int] = Field(default=1000, description="User ID")
    run_as_group: Optional[int] = Field(default=3000, description="Group ID")
    fs_group: Optional[int] = Field(default=2000, description="FS group")
    read_only_root_filesystem: bool = Field(default=True, description="Read-only root filesystem")
    allow_privilege_escalation: bool = Field(default=False, description="Allow privilege escalation")


class HelmValues(BaseModel):
    """Helm values.yaml configuration."""
    replica_count: int = Field(default=1, description="Number of replicas")
    image_repository: str = Field(description="Container image repository")
    image_tag: str = Field(default="latest", description="Container image tag")
    image_pull_policy: str = Field(default="IfNotPresent", description="Image pull policy")
    image_pull_secrets: List[str] = Field(default_factory=list, description="Image pull secrets")
    name_override: str = Field(default="", description="Name override")
    fullname_override: str = Field(default="", description="Fullname override")
    service_account_create: bool = Field(default=True, description="Create service account")
    service_account_name: str = Field(default="", description="Service account name")
    service_account_annotations: Dict[str, str] = Field(default_factory=dict, description="SA annotations")
    pod_annotations: Dict[str, str] = Field(default_factory=dict, description="Pod annotations")
    pod_labels: Dict[str, str] = Field(default_factory=dict, description="Pod labels")
    pod_security_context: SecurityContextConfig = Field(
        default_factory=SecurityContextConfig, description="Pod security context"
    )
    security_context: SecurityContextConfig = Field(
        default_factory=SecurityContextConfig, description="Container security context"
    )
    service: ServiceConfig = Field(default_factory=ServiceConfig, description="Service configuration")
    ingress: IngressConfig = Field(default_factory=IngressConfig, description="Ingress configuration")
    resources: ResourceRequirements = Field(default_factory=ResourceRequirements, description="Resource requirements")
    autoscaling: AutoscalingConfig = Field(default_factory=AutoscalingConfig, description="HPA configuration")
    liveness_probe: ProbeConfig = Field(default_factory=ProbeConfig, description="Liveness probe")
    readiness_probe: ProbeConfig = Field(default_factory=ProbeConfig, description="Readiness probe")
    node_selector: Dict[str, str] = Field(default_factory=dict, description="Node selector")
    tolerations: List[Dict[str, Any]] = Field(default_factory=list, description="Pod tolerations")
    affinity: Dict[str, Any] = Field(default_factory=dict, description="Pod affinity")
    env: List[Dict[str, Any]] = Field(default_factory=list, description="Environment variables")
    env_from: List[Dict[str, Any]] = Field(default_factory=list, description="Environment from")
    volumes: List[Dict[str, Any]] = Field(default_factory=list, description="Volumes")
    volume_mounts: List[Dict[str, Any]] = Field(default_factory=list, description="Volume mounts")
    extra_config: Dict[str, Any] = Field(default_factory=dict, description="Extra configuration values")


class HelmConfig(BaseModel):
    """Configuration for generating Helm charts."""
    chart: HelmChart = Field(description="Chart.yaml configuration")
    values: HelmValues = Field(description="values.yaml configuration")
    generate_tests: bool = Field(default=True, description="Generate test templates")
    generate_notes: bool = Field(default=True, description="Generate NOTES.txt")
    generate_helpers: bool = Field(default=True, description="Generate _helpers.tpl")
    include_network_policy: bool = Field(default=False, description="Include NetworkPolicy template")
    include_pdb: bool = Field(default=False, description="Include PodDisruptionBudget template")
    include_hpa: bool = Field(default=True, description="Include HPA template")
    include_service_account: bool = Field(default=True, description="Include ServiceAccount template")
    include_configmap: bool = Field(default=False, description="Include ConfigMap template")
    include_secret: bool = Field(default=False, description="Include Secret template")


class GeneratedHelmChart(BaseModel):
    """Result of Helm chart generation."""
    id: str = Field(description="Unique chart ID")
    config_hash: str = Field(description="Hash of the configuration")
    chart_files: Dict[str, str] = Field(description="Generated chart files (path -> content)")
    validation_results: List[str] = Field(default_factory=list, description="Validation issues found")
    best_practice_score: float = Field(ge=0, le=100, description="Best practice compliance score")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    output_path: Optional[str] = Field(default=None, description="Path where chart was saved")

    @property
    def has_issues(self) -> bool:
        """Check if there are validation issues."""
        return len(self.validation_results) > 0

    @property
    def file_count(self) -> int:
        """Get the number of generated files."""
        return len(self.chart_files)
