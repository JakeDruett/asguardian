"""
Forseti-Verdandi Integration Tests

Tests for cross-package integration between Forseti (API/schema validation) and
Verdandi (performance metrics). These tests validate workflows where API specifications
inform SLA thresholds and performance monitoring configuration.
"""

from pathlib import Path

import pytest
import yaml

from Asgard.Forseti.OpenAPI import SpecValidatorService, OpenAPIConfig
from Asgard.Verdandi.Analysis import SLAChecker, SLAConfig, ApdexCalculator, ApdexConfig


@pytest.mark.cross_package
@pytest.mark.forseti_verdandi
class TestAPISpecToSLAChecker:
    """
    Test workflow: Parse OpenAPI spec with Forseti, then configure SLA thresholds
    with Verdandi based on operation complexity and requirements.
    """

    def test_endpoint_count_influences_sla_targets(
        self, sample_openapi_spec: Path
    ):
        """
        Test that OpenAPI endpoint count influences SLA target configuration.

        Workflow:
        1. Validate and parse OpenAPI spec with Forseti
        2. Count endpoints and analyze complexity
        3. Configure SLA thresholds with Verdandi based on API size
        4. Verify SLA configuration is appropriate for API scale
        """
        # Step 1: Validate OpenAPI spec with Forseti
        validator = SpecValidatorService()
        validation_result = validator.validate(str(sample_openapi_spec))

        # Verify validation passed
        assert validation_result.is_valid
        assert validation_result.spec_version is not None

        # Step 2: Parse spec to count endpoints
        with open(sample_openapi_spec, 'r') as f:
            spec_data = yaml.safe_load(f)

        paths = spec_data.get('paths', {})
        endpoint_count = sum(len(methods) for methods in paths.values())

        # Step 3: Configure SLA based on API complexity
        # More endpoints = more lenient overall SLA, but stricter per-endpoint
        if endpoint_count > 20:
            # Large API: expect some slower endpoints
            target_success_rate = 0.95
            max_response_time_ms = 2000
            target_percentile = 95
        elif endpoint_count > 10:
            # Medium API
            target_success_rate = 0.98
            max_response_time_ms = 1000
            target_percentile = 99
        else:
            # Small API: should be fast and reliable
            target_success_rate = 0.99
            max_response_time_ms = 500
            target_percentile = 99

        # Step 4: Create SLA configuration with Verdandi
        sla_config = SLAConfig(
            target_success_rate=target_success_rate,
            max_response_time_ms=max_response_time_ms,
            target_percentile=target_percentile,
            measurement_window_seconds=3600
        )

        # Verify SLA config
        assert sla_config.target_success_rate > 0.9
        assert sla_config.max_response_time_ms > 0
        assert sla_config.target_percentile in [95, 99]

        # Create SLA checker
        sla_checker = SLAChecker(sla_config)

        # Simulate some response times
        response_times = [100, 150, 200, 250, 300, 350, 400, 450, 500]
        success_count = 9
        total_count = 10

        # Check SLA compliance
        sla_result = sla_checker.check_sla(
            response_times=response_times,
            success_count=success_count,
            total_count=total_count
        )

        # Verify SLA result structure
        assert sla_result is not None
        assert hasattr(sla_result, 'success_rate_met')
        assert hasattr(sla_result, 'response_time_met')

    def test_operation_types_set_apdex_thresholds(
        self, sample_openapi_spec: Path
    ):
        """
        Test that operation types (GET, POST, etc.) influence Apdex thresholds.

        GET operations should be faster than POST/PUT operations.
        """
        # Parse OpenAPI spec
        with open(sample_openapi_spec, 'r') as f:
            spec_data = yaml.safe_load(f)

        paths = spec_data.get('paths', {})

        # Count operation types
        operation_types = {}
        for path, methods in paths.items():
            for method in methods.keys():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    operation_types[method] = operation_types.get(method, 0) + 1

        # Configure Apdex based on predominant operation type
        get_count = operation_types.get('get', 0)
        post_count = operation_types.get('post', 0)

        if get_count > post_count:
            # Read-heavy API: stricter timing
            satisfied_threshold_ms = 100
            tolerating_threshold_ms = 500
        else:
            # Write-heavy API: more lenient
            satisfied_threshold_ms = 200
            tolerating_threshold_ms = 1000

        # Create Apdex configuration
        apdex_config = ApdexConfig(
            satisfied_threshold_ms=satisfied_threshold_ms,
            tolerating_threshold_ms=tolerating_threshold_ms
        )

        apdex_calculator = ApdexCalculator(apdex_config)

        # Test with sample response times
        response_times = [50, 150, 300, 600, 1200]

        apdex_result = apdex_calculator.calculate(response_times)

        # Verify Apdex result
        assert apdex_result is not None
        assert 0 <= apdex_result.score <= 1.0
        assert apdex_result.satisfied_count >= 0
        assert apdex_result.tolerating_count >= 0
        assert apdex_result.frustrated_count >= 0

    def test_security_schemes_affect_timeout_budgets(
        self, sample_openapi_spec: Path
    ):
        """
        Test that security schemes in OpenAPI spec influence timeout budgets.

        APIs with OAuth2 need higher timeouts to account for token validation.
        """
        # Validate spec
        validator = SpecValidatorService()
        validation_result = validator.validate(str(sample_openapi_spec))

        assert validation_result.is_valid

        # Parse spec for security schemes
        with open(sample_openapi_spec, 'r') as f:
            spec_data = yaml.safe_load(f)

        # Check for security schemes
        components = spec_data.get('components', {})
        security_schemes = components.get('securitySchemes', {})

        # Determine timeout budget based on auth complexity
        has_oauth = any(
            scheme.get('type') == 'oauth2'
            for scheme in security_schemes.values()
        )
        has_openid = any(
            scheme.get('type') == 'openIdConnect'
            for scheme in security_schemes.values()
        )

        # Base timeout
        base_timeout_ms = 500

        # Add overhead for auth
        if has_oauth or has_openid:
            # OAuth/OIDC adds token validation overhead
            timeout_ms = base_timeout_ms + 500
        elif security_schemes:
            # API key or basic auth is faster
            timeout_ms = base_timeout_ms + 100
        else:
            # No auth
            timeout_ms = base_timeout_ms

        # Configure SLA with appropriate timeout
        sla_config = SLAConfig(
            target_success_rate=0.99,
            max_response_time_ms=timeout_ms,
            target_percentile=95
        )

        # Verify timeout is reasonable
        assert sla_config.max_response_time_ms >= base_timeout_ms
        assert sla_config.max_response_time_ms <= base_timeout_ms + 500


