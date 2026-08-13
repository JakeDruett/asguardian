"""L3 Contract tests for Heimdall Security models not yet covered.

Covers finding models (API, Backdoor, Deserialization, Frontend,
InputValidation, Malware, Misconfig, PathTraversal, RaceCondition, SSRF,
SensitiveData), FileIntegrity PermissionChange, TaintAnalysis
SanitizerRecord/TaintReport, CWEComplianceReport, ConfigSecretsReport,
DependencyVulnerability, the security_models_findings reports
(Crypto/Dependency/Secrets/Vulnerability/Security), runtime observation
models, and TriageVerdict.
"""
import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.API.models.api_models import (
    APIFinding,
    APISeverity,
    APISecurityCategory,
)


class TestAPIFindingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            APIFinding()

    def test_accepts_valid_data(self):
        f = APIFinding(
            file_path="/api.py",
            line_number=12,
            severity=APISeverity.HIGH,
            category=APISecurityCategory.AUTHENTICATION,
            pattern_type="missing_auth_decorator",
            description="Endpoint lacks authentication",
            recommendation="Add an auth decorator",
        )
        assert f.file_path == "/api.py"
        assert f.severity == APISeverity.HIGH
        assert f.code_snippet == ""

    def test_serialization_round_trip(self):
        f = APIFinding(
            file_path="/api.py",
            line_number=12,
            severity=APISeverity.CRITICAL,
            category=APISecurityCategory.DATA_EXPOSURE,
            pattern_type="verbose_error",
            description="Stack trace exposed",
            recommendation="Disable debug output",
        )
        assert APIFinding(**f.model_dump()) == f


# ---------------------------------------------------------------------------
# Backdoor
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.Backdoor.models.backdoor_models import (
    BackdoorFinding,
    BackdoorType,
    BackdoorSeverity,
)


class TestBackdoorFindingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            BackdoorFinding()

    def test_accepts_valid_data(self):
        f = BackdoorFinding(
            file_path="/shell.php",
            line_number=3,
            backdoor_type=BackdoorType.PHP_WEBSHELL,
            severity=BackdoorSeverity.CRITICAL,
            description="eval of request parameter",
        )
        assert f.backdoor_type == BackdoorType.PHP_WEBSHELL
        assert f.code_snippet == ""
        assert f.ioc == ""

    def test_serialization_round_trip(self):
        f = BackdoorFinding(
            file_path="/shell.php",
            line_number=3,
            backdoor_type=BackdoorType.REVERSE_SHELL,
            severity=BackdoorSeverity.CRITICAL,
            description="reverse shell one-liner",
            ioc="203.0.113.7:4444",
        )
        assert BackdoorFinding(**f.model_dump()) == f


# ---------------------------------------------------------------------------
# Compliance (CWE report)
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.Compliance.models.compliance_models import (
    CWEComplianceReport,
    CategoryCompliance,
    ComplianceGrade,
)


class TestCWEComplianceReportContract:
    def test_instantiates_with_defaults(self):
        report = CWEComplianceReport()
        assert report.cwe_version == "2024"
        assert report.top_25_coverage == {}
        assert report.overall_grade == ComplianceGrade.A
        assert report.scan_path == ""

    def test_accepts_coverage_entries(self):
        report = CWEComplianceReport(
            scan_path="/repo",
            overall_grade=ComplianceGrade.C,
            top_25_coverage={
                "CWE-89": CategoryCompliance(
                    category_id="CWE-89", category_name="SQL Injection"
                )
            },
        )
        assert "CWE-89" in report.top_25_coverage
        assert report.overall_grade == ComplianceGrade.C

    def test_serialization_round_trip(self):
        report = CWEComplianceReport(scan_path="/repo")
        assert CWEComplianceReport(**report.model_dump()) == report


# ---------------------------------------------------------------------------
# Deserialization
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.Deserialization.models.deserialization_models import (
    DeserializationFinding,
    DeserializationSeverity,
)


class TestDeserializationFindingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            DeserializationFinding()

    def test_accepts_valid_data(self):
        f = DeserializationFinding(
            file_path="/load.py",
            line_number=7,
            severity=DeserializationSeverity.CRITICAL,
            language="python",
            pattern_type="pickle_loads",
            description="pickle.loads on untrusted data",
            recommendation="Use a safe format such as JSON",
        )
        assert f.language == "python"

    def test_default_honesty(self):
        f = DeserializationFinding(
            file_path="/load.py",
            line_number=7,
            severity=DeserializationSeverity.HIGH,
            language="python",
            pattern_type="yaml_load",
            description="yaml.load without SafeLoader",
            recommendation="Use yaml.safe_load",
        )
        # Defaults must not overstate certainty.
        assert f.confidence == 0.5
        assert f.confidence_bucket == "possible"
        assert f.is_hotspot is False
        assert f.provenance == "unknown"

    def test_serialization_round_trip(self):
        f = DeserializationFinding(
            file_path="/load.py",
            line_number=7,
            severity=DeserializationSeverity.MEDIUM,
            language="java",
            pattern_type="object_input_stream",
            description="ObjectInputStream.readObject",
            recommendation="Use an allowlist filter",
        )
        assert DeserializationFinding(**f.model_dump()) == f


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.Frontend.models.frontend_models import (
    FrontendFinding,
    FrontendSeverity,
)


class TestFrontendFindingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            FrontendFinding()

    def test_accepts_valid_data(self):
        f = FrontendFinding(
            file_path="/app.js",
            line_number=42,
            severity=FrontendSeverity.HIGH,
            category="xss",
            pattern_type="innerHTML_assignment",
            description="innerHTML assigned from user input",
            recommendation="Use textContent or sanitize",
        )
        assert f.category == "xss"

    def test_serialization_round_trip(self):
        f = FrontendFinding(
            file_path="/app.js",
            line_number=42,
            severity=FrontendSeverity.LOW,
            category="storage",
            pattern_type="localstorage_secret",
            description="Token stored in localStorage",
            recommendation="Use httpOnly cookies",
        )
        assert FrontendFinding(**f.model_dump()) == f


# ---------------------------------------------------------------------------
# InputValidation
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.InputValidation.models.input_validation_models import (
    InputValidationFinding,
    InputValidationSeverity,
)


class TestInputValidationFindingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            InputValidationFinding()

    def test_accepts_valid_data(self):
        f = InputValidationFinding(
            file_path="/views.py",
            line_number=9,
            severity=InputValidationSeverity.HIGH,
            category="injection",
            issue_type="unvalidated_input",
            description="Request parameter used unchecked",
            recommendation="Validate and constrain the input",
        )
        assert f.issue_type == "unvalidated_input"

    def test_default_honesty(self):
        f = InputValidationFinding(
            file_path="/views.py",
            line_number=9,
            severity=InputValidationSeverity.MEDIUM,
            category="injection",
            issue_type="unvalidated_input",
            description="d",
            recommendation="r",
        )
        assert f.confidence == 0.6
        assert f.confidence_bucket == "probable"
        assert f.is_advisory is False
        assert f.cwe_id == ""

    def test_serialization_round_trip(self):
        f = InputValidationFinding(
            file_path="/views.py",
            line_number=9,
            severity=InputValidationSeverity.CRITICAL,
            category="injection",
            issue_type="sql_concat",
            description="SQL built by concatenation",
            recommendation="Use parameterized queries",
        )
        assert InputValidationFinding(**f.model_dump()) == f


# ---------------------------------------------------------------------------
# Malware
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.Malware.models.malware_models import (
    MalwareFinding,
    MalwareSeverity,
)


class TestMalwareFindingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            MalwareFinding()

    def test_accepts_valid_data(self):
        f = MalwareFinding(
            file_path="/setup.py",
            line_number=88,
            indicator_type="obfuscated_exec",
            severity=MalwareSeverity.CRITICAL,
            description="base64-decoded exec call",
        )
        assert f.indicator_type == "obfuscated_exec"
        # Default confidence must not claim certainty.
        assert f.confidence == "MEDIUM"

    def test_serialization_round_trip(self):
        f = MalwareFinding(
            file_path="/setup.py",
            line_number=88,
            indicator_type="crypto_miner",
            severity=MalwareSeverity.HIGH,
            description="miner pool URL",
            confidence="HIGH",
        )
        assert MalwareFinding(**f.model_dump()) == f


# ---------------------------------------------------------------------------
# Misconfig
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.Misconfig.models.misconfig_models import (
    MisconfigFinding,
    MisconfigSeverity,
)


class TestMisconfigFindingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            MisconfigFinding()

    def test_accepts_valid_data(self):
        f = MisconfigFinding(
            file_path="/settings.py",
            line_number=1,
            severity=MisconfigSeverity.HIGH,
            category="framework",
            issue_type="debug_enabled",
            description="DEBUG = True in production settings",
            recommendation="Disable debug in production",
        )
        assert f.issue_type == "debug_enabled"

    def test_serialization_round_trip(self):
        f = MisconfigFinding(
            file_path="/settings.py",
            line_number=1,
            severity=MisconfigSeverity.LOW,
            category="framework",
            issue_type="permissive_cors",
            description="CORS allows all origins",
            recommendation="Restrict origins",
        )
        assert MisconfigFinding(**f.model_dump()) == f


# ---------------------------------------------------------------------------
# PathTraversal
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.PathTraversal.models.path_traversal_models import (
    PathTraversalFinding,
    PathTraversalSeverity,
)


class TestPathTraversalFindingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            PathTraversalFinding()

    def test_accepts_valid_data(self):
        f = PathTraversalFinding(
            file_path="/download.py",
            line_number=15,
            severity=PathTraversalSeverity.HIGH,
            language="python",
            pattern_type="open_user_path",
            description="open() with user-controlled path",
            recommendation="Resolve and validate against a base directory",
        )
        assert f.pattern_type == "open_user_path"

    def test_serialization_round_trip(self):
        f = PathTraversalFinding(
            file_path="/download.py",
            line_number=15,
            severity=PathTraversalSeverity.CRITICAL,
            language="php",
            pattern_type="include_user_path",
            description="include with request data",
            recommendation="Allowlist include targets",
        )
        assert PathTraversalFinding(**f.model_dump()) == f


# ---------------------------------------------------------------------------
# RaceCondition
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.RaceCondition.models.race_condition_models import (
    RaceConditionFinding,
    RaceConditionSeverity,
)


class TestRaceConditionFindingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            RaceConditionFinding()

    def test_accepts_valid_data(self):
        f = RaceConditionFinding(
            file_path="/upload.py",
            line_number=30,
            severity=RaceConditionSeverity.MEDIUM,
            category="toctou",
            issue_type="check_then_use",
            description="os.path.exists followed by open",
            recommendation="Open and handle the error instead",
        )
        assert f.category == "toctou"

    def test_default_honesty(self):
        f = RaceConditionFinding(
            file_path="/upload.py",
            line_number=30,
            severity=RaceConditionSeverity.MEDIUM,
            category="toctou",
            issue_type="check_then_use",
            description="d",
            recommendation="r",
        )
        assert f.confidence == 0.5
        assert f.confidence_bucket == "possible"
        assert f.is_hotspot is False

    def test_serialization_round_trip(self):
        f = RaceConditionFinding(
            file_path="/upload.py",
            line_number=30,
            severity=RaceConditionSeverity.HIGH,
            category="toctou",
            issue_type="tempfile_predictable",
            description="predictable temp file name",
            recommendation="Use tempfile.mkstemp",
        )
        assert RaceConditionFinding(**f.model_dump()) == f


# ---------------------------------------------------------------------------
# SSRF
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.SSRF.models.ssrf_models import (
    SSRFFinding,
    SSRFSeverity,
    SSRFVulnerabilityType,
)


class TestSSRFFindingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            SSRFFinding()

    def test_accepts_valid_data(self):
        f = SSRFFinding(
            file_path="/fetch.py",
            line_number=22,
            vulnerability_type=SSRFVulnerabilityType.SSRF,
            severity=SSRFSeverity.HIGH,
            language="python",
            pattern_type="requests_user_url",
            description="requests.get with user URL",
            recommendation="Validate against an allowlist",
        )
        assert f.vulnerability_type == SSRFVulnerabilityType.SSRF
        assert f.mechanism_id == "ssrf.regex_heuristic"

    def test_serialization_round_trip(self):
        f = SSRFFinding(
            file_path="/parse.py",
            line_number=5,
            vulnerability_type=SSRFVulnerabilityType.XXE,
            severity=SSRFSeverity.CRITICAL,
            language="java",
            pattern_type="xxe_external_entities",
            description="DocumentBuilder without secure processing",
            recommendation="Disable external entities",
        )
        assert SSRFFinding(**f.model_dump()) == f


# ---------------------------------------------------------------------------
# SensitiveData
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.SensitiveData.models.sensitive_data_models import (
    SensitiveDataFinding,
    SensitiveDataSeverity,
)


class TestSensitiveDataFindingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            SensitiveDataFinding()

    def test_accepts_valid_data(self):
        f = SensitiveDataFinding(
            file_path="/config.py",
            line_number=4,
            severity=SensitiveDataSeverity.HIGH,
            data_type="api_key",
            pattern_type="hardcoded_key",
            description="API key committed to source",
            recommendation="Move to a secrets manager",
            masked_value="sk-****",
        )
        assert f.masked_value == "sk-****"
        assert f.compliance_tags == []

    def test_default_honesty(self):
        f = SensitiveDataFinding(
            file_path="/config.py",
            line_number=4,
            severity=SensitiveDataSeverity.MEDIUM,
            data_type="email",
            pattern_type="pii_email",
            description="d",
            recommendation="r",
        )
        assert f.confidence == 0.7
        assert f.confidence_bucket == "probable"
        assert f.is_hotspot is False

    def test_serialization_round_trip(self):
        f = SensitiveDataFinding(
            file_path="/config.py",
            line_number=4,
            severity=SensitiveDataSeverity.CRITICAL,
            data_type="password",
            pattern_type="hardcoded_password",
            description="password literal",
            recommendation="Use env/secret store",
            compliance_tags=["PCI-DSS"],
        )
        assert SensitiveDataFinding(**f.model_dump()) == f


# ---------------------------------------------------------------------------
# FileIntegrity — PermissionChange
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.FileIntegrity.models.file_integrity_models import (
    PermissionChange,
)


class TestPermissionChangeContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            PermissionChange()

    def test_accepts_valid_data(self):
        pc = PermissionChange(path="/etc/passwd", old_perms="0644", new_perms="0666")
        assert pc.old_perms == "0644"
        assert pc.new_perms == "0666"

    def test_serialization_round_trip(self):
        pc = PermissionChange(path="/bin/sh", old_perms="0755", new_perms="4755")
        assert PermissionChange(**pc.model_dump()) == pc


# ---------------------------------------------------------------------------
# TaintAnalysis — SanitizerRecord + TaintReport
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.TaintAnalysis.models.taint_models import (
    SanitizerRecord,
    TaintReport,
)


class TestSanitizerRecordContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            SanitizerRecord()

    def test_accepts_valid_data(self):
        sr = SanitizerRecord(name="shlex.quote", kind="shell", factor=0.1)
        assert sr.name == "shlex.quote"
        assert sr.line_number == 0

    def test_serialization_round_trip(self):
        sr = SanitizerRecord(name="html.escape", kind="html", factor=0.05, line_number=12)
        assert SanitizerRecord(**sr.model_dump()) == sr


class TestTaintReportContract:
    def test_instantiates_with_defaults(self):
        report = TaintReport()
        # Empty report must honestly claim zero, not unknown-positive.
        assert report.total_flows == 0
        assert report.critical_count == 0
        assert report.high_count == 0
        assert report.medium_count == 0
        assert report.flows == []
        assert report.files_analyzed == 0
        assert report.scan_path == ""

    def test_accepts_counts(self):
        report = TaintReport(
            total_flows=2,
            critical_count=1,
            high_count=1,
            files_analyzed=10,
            scan_path="/repo",
        )
        assert report.total_flows == 2

    def test_serialization_round_trip(self):
        report = TaintReport(total_flows=1, high_count=1, scan_path="/repo")
        assert TaintReport(**report.model_dump()) == report


# ---------------------------------------------------------------------------
# ConfigSecretsReport
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.models.config_secrets_models import (
    ConfigSecretsReport,
)


class TestConfigSecretsReportContract:
    def test_instantiates_with_defaults(self):
        report = ConfigSecretsReport()
        assert report.total_findings == 0
        assert report.findings_by_type == {}
        assert report.findings_by_severity == {}
        assert report.detected_findings == []
        assert report.files_scanned == 0

    def test_accepts_valid_data(self):
        report = ConfigSecretsReport(
            total_findings=3,
            findings_by_type={"aws_key": 2, "db_password": 1},
            findings_by_severity={"HIGH": 3},
            most_problematic_files=[("config.py", 2)],
            files_scanned=50,
            scan_path="/repo",
        )
        assert report.findings_by_type["aws_key"] == 2
        assert report.most_problematic_files[0] == ("config.py", 2)

    def test_serialization_round_trip(self):
        report = ConfigSecretsReport(total_findings=1, scan_path="/repo")
        assert ConfigSecretsReport(**report.model_dump()) == report


