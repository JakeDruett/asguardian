"""
Unit tests for the Go toolchain-orchestrating analysers (go vet, go build,
gofmt, go test, govulncheck).

These tests monkeypatch Asgard.Bragi.Quality.languages.common.tool_runner's
run_tool/require_executable/find_optional_executable so the parsing logic
is exercised without depending on the go toolchain actually being
installed. A separate, skip-cleanly integration test near the bottom of
this file exercises the real tools against the checked-in fixture module
(and, for go build, against a second checked-in fixture whose `replace`
directive can never resolve) when they are available.
"""

import json
import shutil
from pathlib import Path

import pytest

from Asgard.Bragi.Quality.languages.common.tool_runner import ToolNotAvailableError, ToolRunResult
from Asgard.Bragi.Quality.languages.go.models.go_toolchain_models import (
    GoBuildConfig,
    GoFmtConfig,
    GoTestConfig,
    GoVetConfig,
    GoVulnConfig,
)
from Asgard.Bragi.Quality.languages.go.services import (
    go_build_analyzer,
    go_fmt_analyzer,
    go_test_analyzer,
    go_vet_analyzer,
    go_vuln_analyzer,
)
from Asgard.Bragi.Quality.languages.go.services.go_build_analyzer import GoBuildAnalyzer
from Asgard.Bragi.Quality.languages.go.services.go_fmt_analyzer import GoFmtAnalyzer
from Asgard.Bragi.Quality.languages.go.services.go_test_analyzer import GoTestAnalyzer
from Asgard.Bragi.Quality.languages.go.services.go_vet_analyzer import GoVetAnalyzer
from Asgard.Bragi.Quality.languages.go.services.go_vuln_analyzer import GoVulnAnalyzer


def _module(tmp_path: Path, name: str = "modname") -> Path:
    module_dir = tmp_path / "mod"
    module_dir.mkdir()
    (module_dir / "go.mod").write_text(f"module {name}\n\ngo 1.21\n", encoding="utf-8")
    return module_dir


# ---------------------------------------------------------------------------
# go vet
# ---------------------------------------------------------------------------

