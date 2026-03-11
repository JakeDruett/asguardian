# Asgard - Universal Development Tools Suite

Named after the realm of the Norse gods, Asgard is a comprehensive suite of development and quality assurance tools. Like the mythical realm that houses the great halls of the Aesir, Asgard houses the tools that watch over and forge your codebase.

## Subpackages

### Heimdall - Code Quality Control
*Named after the Norse watchman god who guards Bifrost*

Static code analysis and quality control:
- Code complexity analysis
- Duplication detection
- Code smell detection
- Technical debt analysis
- Security vulnerability scanning
- Performance profiling
- Dependency analysis
- Architecture validation

### Freya - Visual and UI Testing
*Named after the Norse goddess of love and beauty*

Visual testing and UI validation:
- Accessibility validation (WCAG compliance)
- Visual regression testing
- Responsive design testing
- Layout validation
- Style checking
- Mobile compatibility testing

### Forseti - API and Schema Specification
*Named after the Norse god of justice who presides over contracts*

API contract validation:
- OpenAPI/Swagger specification
- GraphQL schema validation
- Database schema analysis
- JSON Schema generation
- Contract compatibility checking
- Breaking change detection

### Verdandi - Runtime Performance Metrics
*Named after the Norse Norn who measures the present*

Runtime performance calculation:
- Web vitals (LCP, FID, CLS)
- Apdex score calculation
- Percentile analysis
- Cache metrics
- Database query metrics
- Network latency analysis

### Volundr - Infrastructure Generation
*Named after the legendary Norse master smith*

Infrastructure code generation:
- Kubernetes manifests
- Terraform modules
- Dockerfiles and docker-compose
- CI/CD pipelines (GitHub Actions, GitLab CI, etc.)

## Installation

```bash
# Install base package
pip install -e ./Asgard

# Install with specific module dependencies
pip install -e "./Asgard[heimdall]"
pip install -e "./Asgard[freya]"
pip install -e "./Asgard[forseti]"
pip install -e "./Asgard[volundr]"

# Install all dependencies
pip install -e "./Asgard[all]"
```

## CLI Usage

### Unified CLI
```bash
asgard heimdall analyze ./src
asgard freya crawl http://localhost:3000
asgard forseti validate openapi.yaml
asgard verdandi report ./metrics
asgard volundr generate kubernetes --name myapp
```

### Individual Module CLIs (backwards compatible)
```bash
heimdall analyze ./src
freya crawl http://localhost:3000
forseti validate openapi.yaml
verdandi report ./metrics
volundr generate kubernetes --name myapp
```

## Python API

```python
from Asgard.Heimdall.Quality.services import ComplexityAnalyzer
from Asgard.Freya.Accessibility.services import WcagValidator
from Asgard.Forseti.OpenAPI.services import SpecValidatorService
from Asgard.Verdandi.Web.services import VitalsCalculator
from Asgard.Volundr.Kubernetes.services import ManifestGenerator
```

## Project Structure

```
Asgard/
├── Asgard/                 # Main package
│   ├── __init__.py
│   ├── cli.py              # Unified CLI
│   ├── Heimdall/           # Code quality
│   ├── Freya/              # Visual testing
│   ├── Forseti/            # API specs
│   ├── Verdandi/           # Performance metrics
│   └── Volundr/            # Infrastructure
├── Asgard_Test/            # Test suite
│   ├── tests_Heimdall/
│   ├── tests_Freya/
│   ├── tests_Verdandi/
│   └── tests_Volundr/
├── pyproject.toml
└── README.md
```

## License

MIT License - Asgard Contributors
