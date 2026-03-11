# Volundr - Infrastructure Generation

Named after the legendary Norse master smith (equivalent to Hephaestus in Greek mythology), Volundr forges infrastructure configurations from templates with precision and best practices. Like its namesake who crafted magnificent artifacts, Volundr creates production-ready infrastructure code.

## Overview

Volundr is an infrastructure generation library that creates Kubernetes manifests, Terraform modules, Dockerfiles, docker-compose configurations, and CI/CD pipelines. It generates production-ready infrastructure code with built-in best practices, security profiles, and validation.

## Features

- **Kubernetes**: Deployment, Service, ConfigMap, Secret, Ingress, StatefulSet, DaemonSet manifests with security profiles
- **Terraform**: Multi-cloud modules (AWS, Azure, GCP, multi-cloud) with variables, outputs, and best practices
- **Docker**: Dockerfiles with multi-stage builds, security hardening, and docker-compose orchestration
- **CI/CD**: Pipeline generation for GitHub Actions, GitLab CI, Azure DevOps, Jenkins, CircleCI

## Installation

```bash
pip install -e /path/to/Asgard
```

Or install directly:

```bash
cd /path/to/Asgard
pip install .
```

## Quick Start

### CLI Usage

```bash
# Kubernetes manifest generation
python -m Volundr kubernetes generate \
  --name myapp \
  --image nginx:latest \
  --namespace production \
  --type Deployment \
  --replicas 3 \
  --security-profile hardened \
  --environment production

# Terraform module generation
python -m Volundr terraform generate \
  --name vpc-module \
  --provider aws \
  --category networking \
  --complexity moderate \
  --description "VPC with public and private subnets"

# Dockerfile generation
python -m Volundr docker dockerfile \
  --name myapp \
  --base python:3.12-slim \
  --workdir /app \
  --port 8080 \
  --user appuser \
  --multi-stage

# Docker Compose generation
python -m Volundr docker compose \
  --name myproject \
  --services web api database redis

# CI/CD pipeline generation
python -m Volundr cicd generate \
  --name build-deploy \
  --platform github_actions \
  --branch main \
  --docker-image myorg/myapp:latest
```

### Python API Usage

```python
from Asgard.Volundr import (
    ManifestConfig,
    ManifestGenerator,
    WorkloadType,
    SecurityProfile,
    EnvironmentType,
    PortConfig,
    ModuleConfig,
    ModuleBuilder,
    CloudProvider,
    ResourceCategory,
    DockerfileConfig,
    DockerfileGenerator,
    BuildStage,
    PipelineConfig,
    PipelineGenerator,
    CICDPlatform,
)

# Kubernetes Manifest Generation
k8s_config = ManifestConfig(
    name="myapp",
    namespace="production",
    workload_type=WorkloadType.DEPLOYMENT,
    image="nginx:latest",
    replicas=3,
    environment=EnvironmentType.PRODUCTION,
    security_profile=SecurityProfile.HARDENED,
    ports=[PortConfig(container_port=8080, service_port=80)],
    resource_requests={"cpu": "100m", "memory": "128Mi"},
    resource_limits={"cpu": "500m", "memory": "512Mi"},
    health_checks=True,
)

generator = ManifestGenerator(output_dir="./k8s")
manifest = generator.generate(k8s_config)
file_path = generator.save_to_file(manifest, "./k8s")

print(f"Manifest saved: {file_path}")
print(f"Best Practice Score: {manifest.best_practice_score}/100")
print(manifest.yaml_content)

# Terraform Module Generation
tf_config = ModuleConfig(
    name="vpc-module",
    provider=CloudProvider.AWS,
    category=ResourceCategory.NETWORKING,
    description="VPC with public and private subnets",
    variables=[
        {"name": "vpc_cidr", "type": "string", "default": "10.0.0.0/16"},
        {"name": "environment", "type": "string"},
    ],
    outputs=[
        {"name": "vpc_id", "description": "The VPC ID", "value": "aws_vpc.main.id"},
    ],
    tags={"ManagedBy": "Terraform", "Environment": "production"},
)

builder = ModuleBuilder(output_dir="./terraform")
module = builder.generate(tf_config)
module_dir = builder.save_to_directory(module, "./terraform")

print(f"Module saved: {module_dir}")
print(f"Files: {module.file_count}")
print(f"Best Practice Score: {module.best_practice_score}/100")

# Dockerfile Generation
docker_config = DockerfileConfig(
    name="myapp",
    stages=[
        BuildStage(
            name="builder",
            base_image="python:3.12-slim",
            workdir="/app",
            copy_commands=[{"src": "requirements.txt", "dst": "."}],
            run_commands=["pip install --no-cache-dir -r requirements.txt"],
        ),
        BuildStage(
            name="runtime",
            base_image="python:3.12-slim",
            workdir="/app",
            user="appuser",
            copy_from="builder",
            copy_src="/usr/local/lib/python",
            copy_dst="/usr/local/lib/python",
            expose_ports=[8080],
            cmd=["python", "main.py"],
        ),
    ],
    labels={
        "org.opencontainers.image.title": "myapp",
        "org.opencontainers.image.source": "https://github.com/org/repo",
    },
)

docker_gen = DockerfileGenerator(output_dir=".")
docker_result = docker_gen.generate(docker_config)
docker_path = docker_gen.save_to_file(docker_result, ".")

print(f"Dockerfile saved: {docker_path}")
print(f"Best Practice Score: {docker_result.best_practice_score}/100")

# CI/CD Pipeline Generation
pipeline_config = PipelineConfig(
    name="build-deploy",
    platform=CICDPlatform.GITHUB_ACTIONS,
    triggers=[
        {"type": "push", "branches": ["main"]},
        {"type": "pull_request", "branches": ["main"]},
    ],
    stages=[
        {
            "name": "build",
            "runs_on": "ubuntu-latest",
            "steps": [
                {"name": "Checkout", "uses": "actions/checkout@v4"},
                {"name": "Setup Python", "uses": "actions/setup-python@v5"},
                {"name": "Install dependencies", "run": "pip install -r requirements.txt"},
                {"name": "Run tests", "run": "pytest"},
            ],
        },
    ],
)

pipeline_gen = PipelineGenerator(output_dir=".github/workflows")
pipeline = pipeline_gen.generate(pipeline_config)
pipeline_path = pipeline_gen.save_to_file(pipeline, ".github/workflows")

print(f"Pipeline saved: {pipeline_path}")
print(f"Best Practice Score: {pipeline.best_practice_score}/100")
```

