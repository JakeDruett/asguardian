"""
Go dependency vulnerability scanning via govulncheck.

govulncheck (golang.org/x/vuln/cmd/govulncheck) is the Go team's own
vulnerability scanner, chosen over a third-party OSS-Index-style tool
(e.g. Sonatype Nancy) because it is source-aware rather than manifest-only:
it walks the call graph and reports whether a vulnerable symbol is actually
reachable from the scanned code, not just present in go.sum. It is a
separate, `go install`-able tool (not bundled with the go command), so its
absence is reported as an actionable install hint rather than a crash --
the same optional-tool treatment as RustAuditAnalyzer's cargo-audit and
NodeAuditAnalyzer's npm audit.

Schema note (the same trap that made cargo-audit's original severity
mapping silently wrong): govulncheck's Go vulnerability database has no
CVSS or numeric severity field at all -- confirmed against the pinned
library's own source, golang.org/x/vuln@v1.7.0's internal/osv.Entry and
internal/govulncheck.Message/Finding/Frame structs (this analyser targets
that exact version; see pyproject.toml). What it reports instead is call
reachability: a Finding's first trace frame carries a Function when the
vulnerable symbol is actually called, a Package (no Function) when the
vulnerable package is only imported, or neither when the vulnerable module
is merely required. That distinction -- not a severity string -- is what
this analyser maps to ToolSeverity, and it is also exactly what flips
govulncheck's own exit code to 3 (see internal/scan/text.go's
isCalled/errVulnerabilitiesFound), which is why exit 3 is treated as a
normal "findings present" outcome below, not a failure.

A real `govulncheck -json ./...` run (v1.7.0, built from this sandbox's
module cache and run against Lexicon/LexiconGo) was captured to verify the
`config`/`SBOM` message shapes -- and it caught a second, real shape
mistake: despite "streaming JSON" in the package doc, govulncheck's actual
`-json` output is NOT newline-delimited JSON. Each Message is pretty-
printed with indentation and spans many lines, with the next Message
starting immediately after on the same line the previous one closed on.
A naive `line.strip(); json.loads(line)` per output line (the shape every
other tool orchestrated in this package actually uses) parses zero
complete messages against real output and would have silently reported an
empty, "clean" scan every time. `_decode_message_stream` below instead
feeds the whole output through `json.JSONDecoder.raw_decode` in a loop,
which is shape-agnostic to line breaks.

The vulnerability database itself (vuln.go.dev) was unreachable in this
sandbox (403 Forbidden), so no real `osv`/`finding` messages could be
captured live -- exercising that scenario is itself the tool_failed
regression test below, since a DB fetch failure is exactly the
"looks-clean-but-actually-crashed" trap this analyser must not fall into.
The `osv`/`finding` shapes used by the parser and its tests come directly
from the pinned library source, not a guess.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

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
from Asgard.Bragi.Quality.languages.go.models.go_toolchain_models import GoVulnConfig

INSTALL_HINT = "Install with: go install golang.org/x/vuln/cmd/govulncheck@latest"

_SEVERITY_RANK = {ToolSeverity.INFO.value: 0, ToolSeverity.WARNING.value: 1, ToolSeverity.ERROR.value: 2}


def _severity_rank(severity) -> int:
    # ToolFinding stores severity as a plain string (Config.use_enum_values
    # = True on the shared model), but the ToolSeverity member is also
    # accepted defensively here since this helper runs before/after
    # ToolFinding construction depending on caller.
    value = severity.value if hasattr(severity, "value") else severity
    return _SEVERITY_RANK.get(value, -1)


_JSON_DECODER = json.JSONDecoder()


class GoVulnAnalyzer:
    """Runs govulncheck against every module found under a scan path and normalises the output."""

    @staticmethod
    def _decode_message_stream(text: str) -> Iterator[Any]:
        """
        Yield each top-level JSON value from a stream of back-to-back,
        pretty-printed JSON objects with no delimiter between them.

        govulncheck's `-json` output is not newline-delimited JSON (unlike
        `go test -json`/cargo clippy's `--message-format=json`): each
        Message is indented across many lines, and the next Message begins
        immediately where the previous one's closing brace ended, on that
        same line. `json.loads` per line therefore parses nothing; this
        walks the raw text with `raw_decode`, which stops at the end of
        one complete value regardless of line breaks.
        """
        index = 0
        length = len(text)
        while index < length:
            while index < length and text[index].isspace():
                index += 1
            if index >= length:
                return
            try:
                value, end = _JSON_DECODER.raw_decode(text, index)
            except json.JSONDecodeError:
                return
            yield value
            index = end

    def __init__(self, config: Optional[GoVulnConfig] = None) -> None:
        self._config = config or GoVulnConfig()

    def analyze(self, scan_path: Optional[Path] = None) -> ToolReport:
        path = Path(scan_path) if scan_path else self._config.scan_path
        path = path.resolve()
        start = datetime.now()

        report = ToolReport(scan_path=str(path), language="go", tool="govulncheck")

        govulncheck_bin = find_optional_executable("govulncheck", path)
        if not govulncheck_bin:
            report.tools_unavailable.append(f"govulncheck is not installed. {INSTALL_HINT}")
            report.scan_duration_seconds = (datetime.now() - start).total_seconds()
            return report

        module_dirs = find_manifest_dirs(path, "go.mod")
        if not module_dirs:
            report.tools_unavailable.append(f"No go.mod found under {path}; skipping govulncheck.")
            report.scan_duration_seconds = (datetime.now() - start).total_seconds()
            return report

        report.files_analyzed = len(module_dirs)

        for module_dir in module_dirs:
            self._scan_module(govulncheck_bin, module_dir, path, report)
            if self._config.max_findings and report.total_findings >= self._config.max_findings:
                break

        report.scan_duration_seconds = (datetime.now() - start).total_seconds()
        return report

    def _scan_module(self, govulncheck_bin: str, module_dir: Path, root: Path, report: ToolReport) -> None:
        cmd = [govulncheck_bin, "-json", "./..."]
        result = run_tool(cmd, cwd=module_dir, timeout=self._config.timeout_seconds)

        if result.timed_out:
            report.tools_unavailable.append(
                f"govulncheck timed out after {self._config.timeout_seconds}s in {module_dir}"
            )
            report.tool_failed = True
            return

        osv_entries: Dict[str, dict] = {}
        raw_findings: List[dict] = []
        messages_parsed = 0

        for message in self._decode_message_stream(result.stdout):
            if not isinstance(message, dict):
                continue
            messages_parsed += 1
            osv = message.get("osv")
            if isinstance(osv, dict) and osv.get("id"):
                osv_entries[osv["id"]] = osv
            finding = message.get("finding")
            if isinstance(finding, dict) and finding.get("osv"):
                raw_findings.append(finding)

        if messages_parsed == 0 or (result.returncode not in (0, 3) and not raw_findings and not osv_entries):
            # Exit 0 = clean, exit 3 = vulnerabilities found (govulncheck's
            # own documented codes -- see the module docstring). Any other
            # exit code with nothing parsed from the JSON stream (the
            # vulnerability database being unreachable produces exactly
            # this: valid config/SBOM messages, a plain-text error on
            # stderr, exit 1) is a genuine failure, not a clean scan.
            detail_lines = (result.stderr or result.stdout or "").strip().splitlines()
            detail = detail_lines[-1] if detail_lines else "produced no parseable output"
            report.tools_unavailable.append(
                f"govulncheck failed in {module_dir} (exit {result.returncode}): {detail}"
            )
            report.tool_failed = True
            return

        best_by_osv: Dict[str, ToolFinding] = {}
        for raw in raw_findings:
            finding = self._finding_from_raw(raw, osv_entries.get(raw["osv"], {}), module_dir, root)
            if finding is None:
                continue
            existing = best_by_osv.get(finding.rule_id)
            if existing is None or _severity_rank(finding.severity) > _severity_rank(existing.severity):
                best_by_osv[finding.rule_id] = finding

        for finding in best_by_osv.values():
            report.add_finding(finding)
            if self._config.max_findings and report.total_findings >= self._config.max_findings:
                report.tool_failed = True
                report.tools_unavailable.append("govulncheck finding limit reached; remaining vulnerabilities are unverified")
                return

    @staticmethod
    def _finding_from_raw(raw: dict, osv_entry: dict, module_dir: Path, root: Path) -> Optional[ToolFinding]:
        osv_id = raw.get("osv")
        if not osv_id:
            return None

        trace = raw.get("trace") or []
        top_frame = trace[0] if trace else {}
        function = top_frame.get("function") or ""
        package = top_frame.get("package") or ""

        if function:
            severity = ToolSeverity.ERROR
            call_state = "called from your code"
        elif package:
            severity = ToolSeverity.WARNING
            call_state = "imported but not called"
        else:
            severity = ToolSeverity.INFO
            call_state = "required but not imported"

        file_path = "go.mod"
        line_number = 0
        column = 0
        position = top_frame.get("position") or {}
        if position.get("filename"):
            try:
                absolute = (module_dir / position["filename"]).resolve()
                file_path = str(absolute.relative_to(root))
            except ValueError:
                file_path = position["filename"]
            line_number = position.get("line", 0) or 0
            column = position.get("column", 0) or 0

        module_path = top_frame.get("module") or package or "unknown module"
        summary = osv_entry.get("summary") or osv_entry.get("details", "")[:200] or osv_id
        fixed_version = raw.get("fixed_version") or ""
        if fixed_version:
            fix_suggestion = f"Upgrade {module_path} to {fixed_version}."
        else:
            db_specific = osv_entry.get("database_specific") or {}
            fix_suggestion = f"See {db_specific.get('url', 'https://pkg.go.dev/' + osv_id)} for remediation."

        return ToolFinding(
            file_path=file_path,
            line_number=line_number,
            column=column,
            rule_id=osv_id,
            category=ToolCategory.DEPENDENCY,
            severity=severity,
            title=f"{module_path}: {summary}",
            description=(osv_entry.get("details") or summary) + f" ({call_state})",
            code_snippet="",
            fix_suggestion=fix_suggestion,
            tool="govulncheck",
        )
