# Asguardian

Named after the realm of the Norse gods, **Asguardian** is a comprehensive suite of development quality assurance tools for Python projects. It covers static analysis, security scanning, API validation, performance metrics, infrastructure generation, and more — all from a single package.

## Installation

```bash
pip install asguardian
```

Python 3.11 or higher is required.

## Quick Start

### Static Analysis and Code Quality

```bash
# Analyse a project directory
asgard heimdall analyze ./src

# Get letter ratings (A–E) for Maintainability, Reliability, and Security
asgard heimdall ratings ./src

# Check quality gate (pass/fail against thresholds)
asgard heimdall gate ./src

# Check for security vulnerabilities
asgard heimdall security scan ./src

# View tracked issues with lifecycle states
asgard heimdall issues ./src
```

### Security Scanning

```bash
# Detect security hotspots requiring manual review
asgard heimdall security hotspots ./src

# OWASP Top 10 and CWE Top 25 compliance report
asgard heimdall security compliance ./src

# Taint analysis: source-to-sink injection tracking
asgard heimdall security taint ./src
```

### API and Schema Validation

```bash
# Validate an OpenAPI specification
asgard forseti validate openapi.yaml

# Check for breaking changes between two specs
asgard forseti breaking-changes old.yaml new.yaml

# Validate a GraphQL schema
asgard forseti validate schema.graphql
```

### Web and UI Testing

```bash
# Crawl a site and check for broken links
asgard freya crawl http://localhost:3000

# Run image optimisation scan
asgard freya images http://localhost:3000
```

### Performance Metrics

```bash
# Calculate web vitals from a metrics file
asgard verdandi report ./metrics.json

# Check SLO compliance
asgard verdandi slo ./metrics.json
```

### Infrastructure Generation

```bash
# Generate Kubernetes manifests
asgard volundr generate kubernetes --name myapp --image myapp:latest

# Generate a Dockerfile
asgard volundr generate dockerfile --lang python

# Generate a GitHub Actions CI/CD pipeline
asgard volundr generate ci github
```

## Web Dashboard

Asguardian includes a standalone web dashboard that displays your project's quality metrics, issues, and history in a browser.

### Launch the dashboard

```bash
# Start on the default port (8080)
asgard-dashboard --path ./src

# Specify a custom port
asgard-dashboard --path ./src --port 9090
```

Then open `http://localhost:8080` in your browser.

The dashboard provides three pages:

- **Overview** — quality gate status, A–E ratings (Maintainability, Reliability, Security), and issue summary
- **Issues** — filterable table of all tracked issues with severity and lifecycle status
- **History** — trend view of analysis snapshots over time

The `heimdall dashboard` command is an alias for `asgard-dashboard`.

## MCP Server (AI Agent Integration)

Asguardian includes a JSON-RPC MCP server that exposes analysis results to AI coding assistants such as Claude Code, Cursor, and Windsurf.

### Start the MCP server

```bash
asgard-mcp --path ./src
```

### Configure Claude Code

Add the following to your `.claude/mcp.json` (or Claude Code settings):

```json
{
  "mcpServers": {
    "asguardian": {
      "command": "asgard-mcp",
      "args": ["--path", "/path/to/your/project"]
    }
  }
}
```

Once configured, your AI assistant can query quality ratings, issues, hotspots, and history directly.

## Quality Profiles

Asguardian ships with built-in quality profiles that group rules into named sets.

```bash
# List available profiles
asgard heimdall profiles list

# Run analysis using a specific profile
asgard heimdall analyze ./src --profile "Asgard Way - Strict"
```

Built-in profiles:

| Profile | Description |
|---|---|
| Asgard Way - Python | Balanced rule set for Python projects |
| Asgard Way - Strict | Stricter thresholds for production codebases |

## Quality Gates

```bash
# Evaluate the built-in "Asgard Way" gate
asgard heimdall gate ./src

# Specify a custom gate configuration
asgard heimdall gate ./src --gate my-gate.yaml
```

