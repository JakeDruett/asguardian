"""
Heimdall Container Analyzer Service

Unified service that orchestrates all container security analyzers.
"""

import time
from pathlib import Path
from typing import Optional

from Asgard.Heimdall.Security.Container.models.container_models import (
    ContainerConfig,
    ContainerFindingType,
    ContainerReport,
)
from Asgard.Heimdall.Security.Container.services.dockerfile_analyzer import DockerfileAnalyzer
from Asgard.Heimdall.Security.Container.services.compose_analyzer import ComposeAnalyzer
from Asgard.Heimdall.Security.models.security_models import SecuritySeverity


class ContainerAnalyzer:
    """
    Unified container security analyzer that combines all container checking services.

    Orchestrates:
    - DockerfileAnalyzer: Dockerfile security analysis
    - ComposeAnalyzer: docker-compose.yml security analysis
    """

    def __init__(self, config: Optional[ContainerConfig] = None):
        """
        Initialize the container analyzer.

        Args:
            config: Container security configuration. Uses defaults if not provided.
        """
        self.config = config or ContainerConfig()
        self.dockerfile_analyzer = DockerfileAnalyzer(self.config)
        self.compose_analyzer = ComposeAnalyzer(self.config)

    def analyze(self, scan_path: Optional[Path] = None) -> ContainerReport:
        """
        Run full container security analysis.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            ContainerReport containing all findings from all analyzers
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        start_time = time.time()

        combined_report = ContainerReport(scan_path=str(path))

        if self.config.check_dockerfile:
            dockerfile_report = self.dockerfile_analyzer.scan(path)
            self._merge_reports(combined_report, dockerfile_report)

        if self.config.check_compose:
            compose_report = self.compose_analyzer.scan(path)
            self._merge_reports(combined_report, compose_report)

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

    def scan(self, scan_path: Optional[Path] = None) -> ContainerReport:
        """
        Alias for analyze() for consistency with other services.

        Args:
            scan_path: Root path to scan

        Returns:
            ContainerReport containing all findings
        """
        return self.analyze(scan_path)

    def scan_dockerfiles_only(self, scan_path: Optional[Path] = None) -> ContainerReport:
        """
        Scan only Dockerfiles for security issues.

        Args:
            scan_path: Root path to scan

        Returns:
            ContainerReport with Dockerfile findings only
        """
        return self.dockerfile_analyzer.scan(scan_path)

    def scan_compose_only(self, scan_path: Optional[Path] = None) -> ContainerReport:
        """
        Scan only docker-compose files for security issues.

        Args:
            scan_path: Root path to scan

        Returns:
            ContainerReport with docker-compose findings only
        """
        return self.compose_analyzer.scan(scan_path)

    def _merge_reports(self, target: ContainerReport, source: ContainerReport) -> None:
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
        target.dockerfiles_analyzed += source.dockerfiles_analyzed
        target.compose_files_analyzed += source.compose_files_analyzed
        target.dockerfile_issues += source.dockerfile_issues
        target.compose_issues += source.compose_issues
        target.findings.extend(source.findings)

    def _recalculate_totals(self, report: ContainerReport) -> None:
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

        dockerfile_types = [
            ContainerFindingType.ROOT_USER.value,
            ContainerFindingType.CHMOD_777.value,
            ContainerFindingType.APT_INSTALL_SUDO.value,
            ContainerFindingType.CURL_PIPE_BASH.value,
            ContainerFindingType.ADD_INSTEAD_OF_COPY.value,
            ContainerFindingType.MISSING_HEALTHCHECK.value,
        ]
        compose_types = [
            ContainerFindingType.PRIVILEGED_MODE.value,
            ContainerFindingType.HOST_NETWORK.value,
            ContainerFindingType.HOST_PID.value,
            ContainerFindingType.CAP_SYS_ADMIN.value,
            ContainerFindingType.UNRESTRICTED_VOLUME.value,
            ContainerFindingType.NO_SECURITY_OPT.value,
            ContainerFindingType.WRITABLE_ROOT_FS.value,
        ]

        report.dockerfile_issues = sum(
            1 for f in report.findings if f.finding_type in dockerfile_types
        )
        report.compose_issues = sum(
            1 for f in report.findings if f.finding_type in compose_types
        )

        score = 100.0
        score -= report.critical_issues * 25
        score -= report.high_issues * 10
        score -= report.medium_issues * 5
        score -= report.low_issues * 1
        report.container_score = max(0.0, score)

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

    def get_summary(self, report: ContainerReport) -> str:
        """
        Generate a text summary of the container security report.

        Args:
            report: ContainerReport to summarize

        Returns:
            Formatted text summary
        """
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("  HEIMDALL CONTAINER SECURITY ANALYSIS REPORT")
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
        lines.append(f"  Container Score:        {report.container_score:.1f}/100")
        lines.append(f"  Total Issues:           {report.total_issues}")
        lines.append(f"    Critical:             {report.critical_issues}")
        lines.append(f"    High:                 {report.high_issues}")
        lines.append(f"    Medium:               {report.medium_issues}")
        lines.append(f"    Low:                  {report.low_issues}")
        lines.append("")
        lines.append(f"  Dockerfiles Analyzed:   {report.dockerfiles_analyzed}")
        lines.append(f"  Compose Files Analyzed: {report.compose_files_analyzed}")
        lines.append(f"  Dockerfile Issues:      {report.dockerfile_issues}")
        lines.append(f"  Compose Issues:         {report.compose_issues}")
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
                if finding.service_name:
                    lines.append(f"    Service: {finding.service_name}")
                lines.append(f"    {finding.description}")
                lines.append("")

            if len(report.findings) > 10:
                lines.append(f"  ... and {len(report.findings) - 10} more findings")
                lines.append("")

        lines.append("=" * 70)
        lines.append(f"  RESULT: {'PASS' if report.is_healthy else 'FAIL'}")
        lines.append("=" * 70)
        lines.append("")

        return "\n".join(lines)
