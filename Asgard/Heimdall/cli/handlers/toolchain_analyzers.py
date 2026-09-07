"""
Heimdall CLI handlers for toolchain-orchestrating quality analysers.

Unlike lang_analyzers.py (regex-based, dependency-free JS/TS/Rust/Go scans),
these handlers shell out to each ecosystem's own tool (cargo clippy,
cargo-audit, ESLint, npm audit, tsc, go vet, go build, gofmt, go test,
govulncheck) via
Asgard.Bragi.Quality.languages.common.tool_runner. A missing tool raises
ToolNotAvailableError with an actionable install message, caught here and
printed the same way run_type_check_analysis already handles a missing
mypy/Pyright engine -- never a raw traceback.
"""

import argparse
import json
import traceback as _traceback
from pathlib import Path

from Asgard.Bragi.Quality.languages.common.tool_models import ToolReport
from Asgard.Bragi.Quality.languages.common.tool_runner import ToolNotAvailableError
from Asgard.Bragi.Quality.languages.node.models.node_toolchain_models import (
    NodeAuditConfig,
    NodeLintConfig,
    NodeTypecheckConfig,
)
from Asgard.Bragi.Quality.languages.node.services.node_audit_analyzer import NodeAuditAnalyzer
from Asgard.Bragi.Quality.languages.node.services.node_eslint_analyzer import NodeEslintAnalyzer
from Asgard.Bragi.Quality.languages.node.services.node_typecheck_analyzer import NodeTypecheckAnalyzer
from Asgard.Bragi.Quality.languages.rust.models.rust_toolchain_models import (
    RustAuditConfig,
    RustClippyConfig,
)
from Asgard.Bragi.Quality.languages.rust.services.rust_audit_analyzer import RustAuditAnalyzer
from Asgard.Bragi.Quality.languages.rust.services.rust_clippy_analyzer import RustClippyAnalyzer
from Asgard.Bragi.Quality.languages.go.models.go_toolchain_models import (
    GoBuildConfig,
    GoFmtConfig,
    GoTestConfig,
    GoVetConfig,
    GoVulnConfig,
)
from Asgard.Bragi.Quality.languages.go.services.go_build_analyzer import GoBuildAnalyzer
from Asgard.Bragi.Quality.languages.go.services.go_fmt_analyzer import GoFmtAnalyzer
from Asgard.Bragi.Quality.languages.go.services.go_test_analyzer import GoTestAnalyzer
from Asgard.Bragi.Quality.languages.go.services.go_vet_analyzer import GoVetAnalyzer
from Asgard.Bragi.Quality.languages.go.services.go_vuln_analyzer import GoVulnAnalyzer


def _print_report(report: ToolReport, title: str, output_format: str, verbose: bool) -> int:
    """Render a ToolReport as text or JSON and return the process exit code.

    report.tool_failed marks a genuine execution failure (crash, timeout,
    unparseable output) as distinct from a legitimate empty scan (no
    matching files/manifest, or the tool not installed): it must fail the
    exit code even when zero findings were produced, or a CI pipeline gating
    on this command cannot tell "clean" from "never actually ran".
    """
    if output_format == "json":
        print(json.dumps(report.dict(), default=str, indent=2))
        return 1 if (report.error_count > 0 or report.tool_failed) else 0

    out_lines = [
        "",
        "=" * 70,
        f"  {title}",
        "=" * 70,
        f"  Scan Path:       {report.scan_path}",
        f"  Tool:            {report.tool}",
        f"  Files Analyzed:  {report.files_analyzed}",
        f"  Total Findings:  {report.total_findings}",
        f"  Errors:          {report.error_count}",
        f"  Warnings:        {report.warning_count}",
        f"  Info:            {report.info_count}",
        f"  Duration:        {report.scan_duration_seconds:.2f}s",
        "",
    ]
    if report.tools_unavailable:
        out_lines.extend(["-" * 70, "  SKIPPED", "-" * 70, ""])
        for note in report.tools_unavailable:
            out_lines.append(f"  - {note}")
        out_lines.append("")
    if report.findings:
        out_lines.extend(["-" * 70, "  FINDINGS", "-" * 70, ""])
        for finding in report.findings:
            severity_label = str(finding.severity).upper()
            out_lines.append(f"  [{severity_label}] {finding.rule_id}: {finding.title}")
            out_lines.append(f"  File: {finding.file_path}:{finding.line_number}")
            if verbose:
                out_lines.append(f"  Description: {finding.description}")
                if finding.fix_suggestion:
                    out_lines.append(f"  Fix: {finding.fix_suggestion}")
            out_lines.append("")
    elif not report.tools_unavailable:
        out_lines.extend(["  No findings detected.", ""])
    out_lines.append("=" * 70)
    print("\n".join(out_lines))
    return 1 if (report.error_count > 0 or report.tool_failed) else 0


