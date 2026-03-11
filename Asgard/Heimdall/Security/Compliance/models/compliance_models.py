"""
Heimdall Compliance Models

Pydantic models for OWASP Top 10 (2021) and CWE Top 25 (2024) compliance reporting.

Maps Heimdall security findings to OWASP and CWE categories and produces
compliance grade reports per category.

Compliance grades:
  A: 0 findings
  B: 1-2 LOW findings only
  C: Any MEDIUM findings or 3+ LOW
  D: Any HIGH findings
  F: Any CRITICAL findings
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class OWASPCategory(str, Enum):
    """OWASP Top 10 2021 categories."""
    A01_BROKEN_ACCESS_CONTROL = "A01"
    A02_CRYPTOGRAPHIC_FAILURES = "A02"
    A03_INJECTION = "A03"
    A04_INSECURE_DESIGN = "A04"
    A05_SECURITY_MISCONFIGURATION = "A05"
    A06_VULNERABLE_COMPONENTS = "A06"
    A07_AUTH_FAILURES = "A07"
    A08_DATA_INTEGRITY_FAILURES = "A08"
    A09_LOGGING_MONITORING_FAILURES = "A09"
    A10_SSRF = "A10"


OWASP_CATEGORY_NAMES: Dict[str, str] = {
    "A01": "Broken Access Control",
    "A02": "Cryptographic Failures",
    "A03": "Injection",
    "A04": "Insecure Design",
    "A05": "Security Misconfiguration",
    "A06": "Vulnerable and Outdated Components",
    "A07": "Identification and Authentication Failures",
    "A08": "Software and Data Integrity Failures",
    "A09": "Security Logging and Monitoring Failures",
    "A10": "Server-Side Request Forgery (SSRF)",
}

CWE_TOP_25_2024: Dict[str, str] = {
    "CWE-787": "Out-of-bounds Write",
    "CWE-79": "Improper Neutralization of Input During Web Page Generation (XSS)",
    "CWE-89": "Improper Neutralization of Special Elements used in an SQL Command (SQL Injection)",
    "CWE-416": "Use After Free",
    "CWE-78": "Improper Neutralization of Special Elements used in an OS Command (OS Command Injection)",
    "CWE-20": "Improper Input Validation",
    "CWE-125": "Out-of-bounds Read",
    "CWE-22": "Improper Limitation of a Pathname to a Restricted Directory (Path Traversal)",
    "CWE-352": "Cross-Site Request Forgery (CSRF)",
    "CWE-434": "Unrestricted Upload of File with Dangerous Type",
    "CWE-862": "Missing Authorization",
    "CWE-476": "NULL Pointer Dereference",
    "CWE-287": "Improper Authentication",
    "CWE-190": "Integer Overflow or Wraparound",
    "CWE-502": "Deserialization of Untrusted Data",
    "CWE-77": "Improper Neutralization of Special Elements used in a Command (Command Injection)",
    "CWE-119": "Improper Restriction of Operations within the Bounds of a Memory Buffer",
    "CWE-798": "Use of Hard-coded Credentials",
    "CWE-918": "Server-Side Request Forgery (SSRF)",
    "CWE-306": "Missing Authentication for Critical Function",
    "CWE-362": "Concurrent Execution using Shared Resource with Improper Synchronization (Race Condition)",
    "CWE-269": "Improper Privilege Management",
    "CWE-94": "Improper Control of Generation of Code (Code Injection)",
    "CWE-863": "Incorrect Authorization",
    "CWE-276": "Incorrect Default Permissions",
}


class CWEEntry(BaseModel):
    """A CWE classification entry."""
    cwe_id: str = Field(..., description="CWE identifier (e.g. 'CWE-79')")
    name: str = Field(..., description="CWE name")
    description: str = Field("", description="Brief description of the weakness")

    class Config:
        use_enum_values = True


class ComplianceGrade(str, Enum):
    """Compliance grade for a category."""
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class CategoryCompliance(BaseModel):
    """Compliance status for a single OWASP or CWE category."""
    category_id: str = Field(..., description="Category identifier (e.g. 'A03' or 'CWE-89')")
    category_name: str = Field(..., description="Human-readable category name")
    grade: ComplianceGrade = Field(ComplianceGrade.A, description="Compliance grade for this category")
    findings_count: int = Field(0, description="Total number of findings in this category")
    critical_count: int = Field(0, description="Number of CRITICAL findings")
    high_count: int = Field(0, description="Number of HIGH findings")
    medium_count: int = Field(0, description="Number of MEDIUM findings")
    low_count: int = Field(0, description="Number of LOW findings")
    mapped_findings: List[str] = Field(
        default_factory=list,
        description="Human-readable descriptions of findings mapped to this category"
    )

    class Config:
        use_enum_values = True


class OWASPComplianceReport(BaseModel):
    """OWASP Top 10 compliance report."""
    owasp_version: str = Field("2021", description="OWASP Top 10 version")
    categories: Dict[str, CategoryCompliance] = Field(
        default_factory=dict,
        description="Compliance status per OWASP category"
    )
    overall_grade: ComplianceGrade = Field(
        ComplianceGrade.A,
        description="Overall OWASP compliance grade (worst category grade)"
    )
    total_findings_mapped: int = Field(0, description="Total findings mapped to OWASP categories")
    scan_path: str = Field("", description="Path that was analyzed")
    generated_at: datetime = Field(default_factory=datetime.now, description="Report generation time")

    class Config:
        use_enum_values = True


class CWEComplianceReport(BaseModel):
    """CWE Top 25 compliance report."""
    cwe_version: str = Field("2024", description="CWE Top 25 version")
    top_25_coverage: Dict[str, CategoryCompliance] = Field(
        default_factory=dict,
        description="Compliance status per CWE Top 25 entry"
    )
    overall_grade: ComplianceGrade = Field(
        ComplianceGrade.A,
        description="Overall CWE compliance grade (worst category grade)"
    )
    scan_path: str = Field("", description="Path that was analyzed")
    generated_at: datetime = Field(default_factory=datetime.now, description="Report generation time")

    class Config:
        use_enum_values = True


class ComplianceConfig(BaseModel):
    """Configuration for compliance reporting."""
    include_owasp: bool = Field(True, description="Generate OWASP Top 10 compliance report")
    include_cwe: bool = Field(True, description="Generate CWE Top 25 compliance report")
    owasp_version: str = Field("2021", description="OWASP Top 10 version to use")
    cwe_version: str = Field("2024", description="CWE Top 25 version to use")

    class Config:
        use_enum_values = True
