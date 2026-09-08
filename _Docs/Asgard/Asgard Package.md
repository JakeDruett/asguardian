# Asgard Package

[[Asgard|Back to Asgard]] | [[GAIA Index|Back to GAIA Documentation]]

---
## Package Structure

```
Asgard/
  Asgard/
    cli.py                 # Main CLI entry point
    common/                # Shared utilities (baseline, parallel, output, progress)
    Forseti/               # API and schema validation
      OpenAPI/             # OpenAPI specification validation
      Contracts/           # Contract testing
      JSONSchema/          # JSON Schema inference and validation
      AsyncAPI/            # AsyncAPI specification support
      Avro/                # Avro schema validation and compatibility
    Freya/                 # Web and UI testing
      Accessibility/       # Accessibility scanning
      Visual/              # Visual regression testing
      Responsive/          # Responsive design checks
      Integration/         # Integration with CI/CD
    Heimdall/              # Static analysis and code quality
      Quality/             # Code quality metrics
      Security/            # Security vulnerability scanning
      QualityGate/         # Pass/fail quality gates
      Ratings/             # Letter ratings (A-E)
      Issues/              # Issue tracking with lifecycle states
      Profiles/            # Quality profiles
      Reporting/           # Advanced reporting
    Verdandi/              # Performance metrics
      Analysis/            # Metric analysis
      Web/                 # Web vitals
      Database/            # Database performance
      System/              # System metrics
      Network/             # Network metrics
      Cache/               # Cache performance
    Volundr/               # Infrastructure generation
      Kubernetes/          # K8s manifests
      Terraform/           # Terraform configs
      Docker/              # Dockerfiles
      CICD/                # CI/CD pipelines
```

---
## Installation

```bash
pip install asguardian
```

---
## CLI Reference

The main entry point is `asguardian` (or `python -m Asgard.cli`):

```
asguardian <tool> <command> [options]
```

Where `<tool>` is one of: `forseti`, `freya`, `heimdall`, `verdandi`, `volundr`.

See individual tool documentation for detailed CLI references:
- [[Asgard/Forseti/05-CLI-Reference|Forseti CLI Reference]]
- [[Asgard/Heimdall/03-CLI-Reference|Heimdall CLI Reference]]
- [[Asgard/Volundr/06-CLI-Reference|Volundr CLI Reference]]

---
## Security

`Asgard/common/_hmac_env.py` (env-only HMAC keys), `_bind_host.py` (localhost / `--expose`), and package jails/escapers implement the tree-wide hardening in [[Architecture/Security_Hardening]]. `asguardian init-backend` refuses symlink directories and writes with `O_NOFOLLOW`.

## Related Documentation
- [[Asgard]] - Asgard overview
- [[Architecture/Security_Hardening]] - Applied hardening invariants
- [[04 - DevOps]] - CI/CD integration
