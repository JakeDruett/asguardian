"""Main Csharp analyzer — entry point for Heimdall quality scanning."""

from pathlib import Path
from typing import List, Optional

from Asgard.Bragi.Quality.languages._confined_walk import (
    CSHARP_EXTENSIONS,
    collect_regex_findings,
    read_capped_source,
)
from Asgard.Bragi.Quality.languages.csharp.models.csharp_models import (
    CsharpFinding,
    CsharpReport,
    CsharpScanConfig,
)
from Asgard.Bragi.Quality.languages.csharp.services._csharp_rules import (
    check_sql_injection, check_no_hardcoded_credentials, check_no_empty_catch, check_xss, check_no_weak_crypto, check_path_traversal, check_command_injection, check_no_debug_code,
    check_unsafe_deserialization, check_unsafe_reflection,
)

_RULES = [
    check_sql_injection,
    check_no_hardcoded_credentials,
    check_no_empty_catch,
    check_xss,
    check_no_weak_crypto,
    check_path_traversal,
    check_command_injection,
    check_no_debug_code,
    check_unsafe_deserialization,
    check_unsafe_reflection,
]


class CsharpAnalyzer:
    """Analyses Csharp source files for security and quality issues."""

    def __init__(self, config: Optional[CsharpScanConfig] = None) -> None:
        self._config = config or CsharpScanConfig()

    def analyze(self, scan_path: Optional[str] = None) -> CsharpReport:
        """Analyze all C# files under scan_path and return a CsharpReport."""
        path = Path(scan_path) if scan_path else self._config.scan_path
        report = CsharpReport(scan_path=str(path))
        report.findings.extend(self._scan(path, self._config))
        return report

    def analyze_file(self, file_path: Path) -> List[CsharpFinding]:
        if file_path.suffix.lower() not in CSHARP_EXTENSIONS:
            return []
        source = read_capped_source(file_path, max_file_lines=self._config.max_file_lines)
        if source is None:
            return []
        findings: List[CsharpFinding] = []
        for rule in _RULES:
            findings.extend(rule(str(file_path), source.lines, enabled=True))
        return findings

    def analyze_directory(self, scan_path: Path, config: Optional[CsharpScanConfig] = None) -> List[CsharpFinding]:
        cfg = config or CsharpScanConfig(scan_path=scan_path)
        return self._scan(scan_path, cfg)

    def _scan(self, scan_path: Path, cfg: CsharpScanConfig) -> List[CsharpFinding]:
        return collect_regex_findings(
            scan_path,
            include_extensions=cfg.include_extensions,
            exclude_patterns=cfg.exclude_patterns,
            allowed_extensions=CSHARP_EXTENSIONS,
            max_file_lines=cfg.max_file_lines,
            max_findings=cfg.max_findings,
            rules=_RULES,
            enabled_for=lambda rule_id: cfg.rules.get(rule_id, True),
        )
