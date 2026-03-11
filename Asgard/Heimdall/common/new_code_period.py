"""
Heimdall New Code Period Detection

Defines what constitutes "new code" for the purpose of separate metric tracking.
New code can be defined relative to the last analysis, a date, a branch point, or
a tagged version. This mirrors SonarQube's New Code Period concept.

New code gets separate metrics that can be more strictly gated, allowing teams to
enforce quality on new code without requiring immediate cleanup of existing issues.
"""

import json
import subprocess
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class NewCodePeriodType(str, Enum):
    """Defines the reference point for identifying new code."""
    SINCE_LAST_ANALYSIS = "since_last_analysis"
    SINCE_DATE = "since_date"
    SINCE_BRANCH_POINT = "since_branch_point"
    SINCE_VERSION = "since_version"


class NewCodePeriodConfig(BaseModel):
    """
    Configuration for the new code period detection.

    Determines how the detector identifies which files and lines are considered
    new or modified relative to a reference point.
    """
    period_type: NewCodePeriodType = Field(
        NewCodePeriodType.SINCE_LAST_ANALYSIS,
        description="Type of new code period to apply",
    )
    reference_date: Optional[datetime] = Field(
        None,
        description="Reference date for SINCE_DATE period type",
    )
    reference_branch: str = Field(
        "main",
        description="Base branch for SINCE_BRANCH_POINT period type",
    )
    reference_version: Optional[str] = Field(
        None,
        description="Tagged version for SINCE_VERSION period type",
    )
    baseline_path: Optional[Path] = Field(
        None,
        description="Path to a stored last-analysis snapshot for SINCE_LAST_ANALYSIS",
    )

    class Config:
        use_enum_values = True


class NewCodePeriodResult(BaseModel):
    """
    Result of new code period detection.

    Contains the list of new and modified files along with summary counts
    and a human-readable description of the reference point used.
    """
    period_type: NewCodePeriodType = Field(
        ...,
        description="The period type that was applied",
    )
    new_files: List[str] = Field(
        default_factory=list,
        description="Files added since the reference point",
    )
    modified_files: List[str] = Field(
        default_factory=list,
        description="Files modified since the reference point",
    )
    new_lines_count: int = Field(
        0,
        description="Approximate number of new or changed lines",
    )
    total_new_code_files: int = Field(
        0,
        description="Total number of files with new code (new + modified)",
    )
    reference_point: str = Field(
        "",
        description="Human-readable description of what constitutes new code",
    )
    detected_at: datetime = Field(
        default_factory=datetime.now,
        description="When the detection was performed",
    )

    class Config:
        use_enum_values = True


