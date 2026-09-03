import argparse


def add_bugs_args(parser: argparse.ArgumentParser) -> None:
    """Add bug detection arguments to a parser."""
    parser.add_argument(
        "path",
        type=str,
        nargs="?",
        default=".",
        help="Root path to scan (default: current directory)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--null-only",
        action="store_true",
        help="Run only null dereference detection",
    )
    parser.add_argument(
        "--unreachable-only",
        action="store_true",
        help="Run only unreachable code detection",
    )
    parser.add_argument(
        "--exclude",
        "-x",
        type=str,
        nargs="+",
        default=[],
        help="Glob patterns for paths to exclude from scanning",
    )


def add_js_args(parser: argparse.ArgumentParser) -> None:
    """Add JavaScript analysis arguments to a parser."""
    parser.add_argument(
        "path",
        type=str,
        nargs="?",
        default=".",
        help="Root path to scan (default: current directory)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--exclude",
        "-x",
        type=str,
        nargs="+",
        default=[],
        help="Additional patterns to exclude",
    )
    parser.add_argument(
        "--max-file-lines",
        type=int,
        default=500,
        help="Maximum file line count threshold (default: 500)",
    )
    parser.add_argument(
        "--max-complexity",
        type=int,
        default=10,
        help="Cyclomatic complexity threshold multiplier (default: 10)",
    )
    parser.add_argument(
        "--disable",
        type=str,
        nargs="+",
        default=[],
        dest="disabled_rules",
        help="Rule IDs to disable",
    )


def add_ts_args(parser: argparse.ArgumentParser) -> None:
    """Add TypeScript analysis arguments to a parser."""
    parser.add_argument(
        "path",
        type=str,
        nargs="?",
        default=".",
        help="Root path to scan (default: current directory)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--exclude",
        "-x",
        type=str,
        nargs="+",
        default=[],
        help="Additional patterns to exclude",
    )
    parser.add_argument(
        "--max-file-lines",
        type=int,
        default=500,
        help="Maximum file line count threshold (default: 500)",
    )
    parser.add_argument(
        "--max-complexity",
        type=int,
        default=10,
        help="Cyclomatic complexity threshold multiplier (default: 10)",
    )
    parser.add_argument(
        "--disable",
        type=str,
        nargs="+",
        default=[],
        dest="disabled_rules",
        help="Rule IDs to disable",
    )


def add_shell_args(parser: argparse.ArgumentParser) -> None:
    """Add shell script analysis arguments to a parser."""
    parser.add_argument(
        "path",
        type=str,
        nargs="?",
        default=".",
        help="Root path to scan (default: current directory)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--exclude",
        "-x",
        type=str,
        nargs="+",
        default=[],
        help="Additional patterns to exclude",
    )
    parser.add_argument(
        "--no-shebang-check",
        action="store_true",
        help="Do not include files with shell shebangs that lack .sh/.bash extension",
    )
    parser.add_argument(
        "--disable",
        type=str,
        nargs="+",
        default=[],
        dest="disabled_rules",
        help="Rule IDs to disable",
    )


def add_rust_args(parser: argparse.ArgumentParser) -> None:
    """Add Rust pattern analysis arguments to a parser."""
    parser.add_argument(
        "path",
        type=str,
        nargs="?",
        default=".",
        help="Root path to scan (default: current directory)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--exclude",
        "-x",
        type=str,
        nargs="+",
        default=[],
        help="Additional patterns to exclude",
    )
    parser.add_argument(
        "--disable",
        type=str,
        nargs="+",
        default=[],
        dest="disabled_rules",
        help="Rule IDs to disable",
    )


def _add_toolchain_common_args(parser: argparse.ArgumentParser, timeout_default: int) -> None:
    """Shared path/format/timeout arguments for toolchain-orchestrating analysers."""
    parser.add_argument(
        "path",
        type=str,
        nargs="?",
        default=".",
        help="Root path to scan (default: current directory)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=timeout_default,
        help=f"Subprocess timeout in seconds (default: {timeout_default})",
    )


def add_rust_clippy_args(parser: argparse.ArgumentParser) -> None:
    """Add cargo clippy orchestration arguments to a parser."""
    _add_toolchain_common_args(parser, timeout_default=300)


def add_rust_audit_args(parser: argparse.ArgumentParser) -> None:
    """Add cargo-audit orchestration arguments to a parser."""
    _add_toolchain_common_args(parser, timeout_default=180)


def add_node_lint_args(parser: argparse.ArgumentParser) -> None:
    """Add ESLint orchestration arguments to a parser."""
    _add_toolchain_common_args(parser, timeout_default=300)


def add_node_audit_args(parser: argparse.ArgumentParser) -> None:
    """Add npm audit orchestration arguments to a parser."""
    _add_toolchain_common_args(parser, timeout_default=180)


def add_node_typecheck_args(parser: argparse.ArgumentParser) -> None:
    """Add tsc orchestration arguments to a parser."""
    _add_toolchain_common_args(parser, timeout_default=300)


def add_issues_args(parser: argparse.ArgumentParser) -> None:
    """Add common issue tracking arguments to a parser."""
    parser.add_argument(
        "path",
        type=str,
        nargs="?",
        default=".",
        help="Project root path (default: current directory)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--status",
        type=str,
        nargs="+",
        default=None,
        help="Filter by status (open, confirmed, resolved, closed, false_positive, wont_fix)",
    )
    parser.add_argument(
        "--severity",
        type=str,
        nargs="+",
        default=None,
        help="Filter by severity (critical, high, medium, low, info)",
    )
    parser.add_argument(
        "--rule",
        type=str,
        default=None,
        help="Filter by rule ID",
    )


