"""Main Java analyzer — entry point for Heimdall quality scanning."""

from pathlib import Path
from typing import List, Optional

from Asgard.Bragi.Quality.languages._confined_walk import (
    JAVA_EXTENSIONS,
    collect_regex_findings,
    read_capped_source,
)
from Asgard.Bragi.Quality.languages.java.models.java_models import (
    JavaFinding,
    JavaReport,
    JavaScanConfig,
)
from Asgard.Bragi.Quality.languages.java.services._java_rules import (
    check_sql_injection, check_no_system_exit, check_no_print_stacktrace, check_empty_catch, check_string_equals, check_no_hardcoded_credentials, check_no_raw_types, check_no_object_finalize,
    check_command_injection, check_xss, check_weak_crypto, check_path_traversal, check_no_script_engine_eval,
)

_RULES = [
    check_sql_injection,
    check_no_system_exit,
    check_no_print_stacktrace,
    check_empty_catch,
    check_string_equals,
    check_no_hardcoded_credentials,
    check_no_raw_types,
    check_no_object_finalize,
    check_command_injection,
    check_xss,
    check_weak_crypto,
    check_path_traversal,
    check_no_script_engine_eval,
]


class JavaAnalyzer:
    """Analyses Java source files for security and quality issues."""

    def __init__(self, config: Optional[JavaScanConfig] = None) -> None:
        self._config = config or JavaScanConfig()

    def analyze(self, scan_path: Optional[str] = None) -> JavaReport:
        """Analyze all Java files under scan_path and return a JavaReport."""
        path = Path(scan_path) if scan_path else self._config.scan_path
        report = JavaReport(scan_path=str(path))
        report.findings.extend(self._scan(path, self._config))
        return report

    def analyze_file(self, file_path: Path) -> List[JavaFinding]:
        if file_path.suffix.lower() not in JAVA_EXTENSIONS:
            return []
        source = read_capped_source(file_path, max_file_lines=self._config.max_file_lines)
        if source is None:
            return []
        findings: List[JavaFinding] = []
        for rule in _RULES:
            findings.extend(rule(str(file_path), source.lines, enabled=True))
        return findings

    def analyze_directory(self, scan_path: Path, config: Optional[JavaScanConfig] = None) -> List[JavaFinding]:
        cfg = config or JavaScanConfig(scan_path=scan_path)
        return self._scan(scan_path, cfg)

    def _scan(self, scan_path: Path, cfg: JavaScanConfig) -> List[JavaFinding]:
        return collect_regex_findings(
            scan_path,
            include_extensions=cfg.include_extensions,
            exclude_patterns=cfg.exclude_patterns,
            allowed_extensions=JAVA_EXTENSIONS,
            max_file_lines=cfg.max_file_lines,
            max_findings=cfg.max_findings,
            rules=_RULES,
            enabled_for=lambda rule_id: cfg.rules.get(rule_id, True),
        )