@pytest.mark.cross_package
@pytest.mark.forseti_verdandi
class TestSchemaValidationToMetrics:
    """
    Test workflow: Validate schemas with Forseti, track validation performance
    with Verdandi metrics.
    """

    def test_schema_complexity_sets_performance_baselines(
        self, sample_openapi_spec: Path
    ):
        """
        Test that schema complexity influences performance baselines.

        Complex schemas with many nested objects should have higher baseline times.
        """
        # Validate OpenAPI spec
        validator = SpecValidatorService()
        validation_result = validator.validate(str(sample_openapi_spec))

        assert validation_result.is_valid

        # Parse schemas
        with open(sample_openapi_spec, 'r') as f:
            spec_data = yaml.safe_load(f)

        components = spec_data.get('components', {})
        schemas = components.get('schemas', {})

        # Analyze schema complexity
        total_properties = 0
        max_nesting_level = 0

        for schema_name, schema_def in schemas.items():
            properties = schema_def.get('properties', {})
            total_properties += len(properties)

            # Check for nested objects (simplified)
            for prop_name, prop_def in properties.items():
                if prop_def.get('type') == 'object':
                    max_nesting_level = max(max_nesting_level, 1)
                elif '$ref' in prop_def:
                    max_nesting_level = max(max_nesting_level, 1)

        # Set baseline based on complexity
        complexity_score = total_properties + (max_nesting_level * 10)

        if complexity_score > 50:
            baseline_validation_time_ms = 50
        elif complexity_score > 20:
            baseline_validation_time_ms = 20
        else:
            baseline_validation_time_ms = 10

        # Configure Apdex for validation operations
        apdex_config = ApdexConfig(
            satisfied_threshold_ms=baseline_validation_time_ms,
            tolerating_threshold_ms=baseline_validation_time_ms * 3
        )

        # Simulate validation times
        validation_times = [
            baseline_validation_time_ms * 0.8,
            baseline_validation_time_ms * 1.2,
            baseline_validation_time_ms * 2.5,
            baseline_validation_time_ms * 4.0,
        ]

        apdex_calculator = ApdexCalculator(apdex_config)
        apdex_result = apdex_calculator.calculate(validation_times)

        # Verify Apdex calculation
        assert apdex_result.score >= 0
        assert apdex_result.total_samples == len(validation_times)

    def test_required_fields_influence_validation_strictness(
        self, sample_openapi_spec: Path
    ):
        """
        Test that required field count influences validation monitoring.

        More required fields = stricter validation = potentially slower.
        """
        # Parse spec
        with open(sample_openapi_spec, 'r') as f:
            spec_data = yaml.safe_load(f)

        components = spec_data.get('components', {})
        schemas = components.get('schemas', {})

        # Count required fields
        total_required = 0
        for schema_name, schema_def in schemas.items():
            required_fields = schema_def.get('required', [])
            total_required += len(required_fields)

        # Set SLA based on validation complexity
        if total_required > 20:
            # Many required fields: more validation time needed
            max_validation_time_ms = 200
            target_success_rate = 0.95  # Some validations will fail
        elif total_required > 10:
            max_validation_time_ms = 100
            target_success_rate = 0.98
        else:
            max_validation_time_ms = 50
            target_success_rate = 0.99

        # Create SLA config
        sla_config = SLAConfig(
            target_success_rate=target_success_rate,
            max_response_time_ms=max_validation_time_ms,
            target_percentile=99
        )

        # Verify configuration reflects complexity
        assert sla_config.max_response_time_ms > 0
        assert 0.9 <= sla_config.target_success_rate <= 1.0

        # The more required fields, the longer validation should be allowed
        if total_required > 20:
            assert sla_config.max_response_time_ms >= 200

    def test_endpoint_response_schemas_set_serialization_sla(
        self, sample_openapi_spec: Path
    ):
        """
        Test that response schema size influences serialization SLA.

        Large response schemas need more time for serialization/deserialization.
        """
        # Validate spec
        validator = SpecValidatorService()
        validation_result = validator.validate(str(sample_openapi_spec))
        assert validation_result.is_valid

        # Parse response schemas
        with open(sample_openapi_spec, 'r') as f:
            spec_data = yaml.safe_load(f)

        paths = spec_data.get('paths', {})

        # Analyze response schemas
        response_schema_count = 0
        array_responses = 0

        for path, methods in paths.items():
            for method, operation in methods.items():
                if method not in ['get', 'post', 'put', 'delete', 'patch']:
                    continue

                responses = operation.get('responses', {})
                for status_code, response_def in responses.items():
                    content = response_def.get('content', {})
                    for media_type, schema_info in content.items():
                        schema = schema_info.get('schema', {})
                        response_schema_count += 1

                        # Check if it's an array response
                        if schema.get('type') == 'array':
                            array_responses += 1

        # Set serialization SLA
        # Array responses take longer to serialize
        if array_responses > 0:
            serialization_time_ms = 100 * array_responses
        else:
            serialization_time_ms = 50

        # Configure Apdex for serialization
        apdex_config = ApdexConfig(
            satisfied_threshold_ms=serialization_time_ms,
            tolerating_threshold_ms=serialization_time_ms * 3
        )

        # Verify configuration
        assert apdex_config.satisfied_threshold_ms > 0
        assert apdex_config.tolerating_threshold_ms > apdex_config.satisfied_threshold_ms


