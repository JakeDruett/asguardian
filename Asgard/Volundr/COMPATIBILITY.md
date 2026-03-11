# Volundr Compatibility Matrix

This document defines the compatibility requirements, supported versions, and testing matrix for Volundr's infrastructure generation capabilities.

## Overview

Volundr generates infrastructure-as-code configurations for multiple platforms and cloud providers. This compatibility matrix ensures generated configurations are compatible with current and supported versions of target platforms.

## Versioning Policy

### Semantic Versioning
Volundr follows semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes to API or generated output format
- **MINOR**: New features, new platform support, backwards-compatible changes
- **PATCH**: Bug fixes, security updates, documentation improvements

### Support Lifecycle
- **Current Version**: Full support with new features and bug fixes
- **Previous Major Version**: Security fixes and critical bug fixes for 12 months
- **End of Life**: No updates; upgrade recommended

### Generated Code Compatibility
- Generated configurations target **current stable versions** of each platform
- **Backward compatibility** maintained for one major version back where possible
- **Forward compatibility** tested against release candidates when available

## Kubernetes Compatibility

### Supported Kubernetes Versions

| Kubernetes Version | Status | API Versions | Notes |
|-------------------|--------|--------------|-------|
| 1.29.x | Fully Supported | v1, apps/v1, batch/v1, networking.k8s.io/v1, policy/v1 | Latest stable |
| 1.28.x | Fully Supported | v1, apps/v1, batch/v1, networking.k8s.io/v1, policy/v1 | Recommended |
| 1.27.x | Fully Supported | v1, apps/v1, batch/v1, networking.k8s.io/v1, policy/v1 | LTS |
| 1.26.x | Supported | v1, apps/v1, batch/v1, networking.k8s.io/v1, policy/v1 | Maintenance mode |
| 1.25.x | Limited Support | v1, apps/v1, batch/v1, networking.k8s.io/v1, policy/v1 | Deprecated |
| < 1.25 | Not Supported | - | Upgrade required |

### Kubernetes API Versions

| API Group | Version | Usage | Notes |
|-----------|---------|-------|-------|
| Core API | v1 | Service, ConfigMap, Secret, Pod, PersistentVolume | Stable |
| Apps API | apps/v1 | Deployment, StatefulSet, DaemonSet, ReplicaSet | Stable |
| Batch API | batch/v1 | Job, CronJob | Stable |
| Networking API | networking.k8s.io/v1 | NetworkPolicy, Ingress | Stable |
| Policy API | policy/v1 | PodDisruptionBudget | Stable (PodSecurityPolicy deprecated) |
| RBAC API | rbac.authorization.k8s.io/v1 | Role, RoleBinding, ClusterRole | Stable |
| Autoscaling API | autoscaling/v2 | HorizontalPodAutoscaler | Stable |

### Supported Resource Types

**Workload Resources:**
- Deployment (apps/v1)
- StatefulSet (apps/v1)
- DaemonSet (apps/v1)
- Job (batch/v1)
- CronJob (batch/v1)
- Pod (v1) - Direct pod generation available

**Service Resources:**
- Service (v1) - ClusterIP, NodePort, LoadBalancer
- Ingress (networking.k8s.io/v1)

**Configuration Resources:**
- ConfigMap (v1)
- Secret (v1)

**Policy Resources:**
- NetworkPolicy (networking.k8s.io/v1)
- PodDisruptionBudget (policy/v1)

**Storage Resources:**
- PersistentVolume (v1)
- PersistentVolumeClaim (v1)
- StorageClass (storage.k8s.io/v1)

### Kubernetes Distribution Compatibility

