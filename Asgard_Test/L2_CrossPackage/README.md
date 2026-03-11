# L2 Cross-Package Integration Tests

Integration tests that validate interactions between multiple Asgard packages. These tests ensure that the packages work together cohesively to support real-world development workflows.

## Overview

The L2 tests focus on the "seams" where different packages connect and exchange data. They validate that:

1. **Data flows correctly** between packages
2. **Outputs are consistent** across package boundaries
3. **Realistic workflows** can be completed using multiple packages
4. **Package assumptions** about each other are correct

## Test Structure

```
L2_CrossPackage/
├── conftest.py                              # Shared fixtures and test data
├── test_heimdall_volundr_integration.py     # Code analysis → Infrastructure
├── test_forseti_verdandi_integration.py     # API validation → Performance monitoring
├── test_freya_volundr_integration.py        # UI testing → Deployment config
└── test_full_pipeline_integration.py        # Complete multi-package workflows
```

## Test Categories

### Heimdall-Volundr Integration

Tests how code analysis results from Heimdall influence infrastructure generation in Volundr:

- **Code complexity** → Resource allocation in K8s deployments
- **Security vulnerabilities** → Security profiles and network policies
- **Dependency analysis** → Dockerfile generation and build strategies
- **Modularity scores** → Multi-stage build complexity

**Run:** `pytest -m heimdall_volundr`

### Forseti-Verdandi Integration

Tests how API specifications from Forseti inform performance monitoring in Verdandi:

- **Endpoint count** → SLA target configuration
- **Operation types** (GET/POST) → Apdex thresholds
- **Security schemes** → Timeout budgets
- **Schema complexity** → Performance baselines
- **API versioning** → Versioned monitoring

**Run:** `pytest -m forseti_verdandi`

### Freya-Volundr Integration

Tests how UI testing results from Freya influence infrastructure in Volundr:

- **Accessibility violations** → CI/CD quality gates
- **WCAG compliance levels** → Pipeline strictness
- **Accessibility scores** → Deployment strategies
- **Visual baselines** → Kubernetes ConfigMaps
- **Color contrast issues** → Pipeline warnings

**Run:** `pytest -m freya_volundr`

### Full Pipeline Integration

Complete end-to-end workflows that use all five packages:

1. **Heimdall**: Code quality, security, and dependency analysis
2. **Forseti**: API contract validation
3. **Volundr**: Infrastructure, Docker, and CI/CD generation
4. **Freya**: UI accessibility testing (mocked in tests)
5. **Verdandi**: Performance monitoring configuration

**Run:** `pytest -m full_pipeline`

## Running Tests

### All L2 Cross-Package Tests

```bash
cd Asgard_Test
pytest L2_CrossPackage/ -v
```

### Specific Integration Category

```bash
# Heimdall-Volundr integration
pytest L2_CrossPackage/ -m heimdall_volundr -v

# Forseti-Verdandi integration
pytest L2_CrossPackage/ -m forseti_verdandi -v

# Freya-Volundr integration
pytest L2_CrossPackage/ -m freya_volundr -v

# Full pipeline tests
pytest L2_CrossPackage/ -m full_pipeline -v
```

### Single Test File

```bash
pytest L2_CrossPackage/test_heimdall_volundr_integration.py -v
```

### Single Test Class or Method

```bash
# Run specific test class
pytest L2_CrossPackage/test_heimdall_volundr_integration.py::TestQualityReportToDeployment -v

# Run specific test method
pytest L2_CrossPackage/test_heimdall_volundr_integration.py::TestQualityReportToDeployment::test_complexity_influences_resource_allocation -v
```

### Skip Slow Tests

```bash
pytest L2_CrossPackage/ -m "cross_package and not slow" -v
```

## Test Fixtures

All tests have access to the following fixtures from `conftest.py`:

### Workspace Fixtures

- **`temp_workspace`**: Temporary directory with subdirectories for source, output, and reports
- **`output_dir`**: Directory for generated artifacts (K8s manifests, Dockerfiles, etc.)
- **`reports_dir`**: Directory for test reports and analysis results

### Sample Data Fixtures

- **`sample_python_project`**: Complete Python project with:
  - Multiple modules with varying complexity
  - `requirements.txt` with dependencies
  - Package structure for import analysis
  - Both simple and complex code patterns

- **`sample_openapi_spec`**: OpenAPI 3.0 specification with:
  - Multiple endpoints (GET, POST, etc.)
  - Request/response schemas
  - Security schemes
  - API versioning information

- **`sample_html_page`**: HTML page with:
  - Form elements with proper labels
  - Navigation with ARIA attributes
  - Mix of accessible and potential a11y issues
  - Responsive design elements

## Test Patterns

### Pattern 1: Analysis → Configuration

