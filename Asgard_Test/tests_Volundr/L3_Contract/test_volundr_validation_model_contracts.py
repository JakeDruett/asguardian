"""L3 Contract tests for Volundr Validation-layer models.

Covers canonical_models, rule_registry, score_models, and
suppression_models pydantic contracts.
"""

import pytest
from datetime import date
from pydantic import ValidationError

from Asgard.Volundr.Validation.models.canonical_models import (
    COMPUTED,
    TAINTED,
    is_computed,
    is_tainted,
    is_unknown,
    CanonicalContainer,
    CanonicalWorkload,
    CanonicalNetworkRule,
    CanonicalComposeService,
    CanonicalPipelineStep,
    CanonicalPipelineJob,
    CanonicalDocument,
)
from Asgard.Volundr.Validation.models.rule_registry import (
    RuleSeverity,
    UnknownValueBehavior,
    RegisteredRule,
)
from Asgard.Volundr.Validation.models.score_models import (
    ScoreDimension,
    letter_grade,
    DimensionScore,
    ResourceScore,
    RemediationHint,
    SuppressedReceipt,
    ScoreReport,
    PostureIndex,
)
from Asgard.Volundr.Validation.models.suppression_models import (
    Suppression,
    SuppressionSet,
)
from Asgard.Volundr.Validation.models.validation_models import ValidationCategory


# ---------------------------------------------------------------------------
# canonical_models
# ---------------------------------------------------------------------------
class TestSentinelContract:
    def test_sentinels_are_falsy(self):
        assert not COMPUTED
        assert not TAINTED

    def test_predicates(self):
        assert is_computed(COMPUTED) and not is_computed(TAINTED)
        assert is_tainted(TAINTED) and not is_tainted(COMPUTED)
        assert is_unknown(COMPUTED) and is_unknown(TAINTED)
        assert not is_unknown("value") and not is_unknown(None)


class TestCanonicalContainerContract:
    def test_instantiates_with_defaults(self):
        container = CanonicalContainer()
        assert container.name == "unknown"
        assert container.init is False
        assert container.tainted is False
        assert container.line_number is None

    def test_accepts_sentinel_values(self):
        container = CanonicalContainer(privileged=COMPUTED, run_as_non_root=TAINTED)
        assert is_computed(container.privileged)
        assert is_tainted(container.run_as_non_root)

    def test_has_model_fields(self):
        fields = set(CanonicalContainer.model_fields.keys())
        assert "image" in fields
        assert "allow_privilege_escalation" in fields
        assert "seccomp_profile_type" in fields


class TestCanonicalWorkloadContract:
    def test_requires_kind(self):
        with pytest.raises((ValidationError, TypeError)):
            CanonicalWorkload()

    def test_instantiates_with_required_fields(self):
        workload = CanonicalWorkload(kind="Deployment")
        assert workload.kind == "Deployment"
        assert workload.containers == []
        assert workload.pod_spec_path == "spec"

    def test_has_model_fields(self):
        fields = set(CanonicalWorkload.model_fields.keys())
        assert "host_network" in fields
        assert "automount_service_account_token" in fields
        assert "tainted" in fields


class TestCanonicalNetworkRuleContract:
    def test_instantiates_with_defaults(self):
        rule = CanonicalNetworkRule()
        assert rule.source == ""
        assert rule.host_port is None
        assert rule.tainted is False


class TestCanonicalComposeServiceContract:
    def test_requires_name(self):
        with pytest.raises((ValidationError, TypeError)):
            CanonicalComposeService()

    def test_instantiates_with_required_fields(self):
        service = CanonicalComposeService(name="web")
        assert service.name == "web"
        assert service.ports == []
        assert service.privileged is None


class TestCanonicalPipelineContract:
    def test_step_defaults(self):
        step = CanonicalPipelineStep()
        assert step.name == ""
        assert step.env == {}
        assert step.with_params == {}

    def test_job_requires_name(self):
        with pytest.raises((ValidationError, TypeError)):
            CanonicalPipelineJob()

    def test_job_instantiates_with_required_fields(self):
        job = CanonicalPipelineJob(name="build")
        assert job.name == "build"
        assert job.steps == []
        assert job.permissions is None