# ---------------------------------------------------------------------------
# security_models_base — DependencyVulnerability
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.models.security_models_base import (
    DependencyVulnerability,
    DependencyRiskLevel,
    SecurityScanConfig,
)


class TestDependencyVulnerabilityContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            DependencyVulnerability()

    def test_accepts_valid_data(self):
        dv = DependencyVulnerability(
            package_name="requests",
            installed_version="2.19.0",
            vulnerable_versions="<2.20.0",
            risk_level=DependencyRiskLevel.HIGH,
            title="CRLF injection",
            description="requests before 2.20.0 allows CRLF injection",
            cve_id="CVE-2018-18074",
        )
        assert dv.package_name == "requests"
        assert dv.fixed_version is None
        assert dv.ecosystem == "pypi"

    def test_default_honesty(self):
        dv = DependencyVulnerability(
            package_name="p",
            installed_version="1.0",
            vulnerable_versions="<2.0",
            risk_level=DependencyRiskLevel.LOW,
            title="t",
            description="d",
        )
        # Defaults must state local provenance, not imply a network check.
        assert dv.source_db == "local"
        assert dv.confidence_bucket == "probable"
        assert dv.confidence == 0.7
        assert dv.is_dev_dependency is False
        assert dv.finding_kind == "known_vulnerability"

    def test_serialization_round_trip(self):
        dv = DependencyVulnerability(
            package_name="lodash",
            installed_version="4.17.10",
            vulnerable_versions="<4.17.12",
            fixed_version="4.17.12",
            risk_level=DependencyRiskLevel.CRITICAL,
            title="Prototype pollution",
            description="defaultsDeep prototype pollution",
            ecosystem="npm",
            references=["https://example.invalid/advisory"],
        )
        assert DependencyVulnerability(**dv.model_dump()) == dv


# ---------------------------------------------------------------------------
# security_models_findings — Crypto/Dependency/Secrets/Vulnerability/Security
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.models.security_models_findings import (
    CryptoReport,
    DependencyReport,
    SecretsReport,
    VulnerabilityReport,
    SecurityReport,
)


class TestCryptoReportContract:
    def test_requires_scan_path(self):
        with pytest.raises((ValidationError, TypeError)):
            CryptoReport()

    def test_accepts_valid_data(self):
        report = CryptoReport(scan_path="/repo")
        assert report.total_files_scanned == 0
        assert report.issues_found == 0
        assert report.findings == []

    def test_serialization_round_trip(self):
        report = CryptoReport(scan_path="/repo", issues_found=2)
        assert CryptoReport(**report.model_dump()) == report


class TestDependencyReportContract:
    def test_requires_scan_path(self):
        with pytest.raises((ValidationError, TypeError)):
            DependencyReport()

    def test_default_honesty_no_network(self):
        report = DependencyReport(scan_path="/repo")
        # Default must not claim a network check happened.
        assert report.network_checked is False
        assert report.network_reason == ""
        assert report.vulnerabilities == []
        assert report.requirements_files == []

    def test_serialization_round_trip(self):
        report = DependencyReport(
            scan_path="/repo",
            requirements_files=["requirements.txt"],
            total_dependencies=10,
            vulnerable_dependencies=1,
        )
        assert DependencyReport(**report.model_dump()) == report


class TestSecretsReportContract:
    def test_requires_scan_path(self):
        with pytest.raises((ValidationError, TypeError)):
            SecretsReport()

    def test_accepts_valid_data(self):
        report = SecretsReport(scan_path="/repo", patterns_used=["aws_key"])
        assert report.secrets_found == 0
        assert report.findings == []
        assert report.patterns_used == ["aws_key"]

    def test_serialization_round_trip(self):
        report = SecretsReport(scan_path="/repo", secrets_found=1)
        assert SecretsReport(**report.model_dump()) == report


class TestVulnerabilityReportContract:
    def test_requires_scan_path(self):
        with pytest.raises((ValidationError, TypeError)):
            VulnerabilityReport()

    def test_accepts_valid_data(self):
        report = VulnerabilityReport(scan_path="/repo")
        assert report.vulnerabilities_found == 0
        assert report.findings == []

    def test_serialization_round_trip(self):
        report = VulnerabilityReport(scan_path="/repo", vulnerabilities_found=3)
        assert VulnerabilityReport(**report.model_dump()) == report


class TestSecurityReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            SecurityReport()

    def test_accepts_valid_data(self):
        report = SecurityReport(scan_path="/repo", scan_config=SecurityScanConfig())
        assert report.secrets_report is None
        assert report.dependency_report is None
        assert report.total_issues == 0
        assert report.security_score == 100.0

    def test_nests_sub_reports(self):
        report = SecurityReport(
            scan_path="/repo",
            scan_config=SecurityScanConfig(),
            secrets_report=SecretsReport(scan_path="/repo"),
            dependency_report=DependencyReport(scan_path="/repo"),
            total_issues=1,
            high_issues=1,
        )
        assert report.secrets_report.scan_path == "/repo"
        assert report.dependency_report.network_checked is False

    def test_serialization_round_trip(self):
        report = SecurityReport(scan_path="/repo", scan_config=SecurityScanConfig())
        rebuilt = SecurityReport(**report.model_dump())
        assert rebuilt.scan_path == report.scan_path
        assert rebuilt.security_score == report.security_score
        assert rebuilt.scanned_at == report.scanned_at


# ---------------------------------------------------------------------------
# runtime — RuntimeObservation + RuntimeObservationBatch
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.runtime.models import (
    RuntimeObservation,
    RuntimeObservationBatch,
    RuntimeConfidence,
    TaintSourceType,
    TaintSinkType,
)


class TestRuntimeObservationContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            RuntimeObservation()

    def test_accepts_valid_data(self):
        obs = RuntimeObservation(
            source_type=TaintSourceType.HTTP_PARAMETER,
            source_file="/views.py",
            sink_type=TaintSinkType.SQL_QUERY,
            sink_file="/db.py",
            sink_line=44,
            tainted_value_fingerprint="ab12cd34",
            trace_id="trace-1",
            timestamp_in=1723500000.0,
        )
        assert obs.source_line == 0
        assert obs.confidence_marker == RuntimeConfidence.CONFIRMED_AT_RUNTIME
        assert obs.stack_frames == []

    def test_serialization_round_trip(self):
        obs = RuntimeObservation(
            source_type=TaintSourceType.COOKIE,
            source_file="/views.py",
            source_line=8,
            sink_type=TaintSinkType.SHELL_COMMAND,
            sink_file="/tasks.py",
            sink_line=91,
            tainted_value_fingerprint="ff00",
            trace_id="trace-2",
            timestamp_in=1723500001.5,
            stack_frames=["views.py:8", "tasks.py:91"],
            cwe_id="CWE-78",
        )
        assert RuntimeObservation(**obs.model_dump()) == obs


class TestRuntimeObservationBatchContract:
    def test_instantiates_with_defaults(self):
        batch = RuntimeObservationBatch()
        assert batch.schema_version == "1.0"
        assert batch.generated_by == ""
        assert batch.observations == []

    def test_serialization_round_trip(self):
        batch = RuntimeObservationBatch(
            generated_by="heimdall-agent",
            observations=[
                RuntimeObservation(
                    source_type=TaintSourceType.ENV_VAR,
                    source_file="/a.py",
                    sink_type=TaintSinkType.FILE_WRITE,
                    sink_file="/b.py",
                    sink_line=2,
                    tainted_value_fingerprint="01",
                    trace_id="t",
                    timestamp_in=1.0,
                )
            ],
        )
        assert RuntimeObservationBatch(**batch.model_dump()) == batch


# ---------------------------------------------------------------------------
# triage — TriageVerdict
# ---------------------------------------------------------------------------
from Asgard.Heimdall.Security.triage.models.triage_models import (
    TriageVerdict,
    TriageLabel,
)


class TestTriageVerdictContract:
    def test_requires_label(self):
        with pytest.raises((ValidationError, TypeError)):
            TriageVerdict()

    def test_accepts_valid_data(self):
        v = TriageVerdict(
            label=TriageLabel.NEEDS_HUMAN,
            rationale="Ambiguous data flow",
            confidence=0.4,
        )
        assert v.label == TriageLabel.NEEDS_HUMAN

    def test_default_honesty(self):
        v = TriageVerdict(label=TriageLabel.NOT_AVAILABLE)
        # Defaults must not fabricate confidence or claim cache provenance.
        assert v.confidence == 0.0
        assert v.rationale == ""
        assert v.reason is None
        assert v.from_cache is False

    def test_serialization_round_trip(self):
        v = TriageVerdict(
            label=TriageLabel.LIKELY_REAL,
            rationale="Confirmed source-to-sink path",
            confidence=0.9,
            from_cache=True,
        )
        assert TriageVerdict(**v.model_dump()) == v
