"""
Tests for Heimdall Compliance Reporter Service

Unit tests for OWASP Top 10 and CWE Top 25 compliance reporting.
"""

import pytest

from Asgard.Heimdall.Security.Compliance.models.compliance_models import (
    CategoryCompliance,
    ComplianceConfig,
    ComplianceGrade,
    CWE_TOP_25_2024,
    CWEComplianceReport,
    OWASPCategory,
    OWASPComplianceReport,
    OWASP_CATEGORY_NAMES,
)
from Asgard.Heimdall.Security.Compliance.services.compliance_reporter import (
    ComplianceReporter,
    _compute_grade,
    _worst_grade,
)


class TestOWASPCategoryEnum:
    """Tests for OWASPCategory enum values."""

    def test_all_ten_categories_defined(self):
        """Test that all 10 OWASP Top 10 2021 categories are defined."""
        categories = list(OWASPCategory)
        assert len(categories) == 10

    def test_a01_broken_access_control(self):
        """Test A01 category value."""
        assert OWASPCategory.A01_BROKEN_ACCESS_CONTROL.value == "A01"

    def test_a02_cryptographic_failures(self):
        """Test A02 category value."""
        assert OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES.value == "A02"

    def test_a03_injection(self):
        """Test A03 category value."""
        assert OWASPCategory.A03_INJECTION.value == "A03"

    def test_a04_insecure_design(self):
        """Test A04 category value."""
        assert OWASPCategory.A04_INSECURE_DESIGN.value == "A04"

    def test_a05_security_misconfiguration(self):
        """Test A05 category value."""
        assert OWASPCategory.A05_SECURITY_MISCONFIGURATION.value == "A05"

    def test_a06_vulnerable_components(self):
        """Test A06 category value."""
        assert OWASPCategory.A06_VULNERABLE_COMPONENTS.value == "A06"

    def test_a07_auth_failures(self):
        """Test A07 category value."""
        assert OWASPCategory.A07_AUTH_FAILURES.value == "A07"

    def test_a08_data_integrity_failures(self):
        """Test A08 category value."""
        assert OWASPCategory.A08_DATA_INTEGRITY_FAILURES.value == "A08"

    def test_a09_logging_monitoring_failures(self):
        """Test A09 category value."""
        assert OWASPCategory.A09_LOGGING_MONITORING_FAILURES.value == "A09"

    def test_a10_ssrf(self):
        """Test A10 category value."""
        assert OWASPCategory.A10_SSRF.value == "A10"

    def test_owasp_category_names_has_all_ten(self):
        """Test OWASP_CATEGORY_NAMES dict contains all 10 entries."""
        assert len(OWASP_CATEGORY_NAMES) == 10
        for i in range(1, 11):
            key = f"A{i:02d}"
            assert key in OWASP_CATEGORY_NAMES


class TestComplianceGradeEnum:
    """Tests for ComplianceGrade enum values."""

    def test_grade_a_value(self):
        """Test grade A value."""
        assert ComplianceGrade.A.value == "A"

    def test_grade_b_value(self):
        """Test grade B value."""
        assert ComplianceGrade.B.value == "B"

    def test_grade_c_value(self):
        """Test grade C value."""
        assert ComplianceGrade.C.value == "C"

    def test_grade_d_value(self):
        """Test grade D value."""
        assert ComplianceGrade.D.value == "D"

    def test_grade_f_value(self):
        """Test grade F value."""
        assert ComplianceGrade.F.value == "F"


class TestComputeGrade:
    """Tests for the _compute_grade helper function."""

    def test_zero_findings_grade_a(self):
        """Test that zero findings yields grade A."""
        cat = CategoryCompliance(category_id="A03", category_name="Injection")
        assert _compute_grade(cat) == ComplianceGrade.A

    def test_one_low_finding_grade_b(self):
        """Test that 1 low finding yields grade B."""
        cat = CategoryCompliance(
            category_id="A03",
            category_name="Injection",
            low_count=1,
            findings_count=1,
        )
        assert _compute_grade(cat) == ComplianceGrade.B

    def test_two_low_findings_grade_b(self):
        """Test that 2 low findings yields grade B."""
        cat = CategoryCompliance(
            category_id="A03",
            category_name="Injection",
            low_count=2,
            findings_count=2,
        )
        assert _compute_grade(cat) == ComplianceGrade.B

    def test_three_or_more_low_findings_grade_c(self):
        """Test that 3+ low findings yields grade C."""
        cat = CategoryCompliance(
            category_id="A03",
            category_name="Injection",
            low_count=3,
            findings_count=3,
        )
        assert _compute_grade(cat) == ComplianceGrade.C

    def test_medium_finding_grade_c(self):
        """Test that any medium finding yields grade C."""
        cat = CategoryCompliance(
            category_id="A03",
            category_name="Injection",
            medium_count=1,
            findings_count=1,
        )
        assert _compute_grade(cat) == ComplianceGrade.C

    def test_high_finding_grade_d(self):
        """Test that any high finding yields grade D."""
        cat = CategoryCompliance(
            category_id="A03",
            category_name="Injection",
            high_count=1,
            findings_count=1,
        )
        assert _compute_grade(cat) == ComplianceGrade.D

    def test_critical_finding_grade_f(self):
        """Test that any critical finding yields grade F."""
        cat = CategoryCompliance(
            category_id="A03",
            category_name="Injection",
            critical_count=1,
            findings_count=1,
        )
        assert _compute_grade(cat) == ComplianceGrade.F

    def test_critical_overrides_all_other_counts(self):
        """Test that critical count produces grade F even with low counts."""
        cat = CategoryCompliance(
            category_id="A03",
            category_name="Injection",
            critical_count=1,
            low_count=10,
            findings_count=11,
        )
        assert _compute_grade(cat) == ComplianceGrade.F


