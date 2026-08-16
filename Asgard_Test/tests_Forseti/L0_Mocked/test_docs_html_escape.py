"""CH-0064: documentation HTML must not interpolate unescaped title/contact/CSS."""

from Asgard.Forseti.Documentation.models.docs_models import (
    APIDocConfig,
    DocumentationStructure,
)
from Asgard.Forseti.Documentation.services._docs_generator_helpers import (
    _safe_href,
    generate_html_overview,
)
from Asgard.Forseti.Documentation.services.docs_generator import DocsGeneratorService


def test_javascript_url_is_not_an_href():
    assert _safe_href("javascript:alert(1)") == "#"
    assert _safe_href("https://example.com/docs").startswith("https://")


def test_contact_javascript_url_not_in_href():
    doc = DocumentationStructure(
        title="API",
        version="1.0",
        contact={"url": "javascript:alert(1)", "email": "a@b.c"},
    )
    html = generate_html_overview(doc)
    assert 'href="javascript:' not in html
    assert "javascript:alert(1)" in html  # visible as escaped text
    assert 'href="#"' in html


def test_title_and_custom_css_not_injected():
    service = DocsGeneratorService(
        APIDocConfig(custom_css="</style><script>alert(1)</script>")
    )
    doc = DocumentationStructure(title="<img src=x onerror=alert(1)>", version="1")
    generated = service._generate_html(doc)
    html = generated.content
    assert "<img src=" not in html
    assert "&lt;img" in html
    assert "</style><script>" not in html
