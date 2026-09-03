"""
Node dependency vulnerability scanning via npm audit.

npm audit cross-references package-lock.json against the npm/GitHub
Advisory Database. Unlike cargo-audit, npm ships with Node itself, so the
only "not available" case is Node/npm missing entirely; a missing
package-lock.json (or no network access to the registry) is reported as a
skipped, non-fatal condition instead.
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
    require_executable,
    run_tool,
)
from Asgard.Bragi.Quality.languages.node.models.node_toolchain_models import NodeAuditConfig

_NPM_SEVERITY_TO_TOOL = {
    "critical": ToolSeverity.ERROR,
    "high": ToolSeverity.ERROR,
    "moderate": ToolSeverity.WARNING,
    "low": ToolSeverity.INFO,
    "info": ToolSeverity.INFO,
}

INSTALL_HINT = "Install Node.js (which bundles npm) from https://nodejs.org"


class NodeAuditAnalyzer:
    """Runs npm audit against a Node project and normalises the output."""

    def __init__(self, config: Optional[NodeAuditConfig] = None) -> None:
        self._config = config or NodeAuditConfig()

    def analyze(self, scan_path: Optional[Path] = None) -> ToolReport:
        path = Path(scan_path) if scan_path else self._config.scan_path
        path = path.resolve()
        start = datetime.now()

        report = ToolReport(scan_path=str(path), language="node", tool="npm-audit")

        npm_bin = require_executable("npm", path, INSTALL_HINT)

        if not (path / "package.json").is_file():
            report.tools_unavailable.append(f"No package.json found under {path}; skipping npm audit.")
            report.scan_duration_seconds = (datetime.now() - start).total_seconds()
            return report

        result = run_tool([npm_bin, "audit", "--json"], cwd=path, timeout=self._config.timeout_seconds)

        if result.timed_out:
            report.tools_unavailable.append(f"npm audit timed out after {self._config.timeout_seconds}s")
            report.tool_failed = True
            report.scan_duration_seconds = (datetime.now() - start).total_seconds()
            return report

        if not result.stdout.strip():
            detail = (result.stderr or "produced no output").strip().splitlines()[-1:] or ["produced no output"]
            report.tools_unavailable.append(f"npm audit failed to run: {detail[0]}")
            report.tool_failed = True
            report.scan_duration_seconds = (datetime.now() - start).total_seconds()
            return report

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            report.tools_unavailable.append("npm audit produced unparseable output")
            report.tool_failed = True
            report.scan_duration_seconds = (datetime.now() - start).total_seconds()
            return report

        # npm's own top-level "error" (e.g. ENOAUDIT for an unreachable
        # registry) means the audit itself did not run, not that it ran and
        # found nothing.
        top_level_error = payload.get("error")
        if top_level_error:
            summary = top_level_error.get("summary") or top_level_error.get("code") or "unknown error"
            report.tools_unavailable.append(f"npm audit could not reach the registry: {summary}")
            report.tool_failed = True
            report.scan_duration_seconds = (datetime.now() - start).total_seconds()
            return report

        vulnerabilities = payload.get("vulnerabilities") or {}
        report.files_analyzed = 1
        for pkg_name, entry in vulnerabilities.items():
            finding = self._finding_from_entry(pkg_name, entry)
            if finding is not None:
                report.add_finding(finding)
                if self._config.max_findings and report.total_findings >= self._config.max_findings:
                    break

        report.scan_duration_seconds = (datetime.now() - start).total_seconds()
        return report

    @staticmethod
    def _finding_from_entry(pkg_name: str, entry: dict) -> Optional[ToolFinding]:
        severity_str = str(entry.get("severity", "")).lower()
        severity = _NPM_SEVERITY_TO_TOOL.get(severity_str)
        if severity is None:
            return None

        advisories = [v for v in (entry.get("via") or []) if isinstance(v, dict)]
        titles = [a.get("title", "") for a in advisories if a.get("title")]
        urls = [a.get("url", "") for a in advisories if a.get("url")]

        description = "; ".join(titles) if titles else (
            f"{pkg_name} is a transitive dependency of a vulnerable package"
        )
        fix_available = entry.get("fixAvailable")
        fix_suggestion = ""
        if fix_available is True:
            fix_suggestion = "Fix available: run npm audit fix."
        elif isinstance(fix_available, dict):
            fix_name = fix_available.get("name", pkg_name)
            fix_version = fix_available.get("version", "")
            fix_suggestion = f"Fix available: upgrade {fix_name} to {fix_version} (npm audit fix)."
        elif urls:
            fix_suggestion = f"See {urls[0]}"

        return ToolFinding(
            file_path="package.json",
            line_number=0,
            column=0,
            rule_id=f"npm-audit::{pkg_name}",
            category=ToolCategory.DEPENDENCY,
            severity=severity,
            title=f"{pkg_name}: {severity_str} severity vulnerability",
            description=description,
            code_snippet="",
            fix_suggestion=fix_suggestion,
            tool="npm-audit",
        )