def run_rust_clippy_analysis(args: argparse.Namespace, verbose: bool = False) -> int:
    try:
        scan_path = Path(args.path).resolve()
        if not scan_path.exists():
            print(f"Error: Path does not exist: {scan_path}")
            return 1

        config = RustClippyConfig(
            scan_path=scan_path,
            timeout_seconds=getattr(args, "timeout", 300),
        )
        report = RustClippyAnalyzer(config).analyze()
        return _print_report(report, "RUST CLIPPY ANALYSIS REPORT", getattr(args, "format", "text"), verbose)

    except ToolNotAvailableError as exc:
        print(f"Error: {exc}")
        return 1
    except Exception as exc:
        print(f"Error: {exc}")
        if verbose:
            _traceback.print_exc()
        return 1


def run_rust_audit_analysis(args: argparse.Namespace, verbose: bool = False) -> int:
    try:
        scan_path = Path(args.path).resolve()
        if not scan_path.exists():
            print(f"Error: Path does not exist: {scan_path}")
            return 1

        config = RustAuditConfig(
            scan_path=scan_path,
            timeout_seconds=getattr(args, "timeout", 180),
        )
        report = RustAuditAnalyzer(config).analyze()
        return _print_report(report, "RUST DEPENDENCY AUDIT REPORT", getattr(args, "format", "text"), verbose)

    except ToolNotAvailableError as exc:
        print(f"Error: {exc}")
        return 1
    except Exception as exc:
        print(f"Error: {exc}")
        if verbose:
            _traceback.print_exc()
        return 1


def run_node_lint_analysis(args: argparse.Namespace, verbose: bool = False) -> int:
    try:
        scan_path = Path(args.path).resolve()
        if not scan_path.exists():
            print(f"Error: Path does not exist: {scan_path}")
            return 1

        config = NodeLintConfig(
            scan_path=scan_path,
            timeout_seconds=getattr(args, "timeout", 300),
        )
        report = NodeEslintAnalyzer(config).analyze()
        return _print_report(report, "NODE ESLINT ANALYSIS REPORT", getattr(args, "format", "text"), verbose)

    except ToolNotAvailableError as exc:
        print(f"Error: {exc}")
        return 1
    except Exception as exc:
        print(f"Error: {exc}")
        if verbose:
            _traceback.print_exc()
        return 1


def run_node_audit_analysis(args: argparse.Namespace, verbose: bool = False) -> int:
    try:
        scan_path = Path(args.path).resolve()
        if not scan_path.exists():
            print(f"Error: Path does not exist: {scan_path}")
            return 1

        config = NodeAuditConfig(
            scan_path=scan_path,
            timeout_seconds=getattr(args, "timeout", 180),
        )
        report = NodeAuditAnalyzer(config).analyze()
        return _print_report(report, "NODE DEPENDENCY AUDIT REPORT", getattr(args, "format", "text"), verbose)

    except ToolNotAvailableError as exc:
        print(f"Error: {exc}")
        return 1
    except Exception as exc:
        print(f"Error: {exc}")
        if verbose:
            _traceback.print_exc()
        return 1


def run_node_typecheck_analysis(args: argparse.Namespace, verbose: bool = False) -> int:
    try:
        scan_path = Path(args.path).resolve()
        if not scan_path.exists():
            print(f"Error: Path does not exist: {scan_path}")
            return 1

        config = NodeTypecheckConfig(
            scan_path=scan_path,
            timeout_seconds=getattr(args, "timeout", 300),
        )
        report = NodeTypecheckAnalyzer(config).analyze()
        return _print_report(report, "NODE TYPESCRIPT TYPE CHECK REPORT", getattr(args, "format", "text"), verbose)

    except ToolNotAvailableError as exc:
        print(f"Error: {exc}")
        return 1
    except Exception as exc:
        print(f"Error: {exc}")
        if verbose:
            _traceback.print_exc()
        return 1


