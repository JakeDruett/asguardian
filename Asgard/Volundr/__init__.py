"""
Volundr - Infrastructure Generation Library

Named after the legendary Norse master smith (equivalent to Hephaestus in Greek mythology),
Volundr forges infrastructure configurations from templates with precision and best practices.

Subpackages:
- Kubernetes: Manifest generation (Deployments, Services, ConfigMaps, etc.)
- Terraform: Module generation (multi-cloud support, variables, outputs)
- Docker: Dockerfile and docker-compose generation
- CICD: Pipeline generation (GitHub Actions, GitLab CI, Azure DevOps, Jenkins)
- Helm: Helm chart generation
- Kustomize: Kustomize configuration generation
- GitOps: ArgoCD and Flux configuration generation
- Compose: Enhanced Docker Compose generation
- Validation: Infrastructure configuration validation
- Scaffold: Project scaffolding for microservices and monorepos

Usage:
    python -m Volundr --help
    python -m Volundr kubernetes generate --name myapp --image nginx:latest
    python -m Volundr terraform generate --name vpc --provider aws --category networking
    python -m Volundr docker dockerfile --name myapp --base python:3.12-slim
    python -m Volundr cicd generate --name ci-pipeline --platform github_actions
    python -m Volundr helm init myapp
    python -m Volundr kustomize init myapp
    python -m Volundr argocd app https://github.com/org/repo
    python -m Volundr validate kubernetes ./manifests
    python -m Volundr scaffold microservice myapp

Programmatic Usage:
    from Asgard.Volundr.Kubernetes import ManifestConfig, ManifestGenerator
    from Asgard.Volundr.Terraform import ModuleConfig, ModuleBuilder
    from Asgard.Volundr.Docker import DockerfileConfig, DockerfileGenerator
    from Asgard.Volundr.CICD import PipelineConfig, PipelineGenerator
    from Asgard.Volundr.Helm import HelmConfig, ChartGenerator
    from Asgard.Volundr.Kustomize import KustomizeConfig, BaseGenerator
    from Asgard.Volundr.GitOps import ArgoApplication, ArgoCDGenerator
    from Asgard.Volundr.Validation import KubernetesValidator, DockerfileValidator
    from Asgard.Volundr.Scaffold import ServiceConfig, MicroserviceScaffold

    # Kubernetes manifest generation
    config = ManifestConfig(name="myapp", image="nginx:latest")
    generator = ManifestGenerator()
    manifest = generator.generate(config)
    print(manifest.yaml_content)

    # Terraform module generation
    tf_config = ModuleConfig(name="vpc", provider="aws", category="networking")
    builder = ModuleBuilder()
    module = builder.generate(tf_config)
    builder.save_to_directory(module)
"""

__version__ = "2.0.0"
__author__ = "Asgard Contributors"

PACKAGE_INFO = {
    "name": "Volundr",
    "version": __version__,
    "description": "Infrastructure generation library",
    "author": __author__,
    "sub_packages": [
        "Kubernetes - Manifest generation (Deployments, Services, ConfigMaps)",
        "Terraform - Module generation (multi-cloud, variables, outputs)",
        "Docker - Dockerfile and docker-compose generation",
        "CICD - Pipeline generation (GitHub Actions, GitLab CI, etc.)",
        "Helm - Helm chart generation with templates",
        "Kustomize - Kustomize base and overlay generation",
        "GitOps - ArgoCD and Flux configuration generation",
        "Compose - Enhanced Docker Compose generation",
        "Validation - Infrastructure configuration validation",
        "Scaffold - Project scaffolding for microservices and monorepos",
    ],
}

from . import Kubernetes
from . import Terraform
from . import Docker
from . import CICD
from . import Helm
from . import Kustomize
from . import GitOps
from . import Compose
from . import Validation
from . import Scaffold

from Asgard.Volundr.Kubernetes import (
    ManifestConfig,
    ManifestGenerator,
    GeneratedManifest,
    WorkloadType,
    SecurityProfile,
    EnvironmentType,
    PortConfig,
    ResourceRequirements,
    SecurityContext,
    ProbeConfig,
)

from Asgard.Volundr.Terraform import (
    ModuleConfig,
    ModuleBuilder,
    GeneratedModule,
    CloudProvider,
    ResourceCategory,
    ModuleComplexity,
)