@pytest.mark.cross_package
@pytest.mark.forseti_verdandi
class TestAPIVersioningToPerformanceTracking:
    """
    Test workflow: Use API version from Forseti to set up versioned performance
    tracking with Verdandi.
    """

    def test_api_version_creates_separate_sla_baselines(
        self, sample_openapi_spec: Path
    ):
        """
        Test that API version information creates versioned SLA baselines.

        Different API versions may have different performance characteristics.
        """
        # Parse OpenAPI spec
        with open(sample_openapi_spec, 'r') as f:
            spec_data = yaml.safe_load(f)

        info = spec_data.get('info', {})
        api_version = info.get('version', '1.0.0')

        # Parse version
        major_version = int(api_version.split('.')[0])

        # Configure SLA per version
        # Newer versions might be less optimized initially
        if major_version >= 2:
            # Newer API: more lenient initially
            target_success_rate = 0.95
            max_response_time_ms = 1000
        else:
            # v1 API: should be well-optimized
            target_success_rate = 0.99
            max_response_time_ms = 500

        # Create versioned SLA config
        sla_config = SLAConfig(
            target_success_rate=target_success_rate,
            max_response_time_ms=max_response_time_ms,
            target_percentile=95
        )

        # Verify version-specific configuration
        assert sla_config.target_success_rate > 0
        assert sla_config.max_response_time_ms > 0

        # Store baseline keyed by version
        version_baselines = {
            f"v{major_version}": {
                "success_rate": sla_config.target_success_rate,
                "max_response_ms": sla_config.max_response_time_ms
            }
        }

        assert f"v{major_version}" in version_baselines

    def test_deprecated_endpoints_have_different_sla(
        self, sample_openapi_spec: Path
    ):
        """
        Test that deprecated endpoints can have more lenient SLAs.

        Deprecated endpoints don't need as strict performance requirements.
        """
        # Parse spec
        with open(sample_openapi_spec, 'r') as f:
            spec_data = yaml.safe_load(f)

        paths = spec_data.get('paths', {})

        # Check for deprecated operations
        deprecated_count = 0
        active_count = 0

        for path, methods in paths.items():
            for method, operation in methods.items():
                if method not in ['get', 'post', 'put', 'delete', 'patch']:
                    continue

                is_deprecated = operation.get('deprecated', False)
                if is_deprecated:
                    deprecated_count += 1
                else:
                    active_count += 1

        # Create separate SLA configs
        active_sla = SLAConfig(
            target_success_rate=0.99,
            max_response_time_ms=500,
            target_percentile=99
        )

        deprecated_sla = SLAConfig(
            target_success_rate=0.95,
            max_response_time_ms=1000,
            target_percentile=95
        )

        # Verify deprecated has more lenient SLA
        assert deprecated_sla.target_success_rate <= active_sla.target_success_rate
        assert deprecated_sla.max_response_time_ms >= active_sla.max_response_time_ms
        assert deprecated_sla.target_percentile <= active_sla.target_percentile
