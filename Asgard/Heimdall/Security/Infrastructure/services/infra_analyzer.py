"""
Heimdall Infrastructure Analyzer Service

Unified service that orchestrates all infrastructure security analyzers.
"""

import time
from pathlib import Path
from typing import Optional

from Asgard.Heimdall.Security.Infrastructure.models.infra_models import (
    InfraConfig,
    InfraFindingType,
    InfraReport,
)
from Asgard.Heimdall.Security.Infrastructure.services.credential_analyzer import CredentialAnalyzer
from Asgard.Heimdall.Security.Infrastructure.services.config_validator import ConfigValidator
from Asgard.Heimdall.Security.Infrastructure.services.hardening_checker import HardeningChecker
from Asgard.Heimdall.Security.models.security_models import SecuritySeverity


class InfraAnalyzer:
    """
    Unified infrastructure analyzer that combines all infrastructure checking services.

    Orchestrates:
    - CredentialAnalyzer: Default/weak credential detection
    - ConfigValidator: Configuration security validation
    - HardeningChecker: Hardening best practices
    """

    def __init__(self, config: Optional[InfraConfig] = None):
        """
        Initialize the infrastructure analyzer.

        Args:
            config: Infrastructure configuration. Uses defaults if not provided.
        """
        self.config = config or InfraConfig()
        self.credential_analyzer = CredentialAnalyzer(self.config)
        self.config_validator = ConfigValidator(self.config)
        self.hardening_checker = HardeningChecker(self.config)

    def analyze(self, scan_path: Optional[Path] = None) -> InfraReport:
        """
        Run full infrastructure security analysis.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            InfraReport containing all findings from all analyzers
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        start_time = time.time()

        combined_report = InfraReport(scan_path=str(path))

        if self.config.check_credentials:
            credential_report = self.credential_analyzer.scan(path)
            self._merge_reports(combined_report, credential_report)

        if self.config.check_debug_mode or self.config.check_hosts or self.config.check_cors:
            config_report = self.config_validator.scan(path)
            self._merge_reports(combined_report, config_report)

        if self.config.check_endpoints or self.config.check_permissions:
            hardening_report = self.hardening_checker.scan(path)
            self._merge_reports(combined_report, hardening_report)

        combined_report.scan_duration_seconds = time.time() - start_time

        combined_report.findings = list({
            (f.file_path, f.line_number, f.finding_type): f
            for f in combined_report.findings
        }.values())

        combined_report.findings.sort(
            key=lambda f: (
                self._severity_order(f.severity),
                f.file_path,
                f.line_number,
            )
        )

        self._recalculate_totals(combined_report)

        return combined_report

    def scan(self, scan_path: Optional[Path] = None) -> InfraReport:
        """
        Alias for analyze() for consistency with other services.

        Args:
            scan_path: Root path to scan

        Returns:
            InfraReport containing all findings
        """
        return self.analyze(scan_path)

    def scan_credentials_only(self, scan_path: Optional[Path] = None) -> InfraReport:
        """
        Scan only for credential issues.

        Args:
            scan_path: Root path to scan

        Returns:
            InfraReport with credential findings only
        """
        return self.credential_analyzer.scan(scan_path)

    def scan_config_only(self, scan_path: Optional[Path] = None) -> InfraReport:
        """
        Scan only for configuration issues.

        Args:
            scan_path: Root path to scan

        Returns:
            InfraReport with configuration findings only
        """
        return self.config_validator.scan(scan_path)

    def scan_hardening_only(self, scan_path: Optional[Path] = None) -> InfraReport:
        """
        Scan only for hardening issues.

        Args:
            scan_path: Root path to scan

        Returns:
            InfraReport with hardening findings only
        """
        return self.hardening_checker.scan(scan_path)

    def _merge_reports(self, target: InfraReport, source: InfraReport) -> None:
        """
        Merge source report into target report.

        Args:
            target: Report to merge into
            source: Report to merge from
        """
        target.total_files_scanned = max(
            target.total_files_scanned,
            source.total_files_scanned
        )
        target.total_config_files = max(
            target.total_config_files,
            source.total_config_files
        )
        target.findings.extend(source.findings)

    def _recalculate_totals(self, report: InfraReport) -> None:
        """
        Recalculate totals after deduplication.

        Args:
            report: Report to recalculate
        """
        report.total_issues = len(report.findings)
        report.critical_issues = sum(
            1 for f in report.findings if f.severity == SecuritySeverity.CRITICAL.value
        )
        report.high_issues = sum(
            1 for f in report.findings if f.severity == SecuritySeverity.HIGH.value
        )
        report.medium_issues = sum(
            1 for f in report.findings if f.severity == SecuritySeverity.MEDIUM.value
        )
        report.low_issues = sum(
            1 for f in report.findings if f.severity == SecuritySeverity.LOW.value
        )

        credential_types = [
            InfraFindingType.DEFAULT_CREDENTIALS.value,
            InfraFindingType.WEAK_CREDENTIAL_PATTERN.value,
            InfraFindingType.HARDCODED_SECRET_KEY.value,
        ]
        config_types = [
            InfraFindingType.DEBUG_MODE.value,
            InfraFindingType.PERMISSIVE_HOSTS.value,
            InfraFindingType.CORS_ALLOW_ALL.value,
            InfraFindingType.INSECURE_DEFAULT.value,
            InfraFindingType.VERBOSE_ERROR_MESSAGES.value,
        ]
        hardening_types = [
            InfraFindingType.EXPOSED_DEBUG_ENDPOINT.value,
            InfraFindingType.WORLD_WRITABLE.value,
            InfraFindingType.INSECURE_TRANSPORT.value,
            InfraFindingType.MISSING_SECURITY_HEADER.value,
            InfraFindingType.EXPOSED_ADMIN_INTERFACE.value,
            InfraFindingType.DISABLED_SECURITY_FEATURE.value,
        ]

        report.credential_issues = sum(
            1 for f in report.findings if f.finding_type in credential_types
        )
        report.config_issues = sum(
            1 for f in report.findings if f.finding_type in config_types
        )
        report.hardening_issues = sum(
            1 for f in report.findings if f.finding_type in hardening_types
        )

        score = 100.0
        score -= report.critical_issues * 25
        score -= report.high_issues * 10
        score -= report.medium_issues * 5
        score -= report.low_issues * 1
        report.infra_score = max(0.0, score)

    def _severity_order(self, severity: str) -> int:
        """Get sort order for severity (critical first)."""
        order = {
            SecuritySeverity.CRITICAL.value: 0,
            SecuritySeverity.HIGH.value: 1,
            SecuritySeverity.MEDIUM.value: 2,
            SecuritySeverity.LOW.value: 3,
            SecuritySeverity.INFO.value: 4,
        }
        return order.get(severity, 5)

    def get_summary(self, report: InfraReport) -> str:
        """
        Generate a text summary of the infrastructure report.

        Args:
            report: InfraReport to summarize

        Returns:
            Formatted text summary
        """
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("  HEIMDALL INFRASTRUCTURE SECURITY ANALYSIS REPORT")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"  Scan Path:    {report.scan_path}")
        lines.append(f"  Scanned At:   {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  Duration:     {report.scan_duration_seconds:.2f}s")
        lines.append("")
        lines.append("-" * 70)
        lines.append("  SUMMARY")
        lines.append("-" * 70)
        lines.append("")
        lines.append(f"  Infra Score:            {report.infra_score:.1f}/100")
        lines.append(f"  Total Issues:           {report.total_issues}")
        lines.append(f"    Critical:             {report.critical_issues}")
        lines.append(f"    High:                 {report.high_issues}")
        lines.append(f"    Medium:               {report.medium_issues}")
        lines.append(f"    Low:                  {report.low_issues}")
        lines.append("")
        lines.append(f"  Credential Issues:      {report.credential_issues}")
        lines.append(f"  Configuration Issues:   {report.config_issues}")
        lines.append(f"  Hardening Issues:       {report.hardening_issues}")
        lines.append("")
        lines.append(f"  Files Scanned:          {report.total_files_scanned}")
        lines.append(f"  Config Files:           {report.total_config_files}")
        lines.append("")

        if report.has_issues:
            lines.append("-" * 70)
            lines.append("  FINDINGS")
            lines.append("-" * 70)
            lines.append("")

            for finding in report.findings[:10]:
                severity_marker = f"[{finding.severity.upper()}]"
                lines.append(f"  {severity_marker} {finding.title}")
                lines.append(f"    File: {finding.file_path}:{finding.line_number}")
                lines.append(f"    {finding.description}")
                if finding.config_key:
                    lines.append(f"    Config: {finding.config_key}")
                if finding.recommended_value:
                    lines.append(f"    Recommended: {finding.recommended_value}")
                lines.append("")

            if len(report.findings) > 10:
                lines.append(f"  ... and {len(report.findings) - 10} more findings")
                lines.append("")

        lines.append("=" * 70)
        lines.append(f"  RESULT: {'PASS' if report.is_healthy else 'FAIL'}")
        lines.append("=" * 70)
        lines.append("")

        return "\n".join(lines)