```python
def test_analysis_drives_config(sample_project, output_dir):
    # 1. Analyze with Package A
    analyzer = PackageAAnalyzer()
    result = analyzer.analyze(sample_project)

    # 2. Use results to configure Package B
    config = PackageBConfig(
        setting=derive_from_result(result)
    )

    # 3. Generate with Package B
    generator = PackageBGenerator()
    output = generator.generate(config)

    # 4. Verify consistency
    assert output.reflects(result)
```

### Pattern 2: Validation → Monitoring

```python
def test_validation_sets_monitoring(spec_file):
    # 1. Validate spec with Forseti
    validator = SpecValidator()
    validation = validator.validate(spec_file)

    # 2. Extract complexity metrics
    complexity = analyze_spec_complexity(validation)

    # 3. Configure monitoring with Verdandi
    monitoring_config = create_monitoring(complexity)

    # 4. Verify monitoring matches complexity
    assert monitoring_config.thresholds_match(complexity)
```

### Pattern 3: Full Pipeline

```python
def test_complete_workflow(project, spec, output_dir):
    # Phase 1: Heimdall analysis
    quality = analyze_quality(project)
    security = analyze_security(project)

    # Phase 2: Forseti validation
    api_validation = validate_api(spec)

    # Phase 3: Volundr generation
    infrastructure = generate_infrastructure(
        quality_data=quality,
        security_data=security,
        api_data=api_validation
    )

    # Phase 4: Freya testing (mocked)
    accessibility = mock_accessibility_test()

    # Phase 5: Verdandi monitoring
    monitoring = configure_monitoring(
        api_data=api_validation,
        infrastructure=infrastructure
    )

    # Verify all phases are consistent
    assert_all_consistent([quality, security, api_validation,
                          infrastructure, accessibility, monitoring])
```

## Integration Test Quality Standards

### 1. Realistic Workflows

Tests should mirror actual development workflows:
- Use realistic sample data
- Follow logical sequences (analyze → configure → generate)
- Validate data flows that would occur in production

### 2. Clear Phase Separation

Multi-package tests should clearly separate phases:
- Use comments to mark phases
- Print progress for visibility
- Save intermediate results for debugging

### 3. Comprehensive Verification

Each test should verify:
- Primary workflow completed successfully
- Generated artifacts are valid
- Cross-package data consistency
- Edge cases and error scenarios

### 4. Appropriate Mocking

- Mock browser-dependent operations (Freya accessibility)
- Use real file I/O for generated configs
- Mock external services only when necessary
- Preserve realistic data flows

## Common Issues and Solutions

### Issue: Tests Depend on Package Installation Order

**Solution**: Tests should not depend on Python path manipulation. Use absolute imports from `Asgard.*` packages.

### Issue: Generated Files Not Cleaned Up

**Solution**: Use `temp_workspace` fixture which automatically cleans up after tests.

### Issue: Tests Take Too Long

**Solution**: Mark slow tests with `@pytest.mark.slow` and skip with `-m "not slow"`.

### Issue: Fixtures Not Found

**Solution**: Ensure `conftest.py` is in the test directory and pytest can discover it.

## Adding New Integration Tests

1. **Identify the integration point**: What data flows between which packages?

2. **Create sample data**: Add fixtures to `conftest.py` if needed

3. **Write the test**:
   ```python
   @pytest.mark.cross_package
   @pytest.mark.package_a_package_b
   def test_integration_workflow(fixtures):
       # Phase 1: Package A
       result_a = package_a_operation()

       # Phase 2: Package B uses result_a
       result_b = package_b_operation(result_a)

       # Verify consistency
       assert result_b.reflects(result_a)
   ```

4. **Add appropriate markers**: Use `cross_package` and specific integration markers

5. **Document the workflow**: Add docstring explaining the integration being tested

## Coverage Goals

L2 tests should cover:

- ✅ All major integration points between packages
- ✅ Data transformation between package boundaries
- ✅ Error propagation across packages
- ✅ Configuration consistency validation
- ✅ End-to-end realistic workflows
- ✅ Cross-package naming conventions
- ✅ Output format compatibility

## Related Documentation

- [Asgard Test Suite Guide](../README.md)
- [Heimdall Package Documentation](../../Asgard/Heimdall/README.md)
- [Forseti Package Documentation](../../Asgard/Forseti/README.md)
- [Volundr Package Documentation](../../Asgard/Volundr/README.md)
- [Freya Package Documentation](../../Asgard/Freya/README.md)
- [Verdandi Package Documentation](../../Asgard/Verdandi/README.md)

## Test Maintenance

These integration tests validate real-world workflows. When making changes:

1. **Update fixtures** if package interfaces change
2. **Adjust expectations** if output formats evolve
3. **Add new tests** for new integration points
4. **Keep workflows realistic** - mirror actual usage patterns
5. **Document breaking changes** that affect integrations