A gate returns `PASSED` or `FAILED` with a per-condition breakdown. Exit code is `0` for pass and `1` for failure, making it suitable for CI/CD pipelines.

## New Code Period

Track metrics specifically for code changed since a baseline commit or date.

```bash
# Metrics for code changed since a git tag
asgard heimdall new-code ./src --since v1.0.0

# Metrics for code changed in the last 30 days
asgard heimdall new-code ./src --days 30
```

## SBOM Generation

Generate a Software Bill of Materials in industry-standard formats.

```bash
# SPDX 2.3 format
asgard heimdall sbom ./src --format spdx

# CycloneDX 1.4 format
asgard heimdall sbom ./src --format cyclonedx
```

## Auto CodeFix

Get template-based fix suggestions for common rule violations.

```bash
asgard heimdall codefix ./src
```

## Language Support

| Language | Rules |
|---|---|
| Python | Complexity, duplication, smells, security, naming (PEP 8), documentation, taint analysis |
| JavaScript | no-eval, no-debugger, no-var, eqeqeq, no-console, complexity (12 rules) |
| TypeScript | All JS rules + no-explicit-any, no-any-cast, no-non-null-assertion, prefer-interface |
| Shell/Bash | eval injection, curl --insecure, hardcoded secrets, missing set -e/u (12 rules) |
| Rust | unsafe blocks, unwrap/expect, transmute, raw pointer deref, command injection, hardcoded credentials (8 pattern rules) |

Rust and Node also have toolchain-orchestrating analysers that run the ecosystem's own tools
instead of pattern rules -- see [Toolchain-Orchestrated Analysis](#toolchain-orchestrated-analysis)
below.

## Toolchain-Orchestrated Analysis

For Rust and Node, Heimdall orchestrates each ecosystem's own mature tools rather than
reimplementing their analysis in Python: `cargo clippy`, `cargo-audit`, ESLint, `npm audit`, and
`tsc`. Findings are normalised into the same rating/gate/issue-tracking model used everywhere
else in Heimdall, regardless of which tool produced them.

```bash
# Rust: cargo clippy lint diagnostics (requires cargo + clippy)
asgard heimdall quality rust-clippy ./my-crate

# Rust: Cargo.lock vulnerability scan against the RustSec advisory database
# (requires the separate cargo-audit plugin: cargo install cargo-audit)
asgard heimdall quality rust-audit ./my-crate

# Node: the project's own configured ESLint (requires an ESLint config)
asgard heimdall quality node-lint ./frontend

# Node: package.json/package-lock.json vulnerability scan via npm audit
asgard heimdall quality node-audit ./frontend

# Node: TypeScript compiler diagnostics (requires tsconfig.json)
asgard heimdall quality node-typecheck ./frontend
```

Each of these requires the underlying tool to be installed. `rust-clippy`, `node-lint`, and
`node-typecheck` require their tool (cargo, eslint, tsc); when it is missing, the command prints a
clear, actionable message (what to install and how) and exits non-zero -- it never crashes with a
raw traceback. `rust-audit`'s `cargo-audit` and `node-audit`'s `npm` (bundled with Node) are
treated as optional: when `cargo-audit` specifically is not installed, the command instead exits
0 with an actionable note, so a missing optional scanner does not fail a pipeline that has not
opted into it. A project missing the tool's own configuration (no ESLint config, no
tsconfig.json, no Cargo.toml/Cargo.lock under the scanned path) is reported the same way: a
skipped, non-fatal note and exit 0. In every case, a tool that WAS found and invoked but crashed,
timed out, or produced output the analyser could not parse is a distinct, always-non-zero outcome
even if it happens to find zero issues -- that failure is never presented as a clean scan.