from Asgard.Volundr.Docker import (
    DockerfileConfig,
    DockerfileGenerator,
    ComposeConfig,
    ComposeGenerator,
    GeneratedDockerConfig,
)

from Asgard.Volundr.CICD import (
    PipelineConfig,
    PipelineGenerator,
    GeneratedPipeline,
    CICDPlatform,
    PipelineStage,
    TriggerConfig,
    TriggerType,
    StepConfig,
    DeploymentStrategy,
)

from Asgard.Volundr.Helm import (
    HelmChart,
    HelmValues,
    HelmConfig,
    GeneratedHelmChart,
    ChartGenerator,
    ValuesGenerator,
)

from Asgard.Volundr.Kustomize import (
    KustomizeBase,
    KustomizeOverlay,
    KustomizeConfig,
    GeneratedKustomization,
    BaseGenerator,
    OverlayGenerator,
    PatchGenerator,
)

from Asgard.Volundr.GitOps import (
    ArgoApplication,
    ArgoSource,
    ArgoDestination,
    FluxKustomization,
    FluxGitRepository,
    GitOpsConfig,
    SyncPolicy,
    HealthPolicy,
    GeneratedGitOpsConfig,
    ArgoCDGenerator,
    FluxGenerator,
)

from Asgard.Volundr.Compose import (
    ComposeService,
    ComposeNetwork,
    ComposeProject,
    GeneratedComposeConfig,
    ComposeProjectGenerator,
    ComposeValidator,
)

from Asgard.Volundr.Validation import (
    ValidationResult,
    ValidationReport,
    KubernetesValidator,
    TerraformValidator,
    DockerfileValidator,
)

from Asgard.Volundr.Scaffold import (
    ProjectConfig,
    ServiceConfig,
    ScaffoldReport,
    MicroserviceScaffold,
    MonorepoScaffold,
    ProjectType,
    Language,
    Framework,
)

__all__ = [
    # Modules
    "Kubernetes",
    "Terraform",
    "Docker",
    "CICD",
    "Helm",
    "Kustomize",
    "GitOps",
    "Compose",
    "Validation",
    "Scaffold",
    # Kubernetes
    "ManifestConfig",
    "ManifestGenerator",
    "GeneratedManifest",
    "WorkloadType",
    "SecurityProfile",
    "EnvironmentType",
    "PortConfig",
    "ResourceRequirements",
    "SecurityContext",
    "ProbeConfig",
    # Terraform
    "ModuleConfig",
    "ModuleBuilder",
    "GeneratedModule",
    "CloudProvider",
    "ResourceCategory",
    "ModuleComplexity",
    # Docker
    "DockerfileConfig",
    "DockerfileGenerator",
    "ComposeConfig",
    "ComposeGenerator",
    "GeneratedDockerConfig",
    # CICD
    "PipelineConfig",
    "PipelineGenerator",
    "GeneratedPipeline",
    "CICDPlatform",
    "PipelineStage",
    "TriggerConfig",
    "TriggerType",
    "StepConfig",
    "DeploymentStrategy",
    # Helm
    "HelmChart",
    "HelmValues",
    "HelmConfig",
    "GeneratedHelmChart",
    "ChartGenerator",
    "ValuesGenerator",
    # Kustomize
    "KustomizeBase",
    "KustomizeOverlay",
    "KustomizeConfig",
    "GeneratedKustomization",
    "BaseGenerator",
    "OverlayGenerator",
    "PatchGenerator",
    # GitOps
    "ArgoApplication",
    "ArgoSource",
    "ArgoDestination",
    "FluxKustomization",
    "FluxGitRepository",
    "GitOpsConfig",
    "SyncPolicy",
    "HealthPolicy",
    "GeneratedGitOpsConfig",
    "ArgoCDGenerator",
    "FluxGenerator",
    # Compose
    "ComposeService",
    "ComposeNetwork",
    "ComposeProject",
    "GeneratedComposeConfig",
    "ComposeProjectGenerator",
    "ComposeValidator",
    # Validation
    "ValidationResult",
    "ValidationReport",
    "KubernetesValidator",
    "TerraformValidator",
    "DockerfileValidator",
    # Scaffold
    "ProjectConfig",
    "ServiceConfig",
    "ScaffoldReport",
    "MicroserviceScaffold",
    "MonorepoScaffold",
    "ProjectType",
    "Language",
    "Framework",
]