class TestWorstGrade:
    """Tests for the _worst_grade helper function."""

    def test_empty_list_returns_a(self):
        """Test that empty grade list returns grade A."""
        assert _worst_grade([]) == ComplianceGrade.A

    def test_all_a_returns_a(self):
        """Test that all A grades returns A."""
        assert _worst_grade([ComplianceGrade.A, ComplianceGrade.A]) == ComplianceGrade.A

    def test_worst_f_returned(self):
        """Test that F is returned when present."""
        grades = [ComplianceGrade.A, ComplianceGrade.B, ComplianceGrade.F]
        assert _worst_grade(grades) == ComplianceGrade.F

    def test_worst_d_returned(self):
        """Test that D is returned when F not present."""
        grades = [ComplianceGrade.A, ComplianceGrade.D, ComplianceGrade.B]
        assert _worst_grade(grades) == ComplianceGrade.D


class TestComplianceReporterInitialization:
    """Tests for ComplianceReporter initialization."""

    def test_default_initialization(self):
        """Test that reporter initializes with default config."""
        reporter = ComplianceReporter()
        assert reporter.config is not None

    def test_custom_config_initialization(self):
        """Test that reporter accepts custom config."""
        config = ComplianceConfig(include_owasp=True, include_cwe=False)
        reporter = ComplianceReporter(config=config)
        assert reporter.config.include_owasp is True
        assert reporter.config.include_cwe is False