| Distribution | Version | Tested | Notes |
|--------------|---------|--------|-------|
| Kubernetes (upstream) | 1.25-1.29 | Yes | Reference implementation |
| Amazon EKS | 1.25-1.29 | Yes | AWS-specific annotations supported |
| Google GKE | 1.25-1.29 | Yes | GCP-specific annotations supported |
| Azure AKS | 1.25-1.29 | Yes | Azure-specific annotations supported |
| Red Hat OpenShift | 4.12-4.14 | Partial | Some OpenShift-specific features not generated |
| Rancher RKE2 | 1.25-1.29 | Yes | Standard Kubernetes compatibility |
| K3s | 1.25-1.29 | Yes | Lightweight distributions supported |

## Terraform Compatibility

### Terraform Core Requirements

| Component | Version | Status | Notes |
|-----------|---------|--------|-------|
| Terraform | >= 1.0.0 | Required | Minimum version |
| Terraform | 1.5.x - 1.7.x | Fully Supported | Latest stable releases |
| Terraform | 0.15.x - 0.15.x | Deprecated | Upgrade recommended |
| Terraform | < 0.15 | Not Supported | Incompatible |

### Cloud Provider Compatibility

#### AWS Provider

| Provider Version | Terraform Version | Status | Notes |
|-----------------|-------------------|--------|-------|
| >= 5.0, < 6.0 | >= 1.0 | Fully Supported | Latest stable |
| >= 4.0, < 5.0 | >= 1.0 | Supported | Maintenance mode |
| < 4.0 | >= 0.15 | Deprecated | Upgrade recommended |

**Supported AWS Resources:**
- VPC, Subnet, Route Table, Internet Gateway
- EC2 Instance, Launch Template, Auto Scaling Group
- S3 Bucket (with encryption and versioning)
- RDS Instance, RDS Cluster
- ECS Cluster, ECS Service, ECS Task Definition
- EKS Cluster, EKS Node Group
- Lambda Function
- IAM Role, IAM Policy
- Security Group, Network ACL
- ALB, NLB
- CloudWatch Log Group

#### Azure Provider (azurerm)

| Provider Version | Terraform Version | Status | Notes |
|-----------------|-------------------|--------|-------|
| >= 3.0, < 4.0 | >= 1.0 | Fully Supported | Latest stable |
| >= 2.90, < 3.0 | >= 0.15 | Supported | Maintenance mode |
| < 2.90 | >= 0.15 | Deprecated | Upgrade recommended |

**Supported Azure Resources:**
- Resource Group
- Virtual Network, Subnet, Network Security Group
- Virtual Machine, Virtual Machine Scale Set
- Storage Account, Storage Container
- Azure SQL Database, Azure SQL Server
- Azure Kubernetes Service (AKS)
- Azure Container Instance
- Azure Functions
- Key Vault
- Application Gateway, Load Balancer

#### GCP Provider (google)

| Provider Version | Terraform Version | Status | Notes |
|-----------------|-------------------|--------|-------|
| >= 5.0, < 6.0 | >= 1.0 | Fully Supported | Latest stable |
| >= 4.0, < 5.0 | >= 1.0 | Supported | Maintenance mode |
| < 4.0 | >= 0.15 | Deprecated | Upgrade recommended |

**Supported GCP Resources:**
- VPC Network, Subnet, Firewall
- Compute Instance, Instance Template, Instance Group
- Cloud Storage Bucket
- Cloud SQL Instance
- Google Kubernetes Engine (GKE) Cluster
- Cloud Run Service
- Cloud Functions
- IAM Role, IAM Policy
- Cloud Load Balancing

#### Additional Providers

| Provider | Version | Status | Resource Types |
|----------|---------|--------|---------------|
| Kubernetes | >= 2.0 | Supported | Kubernetes resources via Terraform |
| Helm | >= 2.0 | Supported | Helm chart deployments |
| Vault | >= 3.0 | Supported | HashiCorp Vault secrets |

### Terraform Features

