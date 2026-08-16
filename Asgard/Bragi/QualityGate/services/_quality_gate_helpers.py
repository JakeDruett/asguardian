"""
Heimdall Quality Gate - helper functions and default gate definition.

Standalone utilities for gate evaluation: value comparison, default gate
construction, metric extraction from report objects.
"""

from typing import Dict, List, Optional, Union

from Asgard.Bragi.QualityGate.models.quality_gate_models import (
    METRIC_DETERMINISM,
    GateCondition,
    GateOperator,
    MetricDeterminism,
    MetricType,
    OnMissing,
    QualityGate,
)


# Letter rating ordering for comparison (lower ordinal = better).
# Unmeasured "N/A" is omitted from extract, never ranked as A.
RATING_ORDER = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
_UNMEASURED_RATINGS = frozenset({"N/A", "NA", "n/a"})
_NOT_MEASURED = frozenset({"not_measured", "MeasurementConfidence.NOT_MEASURED"})


def build_asgard_way_gate() -> QualityGate:
    """Build and return the built-in 'Asgard Way' quality gate."""
    return QualityGate(
        name="Asgard Way",
        description=(
            "Default quality gate inspired by SonarQube's recommended gate. "
            "Hard-fails on critical security/reliability/maintainability thresholds; "
            "warns on documentation and duplication."
        ),
        conditions=[
            GateCondition(
                metric=MetricType.SECURITY_RATING,
                operator=GateOperator.LESS_THAN_OR_EQUAL,
                threshold="B",
                error_on_fail=True,
                description="Security rating must be B or better",
            ),
            GateCondition(
                metric=MetricType.RELIABILITY_RATING,
                operator=GateOperator.LESS_THAN_OR_EQUAL,
                threshold="C",
                error_on_fail=True,
                description="Reliability rating must be C or better",
            ),
            GateCondition(
                metric=MetricType.MAINTAINABILITY_RATING,
                operator=GateOperator.LESS_THAN_OR_EQUAL,
                threshold="C",
                error_on_fail=True,
                description="Maintainability rating must be C or better",
            ),
            GateCondition(
                metric=MetricType.DUPLICATION_PERCENTAGE,
                operator=GateOperator.LESS_THAN_OR_EQUAL,
                threshold=3.0,
                error_on_fail=False,
                description="Code duplication should be 3% or less",
            ),
            GateCondition(
                metric=MetricType.COMMENT_DENSITY,
                operator=GateOperator.GREATER_THAN_OR_EQUAL,
                threshold=10.0,
                error_on_fail=False,
                description="Comment density should be 10% or more",
            ),
            GateCondition(
                metric=MetricType.API_DOCUMENTATION_COVERAGE,
                operator=GateOperator.GREATER_THAN_OR_EQUAL,
                threshold=70.0,
                error_on_fail=False,
                description="Public API documentation coverage should be 70% or more",
            ),
            GateCondition(
                metric=MetricType.CRITICAL_VULNERABILITIES,
                operator=GateOperator.EQUALS,
                threshold=0.0,
                error_on_fail=True,
                description="No critical security vulnerabilities are permitted",
            ),
            GateCondition(
                metric=MetricType.SECURITY_SCORE,
                operator=GateOperator.GREATER_THAN_OR_EQUAL,
                threshold=40.0,
                error_on_fail=False,
                on_missing=OnMissing.SKIP,
                description=(
                    "Multiplicative-decay security score should be 40 or "
                    "better (a single CRITICAL scores exactly 40; below "
                    "that means multiple criticals or heavy high-severity "
                    "load). Warn-only: the score is HEURISTIC-class."
                ),
            ),
            # Tier-2 (asgard-main) conditions — evaluated when the async
            # project-wide tier supplies them; skipped by explicit policy
            # otherwise (Plan Bragi-06 §3.3).
            GateCondition(
                metric=MetricType.COMPOSITE_SCORE,
                operator=GateOperator.GREATER_THAN_OR_EQUAL,
                threshold=0.60,
                error_on_fail=False,
                on_missing=OnMissing.SKIP,
                description="Project composite score should be C (0.60) or better",
            ),
            GateCondition(
                metric=MetricType.RISK_PROFILE_E_LOC_PCT,
                operator=GateOperator.EQUALS,
                threshold=0.0,
                error_on_fail=False,
                on_missing=OnMissing.SKIP,
                description="No LOC should sit in E-grade (worst risk) files",
            ),
            GateCondition(
                metric=MetricType.DEPENDENCY_CYCLES,
                operator=GateOperator.EQUALS,
                threshold=0.0,
                error_on_fail=False,
                on_missing=OnMissing.SKIP,
                description="The import graph should be free of dependency cycles",
            ),
            GateCondition(
                metric=MetricType.PROHIBITED_LICENSE_COUNT,
                operator=GateOperator.EQUALS,
                threshold=0.0,
                error_on_fail=True,
                on_missing=OnMissing.SKIP,
                description="No dependency may carry a prohibited license",
            ),
        ],
    )