class TestGenerateOWASPReport:
    """Tests for ComplianceReporter.generate_owasp_report()."""

    def test_empty_findings_all_categories_grade_a(self):
        """Test that with no findings all 10 OWASP categories receive grade A."""
        reporter = ComplianceReporter()
        report = reporter.generate_owasp_report()

        assert isinstance(report, OWASPComplianceReport)
        assert len(report.categories) == 10
        for cat_id, cat in report.categories.items():
            assert cat.grade == ComplianceGrade.A.value, (
                f"Expected grade A for {cat_id}, got {cat.grade}"
            )

    def test_empty_findings_overall_grade_a(self):
        """Test that with no findings the overall grade is A."""
        reporter = ComplianceReporter()
        report = reporter.generate_owasp_report()

        assert report.overall_grade == ComplianceGrade.A.value

    def test_empty_findings_zero_total_mapped(self):
        """Test that with no findings total_findings_mapped is 0."""
        reporter = ComplianceReporter()
        report = reporter.generate_owasp_report()

        assert report.total_findings_mapped == 0

    def test_report_contains_all_ten_owasp_categories(self):
        """Test that report always contains all 10 OWASP categories."""
        reporter = ComplianceReporter()
        report = reporter.generate_owasp_report()

        expected_ids = {f"A{i:02d}" for i in range(1, 11)}
        assert set(report.categories.keys()) == expected_ids

    def test_sql_injection_finding_affects_a03(self):
        """Test that a SQL injection finding affects the A03 (Injection) category."""

        class FakeFinding:
            vulnerability_type = "sql_injection"
            severity = "critical"
            title = "SQL Injection"
            file_path = "app.py"
            line_number = 42
            cwe_id = "CWE-89"

        class FakeSecurityReport:
            vulnerability_findings = [FakeFinding()]

        reporter = ComplianceReporter()
        report = reporter.generate_owasp_report(security_report=FakeSecurityReport())

        a03 = report.categories.get("A03")
        assert a03 is not None
        assert a03.findings_count > 0
        assert a03.critical_count > 0
        assert a03.grade == ComplianceGrade.F.value

    def test_sql_injection_does_not_affect_unrelated_categories(self):
        """Test that a SQL injection finding does not affect A01 or A06."""

        class FakeFinding:
            vulnerability_type = "sql_injection"
            severity = "high"
            title = "SQL Injection"
            file_path = "db.py"
            line_number = 10
            cwe_id = "CWE-89"

        class FakeSecurityReport:
            vulnerability_findings = [FakeFinding()]

        reporter = ComplianceReporter()
        report = reporter.generate_owasp_report(security_report=FakeSecurityReport())

        for cat_id in ("A01", "A06", "A07", "A08", "A09", "A10"):
            cat = report.categories.get(cat_id)
            assert cat is not None
            assert cat.findings_count == 0, f"{cat_id} should have 0 findings"

    def test_xss_finding_mapped_to_a03(self):
        """Test that an XSS finding maps to A03."""

        class FakeFinding:
            vulnerability_type = "xss"
            severity = "high"
            title = "XSS"
            file_path = "template.html"
            line_number = 5
            cwe_id = "CWE-79"

        class FakeSecurityReport:
            vulnerability_findings = [FakeFinding()]

        reporter = ComplianceReporter()
        report = reporter.generate_owasp_report(security_report=FakeSecurityReport())

        a03 = report.categories.get("A03")
        assert a03 is not None
        assert a03.high_count > 0

    def test_path_traversal_finding_mapped_to_a01(self):
        """Test that a path traversal finding maps to A01."""

        class FakeFinding:
            vulnerability_type = "path_traversal"
            severity = "medium"
            title = "Path Traversal"
            file_path = "files.py"
            line_number = 22
            cwe_id = "CWE-22"

        class FakeSecurityReport:
            vulnerability_findings = [FakeFinding()]

        reporter = ComplianceReporter()
        report = reporter.generate_owasp_report(security_report=FakeSecurityReport())

        a01 = report.categories.get("A01")
        assert a01 is not None
        assert a01.medium_count > 0

    def test_hotspot_findings_mapped_to_owasp(self):
        """Test that hotspot findings are mapped to OWASP categories."""

        class FakeHotspot:
            category = "dynamic_execution"
            review_priority = "high"
            title = "Dynamic Execution"

        class FakeHotspotReport:
            hotspots = [FakeHotspot()]

        reporter = ComplianceReporter()
        report = reporter.generate_owasp_report(hotspot_report=FakeHotspotReport())

        a03 = report.categories.get("A03")
        assert a03 is not None
        assert a03.findings_count > 0

    def test_overall_grade_reflects_worst_category(self):
        """Test that overall grade is the worst grade across all categories."""

        class FakeCriticalFinding:
            vulnerability_type = "sql_injection"
            severity = "critical"
            title = "SQL Injection"
            file_path = "db.py"
            line_number = 1
            cwe_id = "CWE-89"

        class FakeSecurityReport:
            vulnerability_findings = [FakeCriticalFinding()]

        reporter = ComplianceReporter()
        report = reporter.generate_owasp_report(security_report=FakeSecurityReport())

        assert report.overall_grade == ComplianceGrade.F.value

    def test_scan_path_recorded_in_report(self):
        """Test that the provided scan_path is recorded in the report."""
        reporter = ComplianceReporter()
        report = reporter.generate_owasp_report(scan_path="/some/project")

        assert report.scan_path == "/some/project"

    def test_multiple_findings_different_categories(self):
        """Test that findings in different vulnerability types map to correct categories."""

        class SqlFinding:
            vulnerability_type = "sql_injection"
            severity = "high"
            title = "SQL Injection"
            file_path = "db.py"
            line_number = 1
            cwe_id = "CWE-89"

        class SsrfFinding:
            vulnerability_type = "ssrf"
            severity = "medium"
            title = "SSRF"
            file_path = "http.py"
            line_number = 20
            cwe_id = "CWE-918"

        class FakeSecurityReport:
            vulnerability_findings = [SqlFinding(), SsrfFinding()]

        reporter = ComplianceReporter()
        report = reporter.generate_owasp_report(security_report=FakeSecurityReport())

        a03 = report.categories.get("A03")
        a10 = report.categories.get("A10")
        assert a03 is not None and a03.findings_count > 0
        assert a10 is not None and a10.findings_count > 0