| Feature | Terraform Version | Support Status |
|---------|------------------|----------------|
| Required Providers | >= 0.13 | Fully Supported |
| Variable Validation | >= 0.13 | Fully Supported |
| Sensitive Variables | >= 0.14 | Fully Supported |
| Module Count/For Each | >= 0.13 | Fully Supported |
| Dynamic Blocks | >= 0.12 | Fully Supported |
| Local Values | >= 0.10 | Fully Supported |
| Data Sources | All Versions | Fully Supported |
| Remote State | All Versions | Fully Supported |

## Docker Compatibility

### Docker Engine Requirements

| Component | Version | Status | Notes |
|-----------|---------|--------|-------|
| Docker Engine | >= 20.10 | Fully Supported | Minimum version for BuildKit |
| Docker Engine | >= 23.0 | Recommended | Latest features |
| Docker Engine | 19.03 - 20.09 | Limited Support | Basic features only |
| Docker Engine | < 19.03 | Not Supported | BuildKit unavailable |

### Dockerfile Syntax

| Syntax Version | Docker Version | Status | Features |
|---------------|----------------|--------|----------|
| 1.4+ (BuildKit) | >= 20.10 | Fully Supported | Multi-stage, cache mounts, secrets |
| 1.3 | >= 19.03 | Supported | Multi-stage builds |
| 1.2 | >= 18.09 | Limited | Basic features only |
| < 1.2 | < 18.09 | Not Supported | Upgrade required |

### Docker Compose Versions

| Compose Version | Docker Compose | Status | Notes |
|----------------|----------------|--------|-------|
| 3.8 | >= 1.28.0 | Fully Supported | Latest stable format |
| 3.7 | >= 1.25.0 | Supported | Minor features missing |
| 3.6 | >= 1.22.0 | Limited | Legacy support only |
| 2.x | Legacy | Not Supported | Upgrade to 3.x |

**Compose File Features:**
- Service definitions with build context
- Multi-service orchestration
- Network configuration (bridge, host, overlay)
- Volume mounts (bind, named volumes)
- Environment variable substitution
- Health checks
- Restart policies
- Resource limits (CPU, memory)
- Dependency ordering (depends_on)

### Base Image Compatibility

| Base Image | Tag Pattern | Status | Notes |
|------------|-------------|--------|-------|
| Python | 3.12-slim, 3.12-alpine | Fully Supported | Recommended |
| Python | 3.11-slim, 3.11-alpine | Fully Supported | LTS support |
| Python | 3.10-slim | Supported | Maintenance mode |
| Node.js | 20-slim, 20-alpine | Fully Supported | Latest LTS |
| Node.js | 18-slim, 18-alpine | Fully Supported | LTS support |
| Go | 1.22-alpine | Fully Supported | Latest stable |
| Rust | 1.75-slim | Fully Supported | Latest stable |
| Distroless | python3, static | Fully Supported | Security-focused |
| Ubuntu | 22.04, 24.04 | Fully Supported | LTS releases |
| Alpine | 3.19, 3.18 | Fully Supported | Lightweight option |

### BuildKit Features

| Feature | BuildKit Version | Status |
|---------|-----------------|--------|
| Multi-stage builds | >= 0.8 | Fully Supported |
| Cache mounts | >= 0.8 | Fully Supported |
| Secret mounts | >= 0.8 | Fully Supported |
| SSH mounts | >= 0.8 | Fully Supported |
| Heredoc syntax | >= 0.9 | Fully Supported |

## CI/CD Platform Compatibility

### GitHub Actions

| Component | Version | Status | Notes |
|-----------|---------|--------|-------|
| Workflow Syntax | 2022+ | Fully Supported | Latest stable format |
| Actions Version | v3, v4 | Fully Supported | checkout, setup-*, etc. |
| Actions Version | v2 | Supported | Legacy actions |
| YAML Version | 1.2 | Required | Standard YAML format |

**Supported Features:**
- Workflow triggers (push, pull_request, schedule, workflow_dispatch)
- Multiple jobs with dependencies
- Matrix builds
- Reusable workflows
- Composite actions
- Environment secrets and variables
- Artifact upload/download
- Caching (actions/cache@v3)
- Container services
- Concurrency control
- Environment protection rules
- OIDC authentication

