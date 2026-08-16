"""Main Go analyzer — entry point for Heimdall quality scanning."""

from pathlib import Path
from typing import List, Optional

from Asgard.Bragi.Quality.languages._confined_walk import (
    GO_EXTENSIONS,
    collect_regex_findings,
    read_capped_source,
)
from Asgard.Bragi.Quality.languages.go.models.go_models import (
    GoFinding,
    GoReport,
    GoScanConfig,
)
from Asgard.Bragi.Quality.languages.go.services._go_rules import (
    check_error_not_checked, check_no_panic, check_sql_injection, check_no_defer_in_loop, check_no_hardcoded_credentials, check_no_unbuffered_channel, check_no_global_mutex, check_context_not_propagated,
    check_command_injection, check_xss, check_path_traversal, check_weak_crypto,
)

_RULES = [
    check_error_not_checked,
    check_no_panic,
    check_sql_injection,
    check_no_defer_in_loop,
    check_no_hardcoded_credentials,
    check_no_unbuffered_channel,
    check_no_global_mutex,
    check_context_not_propagated,
    check_command_injection,
    check_xss,
    check_path_traversal,
    check_weak_crypto,
]


class GoAnalyzer:
    """Analyses Go source files for security and quality issues."""

    def __init__(self, config: Optional[GoScanConfig] = None) -> None:
        self._config = config or GoScanConfig()

    def analyze(self, scan_path: Optional[str] = None) -> GoReport:
        """Analyze all Go files under scan_path and return a GoReport."""
        path = Path(scan_path) if scan_path else self._config.scan_path
        report = GoReport(scan_path=str(path))
        report.findings.extend(self._scan(path, self._config))
        return report

    def analyze_file(self, file_path: Path) -> List[GoFinding]:
        if file_path.suffix.lower() not in GO_EXTENSIONS:
            return []
        source = read_capped_source(file_path, max_file_lines=self._config.max_file_lines)
        if source is None:
            return []
        findings: List[GoFinding] = []
        for rule in _RULES:
            findings.extend(rule(str(file_path), source.lines, enabled=True))
        return findings

    def analyze_directory(self, scan_path: Path, config: Optional[GoScanConfig] = None) -> List[GoFinding]:
        cfg = config or GoScanConfig(scan_path=scan_path)
        return self._scan(scan_path, cfg)

    def _scan(self, scan_path: Path, cfg: GoScanConfig) -> List[GoFinding]:
        return collect_regex_findings(
            scan_path,
            include_extensions=cfg.include_extensions,
            exclude_patterns=cfg.exclude_patterns,
            allowed_extensions=GO_EXTENSIONS,
            max_file_lines=cfg.max_file_lines,
            max_findings=cfg.max_findings,
            rules=_RULES,
            enabled_for=lambda rule_id: cfg.rules.get(rule_id, True),
        )
