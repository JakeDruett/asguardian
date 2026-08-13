"""
Asgard MCP Server - Tool Implementations

Implements the individual tool handler functions called by AsgardMCPServer.
Each function takes a params dict and an MCPServerConfig and returns a result dict.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, cast

from Asgard.Bragi.Dependencies.models.sbom_models import SBOMConfig, SBOMFormat
from Asgard.Bragi.Dependencies.services.sbom_generator import SBOMGenerator
from Asgard.Shared.Issues.models.issue_models import IssueFilter, IssueStatus
from Asgard.Shared.Issues.services.issue_tracker import IssueTracker
from Asgard.Bragi.Quality.models.analysis_models import AnalysisConfig
from Asgard.Bragi.Quality.models.debt_models import DebtConfig
from Asgard.Bragi.Quality.services.file_length_analyzer import FileAnalyzer
from Asgard.Bragi.Quality.services.technical_debt_analyzer import TechnicalDebtAnalyzer
from Asgard.Bragi.QualityGate.services.quality_gate_evaluator import QualityGateEvaluator
from Asgard.Bragi.Ratings.models.ratings_models import RatingsConfig
from Asgard.Bragi.Ratings.services.ratings_calculator import RatingsCalculator
from Asgard.Heimdall.Security.models.security_models import SecurityScanConfig
from Asgard.Heimdall.Security.services.static_security_service import StaticSecurityService
from Asgard.MCP.models.mcp_models import MCPServerConfig


def tool_quality_analyze(params: Dict[str, Any], config: MCPServerConfig) -> Dict[str, Any]:
    """Run quality analysis and return a summary."""
    path = params.get("path", config.project_path)
    scan_path = Path(path).resolve()

    analysis_config = AnalysisConfig(scan_path=scan_path)
    analyzer = FileAnalyzer(analysis_config)
    result = analyzer.analyze()

    top_violations = []
    for v in list(result.violations)[:10]:
        top_violations.append({
            "file": v.relative_path,
            "line_count": v.line_count,
            "lines_over": v.lines_over,
            "message": f"{v.line_count} lines (+{v.lines_over} over threshold {v.threshold})",
            "severity": str(v.severity),
        })

    return {
        "scan_path": str(scan_path),
        "analyzed_at": datetime.now().isoformat(),
        "total_files": result.total_files_scanned,
        "total_violations": len(result.violations),
        "violations_by_severity": result.get_violations_by_severity(),
        "top_violations": top_violations,
    }


def tool_security_scan(params: Dict[str, Any], config: MCPServerConfig) -> Dict[str, Any]:
    """Run security scan and return a summary."""
    path = params.get("path", config.project_path)
    scan_path = Path(path).resolve()

    scan_config = SecurityScanConfig(scan_path=scan_path)
    service = StaticSecurityService(scan_config)
    report = service.scan(str(scan_path))

    top_findings = []
    if report.vulnerability_report is not None:
        for f in report.vulnerability_report.findings:
            top_findings.append({
                "file": f.file_path,
                "line": f.line_number,
                "title": f.title,
                "severity": str(f.severity),
                "type": str(f.vulnerability_type),
            })
    if report.secrets_report is not None:
        for s in report.secrets_report.findings:
            top_findings.append({
                "file": s.file_path,
                "line": s.line_number,
                "title": f"Secret detected: {s.pattern_name}",
                "severity": str(s.severity),
                "type": str(s.secret_type),
            })
    top_findings = top_findings[:10]

    return {
        "scan_path": str(scan_path),
        "scanned_at": datetime.now().isoformat(),
        "security_score": report.security_score,
        "total_findings": report.total_issues,
        "findings_by_severity": {
            "critical": report.critical_issues,
            "high": report.high_issues,
            "medium": report.medium_issues,
            "low": report.low_issues,
        },
        "top_findings": top_findings,
    }


def tool_quality_gate(params: Dict[str, Any], config: MCPServerConfig) -> Dict[str, Any]:
    """Evaluate the quality gate and return gate status."""
    path = params.get("path", config.project_path)
    scan_path = Path(path).resolve()

    debt_config = DebtConfig(scan_path=scan_path)
    debt_analyzer = TechnicalDebtAnalyzer(debt_config)
    debt_report = debt_analyzer.analyze(scan_path)

    sec_config = SecurityScanConfig(scan_path=scan_path)
    sec_service = StaticSecurityService(sec_config)
    security_report = sec_service.scan(str(scan_path))

    ratings_config = RatingsConfig(scan_path=scan_path)
    calculator = RatingsCalculator(ratings_config)
    ratings = calculator.calculate_from_reports(
        scan_path=str(scan_path),
        debt_report=debt_report,
        security_report=security_report,
    )

    evaluator = QualityGateEvaluator()
    gate = evaluator.get_default_gate()
    gate_result = evaluator.evaluate_from_reports(
        gate,
        ratings=ratings,
        security_report=security_report,
    )

    conditions = []
    for cr in gate_result.condition_results:
        if cr.passed is True:
            condition_status = "passed"
        elif cr.passed is False:
            condition_status = "failed"
        else:
            condition_status = "not_evaluated"
        conditions.append({
            "metric": str(cr.condition.metric),
            "status": condition_status,
            "actual_value": cr.actual_value,
            "threshold": cr.condition.threshold,
        })

    status = str(gate_result.status)
    return {
        "scan_path": str(scan_path),
        "gate_name": gate_result.gate_name,
        "status": status,
        "passed": status == "passed",
        "conditions": conditions,
        "evaluated_at": datetime.now().isoformat(),
    }


def tool_ratings(params: Dict[str, Any], config: MCPServerConfig) -> Dict[str, Any]:
    """Calculate A-E ratings and return the result."""
    path = params.get("path", config.project_path)
    scan_path = Path(path).resolve()

    debt_config = DebtConfig(scan_path=scan_path)
    debt_analyzer = TechnicalDebtAnalyzer(debt_config)
    debt_report = debt_analyzer.analyze(scan_path)

    sec_config = SecurityScanConfig(scan_path=scan_path)
    sec_service = StaticSecurityService(sec_config)
    security_report = sec_service.scan(str(scan_path))

    ratings_config = RatingsConfig(scan_path=scan_path)
    calculator = RatingsCalculator(ratings_config)
    ratings = calculator.calculate_from_reports(
        scan_path=str(scan_path),
        debt_report=debt_report,
        security_report=security_report,
    )

    return {
        "scan_path": str(scan_path),
        "overall_rating": getattr(ratings, "overall_rating", ""),
        "maintainability": {
            "rating": getattr(ratings.maintainability, "rating", ""),
            "score": getattr(ratings.maintainability, "score", 0),
            "rationale": getattr(ratings.maintainability, "rationale", ""),
        },
        "reliability": {
            "rating": getattr(ratings.reliability, "rating", ""),
            "score": getattr(ratings.reliability, "score", 0),
            "rationale": getattr(ratings.reliability, "rationale", ""),
        },
        "security": {
            "rating": getattr(ratings.security, "rating", ""),
            "score": getattr(ratings.security, "score", 0),
            "rationale": getattr(ratings.security, "rationale", ""),
        },
        "calculated_at": datetime.now().isoformat(),
    }


def tool_sbom(params: Dict[str, Any], config: MCPServerConfig) -> Dict[str, Any]:
    """Generate an SBOM and return the document."""
    path = params.get("path", config.project_path)
    fmt_str = params.get("format", "cyclonedx")
    scan_path = Path(path).resolve()

    fmt = SBOMFormat.CYCLONEDX if fmt_str == "cyclonedx" else SBOMFormat.SPDX
    sbom_config = SBOMConfig(scan_path=scan_path, output_format=fmt)
    generator = SBOMGenerator(sbom_config)
    document = generator.generate(str(scan_path))

    if fmt == SBOMFormat.CYCLONEDX:
        return cast(Dict[str, Any], generator.to_cyclonedx_json(document))
    return cast(Dict[str, Any], generator.to_spdx_json(document))


def tool_list_issues(params: Dict[str, Any], config: MCPServerConfig) -> Dict[str, Any]:
    """List tracked issues for a project."""
    path = params.get("path", config.project_path)
    status_str = params.get("status", "open")
    limit = int(params.get("limit", 20))
    scan_path = str(Path(path).resolve())

    try:
        status = IssueStatus(status_str)
    except ValueError:
        status = IssueStatus.OPEN

    tracker = IssueTracker()
    issue_filter = IssueFilter(status=[status])
    issues = tracker.get_issues(scan_path, issue_filter)

    issue_list = []
    for issue in issues[:limit]:
        issue_list.append({
            "issue_id": str(getattr(issue, "issue_id", "")),
            "rule_id": getattr(issue, "rule_id", ""),
            "file_path": getattr(issue, "file_path", ""),
            "line_number": getattr(issue, "line_number", 0),
            "severity": str(getattr(issue, "severity", "")),
            "status": str(getattr(issue, "status", "")),
            "title": getattr(issue, "title", ""),
            "created_at": str(getattr(issue, "created_at", "")),
        })

    return {
        "project_path": scan_path,
        "status_filter": status_str,
        "total_returned": len(issue_list),
        "issues": issue_list,
    }


def _extract_owasp_compliance(security_report: Any) -> Optional[Dict[str, Any]]:
    """
    Extract OWASP Top 10 compliance data from a security report.

    Returns a dict with 'categories' and 'overall_grade' keys, or None if the
    report does not contain OWASP compliance data.
    """
    if not hasattr(security_report, "owasp_compliance"):
        return None
    owasp = security_report.owasp_compliance
    categories: Dict[str, Any] = {}
    if hasattr(owasp, "categories"):
        for cat in owasp.categories:
            categories[str(getattr(cat, "category_id", ""))] = {
                "name": getattr(cat, "name", ""),
                "grade": str(getattr(cat, "grade", "")),
                "finding_count": getattr(cat, "finding_count", 0),
            }
    return {
        "owasp_top10": categories,
        "overall_grade": str(getattr(owasp, "overall_grade", "")),
    }


def _extract_cwe_compliance(security_report: Any) -> Optional[Dict[str, Any]]:
    """
    Extract CWE Top 25 compliance data from a security report.

    Returns a dict with 'categories' and 'overall_grade' keys, or None if the
    report does not contain CWE compliance data.
    """
    if not hasattr(security_report, "cwe_compliance"):
        return None
    cwe = security_report.cwe_compliance
    categories: Dict[str, Any] = {}
    if hasattr(cwe, "categories"):
        for cat in cwe.categories:
            categories[str(getattr(cat, "cwe_id", ""))] = {
                "name": getattr(cat, "name", ""),
                "grade": str(getattr(cat, "grade", "")),
                "finding_count": getattr(cat, "finding_count", 0),
            }
    return {
        "cwe_top25": categories,
        "overall_grade": str(getattr(cwe, "overall_grade", "")),
    }


# Registry mapping compliance standard names to their extractor functions.
# To support a new standard (e.g. PCI-DSS), register a new extractor here
# without modifying tool_compliance_report (OCP).
_COMPLIANCE_EXTRACTORS: Dict[str, Callable[[Any], Optional[Dict[str, Any]]]] = {
    "owasp": _extract_owasp_compliance,
    "cwe": _extract_cwe_compliance,
}


def tool_compliance_report(params: Dict[str, Any], config: MCPServerConfig) -> Dict[str, Any]:
    """Generate a compliance report for a registered standard (e.g. owasp, cwe)."""
    path = params.get("path", config.project_path)
    standard = params.get("standard", "owasp")
    scan_path = Path(path).resolve()

    scan_config = SecurityScanConfig(scan_path=scan_path)
    service = StaticSecurityService(scan_config)
    security_report = service.scan(str(scan_path))

    compliance_data: Dict[str, Any] = {
        "scan_path": str(scan_path),
        "standard": standard,
        "generated_at": datetime.now().isoformat(),
    }

    extractor = _COMPLIANCE_EXTRACTORS.get(standard)
    if extractor is not None:
        extracted = extractor(security_report)
        if extracted is not None:
            compliance_data.update(extracted)
            return compliance_data

    compliance_data["note"] = (
        f"Compliance data for standard '{standard}' is not available in this scan result. "
        "Run 'heimdall security compliance' for a full report."
    )
    compliance_data["total_findings"] = getattr(security_report, "total_findings", 0)
    return compliance_data
