"""Main Ruby analyzer — entry point for Heimdall quality scanning."""

from pathlib import Path
from typing import List, Optional

from Asgard.Bragi.Quality.languages._confined_walk import (
    RUBY_EXTENSIONS,
    collect_regex_findings,
    read_capped_source,
)
from Asgard.Bragi.Quality.languages.ruby.models.ruby_models import (
    RubyFinding,
    RubyReport,
    RubyScanConfig,
)
from Asgard.Bragi.Quality.languages.ruby.services._ruby_rules import (
    check_sql_injection, check_no_eval, check_command_injection, check_no_yaml_load, check_no_send, check_mass_assignment, check_no_hardcoded_credentials, check_no_md5_sha1,
    check_xss, check_path_traversal,
)

_RULES = [
    check_sql_injection,
    check_no_eval,
    check_command_injection,
    check_no_yaml_load,
    check_no_send,
    check_mass_assignment,
    check_no_hardcoded_credentials,
    check_no_md5_sha1,
    check_xss,
    check_path_traversal,
]


class RubyAnalyzer:
    """Analyses Ruby source files for security and quality issues."""

    def __init__(self, config: Optional[RubyScanConfig] = None) -> None:
        self._config = config or RubyScanConfig()

    def analyze(self, scan_path: Optional[str] = None) -> RubyReport:
        """Analyze all Ruby files under scan_path and return a RubyReport."""
        path = Path(scan_path) if scan_path else self._config.scan_path
        report = RubyReport(scan_path=str(path))
        report.findings.extend(self._scan(path, self._config))
        return report

    def analyze_file(self, file_path: Path) -> List[RubyFinding]:
        if file_path.suffix.lower() not in RUBY_EXTENSIONS:
            return []
        source = read_capped_source(file_path, max_file_lines=self._config.max_file_lines)
        if source is None:
            return []
        findings: List[RubyFinding] = []
        for rule in _RULES:
            findings.extend(rule(str(file_path), source.lines, enabled=True))
        return findings

    def analyze_directory(self, scan_path: Path, config: Optional[RubyScanConfig] = None) -> List[RubyFinding]:
        cfg = config or RubyScanConfig(scan_path=scan_path)
        return self._scan(scan_path, cfg)

    def _scan(self, scan_path: Path, cfg: RubyScanConfig) -> List[RubyFinding]:
        return collect_regex_findings(
            scan_path,
            include_extensions=cfg.include_extensions,
            exclude_patterns=cfg.exclude_patterns,
            allowed_extensions=RUBY_EXTENSIONS,
            max_file_lines=cfg.max_file_lines,
            max_findings=cfg.max_findings,
            rules=_RULES,
            enabled_for=lambda rule_id: cfg.rules.get(rule_id, True),
        )
