"""CH-0043: Hardcoded-credential snippets must not include the full secret."""

import argparse
import json
import tempfile
from pathlib import Path

from Asgard.Bragi.Quality.languages.javascript.services.js_analyzer import JSAnalyzer
from Asgard.Bragi.Quality.languages.php.services.php_analyzer import PhpAnalyzer
from Asgard.Bragi.Quality.languages.ruby.services.ruby_analyzer import RubyAnalyzer
from Asgard.Bragi.Quality.languages.rust.services._rust_rules import check_hardcoded_credentials
from Asgard.Bragi.Quality.models.env_fallback_models import (
    EnvFallbackSeverity,
    EnvFallbackType,
    EnvFallbackViolation,
)
from Asgard.Bragi.Quality.services.env_fallback_scanner import EnvFallbackScanner
from Asgard.Bragi.Quality.services._env_fallback_reporter import (
    generate_json_report,
    generate_markdown_report,
    generate_text_report,
)
from Asgard.Bragi.Quality.utilities.secret_snippet import (
    mask_quoted_literals,
    mask_stored_secret,
)
from Asgard.Heimdall.Security.utilities.security_utils import mask_secret
from Asgard.Heimdall.cli.handlers.lang_analyzers import run_js_analysis

# Unique 32-char token (not a placeholder; high entropy; no "test"/"example").
_FAKE_KEY = "Zq8nR3wK7pM4yT9eX2vC6dH1zJ5uB0Wf"


def _assert_secret_absent(token: str, *blobs: str) -> None:
    joined = "\n".join(blob or "" for blob in blobs)
    assert len(token) == 32
    assert token not in joined
    assert token[:4] not in joined
    assert token[-4:] not in joined


class TestMaskQuotedLiteralsPolicy:
    def test_long_literal_is_last_two_only(self):
        line = f'const apiKey = "{_FAKE_KEY}";'
        masked = mask_quoted_literals(line)
        assert masked == f'const apiKey = "{mask_secret(_FAKE_KEY)}";'
        assert masked.endswith('Wf";')
        assert not masked.startswith(_FAKE_KEY[:2])
        _assert_secret_absent(_FAKE_KEY, masked)

    def test_short_literal_is_length_only(self):
        assert mask_quoted_literals('password = "ab"') == 'password = "**"'

    def test_stored_default_preserves_quotes(self):
        assert mask_stored_secret(f"'{_FAKE_KEY}'") == f"'{mask_secret(_FAKE_KEY)}'"


class TestJsHardcodedCredentialSnippet:
    def test_fake_key_absent_from_finding_and_report_dict(self):
        code = f'const apiKey = "{_FAKE_KEY}";\n'
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "config.js").write_text(code)
            report = JSAnalyzer().analyze(scan_path=tmpdir)
        findings = [f for f in report.findings if f.rule_id == "js.hardcoded-credentials"]
        assert findings
        finding = findings[0]
        dumped = json.dumps(report.dict(), default=str)
        assert "apiKey" in finding.code_snippet
        assert mask_secret(_FAKE_KEY) in finding.code_snippet
        _assert_secret_absent(
            _FAKE_KEY,
            finding.code_snippet,
            finding.description,
            dumped,
        )


class TestPhpHardcodedCredentialSnippet:
    def test_fake_key_absent_from_finding_and_report_dict(self):
        code = f"<?php\n$api_key = '{_FAKE_KEY}';\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "config.php").write_text(code)
            report = PhpAnalyzer().analyze(scan_path=tmpdir)
        findings = [f for f in report.findings if f.rule_id == "php.no-hardcoded-credentials"]
        assert findings
        dumped = json.dumps(report.dict(), default=str)
        _assert_secret_absent(_FAKE_KEY, findings[0].code_snippet, dumped)


class TestRubyHardcodedCredentialSnippet:
    def test_fake_key_absent_from_finding_and_report_dict(self):
        code = f'api_key = "{_FAKE_KEY}"\n'
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "config.rb").write_text(code)
            report = RubyAnalyzer().analyze(scan_path=tmpdir)
        findings = [f for f in report.findings if f.rule_id == "ruby.no-hardcoded-credentials"]
        assert findings
        dumped = json.dumps(report.dict(), default=str)
        _assert_secret_absent(_FAKE_KEY, findings[0].code_snippet, dumped)


class TestRustHardcodedCredentialSnippet:
    def test_fake_key_absent_from_finding(self):
        lines = [f'    let api_key = "{_FAKE_KEY}";']
        findings = check_hardcoded_credentials("main.rs", lines)
        assert findings
        dumped = json.dumps(findings[0].dict(), default=str)
        _assert_secret_absent(_FAKE_KEY, findings[0].code_snippet, dumped)


class TestEnvFallbackSecretMasking:
    def test_model_masks_default_and_snippet(self):
        violation = EnvFallbackViolation(
            file_path="/app.py",
            line_number=1,
            code_snippet=f'os.getenv("PASSWORD", "{_FAKE_KEY}")',
            variable_name="PASSWORD",
            default_value=repr(_FAKE_KEY),
            fallback_type=EnvFallbackType.CREDENTIAL_KEY_GETENV_DEFAULT,
            severity=EnvFallbackSeverity.HIGH,
            context_description="Environment variable fallback at module level",
        )
        assert violation.variable_name == "PASSWORD"
        assert "PASSWORD" in violation.code_snippet
        _assert_secret_absent(
            _FAKE_KEY,
            violation.code_snippet,
            violation.default_value or "",
            violation.context_description,
        )

    def test_scanner_reports_omit_full_key(self):
        source = f'value = os.getenv("PASSWORD", "{_FAKE_KEY}")\n'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "app.py"
            path.write_text(source)
            report = EnvFallbackScanner().analyze(path)
        assert report.has_violations
        violation = report.detected_violations[0]
        text = generate_text_report(report)
        json_report = generate_json_report(report)
        markdown = generate_markdown_report(report)
        dumped = json.dumps(report.dict(), default=str)
        _assert_secret_absent(
            _FAKE_KEY,
            violation.code_snippet,
            violation.default_value or "",
            text,
            json_report,
            markdown,
            dumped,
        )


class TestJsCliReportOmitsFullKey:
    def test_text_and_json_cli_output(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "app.js").write_text(f'const apiKey = "{_FAKE_KEY}";\n')
            args = argparse.Namespace(
                path=tmpdir,
                exclude=None,
                disabled_rules=None,
                max_file_lines=500,
                max_complexity=10,
                format="text",
            )
            run_js_analysis(args)
            text_out = capsys.readouterr().out
            args.format = "json"
            run_js_analysis(args)
            json_out = capsys.readouterr().out
        assert "js.hardcoded-credentials" in text_out
        assert "js.hardcoded-credentials" in json_out
        _assert_secret_absent(_FAKE_KEY, text_out, json_out)
