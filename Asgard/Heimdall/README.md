# Heimdall - Code Quality Control

Named after the Norse watchman god who guards Bifrost and can see and hear everything across all realms, Heimdall watches over your codebase for quality issues, security vulnerabilities, and performance problems.

## Overview

Heimdall is a comprehensive code quality control package that provides static analysis, security scanning, performance profiling, and architectural validation for Python codebases. Like its namesake who vigilantly guards the bridge between worlds, Heimdall provides watchful protection over code quality.

## Features

- **Quality Analysis**: Code complexity, duplication detection, code smells, technical debt, maintainability index
- **Security Scanning**: Secrets detection, vulnerability scanning, injection pattern detection, cryptographic validation
- **Performance Profiling**: Static analysis for memory patterns, CPU hotspots, database access optimization
- **OOP Metrics**: Class coupling (CBO), inheritance depth (DIT), cohesion (LCOM), complexity (WMC, RFC)
- **Dependency Analysis**: Circular dependency detection, dependency graphs, modularity scoring
- **Architecture Validation**: SOLID principles, layer compliance, design pattern detection
- **Coverage Analysis**: Test coverage gaps, missing test suggestions, untested class detection

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
# Run comprehensive quality audit
python -m Heimdall audit ./src

# Quality analysis
python -m Heimdall quality analyze ./src
python -m Heimdall quality complexity ./src --threshold 10
python -m Heimdall quality duplication ./src --min-lines 6

# Security scanning
python -m Heimdall security scan ./src
python -m Heimdall security secrets ./src
python -m Heimdall security dependencies ./src

# Performance analysis
python -m Heimdall performance scan ./src
python -m Heimdall performance memory ./src
python -m Heimdall performance database ./src

# OOP metrics
python -m Heimdall oop analyze ./src
python -m Heimdall oop coupling ./src
python -m Heimdall oop cohesion ./src

# Dependency analysis
python -m Heimdall dependencies analyze ./src
python -m Heimdall dependencies cycles ./src

# Architecture validation
python -m Heimdall architecture analyze ./src
python -m Heimdall architecture solid ./src

# Coverage analysis
python -m Heimdall coverage analyze ./src
python -m Heimdall coverage gaps ./src
```

### Python API Usage

```python
from Asgard.Heimdall import (
    FileAnalyzer,
    AnalysisConfig,
    StaticSecurityService,
    OOPAnalyzer,
    DependencyAnalyzer,
    ArchitectureAnalyzer,
)

# Quality Analysis
config = AnalysisConfig(threshold=300, min_duplication_lines=6)
analyzer = FileAnalyzer(config)
result = analyzer.analyze("./src")
print(f"Files analyzed: {len(result.files)}")
print(f"Total issues: {result.total_issues}")

# Security Scanning
security_service = StaticSecurityService()
security_report = security_service.scan("./src")
print(f"Security Score: {security_report.security_score}/100")
print(f"Vulnerabilities: {security_report.total_vulnerabilities}")

# OOP Metrics
oop_analyzer = OOPAnalyzer()
oop_report = oop_analyzer.analyze("./src")
for cls in oop_report.classes:
    print(f"{cls.name}: CBO={cls.cbo}, LCOM={cls.lcom}")

# Dependency Analysis
dep_analyzer = DependencyAnalyzer()
dep_report = dep_analyzer.analyze("./src")
if dep_report.has_cycles:
    print(f"Found {dep_report.total_cycles} circular dependencies!")