class TestGoVetAnalyzerParsing:
    def test_no_go_mod_is_graceful_not_a_crash(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(go_vet_analyzer, "require_executable", lambda *a, **k: "/usr/bin/go")
        report = GoVetAnalyzer(GoVetConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 0
        assert report.tools_unavailable
        assert "go.mod" in report.tools_unavailable[0]

    def test_go_missing_raises_actionable_error(self, tmp_path: Path, monkeypatch):
        def _raise(*args, **kwargs):
            raise ToolNotAvailableError("go is not available. Install Go from https://go.dev/dl")

        monkeypatch.setattr(go_vet_analyzer, "require_executable", _raise)
        with pytest.raises(ToolNotAvailableError) as excinfo:
            GoVetAnalyzer(GoVetConfig(scan_path=tmp_path)).analyze()
        assert "go.dev" in str(excinfo.value)

    def test_parses_diagnostic_and_skips_package_header(self, tmp_path: Path, monkeypatch):
        module_dir = _module(tmp_path)
        monkeypatch.setattr(go_vet_analyzer, "require_executable", lambda *a, **k: "/usr/bin/go")
        output = (
            "# modname/pkg\n"
            'pkg/main.go:6:2: fmt.Printf format %d has arg "x" of wrong type string\n'
        )
        monkeypatch.setattr(
            go_vet_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=1, stdout="", stderr=output),
        )
        report = GoVetAnalyzer(GoVetConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 1
        finding = report.findings[0]
        assert finding.rule_id == "go-vet"
        assert finding.severity == "error"
        assert finding.file_path == str(Path("mod/pkg/main.go"))
        assert finding.line_number == 6
        assert not report.tool_failed

    def test_clean_run_is_zero_findings_not_failed(self, tmp_path: Path, monkeypatch):
        _module(tmp_path)
        monkeypatch.setattr(go_vet_analyzer, "require_executable", lambda *a, **k: "/usr/bin/go")
        monkeypatch.setattr(
            go_vet_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=0, stdout="", stderr=""),
        )
        report = GoVetAnalyzer(GoVetConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 0
        assert not report.tool_failed

    def test_malformed_go_mod_failure_is_reported_not_clean(self, tmp_path: Path, monkeypatch):
        # A malformed go.mod produces a one-line "go: errors parsing go.mod:
        # ..." message with no file:line:col shape at all -- this MUST NOT
        # be read as "zero vet findings" (a clean pass).
        _module(tmp_path)
        monkeypatch.setattr(go_vet_analyzer, "require_executable", lambda *a, **k: "/usr/bin/go")
        monkeypatch.setattr(
            go_vet_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(
                returncode=1, stdout="", stderr="go: errors parsing go.mod:\ngo.mod:1: unknown directive: not\n"
            ),
        )
        report = GoVetAnalyzer(GoVetConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 0
        assert report.tool_failed is True
        assert report.tools_unavailable

    def test_timeout_is_reported_not_raised(self, tmp_path: Path, monkeypatch):
        _module(tmp_path)
        monkeypatch.setattr(go_vet_analyzer, "require_executable", lambda *a, **k: "/usr/bin/go")
        monkeypatch.setattr(
            go_vet_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=-1, stdout="", stderr="", timed_out=True),
        )
        report = GoVetAnalyzer(GoVetConfig(scan_path=tmp_path, timeout_seconds=5)).analyze()
        assert report.total_findings == 0
        assert report.tool_failed is True
        assert any("timed out" in note for note in report.tools_unavailable)


# ---------------------------------------------------------------------------
# go build
# ---------------------------------------------------------------------------

class TestGoBuildAnalyzerParsing:
    def test_no_go_mod_is_graceful(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(go_build_analyzer, "require_executable", lambda *a, **k: "/usr/bin/go")
        report = GoBuildAnalyzer(GoBuildConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 0
        assert "go.mod" in report.tools_unavailable[0]

    def test_unresolved_replace_directive_is_an_unmistakable_finding(self, tmp_path: Path, monkeypatch):
        # This is the exact shape of the real GAIA/Keryx failure (see the
        # skip-cleanly integration test below): a go.mod `replace` pointing
        # at a sibling checkout path that does not exist. Every prior
        # `go build`/`go vet` output in this suite proved this string shape
        # comes straight from a real run against that checkout.
        module_dir = _module(tmp_path, name="gaia/keryx")
        monkeypatch.setattr(go_build_analyzer, "require_executable", lambda *a, **k: "/usr/bin/go")
        output = (
            "app/broker.go:14:2: gaia/lexicon@v0.0.0 (replaced by ../Lexicon/LexiconGo): "
            "reading ../Lexicon/LexiconGo/go.mod: open /home/user/GAIA/Lexicon/LexiconGo/go.mod: "
            "no such file or directory\n"
        )
        monkeypatch.setattr(
            go_build_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=1, stdout="", stderr=output),
        )
        report = GoBuildAnalyzer(GoBuildConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 1
        finding = report.findings[0]
        assert finding.rule_id == "go-build"
        assert finding.severity == "error"
        assert finding.line_number == 14
        assert "no such file or directory" in finding.description
        assert not report.tool_failed  # a real, parsed diagnostic -- not a crash

    def test_compile_failure_with_no_diagnostic_shape_is_a_tool_failure(self, tmp_path: Path, monkeypatch):
        # Defect-2 regression: a fatal, non-per-file failure (a malformed
        # go.mod) must not silently read as "zero compile errors".
        _module(tmp_path)
        monkeypatch.setattr(go_build_analyzer, "require_executable", lambda *a, **k: "/usr/bin/go")
        monkeypatch.setattr(
            go_build_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(
                returncode=1, stdout="", stderr="go: errors parsing go.mod:\ngo.mod:1: unknown directive: not\n"
            ),
        )
        report = GoBuildAnalyzer(GoBuildConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 0
        assert report.tool_failed is True

    def test_clean_build_is_zero_findings(self, tmp_path: Path, monkeypatch):
        _module(tmp_path)
        monkeypatch.setattr(go_build_analyzer, "require_executable", lambda *a, **k: "/usr/bin/go")
        monkeypatch.setattr(
            go_build_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=0, stdout="", stderr=""),
        )
        report = GoBuildAnalyzer(GoBuildConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 0
        assert not report.tool_failed


# ---------------------------------------------------------------------------
# gofmt
# ---------------------------------------------------------------------------

class TestGoFmtAnalyzerParsing:
    def test_no_go_mod_is_graceful(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(go_fmt_analyzer, "require_executable", lambda *a, **k: "/usr/bin/gofmt")
        report = GoFmtAnalyzer(GoFmtConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 0
        assert "go.mod" in report.tools_unavailable[0]

    def test_drift_line_becomes_style_warning(self, tmp_path: Path, monkeypatch):
        _module(tmp_path)
        monkeypatch.setattr(go_fmt_analyzer, "require_executable", lambda *a, **k: "/usr/bin/gofmt")
        monkeypatch.setattr(
            go_fmt_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=0, stdout="pkg/main.go\n", stderr=""),
        )
        report = GoFmtAnalyzer(GoFmtConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 1
        finding = report.findings[0]
        assert finding.rule_id == "gofmt.not-formatted"
        assert finding.category == "style"
        assert finding.severity == "warning"
        assert finding.file_path == str(Path("mod/pkg/main.go"))
        assert not report.tool_failed

    def test_parse_error_line_becomes_bug_error_distinct_from_drift(self, tmp_path: Path, monkeypatch):
        _module(tmp_path)
        monkeypatch.setattr(go_fmt_analyzer, "require_executable", lambda *a, **k: "/usr/bin/gofmt")
        output = "pkg/bad.go:3:12: expected ')', found '{'\npkg/main.go\n"
        monkeypatch.setattr(
            go_fmt_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=2, stdout=output, stderr=""),
        )
        report = GoFmtAnalyzer(GoFmtConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 2
        parse_error = next(f for f in report.findings if f.rule_id == "gofmt.parse-error")
        assert parse_error.severity == "error"
        assert parse_error.category == "bug"
        assert parse_error.line_number == 3
        drift = next(f for f in report.findings if f.rule_id == "gofmt.not-formatted")
        assert drift.severity == "warning"
        assert not report.tool_failed  # gofmt ran and reported something real, even mid-error

    def test_nonzero_exit_with_no_output_is_a_tool_failure(self, tmp_path: Path, monkeypatch):
        _module(tmp_path)
        monkeypatch.setattr(go_fmt_analyzer, "require_executable", lambda *a, **k: "/usr/bin/gofmt")
        monkeypatch.setattr(
            go_fmt_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=1, stdout="", stderr=""),
        )
        report = GoFmtAnalyzer(GoFmtConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 0
        assert report.tool_failed is True


# ---------------------------------------------------------------------------
# go test
# ---------------------------------------------------------------------------

_GO_TEST_PASS_AND_FAIL = "\n".join([
    json.dumps({"Time": "t", "Action": "start", "Package": "modname"}),
    json.dumps({"Time": "t", "Action": "run", "Package": "modname", "Test": "TestOk"}),
    json.dumps({"Time": "t", "Action": "pass", "Package": "modname", "Test": "TestOk", "Elapsed": 0}),
    json.dumps({"Time": "t", "Action": "run", "Package": "modname", "Test": "TestBad"}),
    json.dumps({
        "Time": "t", "Action": "output", "Package": "modname", "Test": "TestBad",
        "Output": "    add_test.go:13: Add(2, 2) = 4, want 5\n",
    }),
    json.dumps({"Time": "t", "Action": "fail", "Package": "modname", "Test": "TestBad", "Elapsed": 0}),
    json.dumps({"Time": "t", "Action": "fail", "Package": "modname", "Elapsed": 0.01}),
]) + "\n"

_GO_TEST_BUILD_FAIL = "\n".join([
    json.dumps({
        "ImportPath": "modname [modname.test]", "Action": "build-output",
        "Output": "./broken.go:4:2: undefined: thisDoesNotExist\n",
    }),
    json.dumps({"ImportPath": "modname [modname.test]", "Action": "build-fail"}),
    json.dumps({"Time": "t", "Action": "start", "Package": "modname"}),
    json.dumps({
        "Time": "t", "Action": "fail", "Package": "modname", "Elapsed": 0,
        "FailedBuild": "modname [modname.test]",
    }),
]) + "\n"

_GO_TEST_NO_TEST_FILES = "\n".join([
    json.dumps({"Time": "t", "Action": "start", "Package": "modname"}),
    json.dumps({"Time": "t", "Action": "skip", "Package": "modname", "Elapsed": 0}),
]) + "\n"


class TestGoTestAnalyzerParsing:
    def test_no_go_mod_is_graceful(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(go_test_analyzer, "require_executable", lambda *a, **k: "/usr/bin/go")
        report = GoTestAnalyzer(GoTestConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 0
        assert "go.mod" in report.tools_unavailable[0]

    def test_passing_and_failing_test_produce_one_finding(self, tmp_path: Path, monkeypatch):
        _module(tmp_path)
        monkeypatch.setattr(go_test_analyzer, "require_executable", lambda *a, **k: "/usr/bin/go")
        monkeypatch.setattr(
            go_test_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=1, stdout=_GO_TEST_PASS_AND_FAIL, stderr=""),
        )
        report = GoTestAnalyzer(GoTestConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 1
        finding = report.findings[0]
        assert finding.rule_id == "go-test::TestBad"
        assert finding.severity == "error"
        assert "Add(2, 2)" in finding.description
        assert finding.file_path == str(Path("mod/add_test.go"))
        assert finding.line_number == 13
        assert not report.tool_failed

    def test_build_fail_produces_per_file_diagnostic(self, tmp_path: Path, monkeypatch):
        _module(tmp_path)
        monkeypatch.setattr(go_test_analyzer, "require_executable", lambda *a, **k: "/usr/bin/go")
        monkeypatch.setattr(
            go_test_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=1, stdout=_GO_TEST_BUILD_FAIL, stderr=""),
        )
        report = GoTestAnalyzer(GoTestConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 1
        finding = report.findings[0]
        assert finding.rule_id == "go-test::build-failed"
        assert finding.line_number == 4
        assert "undefined: thisDoesNotExist" in finding.description
        assert not report.tool_failed

    def test_no_test_files_is_a_clean_skip_not_a_failure(self, tmp_path: Path, monkeypatch):
        _module(tmp_path)
        monkeypatch.setattr(go_test_analyzer, "require_executable", lambda *a, **k: "/usr/bin/go")
        monkeypatch.setattr(
            go_test_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=0, stdout=_GO_TEST_NO_TEST_FILES, stderr=""),
        )
        report = GoTestAnalyzer(GoTestConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 0
        assert not report.tool_failed

    def test_no_parseable_events_at_all_is_a_tool_failure(self, tmp_path: Path, monkeypatch):
        # A malformed go.mod: go test fails before emitting a single JSON
        # event. Zero findings here must not read as "all tests passed".
        _module(tmp_path)
        monkeypatch.setattr(go_test_analyzer, "require_executable", lambda *a, **k: "/usr/bin/go")
        monkeypatch.setattr(
            go_test_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(
                returncode=1, stdout="", stderr="go: errors parsing go.mod:\ngo.mod:1: unknown directive: not\n"
            ),
        )
        report = GoTestAnalyzer(GoTestConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 0
        assert report.tool_failed is True

    def test_timeout_is_reported_not_raised(self, tmp_path: Path, monkeypatch):
        _module(tmp_path)
        monkeypatch.setattr(go_test_analyzer, "require_executable", lambda *a, **k: "/usr/bin/go")
        monkeypatch.setattr(
            go_test_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=-1, stdout="", stderr="", timed_out=True),
        )
        report = GoTestAnalyzer(GoTestConfig(scan_path=tmp_path, timeout_seconds=5)).analyze()
        assert report.total_findings == 0
        assert report.tool_failed is True


# ---------------------------------------------------------------------------
# govulncheck
# ---------------------------------------------------------------------------

def _pretty_messages(*messages: dict) -> str:
    """
    Real govulncheck `-json` output is NOT newline-delimited: each Message
    is pretty-printed and concatenated directly onto the next with no
    separator. This mirrors that shape rather than one-JSON-object-per-line,
    which is what the real captured sample (see go_vuln_analyzer's module
    docstring) actually looks like.
    """
    return "".join(json.dumps(message, indent=2) for message in messages)


_REAL_SHAPE_OSV = {
    "osv": {
        "id": "GO-2023-1495",
        "summary": "Denial of service via crafted input",
        "details": "Full advisory details.",
        "affected": [{"package": {"name": "example.com/vulnpkg", "ecosystem": "Go"}}],
        "database_specific": {"url": "https://pkg.go.dev/GO-2023-1495"},
    }
}


class TestGoVulnAnalyzerParsing:
    def test_not_installed_is_graceful_not_a_crash(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(go_vuln_analyzer, "find_optional_executable", lambda *a, **k: None)
        report = GoVulnAnalyzer(GoVulnConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 0
        assert "go install golang.org/x/vuln/cmd/govulncheck" in report.tools_unavailable[0]

    def test_no_go_mod_is_graceful(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(go_vuln_analyzer, "find_optional_executable", lambda *a, **k: "/usr/bin/govulncheck")
        report = GoVulnAnalyzer(GoVulnConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 0
        assert "go.mod" in report.tools_unavailable[0]

    def test_pretty_printed_multiline_stream_is_parsed_not_ndjson(self, tmp_path: Path, monkeypatch):
        # Regression lock for the real shape mistake this analyser's
        # docstring documents: a naive line-by-line json.loads over this
        # exact fixture parses zero complete messages.
        module_dir = _module(tmp_path)
        called_finding = {
            "finding": {
                "osv": "GO-2023-1495",
                "fixed_version": "v1.2.3",
                "trace": [{
                    "module": "example.com/vulnpkg", "package": "example.com/vulnpkg",
                    "function": "Parse", "position": {"filename": "main.go", "line": 10, "column": 5},
                }],
            }
        }
        output = _pretty_messages(
            {"config": {"protocol_version": "v1.0.0"}}, _REAL_SHAPE_OSV, called_finding
        )
        naive_ndjson_count = sum(1 for line in output.splitlines() if _is_complete_json(line))
        assert naive_ndjson_count == 0  # proves the fixture really is multi-line, not NDJSON

        monkeypatch.setattr(go_vuln_analyzer, "find_optional_executable", lambda *a, **k: "/usr/bin/govulncheck")
        monkeypatch.setattr(
            go_vuln_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=3, stdout=output, stderr=""),
        )
        report = GoVulnAnalyzer(GoVulnConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 1
        finding = report.findings[0]
        assert finding.rule_id == "GO-2023-1495"
        assert finding.severity == "error"  # called -- reachable from user code
        assert finding.file_path == str(Path("mod/main.go"))
        assert finding.line_number == 10
        assert "v1.2.3" in finding.fix_suggestion
        assert not report.tool_failed

    def test_imported_but_not_called_is_warning_not_error(self, tmp_path: Path, monkeypatch):
        module_dir = _module(tmp_path)
        finding = {"finding": {"osv": "GO-2023-1495", "trace": [{"module": "example.com/vulnpkg", "package": "example.com/vulnpkg"}]}}
        output = _pretty_messages(_REAL_SHAPE_OSV, finding)
        monkeypatch.setattr(go_vuln_analyzer, "find_optional_executable", lambda *a, **k: "/usr/bin/govulncheck")
        monkeypatch.setattr(
            go_vuln_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=0, stdout=output, stderr=""),
        )
        report = GoVulnAnalyzer(GoVulnConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 1
        assert report.findings[0].severity == "warning"
        assert not report.tool_failed

    def test_required_only_is_info(self, tmp_path: Path, monkeypatch):
        _module(tmp_path)
        finding = {"finding": {"osv": "GO-2023-1495", "trace": [{"module": "example.com/vulnpkg"}]}}
        output = _pretty_messages(_REAL_SHAPE_OSV, finding)
        monkeypatch.setattr(go_vuln_analyzer, "find_optional_executable", lambda *a, **k: "/usr/bin/govulncheck")
        monkeypatch.setattr(
            go_vuln_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=0, stdout=output, stderr=""),
        )
        report = GoVulnAnalyzer(GoVulnConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 1
        assert report.findings[0].severity == "info"

    def test_multiple_findings_for_same_osv_keep_highest_severity_only(self, tmp_path: Path, monkeypatch):
        _module(tmp_path)
        module_only = {"finding": {"osv": "GO-2023-1495", "trace": [{"module": "example.com/vulnpkg"}]}}
        called = {
            "finding": {
                "osv": "GO-2023-1495",
                "trace": [{"module": "example.com/vulnpkg", "package": "example.com/vulnpkg", "function": "Parse"}],
            }
        }
        output = _pretty_messages(_REAL_SHAPE_OSV, module_only, called)
        monkeypatch.setattr(go_vuln_analyzer, "find_optional_executable", lambda *a, **k: "/usr/bin/govulncheck")
        monkeypatch.setattr(
            go_vuln_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=3, stdout=output, stderr=""),
        )
        report = GoVulnAnalyzer(GoVulnConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 1
        assert report.findings[0].severity == "error"

    def test_vulnerability_database_unreachable_is_a_tool_failure_not_clean(self, tmp_path: Path, monkeypatch):
        # This is the exact real failure this sandbox produced when running
        # the real, freshly-built govulncheck v1.7.0 against
        # Lexicon/LexiconGo: valid config/SBOM messages on stdout, a plain
        # error on stderr, exit 1 -- and critically, zero osv/finding
        # messages. This is the "looks clean but actually crashed" trap the
        # task exists to close: a naive "did it produce any findings"
        # check would report this as a clean scan.
        _module(tmp_path)
        output = _pretty_messages(
            {"config": {"protocol_version": "v1.0.0", "scanner_name": "govulncheck"}},
            {"SBOM": {"go_version": "go1.24.7", "modules": [{"path": "modname"}]}},
        )
        monkeypatch.setattr(go_vuln_analyzer, "find_optional_executable", lambda *a, **k: "/usr/bin/govulncheck")
        monkeypatch.setattr(
            go_vuln_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(
                returncode=1, stdout=output,
                stderr='govulncheck: fetching vulnerabilities: Get "https://vuln.go.dev/index/modules.json.gz": Forbidden\n',
            ),
        )
        report = GoVulnAnalyzer(GoVulnConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 0
        assert report.tool_failed is True
        assert "Forbidden" in report.tools_unavailable[0]

    def test_clean_scan_exit_zero_zero_findings_is_not_a_failure(self, tmp_path: Path, monkeypatch):
        _module(tmp_path)
        output = _pretty_messages({"config": {"protocol_version": "v1.0.0"}})
        monkeypatch.setattr(go_vuln_analyzer, "find_optional_executable", lambda *a, **k: "/usr/bin/govulncheck")
        monkeypatch.setattr(
            go_vuln_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=0, stdout=output, stderr=""),
        )
        report = GoVulnAnalyzer(GoVulnConfig(scan_path=tmp_path)).analyze()
        assert report.total_findings == 0
        assert not report.tool_failed

    def test_timeout_is_reported_not_raised(self, tmp_path: Path, monkeypatch):
        _module(tmp_path)
        monkeypatch.setattr(go_vuln_analyzer, "find_optional_executable", lambda *a, **k: "/usr/bin/govulncheck")
        monkeypatch.setattr(
            go_vuln_analyzer, "run_tool",
            lambda cmd, cwd, timeout: ToolRunResult(returncode=-1, stdout="", stderr="", timed_out=True),
        )
        report = GoVulnAnalyzer(GoVulnConfig(scan_path=tmp_path, timeout_seconds=5)).analyze()
        assert report.total_findings == 0
        assert report.tool_failed is True


def _is_complete_json(line: str) -> bool:
    try:
        json.loads(line)
        return True
    except json.JSONDecodeError:
        return False


# ---------------------------------------------------------------------------
# Real-tool integration (skip cleanly when the toolchain is unavailable)
# ---------------------------------------------------------------------------

_GO_TOOLS_PRESENT = all(shutil.which(tool) is not None for tool in ("go", "gofmt"))


@pytest.mark.skipif(not _GO_TOOLS_PRESENT, reason="go/gofmt not installed in this environment")
class TestGoRealToolIntegration:
    """Exercises the real Go toolchain against the checked-in fixture module."""

    def _fixture_copy(self, tmp_path: Path) -> Path:
        fixture_src = Path(__file__).resolve().parents[4] / "fixtures" / "go_toolchain_demo"
        module_copy = tmp_path / "go_toolchain_demo"
        shutil.copytree(fixture_src, module_copy)
        return module_copy

    def test_go_vet_detects_known_finding_in_fixture(self, tmp_path: Path):
        module_copy = self._fixture_copy(tmp_path)
        report = GoVetAnalyzer(GoVetConfig(scan_path=module_copy, timeout_seconds=60)).analyze()
        assert not report.tools_unavailable
        assert report.total_findings >= 1
        assert all(f.rule_id == "go-vet" for f in report.findings)

    def test_go_build_is_clean_on_fixture(self, tmp_path: Path):
        module_copy = self._fixture_copy(tmp_path)
        before = set(module_copy.rglob("*"))
        report = GoBuildAnalyzer(GoBuildConfig(scan_path=module_copy, timeout_seconds=60)).analyze()
        assert not report.tool_failed
        assert report.total_findings == 0
        # go build must not leave a compiled binary in the scanned tree.
        after = set(module_copy.rglob("*"))
        assert after == before

    def test_gofmt_detects_drift_in_fixture(self, tmp_path: Path):
        module_copy = self._fixture_copy(tmp_path)
        report = GoFmtAnalyzer(GoFmtConfig(scan_path=module_copy, timeout_seconds=60)).analyze()
        assert not report.tools_unavailable
        rule_ids = {f.rule_id for f in report.findings}
        assert "gofmt.not-formatted" in rule_ids

    def test_go_test_detects_known_failure_and_build_fail_in_fixture(self, tmp_path: Path):
        module_copy = self._fixture_copy(tmp_path)
        report = GoTestAnalyzer(GoTestConfig(scan_path=module_copy, timeout_seconds=60)).analyze()
        assert not report.tools_unavailable
        rule_ids = {f.rule_id for f in report.findings}
        assert "go-test::TestAddFailsOnPurpose" in rule_ids
        assert "go-test::build-failed" in rule_ids


@pytest.mark.skipif(not _GO_TOOLS_PRESENT, reason="go not installed in this environment")
class TestGoBuildRealBrokenReplaceFailure:
    """
    Exercises GoBuildAnalyzer against a real, unresolved `replace` directive
    -- a genuine `go build` compile failure, not a synthetic ToolFinding.

    This used to point at the real GAIA/Keryx checkout, whose own go.mod
    replaces gaia/lexicon with a relative sibling path (`../Lexicon/
    LexiconGo`) that only fails to resolve when GAIA and Lexicon are cloned
    as true siblings under the same parent directory. That made the test
    dependent on an accident of sandbox layout: a Lexicon checkout later
    appearing *nested inside* GAIA/ (GAIA/Lexicon/LexiconGo) made the
    relative path resolve after all, so the "known failing" build started
    succeeding -- a change in checkout layout, not in GoBuildAnalyzer's
    correctness, silently flipped this test's assumption.

    The checked-in go_toolchain_broken_replace fixture reproduces the same
    class of failure deterministically: its go.mod's `replace` points at a
    relative sibling path (`../does-not-exist-on-disk/...`) chosen
    specifically so that it can never resolve, regardless of what other
    repositories happen to be checked out alongside this one.
    """

    def _fixture_copy(self, tmp_path: Path) -> Path:
        fixture_src = Path(__file__).resolve().parents[4] / "fixtures" / "go_toolchain_broken_replace"
        module_copy = tmp_path / "go_toolchain_broken_replace"
        shutil.copytree(fixture_src, module_copy)
        return module_copy

    def test_unresolved_replace_produces_a_real_build_failure_finding(self, tmp_path: Path):
        module_copy = self._fixture_copy(tmp_path)
        report = GoBuildAnalyzer(GoBuildConfig(scan_path=module_copy, timeout_seconds=120)).analyze()
        assert not report.tool_failed
        assert report.total_findings >= 1
        assert all(f.rule_id == "go-build" for f in report.findings)
        assert any("does-not-exist-on-disk" in f.description.lower() for f in report.findings)