def build_asgard_main_gate() -> QualityGate:
    """
    Tier-2 gate (merge-to-main / nightly): absolute project conditions plus
    composite score, risk profile, dependency cycles, and license compliance
    (skipped by policy when the async tier has not supplied them).

    Alias target of the historical 'Asgard Way' gate.
    """
    return build_asgard_way_gate()


def build_asgard_pr_gate() -> QualityGate:
    """
    Tier-1 blocking PR gate: new-code conditions on FACT-class metrics only.

    Designed to be evaluated over new/changed code; used alongside the
    fingerprint-based differential engine. Every condition requires its
    metric to be present (on_missing=fail): a skipped scan fails, it does
    not silently pass.
    """
    return QualityGate(
        name="asgard-pr",
        description=(
            "Tier-1 blocking PR gate: fails only when NEW technical debt or "
            "NEW high-severity findings are introduced. Deterministic "
            "(FACT-class) metrics only."
        ),
        conditions=[
            GateCondition(
                metric=MetricType.NEW_BLOCKER_ISSUES,
                operator=GateOperator.EQUALS,
                threshold=0.0,
                error_on_fail=True,
                on_missing=OnMissing.FAIL,
                description="No new blocker (HIGH/CRITICAL) issues in new code",
            ),
            GateCondition(
                metric=MetricType.SCAN_COMPLETENESS,
                operator=GateOperator.GREATER_THAN_OR_EQUAL,
                threshold=1.0,
                error_on_fail=True,
                on_missing=OnMissing.FAIL,
                description="All expected scan inputs must be present",
            ),
            GateCondition(
                metric=MetricType.DEBT_DELTA_MINUTES,
                operator=GateOperator.LESS_THAN_OR_EQUAL,
                threshold=0.0,
                error_on_fail=False,
                on_missing=OnMissing.WARN,
                description="Waterline ratchet: technical debt may only improve",
            ),
        ],
    )


def validate_gate_determinism(gate: QualityGate) -> List[str]:
    """
    Warn when a hard-blocking condition is attached to a HEURISTIC metric
    (DEEPTHINK_02: blocking gates demand ~99% precision — deterministic,
    mechanically verifiable conditions only).

    Returns a list of human-readable warnings (empty when clean).
    """
    warnings: List[str] = []
    for condition in gate.conditions:
        metric = condition.metric
        if isinstance(metric, str):
            metric = MetricType(metric)
        determinism = METRIC_DETERMINISM.get(metric, MetricDeterminism.HEURISTIC)
        if condition.error_on_fail and determinism == MetricDeterminism.HEURISTIC:
            warnings.append(
                f"Condition on '{metric.value}' is hard-blocking "
                f"(error_on_fail=True) but the metric is HEURISTIC; "
                "heuristic metrics should warn, not block."
            )
    return warnings


def compare_values(
    actual: Union[float, str],
    operator: GateOperator,
    threshold: Union[float, str],
) -> bool:
    """
    Compare actual vs threshold using the given operator.

    Letter rating strings (A-E) are compared by their ordinal (A=1 best, E=5 worst).
    Numeric values are compared directly.
    """
    if isinstance(threshold, str) and threshold.upper() in RATING_ORDER:
        actual_str = str(actual).upper() if actual is not None else "E"
        if actual_str in _UNMEASURED_RATINGS:
            actual_str = "E"
        actual_ord = RATING_ORDER.get(actual_str, 5)
        threshold_ord = RATING_ORDER.get(threshold.upper(), 5)
        if operator == GateOperator.LESS_THAN:
            return actual_ord < threshold_ord
        elif operator == GateOperator.LESS_THAN_OR_EQUAL:
            return actual_ord <= threshold_ord
        elif operator == GateOperator.GREATER_THAN:
            return actual_ord > threshold_ord
        elif operator == GateOperator.GREATER_THAN_OR_EQUAL:
            return actual_ord >= threshold_ord
        elif operator == GateOperator.EQUALS:
            return actual_ord == threshold_ord
        elif operator == GateOperator.NOT_EQUALS:
            return actual_ord != threshold_ord
        return False

    try:
        actual_num = float(actual) if actual is not None else 0.0
        threshold_num = float(threshold)
    except (TypeError, ValueError):
        return False

    if operator == GateOperator.LESS_THAN:
        return actual_num < threshold_num
    elif operator == GateOperator.LESS_THAN_OR_EQUAL:
        return actual_num <= threshold_num
    elif operator == GateOperator.GREATER_THAN:
        return actual_num > threshold_num
    elif operator == GateOperator.GREATER_THAN_OR_EQUAL:
        return actual_num >= threshold_num
    elif operator == GateOperator.EQUALS:
        return actual_num == threshold_num
    elif operator == GateOperator.NOT_EQUALS:
        return actual_num != threshold_num
    return False


