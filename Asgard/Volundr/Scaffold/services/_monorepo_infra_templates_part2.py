"""Monorepo infrastructure templates - CI/CD and project metadata."""

from typing import List

from Asgard.Volundr.CICD.services.action_pins import pinned
from Asgard.Volundr.Scaffold.models.scaffold_models import ProjectConfig


def github_actions_cd(config: ProjectConfig) -> str:
    return f'''name: CD

on:
  push:
    branches: [main]
    tags: ["v*"]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{{{ github.ref == 'refs/heads/main' && 'development' || 'production' }}}}
    steps:
      - uses: {pinned("actions/checkout@v4")}

      - name: Deploy to Kubernetes
        run: |
          kubectl apply -k infrastructure/kubernetes/overlays/$ENVIRONMENT
        env:
          ENVIRONMENT: ${{{{ github.ref == 'refs/heads/main' && 'development' || 'production' }}}}
'''


def gitlab_ci(config: ProjectConfig) -> str:
    return f'''stages:
  - lint
  - test
  - build
  - deploy

variables:
  DOCKER_DRIVER: overlay2

lint:
  stage: lint
  script:
    - make lint

test:
  stage: test
  parallel:
    matrix:
      - SERVICE: [{", ".join([s.name for s in config.services])}]
  script:
    - cd services/$SERVICE && make test

build:
  stage: build
  parallel:
    matrix:
      - SERVICE: [{", ".join([s.name for s in config.services])}]
  script:
    - docker build -t $SERVICE:$CI_COMMIT_SHA services/$SERVICE

deploy-dev:
  stage: deploy
  environment: development
  only:
    - main
  script:
    - kubectl apply -k infrastructure/kubernetes/overlays/development

deploy-prod:
  stage: deploy
  environment: production
  only:
    - tags
  script:
    - kubectl apply -k infrastructure/kubernetes/overlays/production
'''


def codeowners(config: ProjectConfig) -> str:
    return f'''# Default owners
* @{config.author or "team"}

# Infrastructure
/infrastructure/ @{config.author or "platform-team"}

# Services
/services/ @{config.author or "backend-team"}
'''


def pr_template() -> str:
    return '''## Description

<!-- Describe your changes -->

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Checklist

- [ ] Tests pass locally
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated (if applicable)
'''


def get_next_steps(config: ProjectConfig) -> List[str]:
    steps: List[str] = [
        f"cd {config.name}",
        "git init",
        "make dev",
        "Open http://localhost:<port> for each service",
    ]
    if config.include_pre_commit:
        steps.insert(2, "pre-commit install")
    return steps