class TestCanonicalDocumentContract:
    def test_instantiates_with_defaults(self):
        doc = CanonicalDocument()
        assert doc.workloads == []
        assert doc.compose_services == []
        assert doc.pipeline_jobs == []
        assert doc.raw == {}


# ---------------------------------------------------------------------------
# rule_registry
# ---------------------------------------------------------------------------
class TestRuleSeverityContract:
    def test_five_levels(self):
        assert {s.value for s in RuleSeverity} == {
            "critical",
            "high",
            "medium",
            "low",
            "info",
        }

    def test_legacy_round_trip_mapping_exists(self):
        for severity in RuleSeverity:
            legacy = severity.to_validation_severity()
            assert RuleSeverity.from_validation_severity(legacy) in RuleSeverity


class TestUnknownValueBehaviorContract:
    def test_members(self):
        assert UnknownValueBehavior.SKIP.value == "skip"
        assert UnknownValueBehavior.WARN.value == "warn"
        assert UnknownValueBehavior.CONDITIONAL_ASSERT.value == "conditional-assert"


class TestRegisteredRuleContract:
    def test_requires_core_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            RegisteredRule()

    def test_instantiates_with_required_fields(self):
        rule = RegisteredRule(
            id="VOL-K8S-0001",
            name="no-privileged",
            description="Container must not run privileged",
            severity=RuleSeverity.HIGH,
            category=list(ValidationCategory)[0],
        )
        assert rule.id == "VOL-K8S-0001"
        assert rule.enabled is True
        assert rule.on_computed == UnknownValueBehavior.WARN
        assert rule.on_tainted == UnknownValueBehavior.WARN

    def test_has_model_fields(self):
        fields = set(RegisteredRule.model_fields.keys())
        assert "framework_mappings" in fields
        assert "remediation" in fields
        assert "documentation_url" in fields


# ---------------------------------------------------------------------------
# score_models
# ---------------------------------------------------------------------------
class TestScoreDimensionContract:
    def test_four_dimensions(self):
        assert {d.value for d in ScoreDimension} == {
            "security",
            "operability",
            "completeness",
            "maintainability",
        }


class TestLetterGradeContract:
    def test_boundaries(self):
        assert letter_grade(95) == "A"
        assert letter_grade(90) == "A"
        assert letter_grade(80) == "B"
        assert letter_grade(65) == "C"
        assert letter_grade(50) == "D"
        assert letter_grade(49.9) == "F"


class TestDimensionScoreContract:
    def test_requires_core_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            DimensionScore()

    def test_instantiates_with_required_fields(self):
        score = DimensionScore(
            dimension=ScoreDimension.SECURITY, score=85.0, grade="B", weight=0.4
        )
        assert score.score == 85.0
        assert score.finding_count == 0

    def test_rejects_out_of_range_score(self):
        with pytest.raises(ValidationError):
            DimensionScore(
                dimension=ScoreDimension.SECURITY, score=101.0, grade="A", weight=0.4
            )


class TestResourceScoreContract:
    def test_requires_resource_and_score(self):
        with pytest.raises((ValidationError, TypeError)):
            ResourceScore()

    def test_instantiates_with_required_fields(self):
        score = ResourceScore(resource="deployment/web", score=90.0)
        assert score.aggregate_weight == 1.0
        assert score.finding_count == 0


class TestRemediationHintContract:
    def test_requires_rule_id_and_message(self):
        with pytest.raises((ValidationError, TypeError)):
            RemediationHint()

    def test_instantiates_with_required_fields(self):
        hint = RemediationHint(rule_id="VOL-K8S-0001", message="fix it")
        assert hint.severity == "medium"
        assert hint.effort == "1 edit"


