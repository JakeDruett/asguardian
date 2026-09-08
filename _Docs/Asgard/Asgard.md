# 93 - Asgard
Quality assurance and development tooling package for GAIA.

[[GAIA Index|Back to GAIA Documentation]]

---
## Overview

Asgard (published as `asguardian` on PyPI) is a comprehensive suite of development quality assurance tools for Python projects. It covers static analysis, security scanning, API validation, performance metrics, infrastructure generation, and web/UI testing -- all from a single CLI.

**Requires**: Python 3.11+

```bash
pip install asguardian
```

---
## Sub-Tools

| Tool | Purpose | CLI Prefix |
|------|---------|------------|
| [[Asgard/Forseti/01-Overview\|Forseti]] | API and schema validation (OpenAPI, GraphQL, JSON Schema, AsyncAPI, Avro) | `asguardian forseti` |
| [[Asgard/Freya/01-Overview\|Freya]] | Web and UI testing (crawling, accessibility, visual regression, responsive checks) | `asguardian freya` |
| [[Asgard/Heimdall/01-Overview\|Heimdall]] | Static analysis, code quality, security scanning, quality gates | `asguardian heimdall` |
| [[Asgard/Verdandi/01-Overview\|Verdandi]] | Performance metrics, SLO compliance, web vitals analysis | `asguardian verdandi` |
| [[Asgard/Volundr/01-Overview\|Volundr]] | Infrastructure generation (Kubernetes, Terraform, Docker, CI/CD) | `asguardian volundr` |

---
## Quick Start

### Static Analysis and Code Quality
```bash
asguardian heimdall quality analyze ./src
asguardian heimdall ratings ./src
asguardian heimdall gate ./src
```

### Security Scanning
```bash
asguardian heimdall security scan ./src
asguardian heimdall security hotspots ./src
asguardian heimdall security compliance ./src
```

### API Validation
```bash
asguardian forseti openapi validate openapi.yaml
asguardian forseti contract check-compat old.yaml new.yaml
```

### Web Testing
```bash
asguardian freya crawl http://localhost:3000
asguardian freya images audit http://localhost:3000
```

### Performance
```bash
asguardian verdandi report generate ./metrics.json
asguardian verdandi slo calculate ./metrics.json
```

### Infrastructure
```bash
asguardian volundr k8s generate --name myapp --image myapp:latest --output-dir ./manifests
asguardian volundr docker dockerfile --name myapp --base python:3.12-slim --output-dir .
```

---
## GAIA Integration

Asgard is used in GAIA's CI/CD pipeline and development workflow:
- `python -m Heimdall quality lazy-imports <path>` detects lazy import violations (a GAIA codebase rule)
- Quality gates run as part of the test coverage matrix via Hercules

---
## Security

Default path is offline, fail-closed, and localhost-bound. Scanners jail paths, skip scan-tree symlinks, mask secrets in reports, and treat empty/unsigned analysis as incomplete — not a perfect score. Full control list: [[Architecture/Security_Hardening]].

## Related Documentation
- [[Asgard Package]] - Detailed package documentation
- [[Architecture/Security_Hardening]] - Applied hardening invariants
- [[04 - DevOps]] - CI/CD and deployment
- [[97-Standards]] - Code quality standards
