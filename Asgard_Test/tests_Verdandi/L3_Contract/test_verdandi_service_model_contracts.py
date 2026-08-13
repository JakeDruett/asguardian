"""L3 Contract tests for Verdandi SLO service-layer models.

Covers pydantic models defined in SLO/services: budget_policy,
portfolio_scorer, and tool_slo.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from Asgard.Verdandi.SLO.services.budget_policy import (
    BudgetPolicyTier,
    IncidentBudgetImpact,
    BudgetPolicyState,
)
from Asgard.Verdandi.SLO.services.portfolio_scorer import (
    PortfolioHealthResult,
    UncalibratedSLOFlag,
)
from Asgard.Verdandi.SLO.services.tool_slo import (
    RunOutcome,
    Finding,
    Incident,
    RunRecord,
    SelfSLOResult,
)


_NOW = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# budget_policy models
# ---------------------------------------------------------------------------
class TestBudgetPolicyTierContract:
    def test_members(self):
        assert BudgetPolicyTier.NORMAL.value == "normal"
        assert BudgetPolicyTier.CAUTION.value == "caution"
        assert BudgetPolicyTier.FREEZE.value == "freeze"
        assert BudgetPolicyTier.EXHAUSTED.value == "exhausted"


class TestIncidentBudgetImpactContract:
    def test_requires_bad_events_and_budget_consumed_pct(self):
        with pytest.raises((ValidationError, TypeError)):
            IncidentBudgetImpact()

    def test_instantiates_with_required_fields(self):
        impact = IncidentBudgetImpact(bad_events=10, budget_consumed_pct=25.0)
        assert impact.bad_events == 10
        assert impact.budget_consumed_pct == 25.0
        assert impact.post_mortem_required is False
        assert impact.started_at is None

    def test_has_model_fields(self):
        fields = set(IncidentBudgetImpact.model_fields.keys())
        assert "bad_events" in fields
        assert "budget_consumed_pct" in fields
        assert "post_mortem_required" in fields


class TestBudgetPolicyStateContract:
    def test_requires_core_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            BudgetPolicyState()

    def test_instantiates_with_required_fields(self):
        state = BudgetPolicyState(
            slo_name="availability",
            remaining_budget_pct=42.0,
            tier=BudgetPolicyTier.CAUTION,
            action="Extra review",
        )
        assert state.slo_name == "availability"
        assert state.tier == BudgetPolicyTier.CAUTION
        assert state.incidents == []
        assert state.meta_slo_buffer_minutes is None
        assert state.recommendations == []

    def test_has_model_fields(self):
        fields = set(BudgetPolicyState.model_fields.keys())
        assert "slo_name" in fields
        assert "remaining_budget_pct" in fields
        assert "tier" in fields
        assert "meta_slo_buffer_valid" in fields


# ---------------------------------------------------------------------------
# portfolio_scorer models
# ---------------------------------------------------------------------------
class TestPortfolioHealthResultContract:
    def test_instantiates_with_defaults(self):
        result = PortfolioHealthResult()
        assert result.cxi is None
        assert result.sri is None
        assert result.cxi_journey_scores == {}
        assert result.used_default_centrality is True

    def test_has_model_fields(self):
        fields = set(PortfolioHealthResult.model_fields.keys())
        assert "cxi" in fields
        assert "sri" in fields
        assert "centrality_used" in fields
        assert "recommendations" in fields


class TestUncalibratedSLOFlagContract:
    def test_requires_all_core_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            UncalibratedSLOFlag()

    def test_instantiates_with_required_fields(self):
        flag = UncalibratedSLOFlag(
            service_name="api",
            declared_target=99.99,
            achieved_pct=99.0,
            nines_declared=4.0,
            nines_achieved=2.0,
            reason="sandbagged",
        )
        assert flag.service_name == "api"
        assert flag.nines_declared == 4.0

    def test_has_model_fields(self):
        fields = set(UncalibratedSLOFlag.model_fields.keys())
        assert "service_name" in fields
        assert "declared_target" in fields
        assert "reason" in fields


# ---------------------------------------------------------------------------
# tool_slo models
# ---------------------------------------------------------------------------
class TestRunOutcomeContract:
    def test_members(self):
        assert RunOutcome.SCORED.value == "scored"
        assert RunOutcome.VALID_REJECTION.value == "valid_rejection"
        assert RunOutcome.FAILED.value == "failed"


class TestFindingContract:
    def test_requires_id_and_severity(self):
        with pytest.raises((ValidationError, TypeError)):
            Finding()

    def test_instantiates_with_required_fields(self):
        finding = Finding(id="f-1", severity="high")
        assert finding.id == "f-1"
        assert finding.acknowledged is False
        assert finding.timestamp is None


class TestIncidentContract:
    def test_requires_id_severity_started_at(self):
        with pytest.raises((ValidationError, TypeError)):
            Incident()

    def test_instantiates_with_required_fields(self):
        incident = Incident(id="i-1", severity="sev1", started_at=_NOW)
        assert incident.id == "i-1"
        assert incident.ended_at is None


class TestRunRecordContract:
    def test_requires_submission_and_timestamps(self):
        with pytest.raises((ValidationError, TypeError)):
            RunRecord()

    def test_instantiates_with_required_fields(self):
        record = RunRecord(
            entities_submitted=10,
            run_started=_NOW,
            data_closed_at=_NOW,
            report_ready_at=_NOW,
        )
        assert record.entities_submitted == 10
        assert record.entities_scored == 0
        assert record.findings == []

    def test_accounting_properties(self):
        record = RunRecord(
            entities_submitted=10,
            entities_scored=5,
            valid_rejections=2,
            entities_failed=1,
            run_started=_NOW,
            data_closed_at=_NOW,
            report_ready_at=_NOW,
        )
        assert record.accounted == 8
        assert record.silent_drop == 2
        assert record.has_integrity_error is True

    def test_no_integrity_error_when_fully_accounted(self):
        record = RunRecord(
            entities_submitted=3,
            entities_scored=3,
            run_started=_NOW,
            data_closed_at=_NOW,
            report_ready_at=_NOW,
        )
        assert record.silent_drop == 0
        assert record.has_integrity_error is False


class TestSelfSLOResultContract:
    def test_requires_sli_name_and_target(self):
        with pytest.raises((ValidationError, TypeError)):
            SelfSLOResult()

    def test_instantiates_with_required_fields(self):
        result = SelfSLOResult(sli_name="scoring_coverage", target=0.99)
        assert result.sli_name == "scoring_coverage"
        assert result.value is None
        assert result.governance == "normal"
        assert result.insufficient_data is False

    def test_has_model_fields(self):
        fields = set(SelfSLOResult.model_fields.keys())
        assert "sli_name" in fields
        assert "target" in fields
        assert "governance" in fields
        assert "integrity_errors" in fields