class NewCodePeriodDetector:
    """
    Detects which files constitute new code relative to a configured reference point.

    Uses git to identify changed files wherever git is available. Falls back to
    file modification timestamps when git is not available.

    Usage:
        config = NewCodePeriodConfig(
            period_type=NewCodePeriodType.SINCE_BRANCH_POINT,
            reference_branch="main",
        )
        detector = NewCodePeriodDetector()
        result = detector.detect("./src", config)
        print(f"New files: {result.new_files}")
        print(f"Modified files: {result.modified_files}")
    """

    def detect(self, scan_path: str, config: NewCodePeriodConfig) -> NewCodePeriodResult:
        """
        Detect new code relative to the configured reference point.

        Args:
            scan_path: Root directory of the project to analyse.
            config: Configuration specifying the new code period type.

        Returns:
            NewCodePeriodResult with lists of new and modified files.
        """
        period_type = config.period_type
        if isinstance(period_type, NewCodePeriodType):
            period_type = period_type.value

        if not self._git_available(scan_path):
            return self._detect_by_mtime(scan_path, config)

        if period_type == NewCodePeriodType.SINCE_LAST_ANALYSIS.value:
            return self._detect_since_last_analysis(scan_path, config)
        elif period_type == NewCodePeriodType.SINCE_DATE.value:
            return self._detect_since_date(scan_path, config)
        elif period_type == NewCodePeriodType.SINCE_BRANCH_POINT.value:
            return self._detect_since_branch_point(scan_path, config)
        elif period_type == NewCodePeriodType.SINCE_VERSION.value:
            return self._detect_since_version(scan_path, config)
        else:
            return self._detect_since_last_analysis(scan_path, config)

    def _git_available(self, scan_path: str) -> bool:
        """Check whether git is available and the path is inside a git repo."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                cwd=scan_path,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    def _run_git(self, args: List[str], cwd: str) -> Optional[str]:
        """
        Run a git command and return stdout.

        Args:
            args: Git arguments (without the leading "git").
            cwd: Working directory for the command.

        Returns:
            Stdout text or None if the command failed.
        """
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None

    def _parse_file_list(self, output: Optional[str]) -> List[str]:
        """Parse a newline-separated list of file paths from git output."""
        if not output:
            return []
        return [line.strip() for line in output.splitlines() if line.strip()]

    def _count_new_lines(self, scan_path: str, files: List[str]) -> int:
        """
        Count new/changed lines using git diff --numstat.

        Returns a best-effort total of added lines across the listed files.
        """
        if not files:
            return 0

        try:
            result = subprocess.run(
                ["git", "diff", "--numstat", "HEAD"],
                capture_output=True,
                text=True,
                cwd=scan_path,
                timeout=30,
            )
            if result.returncode != 0:
                return 0

            total = 0
            for line in result.stdout.splitlines():
                parts = line.split("\t")
                if len(parts) >= 1:
                    try:
                        total += int(parts[0])
                    except (ValueError, IndexError):
                        pass
            return total
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return 0

    def _build_result(
        self,
        period_type: str,
        new_files: List[str],
        modified_files: List[str],
        reference_point: str,
        new_lines_count: int = 0,
    ) -> NewCodePeriodResult:
        """Construct a NewCodePeriodResult from collected file lists."""
        return NewCodePeriodResult(
            period_type=period_type,
            new_files=new_files,
            modified_files=modified_files,
            new_lines_count=new_lines_count,
            total_new_code_files=len(new_files) + len(modified_files),
            reference_point=reference_point,
            detected_at=datetime.now(),
        )

    def _detect_since_last_analysis(
        self, scan_path: str, config: NewCodePeriodConfig
    ) -> NewCodePeriodResult:
        """
        Detect new code since the last stored analysis baseline commit.

        If a baseline_path is configured and contains a stored commit hash,
        uses git diff between that commit and HEAD. Otherwise, uses the last
        commit as the reference point (i.e., staged + unstaged changes).
        """
        reference_commit: Optional[str] = None

        if config.baseline_path and config.baseline_path.exists():
            try:
                with open(config.baseline_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                reference_commit = data.get("git_commit")
            except (OSError, ValueError, KeyError):
                reference_commit = None

        if reference_commit:
            output = self._run_git(
                ["diff", "--name-status", f"{reference_commit}...HEAD"],
                scan_path,
            )
            reference_point = f"Since last analysis (commit {reference_commit[:8]})"
        else:
            output = self._run_git(
                ["diff", "--name-status", "HEAD~1", "HEAD"],
                scan_path,
            )
            reference_point = "Since last commit (no baseline found)"

        new_files, modified_files = self._parse_name_status(output)
        lines = self._count_new_lines(scan_path, modified_files + new_files)

        return self._build_result(
            NewCodePeriodType.SINCE_LAST_ANALYSIS.value,
            new_files,
            modified_files,
            reference_point,
            lines,
        )

    def _detect_since_date(
        self, scan_path: str, config: NewCodePeriodConfig
    ) -> NewCodePeriodResult:
        """
        Detect new code since a specific date using git log.

        Args:
            scan_path: Root directory of the project.
            config: Must have reference_date set.
        """
        if not config.reference_date:
            return self._build_result(
                NewCodePeriodType.SINCE_DATE.value,
                [],
                [],
                "Since date: (no date configured)",
            )

        date_str = config.reference_date.strftime("%Y-%m-%d")
        output = self._run_git(
            ["log", f"--since={date_str}", "--name-only", "--pretty=format:"],
            scan_path,
        )
        all_files = self._parse_file_list(output)
        unique_files = list(dict.fromkeys(all_files))
        reference_point = f"Since {date_str}"

        return self._build_result(
            NewCodePeriodType.SINCE_DATE.value,
            [],
            unique_files,
            reference_point,
        )

    def _detect_since_branch_point(
        self, scan_path: str, config: NewCodePeriodConfig
    ) -> NewCodePeriodResult:
        """
        Detect new code since the branch diverged from a base branch.

        Uses git diff --name-status BASE_BRANCH...HEAD.
        """
        base_branch = config.reference_branch

        output = self._run_git(
            ["diff", "--name-status", f"{base_branch}...HEAD"],
            scan_path,
        )
        new_files, modified_files = self._parse_name_status(output)
        reference_point = f"Since branch point from '{base_branch}'"

        return self._build_result(
            NewCodePeriodType.SINCE_BRANCH_POINT.value,
            new_files,
            modified_files,
            reference_point,
        )

    def _detect_since_version(
        self, scan_path: str, config: NewCodePeriodConfig
    ) -> NewCodePeriodResult:
        """
        Detect new code since a tagged version.

        Uses git diff --name-status VERSION...HEAD.
        """
        if not config.reference_version:
            return self._build_result(
                NewCodePeriodType.SINCE_VERSION.value,
                [],
                [],
                "Since version: (no version configured)",
            )

        version = config.reference_version
        output = self._run_git(
            ["diff", "--name-status", f"{version}...HEAD"],
            scan_path,
        )
        new_files, modified_files = self._parse_name_status(output)
        reference_point = f"Since version '{version}'"

        return self._build_result(
            NewCodePeriodType.SINCE_VERSION.value,
            new_files,
            modified_files,
            reference_point,
        )

    def _parse_name_status(self, output: Optional[str]):
        """
        Parse git diff --name-status output into new_files and modified_files.

        Status codes: A = added, M = modified, D = deleted, R = renamed, C = copied.
        Added files go to new_files; all others (M, R, C) go to modified_files.
        Deleted files are excluded.

        Returns:
            Tuple of (new_files, modified_files).
        """
        new_files: List[str] = []
        modified_files: List[str] = []

        if not output:
            return new_files, modified_files

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            status = parts[0].upper()
            file_path = parts[-1]

            if status.startswith("A"):
                new_files.append(file_path)
            elif status.startswith("D"):
                pass
            else:
                modified_files.append(file_path)

        return new_files, modified_files

    def _detect_by_mtime(
        self, scan_path: str, config: NewCodePeriodConfig
    ) -> NewCodePeriodResult:
        """
        Fall back to file modification time when git is not available.

        For SINCE_DATE, uses the configured reference_date.
        For all other period types, uses files modified in the last 24 hours.
        """
        cutoff: Optional[datetime] = None

        period_type = config.period_type
        if isinstance(period_type, NewCodePeriodType):
            period_type = period_type.value

        if period_type == NewCodePeriodType.SINCE_DATE.value and config.reference_date:
            cutoff = config.reference_date
            reference_point = f"Since {cutoff.strftime('%Y-%m-%d')} (mtime fallback)"
        else:
            cutoff = datetime.now() - timedelta(hours=24)
            reference_point = "Files modified in last 24 hours (git unavailable)"

        modified_files: List[str] = []
        root = Path(scan_path)

        for fpath in root.rglob("*.py"):
            try:
                mtime = datetime.fromtimestamp(fpath.stat().st_mtime)
                if mtime >= cutoff:
                    modified_files.append(str(fpath.relative_to(root)))
            except OSError:
                pass

        return self._build_result(
            period_type,
            [],
            modified_files,
            reference_point,
        )