**Supported Actions (Latest Versions):**
- actions/checkout@v4
- actions/setup-python@v5
- actions/setup-node@v4
- actions/setup-go@v5
- actions/cache@v4
- docker/build-push-action@v5
- docker/login-action@v3

### GitLab CI

| Component | Version | Status | Notes |
|-----------|---------|--------|-------|
| GitLab CI Syntax | 15.x - 16.x | Fully Supported | Latest format |
| GitLab Runner | >= 15.0 | Fully Supported | Required for features |
| GitLab Version | 15.x - 16.x | Fully Supported | Self-hosted or SaaS |
| YAML Version | 1.2 | Required | Standard YAML format |

**Supported Features:**
- Stages and jobs
- Pipeline triggers (push, merge_request, schedule, trigger)
- Rules and workflow conditions
- Needs (DAG pipelines)
- Artifacts and dependencies
- Cache configuration
- Services (Docker-in-Docker, databases)
- Variables and secrets
- Include and extends
- Multi-project pipelines
- Parent-child pipelines
- Dynamic pipelines

### Azure DevOps

| Component | Version | Status | Notes |
|-----------|---------|--------|-------|
| Azure Pipelines | 2022+ | Fully Supported | Latest YAML format |
| Azure DevOps Server | 2020-2022 | Supported | Self-hosted option |
| Pipeline Syntax | YAML Schema 2022 | Fully Supported | Standard format |

**Supported Features:**
- Multi-stage pipelines
- Triggers (CI, PR, scheduled)
- Templates and parameters
- Variable groups
- Service connections
- Artifact publishing
- Pipeline caching
- Matrix builds
- Deployment jobs with environments
- Container jobs

**Supported Tasks:**
- Script tasks (Bash, PowerShell)
- Docker tasks (build, push, run)
- Kubernetes manifest deployment
- Azure CLI tasks
- Node/Python/Go setup tasks

### Jenkins

| Component | Version | Status | Notes |
|-----------|---------|--------|-------|
| Jenkins | >= 2.387.x LTS | Fully Supported | Latest LTS |
| Pipeline Plugin | >= 2.6 | Required | Declarative syntax |
| Blue Ocean | Optional | Supported | Modern UI |
| Docker Pipeline | >= 1.26 | Recommended | Docker integration |

**Supported Features:**
- Declarative Pipeline syntax
- Scripted Pipeline (limited)
- Multi-branch pipelines
- Shared libraries
- Agent specifications
- Environment variables
- Credentials binding
- Post-build actions
- Parallel stages
- Stage conditionals
- Input steps

### CircleCI

| Component | Version | Status | Notes |
|-----------|---------|--------|-------|
| Config Version | 2.1 | Fully Supported | Latest format |
| Orbs | Latest | Supported | Reusable packages |

**Supported Features:**
- Jobs and workflows
- Executors (docker, machine, macos)
- Caching
- Workspaces
- Artifacts
- Test splitting
- Resource classes
- Matrix jobs

## Update Policy

### Version Update Cadence

| Component | Update Frequency | Review Cycle |
|-----------|-----------------|--------------|
| Kubernetes APIs | Quarterly | After each K8s release |
| Terraform Providers | Quarterly | After major provider releases |
| Docker Base Images | Monthly | Security patches, version updates |
| CI/CD Platforms | Bi-monthly | After platform updates |

### Deprecation Process

1. **Announcement**: Deprecation announced in release notes (minimum 6 months notice)
2. **Warning Period**: Warnings added to generated output (3 months)
3. **Deprecation**: Feature marked deprecated, still functional (3 months minimum)
4. **Removal**: Feature removed in next major version

### Adding New Platform Support

New platforms/versions are added when:
1. Platform reaches stable/GA status
2. Platform has >5% market adoption or enterprise demand
3. Comprehensive testing can be performed
4. Documentation is available

