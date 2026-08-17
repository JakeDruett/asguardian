"""HTML/GHA leftover escapes for CH-0064 / CH-0094 / CH-0046 / CH-0067."""

from datetime import datetime

from Asgard.common._format_methods import format_result_github, format_result_html
from Asgard.common._formatter_types import FormattedResult, Severity
from Asgard.Forseti.Documentation.models._docs_base_models import EndpointInfo
from Asgard.Forseti.Documentation.services._docs_generator_helpers import generate_html_endpoint
from Asgard.Heimdall.cli.handlers.scan_html import _generate_scan_html_report


def test_status_code_is_escaped():
    html = generate_html_endpoint(EndpointInfo(
        path="/x",
        method="GET",
        responses={"200<script>": {"description": "ok"}},
    ))
    assert "<script>" not in html
    assert "200&lt;script&gt;" in html


def test_github_annotation_escapes_newlines():
    result = FormattedResult(
        severity=Severity.ERROR,
        message="a\nb",
        file_path="f.py",
        line_number=1,
    )
    text = format_result_github(result)
    assert "\n" not in text.split("::", 2)[-1]
    assert "%0A" in text


def test_html_result_escapes_message():
    result = FormattedResult(
        severity=Severity.WARNING,
        message="<img>",
        file_path="x",
    )
    assert "<img>" not in format_result_html(result, verbose=False)
    assert "&lt;img&gt;" in format_result_html(result, verbose=False)


def test_scan_html_escapes_path():
    html = _generate_scan_html_report(
        {},
        {},
        "<script>x</script>",
        0.1,
        datetime(2026, 1, 1),
    )
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;x&lt;/script&gt;" in html