## Submodules

### Kubernetes Module

Kubernetes manifest generation with security profiles and best practices.

**Services:**
- `ManifestGenerator`: Generate complete Kubernetes manifests

**Workload Types:**
- Deployment
- StatefulSet
- DaemonSet
- Job
- CronJob
- Pod

**Security Profiles:**
- **Basic**: Standard security (runAsNonRoot, readOnlyRootFilesystem)
- **Moderate**: Enhanced security (capabilities drop, seccomp, apparmor)
- **Hardened**: Maximum security (all restrictions, pod security standards)

**Features:**
- Resource requests and limits
- Health checks (liveness, readiness, startup)
- Environment variables and ConfigMaps
- Secrets management
- Service creation (ClusterIP, NodePort, LoadBalancer)
- Ingress configuration
- Network policies
- Pod disruption budgets

### Terraform Module

Multi-cloud Terraform module generation with best practices.

**Services:**
- `ModuleBuilder`: Generate complete Terraform modules

**Cloud Providers:**
- AWS
- Azure
- Google Cloud Platform (GCP)
- Multi-cloud

**Resource Categories:**
- Compute (EC2, VMs, instances)
- Storage (S3, Blob Storage, Cloud Storage)
- Networking (VPC, VNet, subnets)
- Database (RDS, SQL Database, Cloud SQL)
- Security (IAM, Security Groups, Firewalls)

**Module Complexity:**
- Simple: Single resource type
- Moderate: Multiple related resources
- Complex: Full infrastructure stack

**Features:**
- Variable definitions with types and defaults
- Output values with descriptions
- Data source integration
- Resource dependencies
- Tagging strategy
- Backend configuration
- Provider versioning

### Docker Module

Dockerfile and docker-compose generation with security hardening.

**Services:**
- `DockerfileGenerator`: Generate optimized Dockerfiles
- `ComposeGenerator`: Generate docker-compose configurations

**Dockerfile Features:**
- Multi-stage builds
- Non-root user creation
- Layer caching optimization
- Security scanning integration
- Health checks
- Labels and metadata
- Build arguments
- Volume management

**docker-compose Features:**
- Multi-service orchestration
- Network configuration
- Volume management
- Environment variable handling
- Health checks
- Restart policies
- Resource constraints

### CICD Module

CI/CD pipeline generation for multiple platforms.

**Services:**
- `PipelineGenerator`: Generate CI/CD pipelines

**Supported Platforms:**
- GitHub Actions
- GitLab CI
- Azure DevOps
- Jenkins
- CircleCI

**Pipeline Features:**
- Trigger configuration (push, PR, schedule)
- Multi-stage builds
- Matrix builds
- Artifact management
- Cache configuration
- Secret management
- Environment variables
- Deployment stages
- Notification integration

## CLI Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `kubernetes generate` | Generate K8s manifests | `python -m Volundr kubernetes generate --name myapp --image nginx` |
| `terraform generate` | Generate Terraform module | `python -m Volundr terraform generate --name vpc --provider aws` |
| `docker dockerfile` | Generate Dockerfile | `python -m Volundr docker dockerfile --name myapp --base python:3.12` |
| `docker compose` | Generate docker-compose | `python -m Volundr docker compose --name project --services web db` |
| `cicd generate` | Generate CI/CD pipeline | `python -m Volundr cicd generate --name ci --platform github_actions` |

## Configuration Options

### Kubernetes Options