**Security note: these commands execute the scanned project's own toolchain.** Unlike Heimdall's
Python type-check orchestration (which runs mypy/Pyright from an isolated, empty working
directory with Asgard-owned config so a hostile tree's `pylintrc`/`mypy.ini` cannot run arbitrary
init-hooks), `cargo clippy`, `cargo-audit`, ESLint, and `tsc` are all invoked with the scanned
project directory as their working directory, because each needs its own `Cargo.toml`,
`eslint.config.*`/`.eslintrc.*`, or `tsconfig.json` to run at all. That means running any of these
five commands against an untrusted or unreviewed tree can execute that tree's own build scripts
(`build.rs`, package install/postinstall scripts under `npm audit`'s dependency resolution) and
plugin/loader configuration (a custom ESLint plugin, a `tsconfig.json` `extends` chain, a Cargo
build script) with the same privileges as the `asgard` process itself. Only run these commands
against code you already trust, the same way you would before running `cargo build`, `npm
install`, or `tsc` directly in that tree.

## Python API

All modules can be used directly in Python code.

```python
from Asgard.Heimdall.Ratings.services.ratings_calculator import RatingsCalculator
from Asgard.Heimdall.QualityGate.services.quality_gate_evaluator import QualityGateEvaluator
from Asgard.Heimdall.Security.services.hotspot_detector import HotspotDetector
from Asgard.Heimdall.Security.services.taint_analyzer import TaintAnalyzer
from Asgard.Heimdall.Issues.services.issue_tracker import IssueTracker
from Asgard.Reporting.services.history_store import HistoryStore
from Asgard.Dashboard.services.data_collector import DataCollector
from Asgard.Forseti.OpenAPI.services import SpecValidatorService
from Asgard.Verdandi.Web.services import VitalsCalculator
from Asgard.Volundr.Kubernetes.services import ManifestGenerator
```

## CLI Reference

### Unified CLI (`asgard`)

```
asgard heimdall analyze <path>
asgard heimdall ratings <path>
asgard heimdall gate <path>
asgard heimdall profiles list
asgard heimdall history <path>
asgard heimdall new-code <path>
asgard heimdall issues <path>
asgard heimdall sbom <path>
asgard heimdall codefix <path>
asgard heimdall mcp-server
asgard heimdall dashboard

asgard heimdall quality documentation <path>
asgard heimdall quality naming <path>
asgard heimdall quality bugs <path>
asgard heimdall quality javascript <path>
asgard heimdall quality typescript <path>
asgard heimdall quality shell <path>
asgard heimdall quality rust <path>
asgard heimdall quality rust-clippy <path>
asgard heimdall quality rust-audit <path>
asgard heimdall quality node-lint <path>
asgard heimdall quality node-audit <path>
asgard heimdall quality node-typecheck <path>

asgard heimdall security hotspots <path>
asgard heimdall security compliance <path>
asgard heimdall security taint <path>

asgard freya crawl <url>
asgard freya images <url>

asgard forseti validate <spec>
asgard forseti breaking-changes <old> <new>

asgard verdandi report <metrics>
asgard verdandi slo <metrics>

asgard volundr generate kubernetes
asgard volundr generate dockerfile
asgard volundr generate ci
```

### Standalone entry points

```
heimdall       Individual Heimdall CLI
freya          Individual Freya CLI
forseti        Individual Forseti CLI
verdandi       Individual Verdandi CLI
volundr        Individual Volundr CLI
asgard-mcp     Start the MCP JSON-RPC server
asgard-dashboard   Start the web dashboard
```

## Project Structure

```
Asgard/
├── Asgard/
│   ├── cli.py
│   ├── Heimdall/           # Static analysis, security, quality
│   ├── Freya/              # Visual and UI testing
│   ├── Forseti/            # API and schema validation
│   ├── Verdandi/           # Runtime performance metrics
│   ├── Volundr/            # Infrastructure generation
│   ├── Reporting/          # History store, PR decoration
│   ├── MCP/                # MCP JSON-RPC server
│   └── Dashboard/          # Web dashboard
├── Asgard_Test/            # Test suite (716 tests)
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

## License

Proprietary. All rights reserved. Commercial use requires a separate, written licensing agreement with the owner. See [LICENSE](LICENSE) for details.
