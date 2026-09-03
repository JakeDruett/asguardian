"""
Rust dependency vulnerability scanning via cargo-audit.

cargo-audit cross-references Cargo.lock against the RustSec Advisory
Database. It is a separate cargo plugin (not bundled with cargo/rustup), so
its absence is reported as an actionable install hint rather than a crash.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from Asgard.Bragi.Quality.languages.common.tool_models import (
    ToolCategory,
    ToolFinding,
    ToolReport,
    ToolSeverity,
)
from Asgard.Bragi.Quality.languages.common.tool_runner import (
    find_manifest_dirs,
    find_optional_executable,
    run_tool,
)
from Asgard.Bragi.Quality.languages.rust.models.rust_toolchain_models import RustAuditConfig

_RUSTSEC_SEVERITY_TO_TOOL = {
    "critical": ToolSeverity.ERROR,
    "high": ToolSeverity.ERROR,
    "medium": ToolSeverity.WARNING,
    "low": ToolSeverity.WARNING,
    "none": ToolSeverity.INFO,
}

INSTALL_HINT = "Install with: cargo install cargo-audit"


class RustAuditAnalyzer:
    """Runs cargo-audit against every Cargo.lock found under a scan path."""

    def __init__(self, config: Optional[RustAuditConfig] = None) -> None:
        self._config = config or RustAuditConfig()

    def analyze(self, scan_path: Optional[Path] = None) -> ToolReport:
        path = Path(scan_path) if scan_path else self._config.scan_path
        path = path.resolve()
        start = datetime.now()

        report = ToolReport(scan_path=str(path), language="rust", tool="cargo-audit")

        audit_bin = find_optional_executable("cargo-audit", path)
        if not audit_bin:
            report.tools_unavailable.append(f"cargo-audit is not installed. {INSTALL_HINT}")
            report.scan_duration_seconds = (datetime.now() - start).total_seconds()
            return report

        lockfile_dirs = find_manifest_dirs(path, "Cargo.lock")
        if not lockfile_dirs:
            report.tools_unavailable.append(f"No Cargo.lock found under {path}; skipping cargo-audit.")
            report.scan_duration_seconds = (datetime.now() - start).total_seconds()
            return report

        report.files_analyzed = len(lockfile_dirs)

        for lock_dir in lockfile_dirs:
            self._audit_lockfile(audit_bin, lock_dir, path, report)
            if self._config.max_findings and report.total_findings >= self._config.max_findings:
                break

        report.scan_duration_seconds = (datetime.now() - start).total_seconds()
        return report

    def _audit_lockfile(self, audit_bin: str, lock_dir: Path, root: Path, report: ToolReport) -> None:
        cmd = [audit_bin, "audit", "--json"]
        result = run_tool(cmd, cwd=lock_dir, timeout=self._config.timeout_seconds)

        if result.timed_out:
            report.tools_unavailable.append(
                f"cargo-audit timed out after {self._config.timeout_seconds}s in {lock_dir}"
            )
            return

        if not result.stdout.strip():
            detail = (result.stderr or "produced no output").strip().splitlines()[-1:] or ["produced no output"]
            report.tools_unavailable.append(f"cargo-audit failed in {lock_dir}: {detail[0]}")
            return

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            report.tools_unavailable.append(f"cargo-audit produced unparseable output in {lock_dir}")
            return

        try:
            relative_lock = str((lock_dir / "Cargo.lock").resolve().relative_to(root))
        except ValueError:
            relative_lock = str(lock_dir / "Cargo.lock")

        vulnerabilities = (payload.get("vulnerabilities") or {}).get("list") or []
        for vuln in vulnerabilities:
            finding = self._finding_from_vulnerability(vuln, relative_lock)
            if finding is not None:
                report.add_finding(finding)
                if self._config.max_findings and report.total_findings >= self._config.max_findings:
                    return

    @staticmethod
    def _finding_from_vulnerability(vuln: dict, relative_lock: str) -> Optional[ToolFinding]:
        advisory = vuln.get("advisory") or {}
        package = vuln.get("package") or {}
        advisory_id = advisory.get("id", "")
        if not advisory_id:
            return None

        severity_str = ""
        cvss = advisory.get("cvss")
        if isinstance(cvss, dict):
            severity_str = str(cvss.get("severity", "")).lower()
        severity = _RUSTSEC_SEVERITY_TO_TOOL.get(severity_str, ToolSeverity.WARNING)

        pkg_name = package.get("name", "unknown")
        pkg_version = package.get("version", "")
        title = advisory.get("title", advisory_id)

        return ToolFinding(
            file_path=relative_lock,
            line_number=0,
            column=0,
            rule_id=advisory_id,
            category=ToolCategory.DEPENDENCY,
            severity=severity,
            title=f"{pkg_name} {pkg_version}: {title}",
            description=advisory.get("description", ""),
            code_snippet="",
            fix_suggestion=(
                f"See {advisory.get('url', 'https://rustsec.org')} for the patched version range."
            ),
            tool="cargo-audit",
        )
