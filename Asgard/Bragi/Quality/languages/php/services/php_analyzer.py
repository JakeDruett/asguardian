"""Main Php analyzer — entry point for Heimdall quality scanning."""

from pathlib import Path
from typing import List, Optional

from Asgard.Bragi.Quality.languages._confined_walk import (
    PHP_EXTENSIONS,
    collect_regex_findings,
    read_capped_source,
)
from Asgard.Bragi.Quality.languages.php.models.php_models import (
    PhpFinding,
    PhpReport,
    PhpScanConfig,
)
from Asgard.Bragi.Quality.languages.php.services._php_rules import (
    check_sql_injection, check_xss, check_no_eval, check_file_inclusion, check_command_injection, check_no_md5_password, check_no_extract, check_no_hardcoded_credentials,
    check_path_traversal,
)

_RULES = [
    check_sql_injection,
    check_xss,
    check_no_eval,
    check_file_inclusion,
    check_command_injection,
    check_no_md5_password,
    check_no_extract,
    check_no_hardcoded_credentials,
    check_path_traversal,
]


class PhpAnalyzer:
    """Analyses Php source files for security and quality issues."""

    def __init__(self, config: Optional[PhpScanConfig] = None) -> None:
        self._config = config or PhpScanConfig()

    def analyze(self, scan_path: Optional[str] = None) -> PhpReport:
        """Analyze all PHP files under scan_path and return a PhpReport."""
        path = Path(scan_path) if scan_path else self._config.scan_path
        report = PhpReport(scan_path=str(path))
        report.findings.extend(self._scan(path, self._config))
        return report

    def analyze_file(self, file_path: Path) -> List[PhpFinding]:
        if file_path.suffix.lower() not in PHP_EXTENSIONS:
            return []
        source = read_capped_source(file_path, max_file_lines=self._config.max_file_lines)
        if source is None:
            return []
        findings: List[PhpFinding] = []
        for rule in _RULES:
            findings.extend(rule(str(file_path), source.lines, enabled=True))
        return findings

    def analyze_directory(self, scan_path: Path, config: Optional[PhpScanConfig] = None) -> List[PhpFinding]:
        cfg = config or PhpScanConfig(scan_path=scan_path)
        return self._scan(scan_path, cfg)

    def _scan(self, scan_path: Path, cfg: PhpScanConfig) -> List[PhpFinding]:
        return collect_regex_findings(
            scan_path,
            include_extensions=cfg.include_extensions,
            exclude_patterns=cfg.exclude_patterns,
            allowed_extensions=PHP_EXTENSIONS,
            max_file_lines=cfg.max_file_lines,
            max_findings=cfg.max_findings,
            rules=_RULES,
            enabled_for=lambda rule_id: cfg.rules.get(rule_id, True),
        )
