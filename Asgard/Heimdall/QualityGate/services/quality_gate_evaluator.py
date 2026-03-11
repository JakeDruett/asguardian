"""
Heimdall Quality Gate Evaluator Service

Evaluates a QualityGate against a set of metric values extracted from
existing Heimdall analysis report objects.

The built-in "Asgard Way" gate provides a sensible default configuration
mirroring SonarQube's default quality gate behaviour.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union

from Asgard.Heimdall.QualityGate.models.quality_gate_models import (
    ConditionResult,
    GateCondition,
    GateOperator,
    GateStatus,
    MetricType,
    QualityGate,
    QualityGateResult,
)


def _build_asgard_way_gate() -> QualityGate:
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
        ],
    )


# Letter rating ordering for comparison (lower ordinal = better)
_RATING_ORDER = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}


def _compare_values(actual: Union[float, str], operator: GateOperator, threshold: Union[float, str]) -> bool:
    """
    Compare actual vs threshold using the given operator.

    Letter rating strings (A-E) are compared by their ordinal (A=1 best, E=5 worst).
    Numeric values are compared directly.
    """
    # Handle letter rating comparisons
    if isinstance(threshold, str) and threshold.upper() in _RATING_ORDER:
        actual_str = str(actual).upper() if actual is not None else "E"
        actual_ord = _RATING_ORDER.get(actual_str, 5)
        threshold_ord = _RATING_ORDER.get(threshold.upper(), 5)
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

    # Numeric comparison
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


class QualityGateEvaluator:
    """
    Evaluates a QualityGate against a dictionary of metric values or report objects.

    Usage:
        evaluator = QualityGateEvaluator()
        gate = evaluator.get_default_gate()

        # Evaluate from raw metrics
        result = evaluator.evaluate(gate, {
            MetricType.SECURITY_RATING: "A",
            MetricType.CRITICAL_VULNERABILITIES: 0,
            MetricType.COMMENT_DENSITY: 12.5,
        })
        print(f"Gate status: {result.status}")

        # Evaluate from reports
        result = evaluator.evaluate_from_reports(
            gate,
            ratings=project_ratings,
            documentation_report=doc_report,
            security_report=security_report,
        )
    """

    def get_default_gate(self) -> QualityGate:
        """
        Return the built-in 'Asgard Way' quality gate.

        Returns:
            QualityGate configured with the Asgard Way conditions
        """
        return _build_asgard_way_gate()

    def evaluate(
        self,
        gate: QualityGate,
        metrics_dict: Dict[MetricType, Union[float, str]],
        scan_path: str = "",
    ) -> QualityGateResult:
        """
        Evaluate a gate against a dictionary of raw metric values.

        Args:
            gate: The QualityGate to evaluate
            metrics_dict: Mapping from MetricType to its current value
            scan_path: Optional scan path string for the result metadata

        Returns:
            QualityGateResult with per-condition results and overall status
        """
        condition_results: List[ConditionResult] = []

        for condition in gate.conditions:
            metric_key = condition.metric
            if isinstance(metric_key, str):
                metric_key = MetricType(metric_key)

            actual_value = metrics_dict.get(metric_key)

            if actual_value is None:
                # Metric not provided - mark as not evaluated (pass with informational note)
                result = ConditionResult(
                    condition=condition,
                    actual_value=None,
                    passed=True,
                    message=f"Metric '{condition.metric}' not provided; condition skipped",
                )
            else:
                operator = condition.operator
                if isinstance(operator, str):
                    operator = GateOperator(operator)

                passed = _compare_values(actual_value, operator, condition.threshold)
                message = self._build_condition_message(condition, actual_value, passed)

                result = ConditionResult(
                    condition=condition,
                    actual_value=actual_value,
                    passed=passed,
                    message=message,
                )

            condition_results.append(result)

        # Derive overall gate status
        has_error_failure = any(
            not r.passed and r.condition.error_on_fail for r in condition_results
        )
        has_warning_failure = any(
            not r.passed and not r.condition.error_on_fail for r in condition_results
        )

        if has_error_failure:
            status = GateStatus.FAILED
        elif has_warning_failure:
            status = GateStatus.WARNING
        else:
            status = GateStatus.PASSED

        gate_result = QualityGateResult(
            gate_name=gate.name,
            status=status,
            condition_results=condition_results,
            scan_path=scan_path,
            evaluated_at=datetime.now(),
        )

        gate_result.summary = self._build_summary(gate_result)

        return gate_result

    def evaluate_from_reports(
        self,
        gate: QualityGate,
        *,
        ratings=None,
        duplication_result=None,
        documentation_report=None,
        security_report=None,
        debt_report=None,
        scan_path: str = "",
    ) -> QualityGateResult:
        """
        Evaluate a gate by extracting metrics from Heimdall report objects.

        Args:
            gate: The QualityGate to evaluate
            ratings: Optional ProjectRatings from RatingsCalculator
            duplication_result: Optional DuplicationResult from DuplicationDetector
            documentation_report: Optional DocumentationReport from DocumentationScanner
            security_report: Optional SecurityReport from StaticSecurityService
            debt_report: Optional DebtReport from TechnicalDebtAnalyzer
            scan_path: Optional scan path string for result metadata

        Returns:
            QualityGateResult with per-condition results and overall status
        """
        metrics: Dict[MetricType, Union[float, str]] = {}

        # Extract ratings
        if ratings is not None:
            maintainability = getattr(ratings, "maintainability", None)
            reliability = getattr(ratings, "reliability", None)
            security_dim = getattr(ratings, "security", None)

            if maintainability is not None:
                metrics[MetricType.MAINTAINABILITY_RATING] = str(
                    getattr(maintainability, "rating", "A")
                )
            if reliability is not None:
                metrics[MetricType.RELIABILITY_RATING] = str(
                    getattr(reliability, "rating", "A")
                )
            if security_dim is not None:
                metrics[MetricType.SECURITY_RATING] = str(
                    getattr(security_dim, "rating", "A")
                )

        # Extract duplication percentage
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

        # Extract documentation metrics
        if documentation_report is not None:
            comment_density = getattr(documentation_report, "overall_comment_density", None)
            api_coverage = getattr(documentation_report, "overall_api_coverage", None)
            if comment_density is not None:
                metrics[MetricType.COMMENT_DENSITY] = float(comment_density)
            if api_coverage is not None:
                metrics[MetricType.API_DOCUMENTATION_COVERAGE] = float(api_coverage)

        # Extract security metrics
        if security_report is not None:
            critical_count = 0
            high_count = 0

            # Try direct findings attribute
            for attr in ("vulnerability_findings", "vulnerabilities", "findings"):
                findings = getattr(security_report, attr, None) or []
                if findings:
                    for finding in findings:
                        sev = str(getattr(finding, "severity", "")).lower()
                        if sev == "critical":
                            critical_count += 1
                        elif sev == "high":
                            high_count += 1
                    break

            # Also try nested VulnerabilityReport
            vuln_report = getattr(security_report, "vulnerability_report", None)
            if vuln_report is not None:
                for attr in ("findings", "vulnerabilities"):
                    findings = getattr(vuln_report, attr, None) or []
                    if findings:
                        for finding in findings:
                            sev = str(getattr(finding, "severity", "")).lower()
                            if sev == "critical":
                                critical_count += 1
                            elif sev == "high":
                                high_count += 1
                        break

            metrics[MetricType.CRITICAL_VULNERABILITIES] = float(critical_count)
            metrics[MetricType.HIGH_VULNERABILITIES] = float(high_count)

        # Extract technical debt hours
        if debt_report is not None:
            debt_hours = getattr(debt_report, "total_debt_hours", None)
            if debt_hours is not None:
                metrics[MetricType.TECHNICAL_DEBT_HOURS] = float(debt_hours)

        return self.evaluate(gate, metrics, scan_path=scan_path)

    def _build_condition_message(
        self,
        condition: GateCondition,
        actual_value: Union[float, str],
        passed: bool,
    ) -> str:
        """Build a human-readable message for a condition result."""
        operator_display = {
            GateOperator.LESS_THAN: "<",
            GateOperator.LESS_THAN_OR_EQUAL: "<=",
            GateOperator.GREATER_THAN: ">",
            GateOperator.GREATER_THAN_OR_EQUAL: ">=",
            GateOperator.EQUALS: "==",
            GateOperator.NOT_EQUALS: "!=",
        }
        op = condition.operator
        if isinstance(op, str):
            op = GateOperator(op)
        op_str = operator_display.get(op, str(op))

        status = "PASS" if passed else "FAIL"
        return (
            f"[{status}] {condition.metric}: "
            f"{actual_value} {op_str} {condition.threshold}"
        )

    def _build_summary(self, result: QualityGateResult) -> str:
        """Build a summary string for the gate result."""
        total = len(result.condition_results)
        passed = result.passed_count
        errors = len(result.error_failures)
        warnings = len(result.warning_failures)

        if result.status == GateStatus.PASSED:
            return f"Gate '{result.gate_name}': PASSED ({passed}/{total} conditions met)"
        elif result.status == GateStatus.WARNING:
            return (
                f"Gate '{result.gate_name}': WARNING "
                f"({errors} error(s), {warnings} warning(s) out of {total} conditions)"
            )
        else:
            return (
                f"Gate '{result.gate_name}': FAILED "
                f"({errors} error failure(s), {warnings} warning(s) out of {total} conditions)"
            )
