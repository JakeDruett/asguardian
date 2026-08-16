"""HTML/XML report escaping helpers (CH-0067 / CWE-79)."""

from Asgard.Freya.Integration.services._report_escape import (
    esc,
    html_link,
    json_for_script,
    safe_css_token,
    safe_href,
    safe_src,
)


class TestEsc:
    def test_escapes_script_and_quotes(self):
        assert esc('<script>alert(1)</script>') == "&lt;script&gt;alert(1)&lt;/script&gt;"
        assert "&quot;" in esc('foo"bar')
        assert esc(None) == ""

    def test_strips_control_chars(self):
        assert "\x00" not in esc("ok\x00<script>")
        assert "&lt;script&gt;" in esc("ok\x00<script>")


class TestSafeHref:
    def test_https_allowed(self):
        assert safe_href("https://example.com/a") == "https://example.com/a"

    def test_javascript_rejected(self):
        assert safe_href("javascript:alert(1)") == ""
        assert safe_href("JAVASCRIPT:alert(1)") == ""

    def test_data_and_file_rejected(self):
        assert safe_href("data:text/html,<script>alert(1)</script>") == ""
        assert safe_href("file:///etc/passwd") == ""

    def test_protocol_relative_rejected(self):
        assert safe_href("//evil.example/x") == ""

    def test_attribute_breakout_escaped(self):
        href = safe_href('https://example.com/" onclick="alert(1)')
        assert href.startswith("https://example.com/")
        assert "&quot;" in href
        assert '" onclick="' not in href


class TestSafeSrc:
    def test_local_image_path_allowed(self):
        assert safe_src("/path/to/test.png") == "/path/to/test.png"
        assert safe_src("screenshots/foo.png") == "screenshots/foo.png"

    def test_javascript_and_data_rejected(self):
        assert safe_src("javascript:alert(1)") == ""
        assert safe_src("data:text/html,<script>alert(1)</script>") == ""

    def test_traversal_rejected(self):
        assert safe_src("../etc/passwd") == ""
        assert safe_src("screenshots/../../secret.png") == ""


class TestHtmlLink:
    def test_https_is_anchor(self):
        html = html_link("https://example.com")
        assert 'href="https://example.com"' in html
        assert "rel=" in html

    def test_javascript_is_text_only(self):
        html = html_link("javascript:alert(1)")
        assert "href=" not in html
        assert "javascript:alert(1)" in html


class TestJsonForScript:
    def test_closes_script_tag_is_escaped(self):
        payload = json_for_script({"</script><script>alert(1)": 1})
        assert "</script>" not in payload
        assert "\\u003c" in payload


class TestSafeCssToken:
    def test_known_severity_kept(self):
        assert safe_css_token("CRITICAL") == "critical"

    def test_injection_rejected(self):
        assert safe_css_token('foo"><script>') == ""
