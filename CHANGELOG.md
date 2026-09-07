# Changelog

All notable changes to the Asgard project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Rust quality analysis, wired into the CLI for the first time: `quality rust` (pattern-based,
  the existing regex analyser -- unsafe blocks, unwrap/expect, transmute, raw pointer deref,
  command injection, hardcoded credentials, integer overflow, path traversal)
- Toolchain-orchestrated analysis: a new language-agnostic `ToolFinding`/`ToolReport` model
  (`Asgard.Bragi.Quality.languages.common`) for analysers that shell out to an ecosystem's own
  tools instead of reimplementing analysis, so ratings/gates/issue tracking work identically
  regardless of language or tool
  - `quality rust-clippy`: cargo clippy lint diagnostics (requires cargo + clippy)
  - `quality rust-audit`: Cargo.lock vulnerability scan against the RustSec advisory database
    (requires the separate `cargo-audit` plugin)
  - `quality node-lint`: the project's own configured ESLint (flat config or legacy `.eslintrc.*`)
  - `quality node-audit`: package.json/package-lock.json vulnerability scan via `npm audit`
  - `quality node-typecheck`: TypeScript compiler diagnostics via `tsc --noEmit`
  - Every toolchain command reports a missing tool as a clear, actionable install message and a
    non-zero exit code rather than crashing; a project missing the tool's own configuration
    (no ESLint config, no tsconfig.json, no Cargo.toml/Cargo.lock) is reported as a skipped,
    non-fatal condition
- L0 unit tests for the new toolchain-orchestration models, subprocess/tool-discovery helpers,
  all five toolchain analysers, and their CLI handlers, plus real-tool integration tests (skipped
  cleanly when the underlying tool is not installed) against new checked-in fixture projects
  (`Asgard_Test/fixtures/rust_toolchain_demo`, `Asgard_Test/fixtures/node_toolchain_demo`)
- Go toolchain analysis, following the same shape as the Rust/Node work above: `quality go-vet`,
  `quality go-build`, `quality go-fmt`, `quality go-test`, `quality go-vuln` (via `govulncheck`),
  plus a fixture project and unit/integration tests
- `.github/workflows/reusable-quality-gate.yml`: a `workflow_call` job any repo in the suite can
  call to run the Rust/Node/Go toolchain analysers in its own CI without vendoring asguardian or
  publishing it to PyPI first. See `_Docs/CI/Consumer-Wiring.md` for the exact per-repo snippet;
  as of this entry no consumer repo has actually added the call yet.

### Fixed
- `quality rust-audit`: an advisory whose `cvss` field is a real, present vector this parser does
  not understand (CVSS v4.0 -- confirmed against a real `rustsec/advisory-db` checkout, where
  62/423 CVSS-bearing advisories are already v4) previously fell through to the same default
  severity used for an advisory with no CVSS data at all, silently downgrading a real, unscored
  vulnerability. It now fails safe to `error` instead of guessing `warning`.

## [1.2.0] - 2026-03-12

### Changed
- License changed from MIT to Polyform Noncommercial 1.0.0 (free for personal and non-commercial use; commercial use requires a separate license)

## [1.1.0] - 2026-03-12

### Added
- Ratings system: A-E letter ratings for Maintainability, Reliability, and Security dimensions
- Quality Gates: configurable pass/fail conditions on metrics with built-in "Asgard Way" gate
- Security Hotspots: detection of security-sensitive code requiring manual review (eval, pickle, SSRF, weak crypto, etc.)
- OWASP Top 10 and CWE Top 25 compliance reporting with letter grades per category
- Comment density and public API documentation coverage metrics
- Naming convention enforcement (PEP 8 snake_case, PascalCase, UPPER_CASE)
- New Code Period: formal tracking of new vs overall code metrics
- Quality Profiles: named rule sets with built-in "Asgard Way - Python" and "Asgard Way - Strict" profiles
- Metrics History: SQLite-backed analysis snapshots with trend tracking (improving/stable/degrading)
- PR Decoration: inline GitHub and GitLab pull request annotations
- Taint Analysis: AST-based source-to-sink tracking for injection vulnerability detection
- Insecure deserialization detection (pickle, marshal, unsafe yaml.load)
- SSRF detection (user-controlled URLs in HTTP requests)
- Bug Detection: null/None dereference and unreachable code detection
- JavaScript quality rules: no-eval, no-debugger, no-var, eqeqeq, no-console, complexity (12 rules)
- TypeScript quality rules: no-explicit-any, no-any-cast, no-non-null-assertion, prefer-interface (extends JS rules)
- Shell/Bash analysis: eval injection, curl --insecure, hardcoded secrets, missing set -e/u (12 rules)
- Issue Lifecycle Tracker: persistent SQLite issue tracking with Open/Confirmed/Resolved/False Positive states, git blame attribution, and cross-scan deduplication
- SBOM generation in SPDX 2.3 and CycloneDX 1.4 formats
- Auto CodeFix: template-based fix suggestions for 12 common rule violations
- MCP Server: JSON-RPC server exposing analysis results to AI agents (Claude Code, Cursor, Windsurf)
- Web Dashboard: standalone Python HTTP dashboard (`heimdall dashboard` / `asgard-dashboard`) with overview, issues browser, and history trend pages
- CLI commands: `ratings`, `gate`, `profiles`, `history`, `new-code`, `issues`, `sbom`, `codefix`, `mcp-server`, `dashboard`
- CLI subcommands: `quality documentation`, `quality naming`, `quality bugs`, `quality javascript`, `quality typescript`, `quality shell`, `security hotspots`, `security compliance`, `security taint`
- `asgard-mcp` and `asgard-dashboard` script entry points
- L0 unit tests for all new modules (716 tests)

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

[Unreleased]: https://github.com/JakeDruett/asgard/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/JakeDruett/asgard/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/JakeDruett/asgard/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/JakeDruett/asgard/releases/tag/v1.0.0
