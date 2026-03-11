"""
Tests for Heimdall CLI

Unit tests for command-line interface functionality.
"""

import pytest
import argparse
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from Asgard.Heimdall.cli import (
    create_parser,
    parse_extension_thresholds,
    format_thresholds_display,
    format_text_report,
    format_json_report,
    format_markdown_report,
    format_dry_run,
    SEVERITY_MARKERS,
    COMPLEXITY_SEVERITY_MARKERS,
    DUPLICATION_SEVERITY_MARKERS,
    SMELL_SEVERITY_MARKERS,
    DEBT_SEVERITY_MARKERS,
    MAINTAINABILITY_LEVEL_MARKERS,
    SECURITY_SEVERITY_MARKERS,
    PERFORMANCE_SEVERITY_MARKERS,
)
from Asgard.Heimdall.Quality.models.analysis_models import (
    AnalysisResult,
    FileAnalysis,
    SeverityLevel,
)


def create_file_analysis(**kwargs):
    """Helper to create FileAnalysis with defaults for required fields."""
    defaults = {
        "file_path": "/test/file.py",
        "line_count": 400,
        "threshold": 300,
        "lines_over": 100,
        "severity": SeverityLevel.SEVERE,
        "file_extension": ".py",
        "relative_path": "file.py",
    }
    defaults.update(kwargs)
    return FileAnalysis(**defaults)