class TestGenerateCWEReport:
    """Tests for ComplianceReporter.generate_cwe_report()."""

    def test_empty_findings_all_cwe_entries_grade_a(self):
        """Test that with no findings all CWE Top 25 entries have grade A."""
        reporter = ComplianceReporter()
        report = reporter.generate_cwe_report()

        assert isinstance(report, CWEComplianceReport)
        for cwe_id, entry in report.top_25_coverage.items():
            assert entry.grade == ComplianceGrade.A.value, (
                f"Expected grade A for {cwe_id}, got {entry.grade}"
            )

    def test_report_contains_all_cwe_top_25_entries(self):
        """Test that report contains all CWE Top 25 entries."""
        reporter = ComplianceReporter()
        report = reporter.generate_cwe_report()

        assert len(report.top_25_coverage) == len(CWE_TOP_25_2024)
        for cwe_id in CWE_TOP_25_2024:
            assert cwe_id in report.top_25_coverage

    def test_sql_injection_finding_mapped_to_cwe89(self):
        """Test that an SQL injection finding maps to CWE-89."""

        class FakeFinding:
            vulnerability_type = "sql_injection"
            severity = "critical"
            title = "SQL Injection"
            file_path = "db.py"
            line_number = 1
            cwe_id = "CWE-89"

        class FakeSecurityReport:
            vulnerability_findings = [FakeFinding()]

        reporter = ComplianceReporter()
        report = reporter.generate_cwe_report(security_report=FakeSecurityReport())

        cwe89 = report.top_25_coverage.get("CWE-89")
        assert cwe89 is not None
        assert cwe89.findings_count > 0
        assert cwe89.critical_count > 0

    def test_xss_finding_mapped_to_cwe79(self):
        """Test that an XSS finding maps to CWE-79."""

        class FakeFinding:
            vulnerability_type = "xss"
            severity = "high"
            title = "XSS"
            file_path = "template.html"
            line_number = 5
            cwe_id = "CWE-79"

        class FakeSecurityReport:
            vulnerability_findings = [FakeFinding()]

        reporter = ComplianceReporter()
        report = reporter.generate_cwe_report(security_report=FakeSecurityReport())

        cwe79 = report.top_25_coverage.get("CWE-79")
        assert cwe79 is not None
        assert cwe79.high_count > 0

    def test_hardcoded_secret_mapped_to_cwe798(self):
        """Test that a hardcoded secret finding maps to CWE-798."""

        class FakeSecret:
            severity = "high"
            title = "Hardcoded API Key"
            file_path = "config.py"
            line_number = 3

        class FakeSecurityReport:
            secrets_report = type("SecretsReport", (), {"findings": [FakeSecret()]})()

        reporter = ComplianceReporter()
        report = reporter.generate_cwe_report(security_report=FakeSecurityReport())

        cwe798 = report.top_25_coverage.get("CWE-798")
        assert cwe798 is not None
        assert cwe798.findings_count > 0

    def test_overall_grade_reflects_worst_cwe_entry(self):
        """Test that overall grade reflects the worst CWE category grade."""

        class FakeFinding:
            vulnerability_type = "ssrf"
            severity = "critical"
            title = "SSRF"
            file_path = "http.py"
            line_number = 10
            cwe_id = "CWE-918"

        class FakeSecurityReport:
            vulnerability_findings = [FakeFinding()]

        reporter = ComplianceReporter()
        report = reporter.generate_cwe_report(security_report=FakeSecurityReport())

        # CWE-918 should be grade F due to critical finding
        assert report.overall_grade == ComplianceGrade.F.value

    def test_cwe_report_scan_path_recorded(self):
        """Test that the scan path is recorded in the CWE report."""
        reporter = ComplianceReporter()
        report = reporter.generate_cwe_report(scan_path="/project")

        assert report.scan_path == "/project"

    def test_hotspot_findings_mapped_to_cwe(self):
        """Test that hotspot findings are mapped to CWE entries."""

        class FakeHotspot:
            category = "ssrf"
            review_priority = "high"
            title = "SSRF Hotspot"
            cwe_id = "CWE-918"

        class FakeHotspotReport:
            hotspots = [FakeHotspot()]

        reporter = ComplianceReporter()
        report = reporter.generate_cwe_report(hotspot_report=FakeHotspotReport())

        cwe918 = report.top_25_coverage.get("CWE-918")
        assert cwe918 is not None
        assert cwe918.findings_count > 0


class TestComplianceReporterNoneInputs:
    """Tests for ComplianceReporter with None/empty inputs."""

    def test_generate_owasp_report_no_args(self):
        """Test generate_owasp_report with no arguments produces a valid report."""
        reporter = ComplianceReporter()
        report = reporter.generate_owasp_report()

        assert report is not None
        assert report.owasp_version == "2021"

    def test_generate_cwe_report_no_args(self):
        """Test generate_cwe_report with no arguments produces a valid report."""
        reporter = ComplianceReporter()
        report = reporter.generate_cwe_report()

        assert report is not None
        assert report.cwe_version == "2024"

    def test_security_report_with_empty_findings(self):
        """Test that a security report with empty findings lists works correctly."""

        class FakeSecurityReport:
            vulnerability_findings = []

        reporter = ComplianceReporter()
        report = reporter.generate_owasp_report(security_report=FakeSecurityReport())

        assert report.total_findings_mapped == 0
        assert report.overall_grade == ComplianceGrade.A.value
