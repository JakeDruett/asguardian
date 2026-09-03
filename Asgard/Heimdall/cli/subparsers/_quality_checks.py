"""
Heimdall CLI - Quality checks subparser registration.

Registers thread-safety, race-conditions, daemon-threads, future-leaks,
blocking-async, resource-cleanup, error-handling, documentation, naming,
bugs, javascript, typescript, shell, rust, rust-clippy, rust-audit,
node-lint, node-audit, node-typecheck, go, go-vet, go-build, go-fmt,
go-test, and go-vuln subcommands onto a quality_subparsers object.
"""

import argparse

from Asgard.Heimdall.cli.common import (
    add_thread_safety_args,
    add_race_conditions_args,
    add_daemon_threads_args,
    add_future_leaks_args,
    add_blocking_async_args,
    add_resource_cleanup_args,
    add_error_handling_args,
    add_documentation_args,
    add_naming_args,
    add_bugs_args,
    add_js_args,
    add_ts_args,
    add_shell_args,
    add_rust_args,
    add_rust_clippy_args,
    add_rust_audit_args,
    add_node_lint_args,
    add_node_audit_args,
    add_node_typecheck_args,
    add_go_args,
    add_go_vet_args,
    add_go_build_args,
    add_go_fmt_args,
    add_go_test_args,
    add_go_vuln_args,
)


