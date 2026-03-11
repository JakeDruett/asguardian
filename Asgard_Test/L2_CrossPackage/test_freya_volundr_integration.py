"""
Freya-Volundr Integration Tests

Tests for cross-package integration between Freya (visual/UI testing) and
Volundr (infrastructure generation). These tests validate workflows where
accessibility and visual testing results inform CI/CD pipeline configuration
and deployment strategies.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from Asgard.Freya.Accessibility import (
    AccessibilityConfig,
    AccessibilityReport,
    AccessibilityViolation,
    WCAGLevel,
    ViolationSeverity,
)
from Asgard.Volundr.CICD import PipelineConfig, PipelineGenerator, CICDPlatform
from Asgard.Volundr.CICD.models.cicd_models import (
    PipelineStage,
    StepConfig,
    TriggerConfig,
    TriggerType,
)
from Asgard.Volundr.Kubernetes import ManifestConfig, ManifestGenerator


@pytest.mark.cross_package
@pytest.mark.freya_volundr
class TestAccessibilityReportToCICD:
    """
    Test workflow: Run accessibility scan with Freya, then generate CI/CD pipeline
    with Volundr that includes accessibility gate based on findings.
    """

    def test_accessibility_violations_add_quality_gate(
        self, sample_html_page: Path, output_dir: Path
    ):
        """
        Test that accessibility violations trigger quality gates in CI/CD.

        Workflow:
        1. Mock accessibility scan (Freya requires browser)
        2. Analyze violation severity
        3. Generate CI/CD pipeline with appropriate a11y gates
        4. Verify pipeline includes accessibility checks
        """
        # Step 1: Mock accessibility report (Freya needs browser context)
        # In real scenario, would use Freya's WCAGValidator
        mock_violations = [
            AccessibilityViolation(
                rule_id="color-contrast",
                description="Text has insufficient color contrast",
                severity=ViolationSeverity.SERIOUS,
                wcag_level=WCAGLevel.AA,
                element="button.submit",
                impact="Users with low vision cannot read text",
                help_url="https://example.com/color-contrast"
            ),
            AccessibilityViolation(
                rule_id="image-alt",
                description="Image missing alt text",
                severity=ViolationSeverity.CRITICAL,
                wcag_level=WCAGLevel.A,
                element="img.logo",
                impact="Screen reader users cannot understand image content",
                help_url="https://example.com/image-alt"
            ),
        ]

        mock_report = AccessibilityReport(
            url="http://localhost:3000",
            wcag_level=WCAGLevel.AA,
            violations=mock_violations,
            passes=[],
            incomplete=[],
            total_violations=len(mock_violations),
            critical_count=1,
            serious_count=1,
            moderate_count=0,
            minor_count=0,
            score=65.5
        )

        # Step 2: Analyze violations
        critical_violations = [v for v in mock_violations if v.severity == ViolationSeverity.CRITICAL]
        serious_violations = [v for v in mock_violations if v.severity == ViolationSeverity.SERIOUS]

        # Step 3: Generate CI/CD pipeline with a11y gate
        # Add accessibility testing stage if violations exist
        stages = [
            PipelineStage(
                name="Build",
                runs_on="ubuntu-latest",
                steps=[
                    StepConfig(name="Checkout", uses="actions/checkout@v3"),
                    StepConfig(name="Build", run="npm run build"),
                ]
            ),
            PipelineStage(
                name="Test",
                runs_on="ubuntu-latest",
                needs=["Build"],
                steps=[
                    StepConfig(name="Unit Tests", run="npm test"),
                ]
            ),
        ]

        # Add accessibility gate if violations found
        if critical_violations or serious_violations:
            a11y_stage = PipelineStage(
                name="Accessibility",
                runs_on="ubuntu-latest",
                needs=["Build"],
                steps=[
                    StepConfig(
                        name="Accessibility Audit",
                        run="npm run test:a11y"
                    ),
                    StepConfig(
                        name="Check Critical Issues",
                        run="npm run check-a11y-critical"
                    ),
                ]
            )

            # If critical violations, make it a blocking gate
            if critical_violations:
                a11y_stage.steps.append(
                    StepConfig(
                        name="Fail on Critical",
                        run="exit 1",
                        condition="failure()"
                    )
                )

            stages.insert(2, a11y_stage)

        # Step 4: Generate pipeline
        pipeline_config = PipelineConfig(
            name="CI with Accessibility Gate",
            platform=CICDPlatform.GITHUB_ACTIONS,
            triggers=[TriggerConfig(type=TriggerType.PUSH, branches=["main"])],
            stages=stages
        )

        generator = PipelineGenerator(output_dir=str(output_dir))
        pipeline = generator.generate(pipeline_config)

        # Verify pipeline
        assert pipeline is not None
        assert pipeline.yaml_content is not None

        yaml_content = pipeline.yaml_content

        # Verify accessibility stage exists if violations found
        if critical_violations or serious_violations:
            assert "Accessibility" in yaml_content
            assert "test:a11y" in yaml_content

        # Verify critical violations cause failure
        if critical_violations:
            assert "check-a11y-critical" in yaml_content

    def test_wcag_level_determines_pipeline_strictness(
        self, output_dir: Path
    ):
        """
        Test that WCAG compliance level determines CI/CD pipeline strictness.

        WCAG AAA requires stricter checks than AA or A.
        """
        # Test different WCAG levels
        wcag_levels = [
            (WCAGLevel.A, "basic"),
            (WCAGLevel.AA, "standard"),
            (WCAGLevel.AAA, "strict"),
        ]

        for wcag_level, expected_strictness in wcag_levels:
            # Configure pipeline based on WCAG level
            if wcag_level == WCAGLevel.AAA:
                # Strictest: fail on any violation
                fail_threshold = 0
                stages = [
                    PipelineStage(
                        name="Accessibility",
                        runs_on="ubuntu-latest",
                        steps=[
                            StepConfig(
                                name="WCAG AAA Audit",
                                run="npm run test:a11y -- --level=AAA"
                            ),
                            StepConfig(
                                name="Fail on Any Violation",
                                run="test $(cat a11y-report.json | jq '.violations | length') -eq 0"
                            ),
                        ]
                    )
                ]
            elif wcag_level == WCAGLevel.AA:
                # Standard: fail on critical/serious
                fail_threshold = 2
                stages = [
                    PipelineStage(
                        name="Accessibility",
                        runs_on="ubuntu-latest",
                        steps=[
                            StepConfig(
                                name="WCAG AA Audit",
                                run="npm run test:a11y -- --level=AA"
                            ),
                            StepConfig(
                                name="Check Critical and Serious",
                                run="npm run check-a11y-threshold -- --max-violations=2"
                            ),
                        ]
                    )
                ]
            else:
                # Basic: fail only on critical
                fail_threshold = 5
                stages = [
                    PipelineStage(
                        name="Accessibility",
                        runs_on="ubuntu-latest",
                        steps=[
                            StepConfig(
                                name="WCAG A Audit",
                                run="npm run test:a11y -- --level=A"
                            ),
                            StepConfig(
                                name="Check Critical Only",
                                run="npm run check-a11y-critical"
                            ),
                        ]
                    )
                ]

            # Generate pipeline
            pipeline_config = PipelineConfig(
                name=f"CI with {wcag_level.value} Accessibility",
                platform=CICDPlatform.GITHUB_ACTIONS,
                stages=stages
            )

            generator = PipelineGenerator(output_dir=str(output_dir))
            pipeline = generator.generate(pipeline_config)

            # Verify pipeline reflects WCAG level
            yaml_content = pipeline.yaml_content
            assert wcag_level.value in yaml_content

            # Verify strictness
            if wcag_level == WCAGLevel.AAA:
                assert "AAA" in yaml_content
                assert "Any Violation" in yaml_content
            elif wcag_level == WCAGLevel.AA:
                assert "AA" in yaml_content

    def test_accessibility_score_influences_deployment_strategy(
        self, output_dir: Path
    ):
        """
        Test that accessibility score influences Kubernetes deployment strategy.

        Low scores should use canary deployments for safer rollouts.
        """
        # Simulate different accessibility scores
        test_cases = [
            (95, "RollingUpdate"),
            (75, "Canary"),
            (50, "Blue-Green"),
        ]

        for score, expected_strategy in test_cases:
            # High score: standard rolling update
            # Medium score: canary (gradual rollout)
            # Low score: blue-green (full rollback capability)

            # Generate K8s manifest with appropriate strategy
            k8s_config = ManifestConfig(
                name=f"app-score-{score}",
                image="myapp:latest",
                replicas=3,
                annotations={
                    "deployment.strategy": expected_strategy,
                    "accessibility.score": str(score)
                }
            )

            generator = ManifestGenerator(output_dir=str(output_dir))
            manifest = generator.generate(k8s_config)

            # Verify strategy annotation
            yaml_content = manifest.yaml_content
            assert f"accessibility.score: \"{score}\"" in yaml_content
            assert f"deployment.strategy: {expected_strategy}" in yaml_content


@pytest.mark.cross_package
@pytest.mark.freya_volundr
class TestVisualBaselineToDeployment:
    """
    Test workflow: Manage visual regression baselines with Freya, store them
    in Kubernetes ConfigMaps generated by Volundr.
    """

    def test_visual_baselines_stored_in_configmap(
        self, output_dir: Path
    ):
        """
        Test that visual regression baselines are stored in K8s ConfigMaps.

        Workflow:
        1. Mock visual baseline data (Freya needs browser)
        2. Generate ConfigMap with Volundr to store baselines
        3. Verify ConfigMap contains baseline references
        """
        # Step 1: Mock visual baseline data
        baselines = {
            "homepage": {
                "hash": "abc123def456",
                "path": "baselines/homepage.png",
                "viewport": "1920x1080",
                "captured_at": "2026-02-02T10:00:00Z"
            },
            "dashboard": {
                "hash": "def789ghi012",
                "path": "baselines/dashboard.png",
                "viewport": "1920x1080",
                "captured_at": "2026-02-02T10:05:00Z"
            }
        }

        # Step 2: Generate ConfigMap with baseline data
        from Asgard.Volundr.Kubernetes.services.configmap_generator import ConfigMapGenerator
        from Asgard.Volundr.Kubernetes.models.kubernetes_models import ConfigMapConfig

        import json

        configmap_config = ConfigMapConfig(
            name="visual-baselines",
            namespace="default",
            data={
                "baselines.json": json.dumps(baselines, indent=2)
            }
        )

        cm_generator = ConfigMapGenerator(output_dir=str(output_dir))
        configmap = cm_generator.generate(configmap_config)

        # Step 3: Verify ConfigMap
        assert configmap is not None
        yaml_content = configmap.yaml_content

        assert "visual-baselines" in yaml_content
        assert "baselines.json" in yaml_content
        assert "homepage" in yaml_content
        assert "abc123def456" in yaml_content

    def test_visual_regression_failures_create_rollback_job(
        self, output_dir: Path
    ):
        """
        Test that visual regression failures trigger K8s Job for rollback.

        If visual regression tests fail, create a Job to rollback deployment.
        """
        # Simulate visual regression failure
        regression_detected = True
        previous_version = "v1.2.3"
        current_version = "v1.2.4"

        if regression_detected:
            # Generate Kubernetes Job for rollback
            from Asgard.Volundr.Kubernetes.models.kubernetes_models import (
                JobConfig,
                RestartPolicy
            )
            from Asgard.Volundr.Kubernetes.services.job_generator import JobGenerator

            job_config = JobConfig(
                name="rollback-visual-regression",
                namespace="default",
                image="kubectl:latest",
                command=["kubectl", "rollout", "undo", "deployment/myapp"],
                restart_policy=RestartPolicy.NEVER,
                labels={
                    "type": "rollback",
                    "reason": "visual-regression",
                    "from-version": current_version,
                    "to-version": previous_version
                }
            )

            job_generator = JobGenerator(output_dir=str(output_dir))
            job = job_generator.generate(job_config)

            # Verify Job
            assert job is not None
            yaml_content = job.yaml_content

            assert "rollback-visual-regression" in yaml_content
            assert "kubectl rollout undo" in yaml_content
            assert "visual-regression" in yaml_content

    def test_responsive_breakpoint_testing_creates_hpa_config(
        self, output_dir: Path
    ):
        """
        Test that responsive breakpoint testing informs HPA (Horizontal Pod Autoscaler).

        More breakpoints tested = anticipate more traffic = configure HPA.
        """
        # Simulate breakpoint testing
        tested_breakpoints = [
            "mobile-sm (320px)",
            "mobile-md (375px)",
            "mobile-lg (425px)",
            "tablet (768px)",
            "desktop (1024px)",
            "desktop-xl (1440px)",
        ]

        # More breakpoints = expect diverse client base = scale for traffic
        breakpoint_count = len(tested_breakpoints)

        if breakpoint_count >= 5:
            # Many breakpoints: expect high traffic from various devices
            min_replicas = 3
            max_replicas = 10
            target_cpu_percent = 70
        elif breakpoint_count >= 3:
            min_replicas = 2
            max_replicas = 5
            target_cpu_percent = 80
        else:
            min_replicas = 1
            max_replicas = 3
            target_cpu_percent = 90

        # Generate HPA configuration
        from Asgard.Volundr.Kubernetes.models.kubernetes_models import HPAConfig
        from Asgard.Volundr.Kubernetes.services.hpa_generator import HPAGenerator

        hpa_config = HPAConfig(
            name="responsive-app-hpa",
            namespace="default",
            target_deployment="myapp",
            min_replicas=min_replicas,
            max_replicas=max_replicas,
            target_cpu_utilization_percentage=target_cpu_percent,
            annotations={
                "tested-breakpoints": str(breakpoint_count),
                "breakpoints": ", ".join(tested_breakpoints)
            }
        )

        hpa_generator = HPAGenerator(output_dir=str(output_dir))
        hpa = hpa_generator.generate(hpa_config)

        # Verify HPA
        assert hpa is not None
        yaml_content = hpa.yaml_content

        assert f"minReplicas: {min_replicas}" in yaml_content
        assert f"maxReplicas: {max_replicas}" in yaml_content
        assert f"{target_cpu_percent}" in yaml_content


@pytest.mark.cross_package
@pytest.mark.freya_volundr
class TestColorContrastToCICDWarnings:
    """
    Test workflow: Color contrast issues detected by Freya trigger warnings
    in CI/CD pipeline generated by Volundr.
    """

    def test_contrast_violations_add_warning_annotations(
        self, output_dir: Path
    ):
        """
        Test that color contrast violations add warning steps to pipeline.

        Non-blocking warnings for minor contrast issues.
        """
        # Mock contrast violations
        contrast_violations = [
            {
                "foreground": "#777777",
                "background": "#ffffff",
                "ratio": 4.2,
                "required": 4.5,
                "level": "AA",
                "size": "normal"
            },
            {
                "foreground": "#999999",
                "background": "#ffffff",
                "ratio": 2.8,
                "required": 3.0,
                "level": "AA",
                "size": "large"
            }
        ]

        # Generate pipeline with warnings
        stages = [
            PipelineStage(
                name="Build",
                runs_on="ubuntu-latest",
                steps=[
                    StepConfig(name="Build", run="npm run build"),
                ]
            ),
            PipelineStage(
                name="Accessibility Checks",
                runs_on="ubuntu-latest",
                needs=["Build"],
                steps=[
                    StepConfig(
                        name="Color Contrast Check",
                        run="npm run check-contrast"
                    ),
                ]
            )
        ]

        # Add warning step for each violation
        for i, violation in enumerate(contrast_violations):
            warning_step = StepConfig(
                name=f"Contrast Warning {i+1}",
                run=f"echo '::warning::Contrast ratio {violation['ratio']} below {violation['required']}'"
            )
            stages[1].steps.append(warning_step)

        # Generate pipeline
        pipeline_config = PipelineConfig(
            name="CI with Contrast Warnings",
            platform=CICDPlatform.GITHUB_ACTIONS,
            stages=stages
        )

        generator = PipelineGenerator(output_dir=str(output_dir))
        pipeline = generator.generate(pipeline_config)

        # Verify warnings
        yaml_content = pipeline.yaml_content
        assert "Color Contrast Check" in yaml_content
        assert "::warning::" in yaml_content
        assert "Contrast ratio" in yaml_content

    def test_severe_contrast_issues_block_deployment(
        self, output_dir: Path
    ):
        """
        Test that severe contrast issues block deployment in pipeline.

        Critical contrast failures should prevent deployment.
        """
        # Mock severe contrast violation
        has_severe_contrast_issue = True
        severe_ratio = 1.5  # Very poor contrast
        required_ratio = 4.5

        stages = [
            PipelineStage(
                name="Build",
                runs_on="ubuntu-latest",
                steps=[
                    StepConfig(name="Build", run="npm run build"),
                ]
            ),
            PipelineStage(
                name="Accessibility Gate",
                runs_on="ubuntu-latest",
                needs=["Build"],
                steps=[
                    StepConfig(
                        name="Check Contrast",
                        run="npm run check-contrast"
                    ),
                ]
            )
        ]

        # Add blocking step if severe issue
        if has_severe_contrast_issue and severe_ratio < 2.0:
            stages[1].steps.append(
                StepConfig(
                    name="Block on Severe Contrast Issue",
                    run=f"echo 'FAIL: Contrast ratio {severe_ratio} is critically low (required: {required_ratio})' && exit 1"
                )
            )

            # Remove deploy stage or make it conditional
            # In this test, we just verify the blocking step exists

        # Generate pipeline
        pipeline_config = PipelineConfig(
            name="CI with Contrast Gate",
            platform=CICDPlatform.GITHUB_ACTIONS,
            stages=stages
        )

        generator = PipelineGenerator(output_dir=str(output_dir))
        pipeline = generator.generate(pipeline_config)

        # Verify blocking
        yaml_content = pipeline.yaml_content
        assert "Block on Severe Contrast Issue" in yaml_content
        assert "exit 1" in yaml_content
        assert "critically low" in yaml_content
