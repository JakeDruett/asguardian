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

# CVSS v3.1 base metric weights, per the published FIRST.org specification
# (https://www.first.org/cvss/v3.1/specification-document, sections 7.4/7.5).
# cargo-audit's `--json` output stores an advisory's `cvss` field as this raw
# vector string (e.g. "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"), not a
# pre-computed severity, so the qualitative rating must be derived here rather
# than read off a "severity" key that does not exist in the real tool output.
_CVSS_V3_AV = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20}
_CVSS_V3_AC = {"L": 0.77, "H": 0.44}
_CVSS_V3_PR_UNCHANGED = {"N": 0.85, "L": 0.62, "H": 0.27}
_CVSS_V3_PR_CHANGED = {"N": 0.85, "L": 0.68, "H": 0.50}
_CVSS_V3_UI = {"N": 0.85, "R": 0.62}
_CVSS_V3_IMPACT = {"H": 0.56, "L": 0.22, "N": 0.0}


def _cvss_v3_roundup(value: float) -> float:
    """CVSS spec's Roundup function: smallest number with one decimal >= value."""
    int_value = round(value * 100000)
    if int_value % 10000 == 0:
        return int_value / 100000.0
    return (int_value // 10000 + 1) / 10.0


def _cvss_v3_base_severity(vector: str) -> Optional[str]:
    """
    Compute the qualitative severity ("critical"/"high"/"medium"/"low"/"none")
    of a CVSS v3.x base vector string.

    Returns None (unknown, not a guess) for anything that is not a
    recognisable CVSS v3 base vector, e.g. a CVSS v2 vector on an older
    advisory, so callers fall back to an explicit default rather than
    silently mis-rating.
    """
    if not vector or not vector.startswith("CVSS:3"):
        return None

    metrics = {}
    for part in vector.split("/"):
        if ":" not in part:
            continue
        key, _, value = part.partition(":")
        metrics[key] = value

    try:
        av = _CVSS_V3_AV[metrics["AV"]]
        ac = _CVSS_V3_AC[metrics["AC"]]
        ui = _CVSS_V3_UI[metrics["UI"]]
        scope_changed = metrics["S"] == "C"
        pr_table = _CVSS_V3_PR_CHANGED if scope_changed else _CVSS_V3_PR_UNCHANGED
        pr = pr_table[metrics["PR"]]
        conf = _CVSS_V3_IMPACT[metrics["C"]]
        integ = _CVSS_V3_IMPACT[metrics["I"]]
        avail = _CVSS_V3_IMPACT[metrics["A"]]
    except KeyError:
        return None

    isc_base = 1 - ((1 - conf) * (1 - integ) * (1 - avail))
    if scope_changed:
        impact = 7.52 * (isc_base - 0.029) - 3.25 * ((isc_base - 0.02) ** 15)
    else:
        impact = 6.42 * isc_base

    exploitability = 8.22 * av * ac * pr * ui

    if impact <= 0:
        base_score = 0.0
    elif scope_changed:
        base_score = _cvss_v3_roundup(min(1.08 * (impact + exploitability), 10.0))
    else:
        base_score = _cvss_v3_roundup(min(impact + exploitability, 10.0))

    if base_score == 0.0:
        return "none"
    if base_score < 4.0:
        return "low"
    if base_score < 7.0:
        return "medium"
    if base_score < 9.0:
        return "high"
    return "critical"


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
            report.tool_failed = True
            return

        if not result.stdout.strip():
            detail = (result.stderr or "produced no output").strip().splitlines()[-1:] or ["produced no output"]
            report.tools_unavailable.append(f"cargo-audit failed in {lock_dir}: {detail[0]}")
            report.tool_failed = True
            return

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            report.tools_unavailable.append(f"cargo-audit produced unparseable output in {lock_dir}")
            report.tool_failed = True
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
            # Defensive: not the real cargo-audit shape (which is a raw CVSS
            # vector string, handled below), but accepted in case a future
            # or third-party cargo-audit build ever pre-computes this.
            severity_str = str(cvss.get("severity", "")).lower()
        elif isinstance(cvss, str):
            severity_str = _cvss_v3_base_severity(cvss) or ""
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