# Architecture Validation
arch_analyzer = ArchitectureAnalyzer()
arch_report = arch_analyzer.analyze("./src")
print(f"SOLID Violations: {arch_report.total_violations}")
```

## Submodules

### Quality Module

Static code quality analysis including complexity, duplication, and maintainability.

**Services:**
- `ComplexityAnalyzer`: Cyclomatic complexity, cognitive complexity
- `DuplicationDetector`: Duplicate code detection
- `CodeSmellDetector`: Long methods, god classes, feature envy
- `TechnicalDebtAnalyzer`: Technical debt estimation
- `MaintainabilityAnalyzer`: Maintainability index calculation
- `EnvFallbackScanner`: Detects environment variable fallback values
- `LazyImportScanner`: Detects imports not at module level

### Security Module

Comprehensive security vulnerability scanning and validation.

**Services:**
- `SecretsDetectionService`: Hardcoded secrets, API keys, passwords
- `DependencyVulnerabilityService`: Known CVE scanning
- `InjectionDetectionService`: SQL injection, command injection patterns
- `CryptographicValidationService`: Weak crypto, insecure hashing
- `AuthAnalyzer`: Authentication implementation analysis
- `AccessAnalyzer`: Access control validation
- `HeadersAnalyzer`: Security headers validation
- `TLSAnalyzer`: TLS/SSL configuration analysis
- `ContainerAnalyzer`: Docker security scanning
- `InfraAnalyzer`: Infrastructure security validation

### Performance Module

Static performance analysis for identifying potential bottlenecks.

**Services:**
- `StaticPerformanceService`: Overall performance scoring
- `MemoryProfilerService`: Memory leak patterns, allocation issues
- `CPUProfilerService`: CPU-intensive patterns
- `DatabaseAnalyzerService`: N+1 queries, missing indexes
- `CacheAnalyzerService`: Caching opportunities

### OOP Module

Object-oriented programming metrics based on CK metrics suite.

**Services:**
- `OOPAnalyzer`: Comprehensive OOP metrics
- `CouplingAnalyzer`: Coupling Between Objects (CBO)
- `CohesionAnalyzer`: Lack of Cohesion of Methods (LCOM)
- `InheritanceAnalyzer`: Depth of Inheritance Tree (DIT), Number of Children (NOC)
- `RFCAnalyzer`: Response For Class (RFC)

### Dependencies Module

Dependency analysis and graph building.

**Services:**
- `DependencyAnalyzer`: Comprehensive dependency analysis
- `CycleDetector`: Circular dependency detection
- `GraphBuilder`: Dependency graph construction
- `ImportAnalyzer`: Import statement analysis
- `ModularityAnalyzer`: Modularity scoring
- `LicenseChecker`: License compliance
- `RequirementsChecker`: Requirements.txt validation

### Architecture Module

Architecture pattern detection and SOLID principle validation.

**Services:**
- `ArchitectureAnalyzer`: Overall architecture analysis
- `SOLIDValidator`: SOLID principles validation
- `LayerAnalyzer`: Layered architecture compliance
- `PatternDetector`: Design pattern detection (Factory, Singleton, Strategy, etc.)

### Coverage Module

Test coverage gap analysis and test suggestions.

**Services:**
- `CoverageAnalyzer`: Test coverage gap detection
- `GapAnalyzer`: Missing test identification
- `SuggestionEngine`: Test suggestion generation
- `MethodExtractor`: Method extraction for coverage

## CLI Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `audit` | Run all quality checks | `python -m Heimdall audit ./src` |
| `quality analyze` | Run all quality checks | `python -m Heimdall quality analyze ./src` |
| `quality complexity` | Analyze code complexity | `python -m Heimdall quality complexity ./src --threshold 10` |
| `quality duplication` | Detect code duplication | `python -m Heimdall quality duplication ./src --min-lines 6` |
| `quality smells` | Detect code smells | `python -m Heimdall quality smells ./src` |
| `quality debt` | Analyze technical debt | `python -m Heimdall quality debt ./src` |
| `quality maintainability` | Calculate maintainability | `python -m Heimdall quality maintainability ./src` |
| `quality env-fallback` | Detect env var fallbacks | `python -m Heimdall quality env-fallback ./src` |
| `quality lazy-imports` | Detect lazy imports | `python -m Heimdall quality lazy-imports ./src` |
| `security scan` | Run all security checks | `python -m Heimdall security scan ./src` |
| `security secrets` | Detect hardcoded secrets | `python -m Heimdall security secrets ./src` |
| `security dependencies` | Scan vulnerable dependencies | `python -m Heimdall security dependencies ./src` |
| `security vulnerabilities` | Detect injection vulnerabilities | `python -m Heimdall security vulnerabilities ./src` |
| `security crypto` | Validate cryptography | `python -m Heimdall security crypto ./src` |
| `performance scan` | Run all performance checks | `python -m Heimdall performance scan ./src` |
| `performance memory` | Analyze memory patterns | `python -m Heimdall performance memory ./src` |
| `performance cpu` | Analyze CPU patterns | `python -m Heimdall performance cpu ./src` |
| `performance database` | Analyze database access | `python -m Heimdall performance database ./src` |
| `oop analyze` | Run all OOP metrics | `python -m Heimdall oop analyze ./src` |
| `oop coupling` | Analyze class coupling | `python -m Heimdall oop coupling ./src` |
| `oop cohesion` | Analyze class cohesion | `python -m Heimdall oop cohesion ./src` |
| `oop inheritance` | Analyze inheritance | `python -m Heimdall oop inheritance ./src` |
| `dependencies analyze` | Full dependency analysis | `python -m Heimdall dependencies analyze ./src` |
| `dependencies cycles` | Detect circular dependencies | `python -m Heimdall dependencies cycles ./src` |
| `dependencies graph` | Build dependency graph | `python -m Heimdall dependencies graph ./src` |
| `architecture analyze` | Full architecture analysis | `python -m Heimdall architecture analyze ./src` |
| `architecture solid` | Validate SOLID principles | `python -m Heimdall architecture solid ./src` |
| `architecture layers` | Check layer compliance | `python -m Heimdall architecture layers ./src` |
| `architecture patterns` | Detect design patterns | `python -m Heimdall architecture patterns ./src` |
| `coverage analyze` | Full coverage analysis | `python -m Heimdall coverage analyze ./src` |
| `coverage gaps` | Find coverage gaps | `python -m Heimdall coverage gaps ./src` |
| `coverage suggestions` | Generate test suggestions | `python -m Heimdall coverage suggestions ./src` |
| `syntax check` | Run syntax/linting checks | `python -m Heimdall syntax check ./src` |
| `requirements check` | Check requirements.txt | `python -m Heimdall requirements check ./src` |
| `licenses check` | Check license compliance | `python -m Heimdall licenses check ./src` |

## Configuration Options

Most commands support the following options:

- `--path`: Path to analyze (default: current directory)
- `--format`: Output format: `text`, `json`, `markdown`, `html`
- `--output`: Output file path
- `--verbose`: Verbose output
- `--threshold`: Numeric threshold for metrics
- `--exclude`: Patterns to exclude
- `--include-tests`: Include test files in analysis

## Troubleshooting

### Common Issues

**Issue: "No Python files found"**
- Ensure the path contains .py files
- Check exclude patterns aren't too broad
- Verify path is correct

**Issue: "Permission denied"**
- Ensure you have read permissions on all files
- Check file ownership and permissions

**Issue: "Out of memory"**
- Analyze smaller directories
- Exclude large generated files
- Increase system memory

**Issue: "Circular import during analysis"**
- This is expected for some codebases
- Use `--exclude` to skip problematic modules
- Analysis will continue despite circular imports

### Performance Tips

- Exclude node_modules, venv, and other large directories
- Use specific commands instead of full audit for faster results
- Run analysis on incremental changes in CI/CD
- Cache results for unchanged files

## Integration with CI/CD

```yaml
# GitHub Actions example
- name: Run Heimdall Quality Check
  run: |
    python -m Heimdall audit ./src --format json --output heimdall-report.json

- name: Check for critical issues
  run: |
    python -m Heimdall security scan ./src --severity critical
```

## Version

Version: 1.1.0

## Author

Asgard Contributors
