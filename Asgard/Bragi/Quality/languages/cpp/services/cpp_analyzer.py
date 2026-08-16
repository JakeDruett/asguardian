"""Main C++ analyzer — entry point for Heimdall quality scanning."""

from pathlib import Path
from typing import List, Optional

from Asgard.Bragi.Quality.languages._confined_walk import (
    CPP_EXTENSIONS,
    collect_regex_findings,
    read_capped_source,
)
from Asgard.Bragi.Quality.languages.cpp.models.cpp_models import (
    CppFinding,
    CppReport,
    CppScanConfig,
)
from Asgard.Bragi.Quality.languages.cpp.services._cpp_rules import (
    check_buffer_overflow,
    check_format_string,
    check_integer_overflow,
    check_memory_leak,
    check_null_deref,
    check_hardcoded_credentials,
    check_command_injection,
    check_use_after_free,
)

_RULES = [
    check_buffer_overflow,
    check_format_string,
    check_integer_overflow,
    check_memory_leak,
    check_null_deref,
    check_hardcoded_credentials,
    check_command_injection,
    check_use_after_free,
]


class CppAnalyzer:
    """Analyses C++ source files for security and quality issues."""

    def __init__(self, config: Optional[CppScanConfig] = None) -> None:
        self._config = config or CppScanConfig()

    def analyze(self, scan_path: Optional[str] = None) -> CppReport:
        """Analyze all C++ files under scan_path and return a CppReport."""
        path = Path(scan_path) if scan_path else self._config.scan_path
        report = CppReport(scan_path=str(path))
        report.findings.extend(self._scan(path, self._config))
        return report

    def analyze_file(self, file_path: Path) -> List[CppFinding]:
        if file_path.suffix.lower() not in CPP_EXTENSIONS:
            return []
        source = read_capped_source(file_path, max_file_lines=self._config.max_file_lines)
        if source is None:
            return []
        findings: List[CppFinding] = []
        for rule in _RULES:
            findings.extend(rule(str(file_path), source.lines, enabled=True))
        return findings

    def analyze_directory(self, scan_path: Path, config: Optional[CppScanConfig] = None) -> List[CppFinding]:
        cfg = config or CppScanConfig(scan_path=scan_path)
        return self._scan(scan_path, cfg)

    def _scan(self, scan_path: Path, cfg: CppScanConfig) -> List[CppFinding]:
        return collect_regex_findings(
            scan_path,
            include_extensions=cfg.include_extensions,
            exclude_patterns=cfg.exclude_patterns,
            allowed_extensions=CPP_EXTENSIONS,
            max_file_lines=cfg.max_file_lines,
            max_findings=cfg.max_findings,
            rules=_RULES,
            enabled_for=lambda rule_id: cfg.rules.get(rule_id, True),
        )
