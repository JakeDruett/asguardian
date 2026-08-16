import json
import os
import subprocess
from pathlib import Path
from typing import List, Optional

from Asgard.Bragi.Quality.models.syntax_models import (
    LinterType,
    SyntaxConfig,
    SyntaxIssue,
    SyntaxSeverity,
)
from Asgard.Bragi.Quality.services._tool_isolation import (
    argv_with_paths,
    isolated_tool_workspace,
    trusted_executable,
    write_isolated_mypy_ini,
    write_isolated_pylint_rc,
)


def _run_isolated(cmd: List[str], timeout: int, cwd: Path, env: Optional[dict] = None):
    """Run *cmd* with cwd in an Asgard-owned empty directory."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        cwd=str(cwd),
        env=env,
    )


def run_ruff(scan_path: Path, config: SyntaxConfig) -> List[SyntaxIssue]:
    """Run ruff linter and parse output."""
    issues = []
    scan_path = Path(scan_path).resolve()
    ruff_bin = trusted_executable("ruff", scan_path)
    if not ruff_bin:
        return issues

    try:
        exclude_args = []
        for pattern in config.exclude_patterns:
            exclude_args.extend(["--exclude", pattern])

        cmd = argv_with_paths(
            [ruff_bin, "check", "--isolated", "--output-format", "json", *exclude_args],
            scan_path,
        )

        with isolated_tool_workspace() as workdir:
            result = _run_isolated(cmd, timeout=300, cwd=workdir)

        if result.stdout:
            try:
                findings = json.loads(result.stdout)
                for finding in findings:
                    severity = _ruff_severity(finding.get("fix"))
                    issue = SyntaxIssue(
                        file_path=finding.get("filename", ""),
                        line_number=finding.get("location", {}).get("row", 0),
                        column=finding.get("location", {}).get("column", 0),
                        code=finding.get("code", ""),
                        message=finding.get("message", ""),
                        severity=severity,
                        linter=LinterType.RUFF,
                        fixable=finding.get("fix") is not None,
                        suggested_fix=finding.get("fix", {}).get("message") if finding.get("fix") else None,
                    )
                    issues.append(issue)
            except json.JSONDecodeError:
                pass

    except subprocess.TimeoutExpired:
        pass
    except FileNotFoundError:
        pass

    return issues


def run_ruff_fix(scan_path: Path, config: SyntaxConfig) -> int:
    """Run ruff with --fix and return number of fixes."""
    scan_path = Path(scan_path).resolve()
    ruff_bin = trusted_executable("ruff", scan_path)
    if not ruff_bin:
        return 0

    try:
        exclude_args = []
        for pattern in config.exclude_patterns:
            exclude_args.extend(["--exclude", pattern])

        cmd = argv_with_paths(
            [ruff_bin, "check", "--isolated", "--fix", "--output-format", "json", *exclude_args],
            scan_path,
        )

        with isolated_tool_workspace() as workdir:
            result = _run_isolated(cmd, timeout=300, cwd=workdir)

        if result.stdout:
            try:
                findings = json.loads(result.stdout)
                return sum(1 for f in findings if f.get("fix"))
            except json.JSONDecodeError:
                pass

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return 0


def run_flake8(scan_path: Path, config: SyntaxConfig) -> List[SyntaxIssue]:
    """Run flake8 linter and parse output."""
    issues = []
    scan_path = Path(scan_path).resolve()
    flake8_bin = trusted_executable("flake8", scan_path)
    if not flake8_bin:
        return issues

    try:
        exclude_str = ",".join(config.exclude_patterns)

        cmd = argv_with_paths(
            [
                flake8_bin,
                "--isolated",
                "--format", "%(path)s:%(row)d:%(col)d:%(code)s:%(text)s",
                "--exclude", exclude_str,
            ],
            scan_path,
        )

        with isolated_tool_workspace() as workdir:
            result = _run_isolated(cmd, timeout=300, cwd=workdir)

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split(":", 4)
            if len(parts) >= 5:
                severity = _flake8_severity(parts[3])
                issue = SyntaxIssue(
                    file_path=parts[0],
                    line_number=int(parts[1]) if parts[1].isdigit() else 0,
                    column=int(parts[2]) if parts[2].isdigit() else 0,
                    code=parts[3],
                    message=parts[4],
                    severity=severity,
                    linter=LinterType.FLAKE8,
                    fixable=False,
                )
                issues.append(issue)

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return issues


def run_pylint(scan_path: Path, config: SyntaxConfig) -> List[SyntaxIssue]:
    """Run pylint and parse output."""
    issues = []
    scan_path = Path(scan_path).resolve()
    pylint_bin = trusted_executable("pylint", scan_path)
    if not pylint_bin:
        return issues

    try:
        ignore_str = ",".join(config.exclude_patterns)

        with isolated_tool_workspace() as workdir:
            rcfile = write_isolated_pylint_rc(workdir)
            cmd = argv_with_paths(
                [
                    pylint_bin,
                    "--rcfile", str(rcfile),
                    "--init-hook=",
                    "--output-format", "json",
                    "--ignore", ignore_str,
                ],
                scan_path,
            )
            env = os.environ.copy()
            env["PYLINTRC"] = str(rcfile)
            result = _run_isolated(cmd, timeout=300, cwd=workdir, env=env)

        if result.stdout:
            try:
                findings = json.loads(result.stdout)
                for finding in findings:
                    severity = _pylint_severity(finding.get("type", ""))
                    issue = SyntaxIssue(
                        file_path=finding.get("path", ""),
                        line_number=finding.get("line", 0),
                        column=finding.get("column", 0),
                        code=finding.get("message-id", ""),
                        message=finding.get("message", ""),
                        severity=severity,
                        linter=LinterType.PYLINT,
                        fixable=False,
                    )
                    issues.append(issue)
            except json.JSONDecodeError:
                pass

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return issues


def run_mypy(scan_path: Path, config: SyntaxConfig) -> List[SyntaxIssue]:
    """Run mypy type checker and parse output."""
    issues = []
    scan_path = Path(scan_path).resolve()
    mypy_bin = trusted_executable("mypy", scan_path)
    if not mypy_bin:
        return issues

    try:
        exclude_pattern = "|".join(config.exclude_patterns)

        with isolated_tool_workspace() as workdir:
            config_file = write_isolated_mypy_ini(workdir)
            cmd = argv_with_paths(
                [
                    mypy_bin,
                    "--config-file", str(config_file),
                    "--no-incremental",
                    "--explicit-package-bases",
                    "--output", "json",
                    "--exclude", exclude_pattern,
                ],
                scan_path,
            )
            result = _run_isolated(cmd, timeout=300, cwd=workdir)

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                finding = json.loads(line)
                severity = _mypy_severity(finding.get("severity", "error"))
                issue = SyntaxIssue(
                    file_path=finding.get("file", ""),
                    line_number=finding.get("line", 0),
                    column=finding.get("column", 0),
                    code=finding.get("code", "mypy"),
                    message=finding.get("message", ""),
                    severity=severity,
                    linter=LinterType.MYPY,
                    fixable=False,
                )
                issues.append(issue)
            except json.JSONDecodeError:
                pass

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return issues


def _ruff_severity(fix_info: Optional[dict]) -> SyntaxSeverity:
    """Convert ruff fix info to severity."""
    return SyntaxSeverity.WARNING


def _flake8_severity(code: str) -> SyntaxSeverity:
    """Convert flake8 code to severity."""
    if code.startswith("E"):
        return SyntaxSeverity.ERROR
    elif code.startswith("W"):
        return SyntaxSeverity.WARNING
    elif code.startswith("F"):
        return SyntaxSeverity.ERROR
    elif code.startswith("C"):
        return SyntaxSeverity.STYLE
    return SyntaxSeverity.INFO


def _pylint_severity(msg_type: str) -> SyntaxSeverity:
    """Convert pylint message type to severity."""
    type_map = {
        "error": SyntaxSeverity.ERROR,
        "fatal": SyntaxSeverity.ERROR,
        "warning": SyntaxSeverity.WARNING,
        "convention": SyntaxSeverity.STYLE,
        "refactor": SyntaxSeverity.INFO,
        "information": SyntaxSeverity.INFO,
    }
    return type_map.get(msg_type.lower(), SyntaxSeverity.WARNING)


def _mypy_severity(severity: str) -> SyntaxSeverity:
    """Convert mypy severity to our severity."""
    severity_map = {
        "error": SyntaxSeverity.ERROR,
        "warning": SyntaxSeverity.WARNING,
        "note": SyntaxSeverity.INFO,
    }
    return severity_map.get(severity.lower(), SyntaxSeverity.ERROR)