def run_go_vet_analysis(args: argparse.Namespace, verbose: bool = False) -> int:
    try:
        scan_path = Path(args.path).resolve()
        if not scan_path.exists():
            print(f"Error: Path does not exist: {scan_path}")
            return 1

        config = GoVetConfig(
            scan_path=scan_path,
            timeout_seconds=getattr(args, "timeout", 180),
        )
        report = GoVetAnalyzer(config).analyze()
        return _print_report(report, "GO VET ANALYSIS REPORT", getattr(args, "format", "text"), verbose)

    except ToolNotAvailableError as exc:
        print(f"Error: {exc}")
        return 1
    except Exception as exc:
        print(f"Error: {exc}")
        if verbose:
            _traceback.print_exc()
        return 1


def run_go_build_analysis(args: argparse.Namespace, verbose: bool = False) -> int:
    try:
        scan_path = Path(args.path).resolve()
        if not scan_path.exists():
            print(f"Error: Path does not exist: {scan_path}")
            return 1

        config = GoBuildConfig(
            scan_path=scan_path,
            timeout_seconds=getattr(args, "timeout", 300),
        )
        report = GoBuildAnalyzer(config).analyze()
        return _print_report(report, "GO BUILD ANALYSIS REPORT", getattr(args, "format", "text"), verbose)

    except ToolNotAvailableError as exc:
        print(f"Error: {exc}")
        return 1
    except Exception as exc:
        print(f"Error: {exc}")
        if verbose:
            _traceback.print_exc()
        return 1


def run_go_fmt_analysis(args: argparse.Namespace, verbose: bool = False) -> int:
    try:
        scan_path = Path(args.path).resolve()
        if not scan_path.exists():
            print(f"Error: Path does not exist: {scan_path}")
            return 1

        config = GoFmtConfig(
            scan_path=scan_path,
            timeout_seconds=getattr(args, "timeout", 120),
        )
        report = GoFmtAnalyzer(config).analyze()
        return _print_report(report, "GOFMT ANALYSIS REPORT", getattr(args, "format", "text"), verbose)

    except ToolNotAvailableError as exc:
        print(f"Error: {exc}")
        return 1
    except Exception as exc:
        print(f"Error: {exc}")
        if verbose:
            _traceback.print_exc()
        return 1


def run_go_test_analysis(args: argparse.Namespace, verbose: bool = False) -> int:
    try:
        scan_path = Path(args.path).resolve()
        if not scan_path.exists():
            print(f"Error: Path does not exist: {scan_path}")
            return 1

        config = GoTestConfig(
            scan_path=scan_path,
            timeout_seconds=getattr(args, "timeout", 600),
        )
        report = GoTestAnalyzer(config).analyze()
        return _print_report(report, "GO TEST RESULTS REPORT", getattr(args, "format", "text"), verbose)

    except ToolNotAvailableError as exc:
        print(f"Error: {exc}")
        return 1
    except Exception as exc:
        print(f"Error: {exc}")
        if verbose:
            _traceback.print_exc()
        return 1


def run_go_vuln_analysis(args: argparse.Namespace, verbose: bool = False) -> int:
    try:
        scan_path = Path(args.path).resolve()
        if not scan_path.exists():
            print(f"Error: Path does not exist: {scan_path}")
            return 1

        config = GoVulnConfig(
            scan_path=scan_path,
            timeout_seconds=getattr(args, "timeout", 300),
        )
        report = GoVulnAnalyzer(config).analyze()
        return _print_report(report, "GO DEPENDENCY VULNERABILITY REPORT", getattr(args, "format", "text"), verbose)

    except ToolNotAvailableError as exc:
        print(f"Error: {exc}")
        return 1
    except Exception as exc:
        print(f"Error: {exc}")
        if verbose:
            _traceback.print_exc()
        return 1