class TestSuppressedReceiptContract:
    def test_requires_all_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            SuppressedReceipt()

    def test_instantiates_with_required_fields(self):
        receipt = SuppressedReceipt(
            rule_id="VOL-K8S-0001", target="web", reason="ticket-42"
        )
        assert receipt.target == "web"


class TestScoreReportContract:
    def test_requires_composite_and_grade(self):
        with pytest.raises((ValidationError, TypeError)):
            ScoreReport()

    def test_instantiates_with_required_fields(self):
        report = ScoreReport(composite=88.0, grade="B")
        assert report.environment == "production"
        assert report.veto_applied is None
        assert report.suppressed_count == 0

    def test_dimension_lookup_and_delta(self):
        dim = DimensionScore(
            dimension=ScoreDimension.SECURITY, score=80.0, grade="B", weight=1.0
        )
        report = ScoreReport(composite=80.0, grade="B", dimensions=[dim])
        baseline_dim = DimensionScore(
            dimension=ScoreDimension.SECURITY, score=70.0, grade="C", weight=1.0
        )
        baseline = ScoreReport(composite=70.0, grade="C", dimensions=[baseline_dim])
        assert report.dimension(ScoreDimension.SECURITY) is dim
        assert report.dimension(ScoreDimension.OPERABILITY) is None
        deltas = report.delta(baseline)
        assert deltas["composite"] == 10.0
        assert deltas["security"] == 10.0


class TestPostureIndexContract:
    def test_requires_posture_and_system_risk(self):
        with pytest.raises((ValidationError, TypeError)):
            PostureIndex()

    def test_instantiates_with_required_fields(self):
        index = PostureIndex(posture=60.0, system_risk=0.4)
        assert index.epistemic_floor == 0.4
        assert len(index.assumptions) == 3

    def test_rejects_out_of_range_risk(self):
        with pytest.raises(ValidationError):
            PostureIndex(posture=60.0, system_risk=1.5)


# ---------------------------------------------------------------------------
# suppression_models
# ---------------------------------------------------------------------------
class TestSuppressionContract:
    def test_requires_rule_target_reason(self):
        with pytest.raises((ValidationError, TypeError)):
            Suppression()

    def test_instantiates_with_required_fields(self):
        supp = Suppression(rule="VOL-K8S-0001", target="web", reason="ticket-42")
        assert supp.expires is None
        assert supp.is_expired() is False

    def test_rejects_empty_reason(self):
        with pytest.raises(ValidationError):
            Suppression(rule="VOL-K8S-0001", target="web", reason="   ")

    def test_expiry_and_receipts(self):
        supp = Suppression(
            rule="VOL-K8S-0001",
            target="web",
            reason="ticket-42",
            expires=date(2026, 1, 1),
        )
        assert supp.is_expired(today=date(2026, 2, 1)) is True
        assert supp.is_expired(today=date(2025, 12, 31)) is False
        assert supp.receipt_annotation_key() == "volundr.asgard/suppress-VOL-K8S-0001"
        assert "volundr:suppress=VOL-K8S-0001" in supp.receipt_comment()


class TestSuppressionSetContract:
    def test_instantiates_empty(self):
        supp_set = SuppressionSet()
        assert len(supp_set) == 0
        assert list(supp_set) == []

    def test_from_yaml_top_level_key_and_bare_list(self):
        yaml_doc = (
            "suppressions:\n"
            "  - rule: VOL-K8S-0001\n"
            "    target: web\n"
            "    reason: ticket-42\n"
        )
        supp_set = SuppressionSet.from_yaml(yaml_doc)
        assert len(supp_set) == 1
        bare = SuppressionSet.from_yaml(
            "- rule: VOL-K8S-0002\n  target: db\n  reason: ticket-43\n"
        )
        assert len(bare) == 1

    def test_from_yaml_rejects_missing_reason(self):
        with pytest.raises(ValidationError):
            SuppressionSet.from_yaml("- rule: VOL-K8S-0001\n  target: web\n")