class TestCreateParser:
    """Tests for create_parser function."""

    def test_create_parser_returns_parser(self):
        """Test that create_parser returns an ArgumentParser."""
        parser = create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_parser_has_verbose_flag(self):
        """Test that parser has verbose flag."""
        parser = create_parser()
        args = parser.parse_args([])
        assert hasattr(args, 'verbose')

    def test_parser_has_version_flag(self):
        """Test that parser has version flag."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    def test_parser_has_quality_command(self):
        """Test that parser has quality command."""
        parser = create_parser()
        args = parser.parse_args(["quality", "analyze", "."])
        assert args.command == "quality"

    def test_parser_has_security_command(self):
        """Test that parser has security command."""
        parser = create_parser()
        args = parser.parse_args(["security", "scan", "."])
        assert args.command == "security"

    def test_parser_has_performance_command(self):
        """Test that parser has performance command."""
        parser = create_parser()
        args = parser.parse_args(["performance", "scan", "."])
        assert args.command == "performance"

    def test_parser_has_audit_command(self):
        """Test that parser has audit command."""
        parser = create_parser()
        args = parser.parse_args(["audit", "."])
        assert args.command == "audit"

    def test_quality_analyze_subcommand(self):
        """Test quality analyze subcommand."""
        parser = create_parser()
        args = parser.parse_args(["quality", "analyze", "/test/path"])
        assert args.quality_command == "analyze"
        assert args.path == "/test/path"

    def test_quality_file_length_subcommand(self):
        """Test quality file-length subcommand."""
        parser = create_parser()
        args = parser.parse_args(["quality", "file-length", "/test/path"])
        assert args.quality_command == "file-length"
        assert args.path == "/test/path"

    def test_quality_complexity_subcommand(self):
        """Test quality complexity subcommand."""
        parser = create_parser()
        args = parser.parse_args(["quality", "complexity", "/test/path"])
        assert args.quality_command == "complexity"
        assert args.path == "/test/path"

    def test_quality_duplication_subcommand(self):
        """Test quality duplication subcommand."""
        parser = create_parser()
        args = parser.parse_args(["quality", "duplication", "/test/path"])
        assert args.quality_command == "duplication"
        assert args.path == "/test/path"

    def test_quality_smells_subcommand(self):
        """Test quality smells subcommand."""
        parser = create_parser()
        args = parser.parse_args(["quality", "smells", "/test/path"])
        assert args.quality_command == "smells"
        assert args.path == "/test/path"

    def test_quality_debt_subcommand(self):
        """Test quality debt subcommand."""
        parser = create_parser()
        args = parser.parse_args(["quality", "debt", "/test/path"])
        assert args.quality_command == "debt"
        assert args.path == "/test/path"

    def test_quality_maintainability_subcommand(self):
        """Test quality maintainability subcommand."""
        parser = create_parser()
        args = parser.parse_args(["quality", "maintainability", "/test/path"])
        assert args.quality_command == "maintainability"
        assert args.path == "/test/path"

    def test_security_secrets_subcommand(self):
        """Test security secrets subcommand."""
        parser = create_parser()
        args = parser.parse_args(["security", "secrets", "/test/path"])
        assert args.security_command == "secrets"

    def test_security_dependencies_subcommand(self):
        """Test security dependencies subcommand."""
        parser = create_parser()
        args = parser.parse_args(["security", "dependencies", "/test/path"])
        assert args.security_command == "dependencies"

    def test_security_vulnerabilities_subcommand(self):
        """Test security vulnerabilities subcommand."""
        parser = create_parser()
        args = parser.parse_args(["security", "vulnerabilities", "/test/path"])
        assert args.security_command == "vulnerabilities"

    def test_security_crypto_subcommand(self):
        """Test security crypto subcommand."""
        parser = create_parser()
        args = parser.parse_args(["security", "crypto", "/test/path"])
        assert args.security_command == "crypto"

    def test_performance_memory_subcommand(self):
        """Test performance memory subcommand."""
        parser = create_parser()
        args = parser.parse_args(["performance", "memory", "/test/path"])
        assert args.performance_command == "memory"

    def test_performance_cpu_subcommand(self):
        """Test performance cpu subcommand."""
        parser = create_parser()
        args = parser.parse_args(["performance", "cpu", "/test/path"])
        assert args.performance_command == "cpu"

    def test_performance_database_subcommand(self):
        """Test performance database subcommand."""
        parser = create_parser()
        args = parser.parse_args(["performance", "database", "/test/path"])
        assert args.performance_command == "database"

    def test_performance_cache_subcommand(self):
        """Test performance cache subcommand."""
        parser = create_parser()
        args = parser.parse_args(["performance", "cache", "/test/path"])
        assert args.performance_command == "cache"

    def test_default_path_is_current_directory(self):
        """Test that default path is current directory."""
        parser = create_parser()
        args = parser.parse_args(["quality", "analyze"])
        assert args.path == "."

    def test_threshold_argument(self):
        """Test threshold argument."""
        parser = create_parser()
        args = parser.parse_args(["quality", "analyze", "--threshold", "500"])
        assert args.threshold == 500

    def test_format_argument(self):
        """Test format argument."""
        parser = create_parser()
        args = parser.parse_args(["quality", "analyze", "--format", "json"])
        assert args.format == "json"

    def test_extensions_argument(self):
        """Test extensions argument."""
        parser = create_parser()
        args = parser.parse_args(["quality", "analyze", "--extensions", ".py", ".js"])
        assert args.extensions == [".py", ".js"]

    def test_exclude_argument(self):
        """Test exclude argument."""
        parser = create_parser()
        args = parser.parse_args(["quality", "analyze", "--exclude", "*.test.py", "*/vendor/*"])
        assert args.exclude == ["*.test.py", "*/vendor/*"]

    def test_dry_run_argument(self):
        """Test dry-run argument."""
        parser = create_parser()
        args = parser.parse_args(["quality", "analyze", "--dry-run"])
        assert args.dry_run is True


class TestParseExtensionThresholds:
    """Tests for parse_extension_thresholds function."""

    def test_parse_empty_list(self):
        """Test parsing empty list."""
        result = parse_extension_thresholds([])
        assert isinstance(result, dict)

    def test_parse_single_threshold(self):
        """Test parsing single threshold."""
        result = parse_extension_thresholds([".py:200"])
        assert result[".py"] == 200

    def test_parse_multiple_thresholds(self):
        """Test parsing multiple thresholds."""
        result = parse_extension_thresholds([".py:200", ".css:500", ".js:300"])
        assert result[".py"] == 200
        assert result[".css"] == 500
        assert result[".js"] == 300

    def test_parse_without_leading_dot(self):
        """Test parsing extension without leading dot."""
        result = parse_extension_thresholds(["py:200"])
        assert result[".py"] == 200

    def test_parse_invalid_format_warning(self, capsys):
        """Test parsing invalid format shows warning."""
        result = parse_extension_thresholds(["invalid"])
        captured = capsys.readouterr()
        assert "Warning" in captured.out

    def test_parse_invalid_threshold_value_warning(self, capsys):
        """Test parsing invalid threshold value shows warning."""
        result = parse_extension_thresholds([".py:invalid"])
        captured = capsys.readouterr()
        assert "Warning" in captured.out

    def test_parse_preserves_defaults(self):
        """Test that parsing preserves default extension thresholds."""
        result = parse_extension_thresholds([".py:200"])
        assert ".css" in result
        assert ".scss" in result


class TestFormatThresholdsDisplay:
    """Tests for format_thresholds_display function."""

    def test_format_with_default_only(self):
        """Test formatting with default threshold only."""
        result = AnalysisResult(
            scan_path="/test",
            default_threshold=300,
        )
        lines = format_thresholds_display(result)

        assert len(lines) >= 1
        assert "Default" in lines[0]
        assert "300" in lines[0]

    def test_format_with_extension_thresholds(self):
        """Test formatting with extension thresholds."""
        result = AnalysisResult(
            scan_path="/test",
            default_threshold=300,
            extension_thresholds={".css": 500, ".py": 200},
        )
        lines = format_thresholds_display(result)

        assert len(lines) > 1
        assert any(".css" in line or ".py" in line for line in lines)


class TestFormatTextReport:
    """Tests for format_text_report function."""

    def test_format_text_report_no_violations(self):
        """Test formatting text report with no violations."""
        result = AnalysisResult(
            scan_path="/test/path",
            default_threshold=300,
        )
        result.increment_files_scanned()
        result.increment_files_scanned()

        text = format_text_report(result)

        assert "HEIMDALL CODE QUALITY REPORT" in text
        assert "/test/path" in text
        assert "All files are within the threshold" in text

    def test_format_text_report_with_violations(self):
        """Test formatting text report with violations."""
        result = AnalysisResult(
            scan_path="/test/path",
            default_threshold=300,
        )
        result.increment_files_scanned()

        violation = create_file_analysis(
            file_path="/test/path/large.py",
            relative_path="large.py",
        )
        result.add_violation(violation)

        text = format_text_report(result)

        assert "FILES EXCEEDING THRESHOLD" in text
        assert "large.py" in text
        assert "400 lines" in text

    def test_format_text_report_groups_by_severity(self):
        """Test that text report groups violations by severity."""
        result = AnalysisResult(
            scan_path="/test/path",
            default_threshold=300,
        )

        critical = create_file_analysis(
            file_path="/test/critical.py",
            line_count=600,
            lines_over=300,
            severity=SeverityLevel.CRITICAL,
            relative_path="critical.py",
        )
        warning = create_file_analysis(
            file_path="/test/warning.py",
            line_count=325,
            lines_over=25,
            severity=SeverityLevel.WARNING,
            relative_path="warning.py",
        )

        result.add_violation(critical)
        result.add_violation(warning)

        text = format_text_report(result)

        assert "[CRITICAL]" in text
        assert "[WARNING]" in text


class TestFormatJsonReport:
    """Tests for format_json_report function."""

    def test_format_json_report_valid_json(self):
        """Test that JSON report is valid JSON."""
        import json

        result = AnalysisResult(
            scan_path="/test/path",
            default_threshold=300,
        )

        json_str = format_json_report(result)
        data = json.loads(json_str)

        assert isinstance(data, dict)

    def test_format_json_report_contains_metadata(self):
        """Test that JSON report contains metadata."""
        import json

        result = AnalysisResult(
            scan_path="/test/path",
            default_threshold=300,
        )

        json_str = format_json_report(result)
        data = json.loads(json_str)

        assert data["scan_path"] == "/test/path"
        assert data["thresholds"]["default"] == 300

    def test_format_json_report_contains_violations(self):
        """Test that JSON report contains violations."""
        import json

        result = AnalysisResult(
            scan_path="/test/path",
            default_threshold=300,
        )

        violation = create_file_analysis(relative_path="large.py")
        result.add_violation(violation)

        json_str = format_json_report(result)
        data = json.loads(json_str)

        assert len(data["violations"]) == 1
        assert data["violations"][0]["line_count"] == 400


class TestFormatMarkdownReport:
    """Tests for format_markdown_report function."""

    def test_format_markdown_report_has_header(self):
        """Test that markdown report has header."""
        result = AnalysisResult(
            scan_path="/test/path",
            default_threshold=300,
        )

        md = format_markdown_report(result)

        assert "# Heimdall Code Quality Report" in md

    def test_format_markdown_report_has_metadata(self):
        """Test that markdown report has metadata."""
        result = AnalysisResult(
            scan_path="/test/path",
            default_threshold=300,
        )

        md = format_markdown_report(result)

        assert "/test/path" in md
        assert "300" in md

    def test_format_markdown_report_has_table_with_violations(self):
        """Test that markdown report has table with violations."""
        result = AnalysisResult(
            scan_path="/test/path",
            default_threshold=300,
        )

        violation = create_file_analysis(relative_path="large.py")
        result.add_violation(violation)

        md = format_markdown_report(result)

        assert "| File |" in md
        assert "large.py" in md


class TestFormatDryRun:
    """Tests for format_dry_run function."""

    def test_format_dry_run_empty_list(self):
        """Test formatting dry run with empty file list."""
        text = format_dry_run([], Path("/test/path"))

        assert "DRY RUN PREVIEW" in text
        assert "test" in text.lower() and "path" in text.lower()
        assert "0" in text

    def test_format_dry_run_with_files(self):
        """Test formatting dry run with files."""
        files = [
            Path("/test/path/file1.py"),
            Path("/test/path/file2.py"),
        ]

        text = format_dry_run(files, Path("/test/path"))

        assert "DRY RUN PREVIEW" in text
        assert "2" in text


class TestSeverityMarkers:
    """Tests for severity marker constants."""

    def test_severity_markers_defined(self):
        """Test that severity markers are defined."""
        assert len(SEVERITY_MARKERS) == 4
        assert SEVERITY_MARKERS[SeverityLevel.CRITICAL.value] == "[CRITICAL]"
        assert SEVERITY_MARKERS[SeverityLevel.SEVERE.value] == "[SEVERE]"
        assert SEVERITY_MARKERS[SeverityLevel.MODERATE.value] == "[MODERATE]"
        assert SEVERITY_MARKERS[SeverityLevel.WARNING.value] == "[WARNING]"

    def test_complexity_severity_markers_defined(self):
        """Test that complexity severity markers are defined."""
        assert len(COMPLEXITY_SEVERITY_MARKERS) == 5

    def test_duplication_severity_markers_defined(self):
        """Test that duplication severity markers are defined."""
        assert len(DUPLICATION_SEVERITY_MARKERS) == 4

    def test_smell_severity_markers_defined(self):
        """Test that smell severity markers are defined."""
        assert len(SMELL_SEVERITY_MARKERS) == 4

    def test_debt_severity_markers_defined(self):
        """Test that debt severity markers are defined."""
        assert len(DEBT_SEVERITY_MARKERS) == 4

    def test_maintainability_level_markers_defined(self):
        """Test that maintainability level markers are defined."""
        assert len(MAINTAINABILITY_LEVEL_MARKERS) == 5

    def test_security_severity_markers_defined(self):
        """Test that security severity markers are defined."""
        assert len(SECURITY_SEVERITY_MARKERS) == 5

    def test_performance_severity_markers_defined(self):
        """Test that performance severity markers are defined."""
        assert len(PERFORMANCE_SEVERITY_MARKERS) == 5
