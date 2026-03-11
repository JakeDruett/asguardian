"""
Heimdall Security Compliance - OWASP/CWE Compliance Reporting

Maps Heimdall security findings to OWASP Top 10 (2021) and CWE Top 25 (2024)
categories and generates compliance grade reports.

Compliance grades per category:
  A: 0 findings
  B: 1-2 LOW findings only
  C: Any MEDIUM findings or 3+ LOW
  D: Any HIGH findings
  F: Any CRITICAL findings

Usage:
    from Asgard.Heimdall.Security.Compliance import ComplianceReporter

    reporter = ComplianceReporter()
    owasp_report = reporter.generate_owasp_report(security_report, hotspot_report)
    cwe_report = reporter.generate_cwe_report(security_report, hotspot_report)

    print(f"OWASP overall: {owasp_report.overall_grade}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Heimdall.Security.Compliance.models.compliance_models import (
    CWE_TOP_25_2024,
    CWEComplianceReport,
    CWEEntry,
    CategoryCompliance,
    ComplianceConfig,
    ComplianceGrade,
    OWASP_CATEGORY_NAMES,
    OWASPCategory,
    OWASPComplianceReport,
)
from Asgard.Heimdall.Security.Compliance.services.compliance_reporter import ComplianceReporter

__all__ = [
    "CWE_TOP_25_2024",
    "CWEComplianceReport",
    "CWEEntry",
    "CategoryCompliance",
    "ComplianceConfig",
    "ComplianceGrade",
    "ComplianceReporter",
    "OWASP_CATEGORY_NAMES",
    "OWASPCategory",
    "OWASPComplianceReport",
]