def _finding_severity(finding) -> str:
    """Normalize a finding severity label (enum or string)."""
    sev = getattr(finding, "severity", None)
    if sev is None:
        return ""
    text = sev.value if hasattr(sev, "value") else sev
    return str(text).lower()


def _measured_letter_rating(dimension) -> Optional[str]:
    """
    Return an A-E letter only when the dimension was actually measured.

    Unmeasured/N/A ratings are omitted so the gate condition stays
    NOT_EVALUATED instead of silently passing as A.
    """
    if dimension is None:
        return None
    rating = getattr(dimension, "rating", None)
    if rating is None:
        return None
    text = str(rating.value if hasattr(rating, "value") else rating)
    if text.upper() in _UNMEASURED_RATINGS:
        return None
    confidence = getattr(dimension, "confidence", None)
    if confidence is not None and str(
        confidence.value if hasattr(confidence, "value") else confidence
    ) in _NOT_MEASURED:
        return None
    return text


def extract_metrics_from_reports(
    ratings=None,
    duplication_result=None,
    documentation_report=None,
    security_report=None,
    debt_report=None,
) -> Dict[MetricType, Union[float, str]]:
    """
    Extract metric values from Heimdall report objects.

    Returns a dict mapping MetricType to its current value.
    """
    metrics: Dict[MetricType, Union[float, str]] = {}

    if ratings is not None:
        maintainability = getattr(ratings, "maintainability", None)
        reliability = getattr(ratings, "reliability", None)
        security_dim = getattr(ratings, "security", None)

        maintainability_letter = _measured_letter_rating(maintainability)
        if maintainability_letter is not None:
            metrics[MetricType.MAINTAINABILITY_RATING] = maintainability_letter
        reliability_letter = _measured_letter_rating(reliability)
        if reliability_letter is not None:
            metrics[MetricType.RELIABILITY_RATING] = reliability_letter
        security_letter = _measured_letter_rating(security_dim)
        if security_letter is not None:
            metrics[MetricType.SECURITY_RATING] = security_letter

    if duplication_result is not None:
        dup_pct = getattr(duplication_result, "duplication_percentage", None)
        if dup_pct is None:
            total_lines = getattr(duplication_result, "total_lines", 0) or 0
            duplicated_lines = getattr(duplication_result, "total_duplicated_lines", 0) or 0
            if total_lines > 0:
                dup_pct = (duplicated_lines / total_lines) * 100.0
            else:
                dup_pct = 0.0
        metrics[MetricType.DUPLICATION_PERCENTAGE] = float(dup_pct)

    if documentation_report is not None:
        comment_density = getattr(documentation_report, "overall_comment_density", None)
        api_coverage = getattr(documentation_report, "overall_api_coverage", None)
        if comment_density is not None:
            metrics[MetricType.COMMENT_DENSITY] = float(comment_density)
        if api_coverage is not None:
            metrics[MetricType.API_DOCUMENTATION_COVERAGE] = float(api_coverage)

    if security_report is not None:
        critical_count = 0
        high_count = 0

        for attr in ("vulnerability_findings", "vulnerabilities", "findings"):
            findings = getattr(security_report, attr, None) or []
            if findings:
                for finding in findings:
                    sev = _finding_severity(finding)
                    if sev in ("critical", "blocker"):
                        critical_count += 1
                    elif sev == "high":
                        high_count += 1
                break

        vuln_report = getattr(security_report, "vulnerability_report", None)
        if vuln_report is not None:
            for attr in ("findings", "vulnerabilities"):
                findings = getattr(vuln_report, attr, None) or []
                if findings:
                    for finding in findings:
                        sev = _finding_severity(finding)
                        if sev in ("critical", "blocker"):
                            critical_count += 1
                        elif sev == "high":
                            high_count += 1
                    break

        metrics[MetricType.CRITICAL_VULNERABILITIES] = float(critical_count)
        metrics[MetricType.HIGH_VULNERABILITIES] = float(high_count)

        # Multiplicative-decay security score (Plan Heimdall-06 §A). Only
        # supplied when the report actually carries it — a missing score
        # is honestly NOT_EVALUATED/SKIP, never assumed clean.
        security_score = getattr(security_report, "security_score", None)
        if security_score is not None:
            metrics[MetricType.SECURITY_SCORE] = float(security_score)

    if debt_report is not None:
        debt_hours = getattr(debt_report, "total_debt_hours", None)
        if debt_hours is not None:
            metrics[MetricType.TECHNICAL_DEBT_HOURS] = float(debt_hours)

    return metrics