def register_quality_check_subcommands(quality_subparsers) -> None:
    """Register safety/checks quality subcommands onto quality_subparsers."""
    quality_thread_safety = quality_subparsers.add_parser(
        "thread-safety",
        help="Detect thread safety issues (uninitialized attrs, shared mutable collections)"
    )
    add_thread_safety_args(quality_thread_safety)

    quality_race_conditions = quality_subparsers.add_parser(
        "race-conditions",
        help="Detect race condition patterns (start-before-store, assign-after-start, check-then-act)"
    )
    add_race_conditions_args(quality_race_conditions)

    quality_daemon_threads = quality_subparsers.add_parser(
        "daemon-threads",
        help="Detect daemon thread lifecycle issues (no join, local var only, event patterns)"
    )
    add_daemon_threads_args(quality_daemon_threads)

    quality_future_leaks = quality_subparsers.add_parser(
        "future-leaks",
        help="Detect futures, tasks, and threads that are created but never resolved"
    )
    add_future_leaks_args(quality_future_leaks)

    quality_blocking_async = quality_subparsers.add_parser(
        "blocking-async",
        help="Detect blocking calls (time.sleep, requests, open, subprocess) inside async functions"
    )
    add_blocking_async_args(quality_blocking_async)

    quality_resource_cleanup = quality_subparsers.add_parser(
        "resource-cleanup",
        help="Detect resource cleanup issues (unclosed files, connections, and context manager violations)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality resource-cleanup ./src\n"
            "  heimdall quality resource-cleanup ./src --severity high\n"
            "  heimdall quality resource-cleanup ./src --include-tests --format json\n"
        ),
    )
    add_resource_cleanup_args(quality_resource_cleanup)

    quality_error_handling = quality_subparsers.add_parser(
        "error-handling",
        help="Detect error handling coverage issues (bare excepts, swallowed exceptions, missing handlers)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality error-handling ./src\n"
            "  heimdall quality error-handling ./src --severity high --format json\n"
            "  heimdall quality error-handling ./src --include-tests\n"
        ),
    )
    add_error_handling_args(quality_error_handling)

    quality_documentation = quality_subparsers.add_parser(
        "documentation",
        help="Scan comment density and public API documentation coverage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality documentation ./src\n"
            "  heimdall quality documentation ./src --min-comment-density 15.0\n"
            "  heimdall quality documentation ./src --min-api-coverage 80.0 --format json\n"
        ),
    )
    add_documentation_args(quality_documentation)

    quality_naming = quality_subparsers.add_parser(
        "naming",
        help="Enforce PEP 8 naming conventions for functions, classes, variables, and constants",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality naming ./src\n"
            "  heimdall quality naming ./src --no-variables --format json\n"
            "  heimdall quality naming ./src --allow MySpecialName --format markdown\n"
        ),
    )
    add_naming_args(quality_naming)

    quality_bugs = quality_subparsers.add_parser(
        "bugs",
        help="Detect null dereferences, unreachable code, and other bugs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality bugs ./src\n"
            "  heimdall quality bugs ./src --null-only\n"
            "  heimdall quality bugs ./src --unreachable-only --format json\n"
        ),
    )
    add_bugs_args(quality_bugs)

    quality_javascript = quality_subparsers.add_parser(
        "javascript",
        help="Analyze JavaScript files for quality issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality javascript ./src\n"
            "  heimdall quality javascript ./src --severity high\n"
            "  heimdall quality javascript ./src --format json\n"
        ),
    )
    add_js_args(quality_javascript)

    quality_typescript = quality_subparsers.add_parser(
        "typescript",
        help="Analyze TypeScript files for quality issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality typescript ./src\n"
            "  heimdall quality typescript ./src --severity high\n"
            "  heimdall quality typescript ./src --format json\n"
        ),
    )
    add_ts_args(quality_typescript)

    quality_shell = quality_subparsers.add_parser(
        "shell",
        help="Analyze shell/bash scripts for quality and security issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality shell ./src\n"
            "  heimdall quality shell ./scripts --severity high\n"
            "  heimdall quality shell ./src --format json\n"
        ),
    )
    add_shell_args(quality_shell)

    quality_rust = quality_subparsers.add_parser(
        "rust",
        help="Analyze Rust files for security and quality issues (pattern-based, no toolchain required)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality rust ./src\n"
            "  heimdall quality rust ./src --severity high\n"
            "  heimdall quality rust ./src --format json\n"
        ),
    )
    add_rust_args(quality_rust)

    quality_rust_clippy = quality_subparsers.add_parser(
        "rust-clippy",
        help="Run cargo clippy over every crate found under a path (requires cargo)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality rust-clippy ./my-crate\n"
            "  heimdall quality rust-clippy ./my-crate --format json\n"
            "  heimdall quality rust-clippy ./my-crate --timeout 600\n"
        ),
    )
    add_rust_clippy_args(quality_rust_clippy)

    quality_rust_audit = quality_subparsers.add_parser(
        "rust-audit",
        help="Scan Cargo.lock for known vulnerabilities via cargo-audit (requires cargo-audit)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality rust-audit ./my-crate\n"
            "  heimdall quality rust-audit ./my-crate --format json\n"
        ),
    )
    add_rust_audit_args(quality_rust_audit)

    quality_node_lint = quality_subparsers.add_parser(
        "node-lint",
        help="Run the project's own ESLint over a Node project (requires an ESLint config)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality node-lint ./frontend\n"
            "  heimdall quality node-lint ./frontend --format json\n"
        ),
    )
    add_node_lint_args(quality_node_lint)

    quality_node_audit = quality_subparsers.add_parser(
        "node-audit",
        help="Scan package.json/package-lock.json for known vulnerabilities via npm audit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality node-audit ./frontend\n"
            "  heimdall quality node-audit ./frontend --format json\n"
        ),
    )
    add_node_audit_args(quality_node_audit)

    quality_node_typecheck = quality_subparsers.add_parser(
        "node-typecheck",
        help="Run tsc --noEmit over a TypeScript project (requires tsconfig.json)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality node-typecheck ./frontend\n"
            "  heimdall quality node-typecheck ./frontend --format json\n"
        ),
    )
    add_node_typecheck_args(quality_node_typecheck)

    quality_go = quality_subparsers.add_parser(
        "go",
        help="Analyze Go files for security and quality issues (pattern-based, no toolchain required)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality go ./src\n"
            "  heimdall quality go ./src --severity high\n"
            "  heimdall quality go ./src --format json\n"
        ),
    )
    add_go_args(quality_go)

    quality_go_vet = quality_subparsers.add_parser(
        "go-vet",
        help="Run go vet over every module found under a path (requires go)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality go-vet ./my-service\n"
            "  heimdall quality go-vet ./my-service --format json\n"
        ),
    )
    add_go_vet_args(quality_go_vet)

    quality_go_build = quality_subparsers.add_parser(
        "go-build",
        help="Run go build over every module found under a path to detect compile failures (requires go)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality go-build ./my-service\n"
            "  heimdall quality go-build ./my-service --format json\n"
        ),
    )
    add_go_build_args(quality_go_build)

    quality_go_fmt = quality_subparsers.add_parser(
        "go-fmt",
        help="Run gofmt -l to detect Go formatting drift (requires go)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality go-fmt ./my-service\n"
            "  heimdall quality go-fmt ./my-service --format json\n"
        ),
    )
    add_go_fmt_args(quality_go_fmt)

    quality_go_test = quality_subparsers.add_parser(
        "go-test",
        help="Run go test -json over every module found under a path and report failing tests (requires go)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality go-test ./my-service\n"
            "  heimdall quality go-test ./my-service --format json\n"
        ),
    )
    add_go_test_args(quality_go_test)

    quality_go_vuln = quality_subparsers.add_parser(
        "go-vuln",
        help="Scan Go modules for known vulnerabilities via govulncheck (requires govulncheck)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  heimdall quality go-vuln ./my-service\n"
            "  heimdall quality go-vuln ./my-service --format json\n"
        ),
    )
    add_go_vuln_args(quality_go_vuln)
