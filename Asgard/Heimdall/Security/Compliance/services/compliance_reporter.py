"""
Heimdall Compliance Reporter Service

Maps Heimdall security findings from existing SecurityReport, VulnerabilityReport,
SecretsReport, CryptoReport, and DependencyReport objects to OWASP Top 10 (2021)
and CWE Top 25 (2024) categories and produces compliance grade reports.

Compliance grades per category:
  A: 0 findings
  B: 1-2 LOW findings only
  C: Any MEDIUM findings or 3+ LOW
  D: Any HIGH findings
  F: Any CRITICAL findings

Mapping logic:
  sql_injection            -> A03, CWE-89
  command_injection        -> A03, CWE-78, CWE-77
  xss                      -> A03, CWE-79
  path_traversal           -> A01, CWE-22
  insecure_crypto / crypto -> A02, CWE-327
  hardcoded_secret         -> A02, CWE-798
  insecure_deserialization -> A08, CWE-502
  ssrf                     -> A10, CWE-918
  missing_auth             -> A07, CWE-306
  dependency vulnerabilities (critical/high) -> A06
  cookie/session issues    -> A07, CWE-287
  weak_random              -> A02, CWE-338
  template_injection       -> A03, CWE-94
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from Asgard.Heimdall.Security.Compliance.models.compliance_models import (
    CategoryCompliance,
    ComplianceConfig,
    ComplianceGrade,
    CWE_TOP_25_2024,
    CWEComplianceReport,
    OWASPComplianceReport,
    OWASP_CATEGORY_NAMES,
)

# Mapping from Heimdall vulnerability type string to OWASP categories and CWE IDs
_VULN_TO_OWASP: Dict[str, List[str]] = {
    "sql_injection": ["A03"],
    "command_injection": ["A03"],
    "xss": ["A03"],
    "path_traversal": ["A01"],
    "insecure_crypto": ["A02"],
    "insecure_deserialization": ["A08"],
    "ssrf": ["A10"],
    "missing_auth": ["A07"],
    "hardcoded_secret": ["A02"],
    "insecure_random": ["A02"],
    "weak_hash": ["A02"],
    "open_redirect": ["A01"],
    "improper_input_validation": ["A03"],
    "template_injection": ["A03"],
}

_VULN_TO_CWE: Dict[str, List[str]] = {
    "sql_injection": ["CWE-89"],
    "command_injection": ["CWE-78", "CWE-77"],
    "xss": ["CWE-79"],
    "path_traversal": ["CWE-22"],
    "insecure_crypto": ["CWE-327"],
    "insecure_deserialization": ["CWE-502"],
    "ssrf": ["CWE-918"],
    "missing_auth": ["CWE-306"],
    "hardcoded_secret": ["CWE-798"],
    "insecure_random": ["CWE-338"],
    "weak_hash": ["CWE-327"],
    "open_redirect": ["CWE-601"],
    "improper_input_validation": ["CWE-20"],
    "template_injection": ["CWE-94"],
}

# Hotspot category mappings
_HOTSPOT_TO_OWASP: Dict[str, List[str]] = {
    "cookie_config": ["A07"],
    "crypto_usage": ["A02"],
    "dynamic_execution": ["A03"],
    "regex_dos": ["A04"],
    "xxe": ["A05"],
    "insecure_deserialization": ["A08"],
    "ssrf": ["A10"],
    "insecure_random": ["A02"],
    "permission_check": ["A01"],
    "tls_verification": ["A02"],
}

_HOTSPOT_TO_CWE: Dict[str, List[str]] = {
    "cookie_config": ["CWE-287"],
    "crypto_usage": ["CWE-327"],
    "dynamic_execution": ["CWE-94"],
    "regex_dos": [],
    "xxe": [],
    "insecure_deserialization": ["CWE-502"],
    "ssrf": ["CWE-918"],
    "insecure_random": ["CWE-338"],
    "permission_check": ["CWE-269"],
    "tls_verification": [],
}

# Severity ordering for grade calculation
_SEVERITY_ORDER = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}


def _compute_grade(category: CategoryCompliance) -> ComplianceGrade:
    """Compute the compliance grade for a category based on its finding counts."""
    if category.critical_count > 0:
        return ComplianceGrade.F
    elif category.high_count > 0:
        return ComplianceGrade.D
    elif category.medium_count > 0:
        return ComplianceGrade.C
    elif category.low_count > 2:
        return ComplianceGrade.C
    elif category.low_count > 0:
        return ComplianceGrade.B
    else:
        return ComplianceGrade.A


def _worst_grade(grades: List[ComplianceGrade]) -> ComplianceGrade:
    """Return the worst (lowest) compliance grade from a list."""
    order = {
        ComplianceGrade.A: 1,
        ComplianceGrade.B: 2,
        ComplianceGrade.C: 3,
        ComplianceGrade.D: 4,
        ComplianceGrade.F: 5,
    }
    if not grades:
        return ComplianceGrade.A
    return max(grades, key=lambda g: order.get(g, 1))


def _get_finding_severity(finding) -> str:
    """Extract the normalized severity string from a finding object."""
    sev = getattr(finding, "severity", None)
    if sev is None:
        return "low"
    return str(sev).lower()


def _get_finding_description(finding) -> str:
    """Build a short description string for a finding."""
    title = getattr(finding, "title", None) or getattr(finding, "description", None) or ""
    file_path = getattr(finding, "file_path", "")
    line_number = getattr(finding, "line_number", "")
    if file_path and line_number:
        return f"{title} ({file_path}:{line_number})"
    return title


class ComplianceReporter:
    """
    Maps Heimdall security findings to OWASP Top 10 and CWE Top 25 categories
    and generates compliance grade reports.

    Usage:
        reporter = ComplianceReporter()

        owasp_report = reporter.generate_owasp_report(security_report, hotspot_report)
        cwe_report = reporter.generate_cwe_report(security_report, hotspot_report)

        print(f"OWASP overall grade: {owasp_report.overall_grade}")
        for cat_id, cat in owasp_report.categories.items():
            print(f"  {cat_id} {cat.category_name}: {cat.grade}")
    """

    def __init__(self, config: Optional[ComplianceConfig] = None):
        """
        Initialize the compliance reporter.

        Args:
            config: Configuration for compliance reporting. If None, uses defaults.
        """
        self.config = config or ComplianceConfig()

    def generate_owasp_report(
        self, security_report=None, hotspot_report=None, scan_path: str = ""
    ) -> OWASPComplianceReport:
        """
        Generate an OWASP Top 10 2021 compliance report.

        Args:
            security_report: Optional SecurityReport from StaticSecurityService
            hotspot_report: Optional HotspotReport from HotspotDetector
            scan_path: Optional scan path for metadata

        Returns:
            OWASPComplianceReport with per-category compliance grades
        """
        # Initialise all OWASP categories with grade A
        categories: Dict[str, CategoryCompliance] = {
            cat_id: CategoryCompliance(
                category_id=cat_id,
                category_name=name,
                grade=ComplianceGrade.A,
            )
            for cat_id, name in OWASP_CATEGORY_NAMES.items()
        }

        total_mapped = 0

        # Map vulnerability findings
        if security_report is not None:
            total_mapped += self._map_vulnerabilities_to_owasp(security_report, categories)
            total_mapped += self._map_secrets_to_owasp(security_report, categories)
            total_mapped += self._map_crypto_to_owasp(security_report, categories)
            total_mapped += self._map_dependencies_to_owasp(security_report, categories)

        # Map hotspot findings
        if hotspot_report is not None:
            total_mapped += self._map_hotspots_to_owasp(hotspot_report, categories)

        # Compute grades
        for cat in categories.values():
            cat.grade = _compute_grade(cat)

        overall = _worst_grade([cat.grade for cat in categories.values()])

        return OWASPComplianceReport(
            owasp_version=self.config.owasp_version,
            categories=categories,
            overall_grade=overall,
            total_findings_mapped=total_mapped,
            scan_path=scan_path,
            generated_at=datetime.now(),
        )

    def generate_cwe_report(
        self, security_report=None, hotspot_report=None, scan_path: str = ""
    ) -> CWEComplianceReport:
        """
        Generate a CWE Top 25 2024 compliance report.

        Args:
            security_report: Optional SecurityReport from StaticSecurityService
            hotspot_report: Optional HotspotReport from HotspotDetector
            scan_path: Optional scan path for metadata

        Returns:
            CWEComplianceReport with per-CWE compliance entries
        """
        # Initialise all CWE Top 25 entries with grade A
        top_25: Dict[str, CategoryCompliance] = {
            cwe_id: CategoryCompliance(
                category_id=cwe_id,
                category_name=name,
                grade=ComplianceGrade.A,
            )
            for cwe_id, name in CWE_TOP_25_2024.items()
        }

        # Map vulnerability findings
        if security_report is not None:
            self._map_vulnerabilities_to_cwe(security_report, top_25)
            self._map_secrets_to_cwe(security_report, top_25)
            self._map_crypto_to_cwe(security_report, top_25)

        # Map hotspot findings
        if hotspot_report is not None:
            self._map_hotspots_to_cwe(hotspot_report, top_25)

        # Compute grades
        for entry in top_25.values():
            entry.grade = _compute_grade(entry)

        overall = _worst_grade([entry.grade for entry in top_25.values()])

        return CWEComplianceReport(
            cwe_version=self.config.cwe_version,
            top_25_coverage=top_25,
            overall_grade=overall,
            scan_path=scan_path,
            generated_at=datetime.now(),
        )

    # -----------------------------------------------------------------------
    # Private mapping helpers - OWASP
    # -----------------------------------------------------------------------

    def _map_vulnerabilities_to_owasp(
        self, security_report, categories: Dict[str, CategoryCompliance]
    ) -> int:
        """Map vulnerability findings from a SecurityReport to OWASP categories."""
        count = 0
        findings = self._extract_vulnerability_findings(security_report)
        for finding in findings:
            vuln_type = str(getattr(finding, "vulnerability_type", "") or "").lower()
            owasp_cats = _VULN_TO_OWASP.get(vuln_type, [])
            severity = _get_finding_severity(finding)
            desc = _get_finding_description(finding)
            for cat_id in owasp_cats:
                if cat_id in categories:
                    self._add_finding_to_category(categories[cat_id], severity, desc)
                    count += 1
        return count

    def _map_secrets_to_owasp(
        self, security_report, categories: Dict[str, CategoryCompliance]
    ) -> int:
        """Map secret findings to A02."""
        count = 0
        secrets = self._extract_secrets(security_report)
        for finding in secrets:
            severity = _get_finding_severity(finding)
            desc = _get_finding_description(finding)
            if "A02" in categories:
                self._add_finding_to_category(categories["A02"], severity, desc)
                count += 1
        return count

    def _map_crypto_to_owasp(
        self, security_report, categories: Dict[str, CategoryCompliance]
    ) -> int:
        """Map crypto findings to A02."""
        count = 0
        crypto_findings = self._extract_crypto_findings(security_report)
        for finding in crypto_findings:
            severity = _get_finding_severity(finding)
            desc = _get_finding_description(finding)
            if "A02" in categories:
                self._add_finding_to_category(categories["A02"], severity, desc)
                count += 1
        return count

    def _map_dependencies_to_owasp(
        self, security_report, categories: Dict[str, CategoryCompliance]
    ) -> int:
        """Map high/critical dependency vulnerabilities to A06."""
        count = 0
        dep_findings = self._extract_dependency_findings(security_report)
        for finding in dep_findings:
            severity = _get_finding_severity(finding)
            if severity in ("critical", "high"):
                desc = _get_finding_description(finding)
                if "A06" in categories:
                    self._add_finding_to_category(categories["A06"], severity, desc)
                    count += 1
        return count

    def _map_hotspots_to_owasp(
        self, hotspot_report, categories: Dict[str, CategoryCompliance]
    ) -> int:
        """Map hotspot findings to OWASP categories."""
        count = 0
        hotspots = getattr(hotspot_report, "hotspots", []) or []
        for hotspot in hotspots:
            cat_str = str(getattr(hotspot, "category", "") or "").lower()
            owasp_cats = _HOTSPOT_TO_OWASP.get(cat_str, [])
            # Hotspots contribute LOW severity unless their priority is HIGH
            priority = str(getattr(hotspot, "review_priority", "low") or "low").lower()
            severity = "high" if priority == "high" else ("medium" if priority == "medium" else "low")
            desc = getattr(hotspot, "title", str(hotspot.category))
            for cat_id in owasp_cats:
                if cat_id in categories:
                    self._add_finding_to_category(categories[cat_id], severity, desc)
                    count += 1
        return count

    # -----------------------------------------------------------------------
    # Private mapping helpers - CWE
    # -----------------------------------------------------------------------

    def _map_vulnerabilities_to_cwe(
        self, security_report, top_25: Dict[str, CategoryCompliance]
    ) -> None:
        """Map vulnerability findings to CWE entries."""
        findings = self._extract_vulnerability_findings(security_report)
        for finding in findings:
            vuln_type = str(getattr(finding, "vulnerability_type", "") or "").lower()
            cwe_ids = _VULN_TO_CWE.get(vuln_type, [])
            # Also use the finding's own cwe_id field if present
            finding_cwe = getattr(finding, "cwe_id", None)
            if finding_cwe and finding_cwe not in cwe_ids:
                cwe_ids = cwe_ids + [finding_cwe]
            severity = _get_finding_severity(finding)
            desc = _get_finding_description(finding)
            for cwe_id in cwe_ids:
                if cwe_id in top_25:
                    self._add_finding_to_category(top_25[cwe_id], severity, desc)

    def _map_secrets_to_cwe(
        self, security_report, top_25: Dict[str, CategoryCompliance]
    ) -> None:
        """Map secrets findings to CWE-798."""
        secrets = self._extract_secrets(security_report)
        for finding in secrets:
            severity = _get_finding_severity(finding)
            desc = _get_finding_description(finding)
            if "CWE-798" in top_25:
                self._add_finding_to_category(top_25["CWE-798"], severity, desc)

    def _map_crypto_to_cwe(
        self, security_report, top_25: Dict[str, CategoryCompliance]
    ) -> None:
        """Map crypto findings to CWE-327 (not in Top 25, skip if absent)."""
        crypto_findings = self._extract_crypto_findings(security_report)
        for finding in crypto_findings:
            finding_cwe = getattr(finding, "cwe_id", None)
            if finding_cwe and finding_cwe in top_25:
                severity = _get_finding_severity(finding)
                desc = _get_finding_description(finding)
                self._add_finding_to_category(top_25[finding_cwe], severity, desc)

    def _map_hotspots_to_cwe(
        self, hotspot_report, top_25: Dict[str, CategoryCompliance]
    ) -> None:
        """Map hotspot findings to CWE entries."""
        hotspots = getattr(hotspot_report, "hotspots", []) or []
        for hotspot in hotspots:
            cat_str = str(getattr(hotspot, "category", "") or "").lower()
            cwe_ids = _HOTSPOT_TO_CWE.get(cat_str, [])
            # Also use the hotspot's own cwe_id field
            hotspot_cwe = getattr(hotspot, "cwe_id", None)
            if hotspot_cwe and hotspot_cwe not in cwe_ids:
                cwe_ids = cwe_ids + [hotspot_cwe]
            priority = str(getattr(hotspot, "review_priority", "low") or "low").lower()
            severity = "high" if priority == "high" else ("medium" if priority == "medium" else "low")
            desc = getattr(hotspot, "title", str(hotspot.category))
            for cwe_id in cwe_ids:
                if cwe_id in top_25:
                    self._add_finding_to_category(top_25[cwe_id], severity, desc)

    # -----------------------------------------------------------------------
    # Helper utilities
    # -----------------------------------------------------------------------

    def _add_finding_to_category(
        self, category: CategoryCompliance, severity: str, description: str
    ) -> None:
        """Increment the finding counts in a CategoryCompliance object."""
        category.findings_count += 1
        if severity == "critical":
            category.critical_count += 1
        elif severity == "high":
            category.high_count += 1
        elif severity == "medium":
            category.medium_count += 1
        else:
            category.low_count += 1
        if description:
            category.mapped_findings.append(description)

    def _extract_vulnerability_findings(self, security_report) -> List:
        """Extract vulnerability findings from a SecurityReport."""
        for attr in ("vulnerability_findings", "vulnerabilities"):
            findings = getattr(security_report, attr, None) or []
            if findings:
                return list(findings)

        vuln_report = getattr(security_report, "vulnerability_report", None)
        if vuln_report is not None:
            for attr in ("findings", "vulnerabilities"):
                findings = getattr(vuln_report, attr, None) or []
                if findings:
                    return list(findings)

        return []

    def _extract_secrets(self, security_report) -> List:
        """Extract secret findings from a SecurityReport."""
        secrets_report = getattr(security_report, "secrets_report", None)
        if secrets_report is not None:
            return list(getattr(secrets_report, "findings", []) or [])

        for attr in ("secrets", "secret_findings"):
            findings = getattr(security_report, attr, None) or []
            if findings:
                return list(findings)

        return []

    def _extract_crypto_findings(self, security_report) -> List:
        """Extract cryptographic findings from a SecurityReport."""
        crypto_report = getattr(security_report, "crypto_report", None)
        if crypto_report is not None:
            return list(getattr(crypto_report, "findings", []) or [])

        for attr in ("crypto_findings", "cryptographic_findings"):
            findings = getattr(security_report, attr, None) or []
            if findings:
                return list(findings)

        return []

    def _extract_dependency_findings(self, security_report) -> List:
        """Extract dependency vulnerability findings from a SecurityReport."""
        dep_report = getattr(security_report, "dependency_report", None)
        if dep_report is not None:
            return list(getattr(dep_report, "vulnerabilities", []) or [])

        for attr in ("dependency_findings", "dependency_vulnerabilities"):
            findings = getattr(security_report, attr, None) or []
            if findings:
                return list(findings)

        return []
