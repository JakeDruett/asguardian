"""
CICD Models for Pipeline Generation

Provides Pydantic models for configuring and generating CI/CD pipelines
across multiple platforms with deployment strategies and best practices.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CICDPlatform(str, Enum):
    """Supported CI/CD platforms."""
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    AZURE_DEVOPS = "azure_devops"
    JENKINS = "jenkins"
    CIRCLECI = "circleci"


class DeploymentStrategy(str, Enum):
    """Deployment strategies."""
    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    RECREATE = "recreate"
    A_B_TESTING = "ab_testing"


class TriggerType(str, Enum):
    """Pipeline trigger types."""
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    TAG = "tag"
    SCHEDULE = "schedule"
    MANUAL = "manual"
    WORKFLOW_DISPATCH = "workflow_dispatch"


class StepConfig(BaseModel):
    """Configuration for a pipeline step/task."""
    name: str = Field(description="Step name")
    run: Optional[str] = Field(default=None, description="Command to run")
    uses: Optional[str] = Field(default=None, description="Action/image to use")
    with_params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the action")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    if_condition: Optional[str] = Field(default=None, description="Conditional execution")
    continue_on_error: bool = Field(default=False, description="Continue on error")
    timeout_minutes: Optional[int] = Field(default=None, description="Step timeout")


class PipelineStage(BaseModel):
    """Configuration for a pipeline stage/job."""
    name: str = Field(description="Stage/job name")
    runs_on: str = Field(default="ubuntu-latest", description="Runner/agent to use")
    needs: List[str] = Field(default_factory=list, description="Dependencies on other stages")
    steps: List[StepConfig] = Field(default_factory=list, description="Steps to execute")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    services: Dict[str, Any] = Field(default_factory=dict, description="Service containers")
    strategy: Optional[Dict[str, Any]] = Field(default=None, description="Matrix/parallel strategy")
    if_condition: Optional[str] = Field(default=None, description="Conditional execution")
    timeout_minutes: int = Field(default=60, description="Job timeout")
    continue_on_error: bool = Field(default=False, description="Continue on error")
    environment: Optional[str] = Field(default=None, description="Deployment environment")


class TriggerConfig(BaseModel):
    """Pipeline trigger configuration."""
    type: TriggerType = Field(description="Trigger type")
    branches: List[str] = Field(default_factory=list, description="Branches to trigger on")
    paths: List[str] = Field(default_factory=list, description="Paths to watch")
    paths_ignore: List[str] = Field(default_factory=list, description="Paths to ignore")
    tags: List[str] = Field(default_factory=list, description="Tags to trigger on")
    schedule: Optional[str] = Field(default=None, description="Cron schedule")


class PipelineConfig(BaseModel):
    """Configuration for generating CI/CD pipelines."""
    name: str = Field(description="Pipeline name")
    platform: CICDPlatform = Field(description="CI/CD platform")
    triggers: List[TriggerConfig] = Field(default_factory=list, description="Pipeline triggers")
    stages: List[PipelineStage] = Field(description="Pipeline stages/jobs")
    env: Dict[str, str] = Field(default_factory=dict, description="Global environment variables")
    secrets: List[str] = Field(default_factory=list, description="Required secrets")
    concurrency: Optional[Dict[str, Any]] = Field(default=None, description="Concurrency settings")
    deployment_strategy: DeploymentStrategy = Field(
        default=DeploymentStrategy.ROLLING, description="Deployment strategy"
    )
    docker_registry: Optional[str] = Field(default=None, description="Docker registry URL")
    kubernetes_cluster: Optional[str] = Field(default=None, description="Kubernetes cluster context")


class GeneratedPipeline(BaseModel):
    """Result of pipeline generation."""
    id: str = Field(description="Unique pipeline ID")
    config_hash: str = Field(description="Hash of the configuration")
    platform: CICDPlatform = Field(description="Target platform")
    pipeline_content: str = Field(description="Generated pipeline content")
    file_path: str = Field(description="Recommended file path")
    validation_results: List[str] = Field(default_factory=list, description="Validation issues found")
    best_practice_score: float = Field(ge=0, le=100, description="Best practice compliance score")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

    @property
    def has_issues(self) -> bool:
        """Check if there are validation issues."""
        return len(self.validation_results) > 0
