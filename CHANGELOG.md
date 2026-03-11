# Changelog

All notable changes to the Asgard project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- LICENSE file (MIT)
- CHANGELOG.md following Keep a Changelog format
- CONTRIBUTING.md with development guidelines
- MANIFEST.in for source distribution packaging

## [1.0.0] - 2026-02-14

### Added
- Unified Asgard CLI (`asgard`) with subcommands for all modules
- Individual module CLIs (backwards compatible): `heimdall`, `freya`, `forseti`, `verdandi`, `volundr`
- Heimdall: Code quality control and static analysis
  - Complexity analysis, duplication detection, code smell detection
  - Security vulnerability scanning
  - Performance profiling and dependency analysis
  - Architecture validation and layer analysis
  - Quality scanners: env fallback, lazy import, library usage
- Freya: Visual and UI testing
  - Site crawling and link validation
  - Image optimization scanning
  - HTML reporting and integration models
  - SEO analysis including robots.txt
- Forseti: API and schema specification
  - OpenAPI/Swagger validation
  - GraphQL schema validation
  - Database schema analysis
  - Protobuf and Avro support
  - AsyncAPI support
  - Contract compatibility checking and breaking change detection
  - Code generation and mock server
- Verdandi: Runtime performance metrics
  - Web vitals calculation (LCP, FID, CLS)
  - APM, anomaly detection, and trend analysis
  - Cache, database, network, and system metrics
  - SLO tracking and tracing
- Volundr: Infrastructure generation
  - Kubernetes manifests
  - Terraform modules
  - Dockerfiles and docker-compose
  - CI/CD pipeline generation
- Python API for direct import of services
- Optional dependency groups: `[heimdall]`, `[freya]`, `[forseti]`, `[volundr]`, `[all]`
- Comprehensive test suite in Asgard_Test with L0 and L1 test levels
- pyproject.toml-based packaging (PEP 621)

### Changed
- Replaced 15 third-party dependencies with custom implementations to reduce dependency footprint

### Removed
- Legacy setup.py build configuration (replaced by pyproject.toml)

[Unreleased]: https://github.com/JakeDruett/asgard/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/JakeDruett/asgard/releases/tag/v1.0.0