### Testing Requirements

#### Unit Testing
- All generators have unit tests with >90% coverage
- Model validation tests for all configuration objects
- Edge case and error handling tests

#### Integration Testing
- Generated configurations validated against target platforms
- Syntax validation using platform-specific tools
- Best practice linters run on generated output

#### Compatibility Testing Matrix

| Platform | Test Frequency | Test Scope |
|----------|---------------|------------|
| Kubernetes | Per commit | Latest 3 minor versions |
| Terraform | Weekly | AWS, Azure, GCP providers |
| Docker | Per commit | Build and run tests |
| CI/CD | Weekly | Syntax validation, dry-run |

#### Validation Tools Used

| Platform | Tool | Version |
|----------|------|---------|
| Kubernetes | kubectl --dry-run | Latest |
| Kubernetes | kubeval | v0.16+ |
| Kubernetes | kube-score | v1.17+ |
| Terraform | terraform validate | Latest |
| Terraform | tflint | v0.50+ |
| Terraform | checkov | Latest |
| Docker | docker build | Latest |
| Docker | hadolint | v2.12+ |
| Docker | trivy | Latest |
| YAML | yamllint | v1.33+ |

## Version Support Matrix Summary

### Current Support Status

| Platform | Minimum Version | Recommended Version | Latest Tested | EOL Warning |
|----------|----------------|--------------------|--------------|-----------|
| Kubernetes | 1.25.0 | 1.27.x - 1.29.x | 1.29.x | 1.25 (June 2026) |
| Terraform | 1.0.0 | 1.5.x - 1.7.x | 1.7.x | < 1.0 |
| AWS Provider | 4.0.0 | 5.0.x+ | 5.35.x | < 4.0 |
| Azure Provider | 3.0.0 | 3.85.x+ | 3.92.x | < 3.0 |
| GCP Provider | 4.0.0 | 5.0.x+ | 5.12.x | < 4.0 |
| Docker Engine | 20.10 | 23.0.x+ | 25.x | < 20.10 |
| Docker Compose | 3.8 | 3.8 | 3.8 | < 3.6 |
| GitHub Actions | 2022 | Latest | 2024 | N/A |
| GitLab CI | 15.0 | 15.x - 16.x | 16.8 | < 15.0 |
| Azure DevOps | 2020 | 2022+ | 2022 | < 2020 |
| Jenkins | 2.387.x LTS | 2.440.x LTS | 2.440.x | < 2.387 |

## Breaking Changes Policy

### Major Version Changes
Breaking changes are only introduced in major version bumps:
- Changes to generated output format
- Removal of deprecated features
- Changes to minimum supported versions
- API signature changes

### Migration Guides
Migration guides provided for:
- Major version upgrades
- Platform version changes with breaking changes
- Deprecated feature removal

## Security Updates

### Security Patch Policy
- **Critical**: Released within 48 hours
- **High**: Released within 1 week
- **Medium**: Released within 1 month
- **Low**: Included in next regular release

### Vulnerability Scanning
- Base images scanned daily for CVEs
- Dependencies checked with Dependabot
- Generated configurations scanned with security linters

## Feedback and Support

### Reporting Compatibility Issues
Report compatibility issues via:
1. GitHub Issues with `compatibility` label
2. Include platform version information
3. Provide generated configuration sample
4. Include error messages or validation failures

### Version Support Requests
Request support for new versions via:
1. GitHub Issues with `version-support` label
2. Include business justification
3. Provide platform documentation links
4. Indicate timeline requirements

## Appendix: Version Detection

Volundr can detect platform versions when possible:
- Kubernetes: Uses kubectl version detection
- Terraform: Reads from `terraform version`
- Docker: Reads from `docker version`
- CI/CD: Platform-specific environment variables

## Document Version

- **Version**: 1.0.0
- **Last Updated**: 2026-02-02
- **Next Review**: 2026-05-02 (Quarterly)
- **Owner**: Asgard Contributors