- `--name`: Application name (required)
- `--image`: Container image (required)
- `--namespace`: Kubernetes namespace (default: default)
- `--type`: Workload type (Deployment, StatefulSet, DaemonSet, Job, CronJob)
- `--replicas`: Number of replicas (default: 1)
- `--environment`: Environment type (development, staging, production)
- `--security-profile`: Security profile (basic, moderate, hardened)
- `--port`: Container port (default: 8080)
- `--output-dir`: Output directory (default: manifests)
- `--format`: Output format (yaml, json)

### Terraform Options

- `--name`: Module name (required)
- `--provider`: Cloud provider (aws, azure, gcp, multi-cloud) (required)
- `--category`: Resource category (compute, storage, networking, database, security) (required)
- `--complexity`: Module complexity (simple, moderate, complex)
- `--description`: Module description
- `--output-dir`: Output directory (default: modules)

### Docker Options

- `--name`: Application name (required)
- `--base`: Base image (required)
- `--workdir`: Working directory (default: /app)
- `--port`: Exposed port (default: 8080)
- `--user`: Non-root user (default: appuser)
- `--output-dir`: Output directory (default: .)
- `--multi-stage`: Use multi-stage build
- `--services`: Service names for compose (space-separated)

### CI/CD Options

- `--name`: Pipeline name (required)
- `--platform`: CI/CD platform (github_actions, gitlab_ci, azure_devops, jenkins, circleci)
- `--branch`: Main branch name (default: main)
- `--docker-image`: Docker image to build/push
- `--output-dir`: Output directory

## Best Practice Scores

All generated configurations include a best practice score (0-100):

- **95-100**: Excellent - Production-ready with all best practices
- **85-94**: Good - Ready with minor improvements possible
- **75-84**: Fair - Acceptable but needs improvements
- **Below 75**: Needs work - Review validation results

## Troubleshooting

### Common Issues

**Issue: "Invalid configuration"**
- Check all required fields are provided
- Verify enum values (WorkloadType, CloudProvider, etc.)
- Ensure image tags are specified

**Issue: "Generated files not found"**
- Check output directory exists
- Verify write permissions
- Look for validation errors in output

**Issue: "Best practice score low"**
- Review validation_results in output
- Add missing health checks
- Specify resource limits
- Enable security features

**Issue: "Multi-stage build not working"**
- Ensure base images are compatible
- Check COPY --from syntax
- Verify stage names

### Performance Tips

- Use multi-stage builds for smaller images
- Enable caching in CI/CD pipelines
- Use specific image tags, not :latest
- Set appropriate resource limits
- Use security profiles for production

## Generated File Structure

### Kubernetes

```
manifests/
  myapp-deployment.yaml    # Deployment manifest
  myapp-service.yaml       # Service manifest (if ports defined)
  myapp-configmap.yaml     # ConfigMap (if env vars defined)
```

### Terraform

```
modules/
  vpc-module/
    main.tf           # Main resources
    variables.tf      # Input variables
    outputs.tf        # Output values
    versions.tf       # Provider versions
    README.md         # Module documentation
```

### Docker

```
Dockerfile              # Generated Dockerfile
docker-compose.yml     # Generated compose file (if services defined)
```

### CI/CD

```
.github/workflows/      # GitHub Actions
  build-deploy.yml

.gitlab-ci.yml         # GitLab CI

azure-pipelines.yml    # Azure DevOps

Jenkinsfile           # Jenkins
```

## Integration with Infrastructure as Code

```yaml
# Example: Automated infrastructure generation in CI/CD
- name: Generate Kubernetes Manifests
  run: |
    python -m Volundr kubernetes generate \
      --name ${{ github.event.repository.name }} \
      --image ${{ env.DOCKER_IMAGE }} \
      --namespace production \
      --environment production \
      --security-profile hardened \
      --output-dir ./k8s

- name: Apply to Cluster
  run: kubectl apply -f ./k8s/
```

## Best Practices

1. **Security First**: Always use hardened security profiles for production
2. **Resource Limits**: Always specify resource requests and limits
3. **Health Checks**: Enable health checks for all services
4. **Multi-stage Builds**: Use multi-stage Docker builds to reduce image size
5. **Tagging**: Use semantic versioning for images and modules
6. **Documentation**: Generated files include inline documentation
7. **Validation**: Review validation results before deploying
8. **Version Control**: Commit generated infrastructure code

## Security Considerations

### Kubernetes

- Non-root user enforcement
- Read-only root filesystem
- Capability dropping
- Pod security standards
- Network policies
- Secret management

### Docker

- Non-root user creation
- Multi-stage builds to reduce attack surface
- No secrets in layers
- Image scanning integration
- Minimal base images

### Terraform

- Encryption at rest
- Secure defaults
- IAM least privilege
- Network segmentation
- Audit logging

### CI/CD

- Secret management
- Least privilege access
- Pipeline approval gates
- Artifact signing
- Vulnerability scanning

## Version

Version: 1.0.0

## Author

Asgard Contributors
