"""
Deterministic Freya browser/page fixture harness.

Provides fake Playwright-shaped page and element objects driven by canned,
declarative DOM specs — NO live browser, NO network. The fakes implement
exactly the async surface Freya's accessibility check functions use
(query_selector_all / query_selector / title / evaluate / get_attribute /
inner_text / screenshot), so the real check logic in
Asgard.Freya.Accessibility.services runs unmodified and deterministically.

Also ships canned screenshot bytes and canned page-load timings consistent
with Freya's Performance models, for cross-package tests that feed frontend
metrics into other packages (e.g. Verdandi SLO/SLA).
"""

import asyncio
import re
from typing import Any, Dict, List, Optional

from Asgard.Freya.Accessibility.models.accessibility_models import (
    AccessibilityConfig,
    AccessibilityReport,
)
from Asgard.Freya.Accessibility.services._wcag_checks import (
    check_forms,
    check_images,
    check_structure,
)
from Asgard.Freya.Accessibility.services.wcag_validator import (
    enrich_violations_dual_axis,
)

# Minimal deterministic PNG payload (header + filler), matching the style of
# the existing Freya L0 fixtures. Enough for code paths that only move bytes.
CANNED_SCREENSHOT_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 128


# =============================================================================
# Selector matching (deliberately small: only the CSS subset Freya checks use)
# =============================================================================

_ATTR_RE = re.compile(r"\[([\w-]+)=['\"]([^'\"]*)['\"]\]")
_NOT_RE = re.compile(r":not\(\[([\w-]+)=['\"]([^'\"]*)['\"]\]\)")


def _match_part(element: "FakeElement", part: str) -> bool:
    """Match a single comma-free selector part against an element."""
    part = part.strip()
    if not part:
        return False
    exclusions = _NOT_RE.findall(part)
    base = _NOT_RE.sub("", part)
    requirements = _ATTR_RE.findall(base)
    tag = _ATTR_RE.sub("", base).strip()
    if tag and element.tag != tag:
        return False
    for attr, value in requirements:
        if element.attrs.get(attr) != value:
            return False
    for attr, value in exclusions:
        if element.attrs.get(attr) == value:
            return False
    return True


def _matches(element: "FakeElement", selector: str) -> bool:
    return any(_match_part(element, part) for part in selector.split(","))


# =============================================================================
# Fake Playwright objects
# =============================================================================

class FakeElement:
    """
    Deterministic stand-in for a Playwright ElementHandle.

    Spec keys: tag (str), attrs (dict), text (str), in_label (bool),
    children (list of element specs).
    """

    def __init__(self, spec: Dict[str, Any]):
        self.tag: str = spec.get("tag", "div")
        self.attrs: Dict[str, str] = dict(spec.get("attrs", {}))
        self.text: str = spec.get("text", "")
        self.in_label: bool = bool(spec.get("in_label", False))
        self.children: List["FakeElement"] = [
            FakeElement(child) for child in spec.get("children", [])
        ]

    def _outer_html(self) -> str:
        attrs = "".join(f' {k}="{v}"' for k, v in sorted(self.attrs.items()))
        return f"<{self.tag}{attrs}>{self.text}</{self.tag}>"

    async def get_attribute(self, name: str) -> Optional[str]:
        return self.attrs.get(name)

    async def inner_text(self) -> str:
        return self.text

    async def evaluate(self, script: str) -> Any:
        if "outerHTML" in script:
            return self._outer_html()
        if "tagName" in script:
            return self.tag
        if "closest('label')" in script:
            return self.in_label
        return None

    async def bounding_box(self) -> Dict[str, float]:
        return {"x": 0.0, "y": 0.0, "width": 100.0, "height": 50.0}

    async def focus(self) -> None:
        return None

    async def screenshot(self, path: Optional[str] = None, **kwargs) -> bytes:
        if path:
            with open(path, "wb") as handle:
                handle.write(CANNED_SCREENSHOT_PNG)
        return CANNED_SCREENSHOT_PNG

    async def query_selector(self, selector: str) -> Optional["FakeElement"]:
        for child in self.children:
            if _matches(child, selector):
                return child
        return None

    async def query_selector_all(self, selector: str) -> List["FakeElement"]:
        return [child for child in self.children if _matches(child, selector)]


class _FakeKeyboard:
    async def press(self, key: str) -> None:
        return None


class FakePage:
    """
    Deterministic stand-in for a Playwright Page.

    Spec keys:
        url (str), title (str), elements (list of element specs, in DOM
        order), metrics (dict: substring of a page.evaluate script -> canned
        return value).
    """

    def __init__(self, spec: Dict[str, Any]):
        self.spec = spec
        self.url: str = spec.get("url", "http://fixture.local/")
        self._title: str = spec.get("title", "")
        self.elements: List[FakeElement] = [
            FakeElement(element) for element in spec.get("elements", [])
        ]
        self.metrics: Dict[str, Any] = dict(spec.get("metrics", {}))
        self.keyboard = _FakeKeyboard()
        self.viewport_size = {"width": 1920, "height": 1080}
        self.visited: List[str] = []

    async def goto(self, url: str, **kwargs) -> None:
        # No network: simply record the navigation.
        self.visited.append(url)
        self.url = url

    async def title(self) -> str:
        return self._title

    async def query_selector(self, selector: str) -> Optional[FakeElement]:
        for element in self.elements:
            if _matches(element, selector):
                return element
        return None

    async def query_selector_all(self, selector: str) -> List[FakeElement]:
        return [element for element in self.elements if _matches(element, selector)]

    async def evaluate(self, script: str) -> Any:
        for key, value in self.metrics.items():
            if key in script:
                return value
        return None

    async def screenshot(self, path: Optional[str] = None, **kwargs) -> bytes:
        if path:
            with open(path, "wb") as handle:
                handle.write(CANNED_SCREENSHOT_PNG)
        return CANNED_SCREENSHOT_PNG

    async def wait_for_selector(self, selector: str, **kwargs) -> Optional[FakeElement]:
        return await self.query_selector(selector)

    async def wait_for_timeout(self, timeout: float) -> None:
        return None

    async def close(self) -> None:
        return None


# =============================================================================
# Canned page specs
# =============================================================================

def accessible_page_spec() -> Dict[str, Any]:
    """A page that passes Freya's image/structure/form checks."""
    return {
        "url": "http://fixture.local/accessible",
        "title": "Asgard Docs - Home",
        "elements": [
            {"tag": "img", "attrs": {"src": "/logo.png", "alt": "Asgard logo"}},
            {"tag": "h1", "text": "Welcome"},
            {"tag": "h2", "text": "Getting started"},
            {"tag": "main", "text": "Main content"},
            {"tag": "label", "attrs": {"for": "email"}, "text": "Email"},
            {
                "tag": "input",
                "attrs": {"type": "email", "id": "email", "name": "email"},
            },
            {"tag": "button", "attrs": {"type": "submit"}, "text": "Submit"},
        ],
    }


def inaccessible_page_spec() -> Dict[str, Any]:
    """
    A page with deterministic, known violations:
    - missing page title (SERIOUS, 2.4.2)
    - img with no alt (CRITICAL, 1.1.1)
    - first heading is h2, then a skip h2 -> h4 (MODERATE x2, 1.3.1)
    - no <main> landmark (MODERATE, 1.3.1)
    - unlabeled input (SERIOUS, 3.3.2)
    - button with no accessible name (CRITICAL, 4.1.2)
    """
    return {
        "url": "http://fixture.local/inaccessible",
        "title": "",
        "elements": [
            {"tag": "img", "attrs": {"src": "/hero.jpg"}},
            {"tag": "h2", "text": "Section"},
            {"tag": "h4", "text": "Deep section"},
            {"tag": "input", "attrs": {"type": "text", "name": "search"}},
            {"tag": "button", "attrs": {}, "text": ""},
        ],
    }


def canned_page_load_timings() -> Dict[str, float]:
    """
    Deterministic page-load timings (milliseconds), shaped like the signals
    Freya's Performance module extracts from a real browser.
    """
    return {
        "ttfb_ms": 120.0,
        "dom_content_loaded_ms": 640.0,
        "load_event_ms": 1180.0,
        "largest_contentful_paint_ms": 1450.0,
        "first_contentful_paint_ms": 820.0,
        "cumulative_layout_shift": 0.02,
        "total_blocking_time_ms": 90.0,
    }


def canned_slow_page_load_timings() -> Dict[str, float]:
    """Deterministic timings for a badly regressed page."""
    return {
        "ttfb_ms": 2400.0,
        "dom_content_loaded_ms": 6800.0,
        "load_event_ms": 11200.0,
        "largest_contentful_paint_ms": 9800.0,
        "first_contentful_paint_ms": 5200.0,
        "cumulative_layout_shift": 0.41,
        "total_blocking_time_ms": 2200.0,
    }


# =============================================================================
# Scan driver
# =============================================================================

def run_accessibility_scan(
    page_spec: Dict[str, Any],
    config: Optional[AccessibilityConfig] = None,
) -> AccessibilityReport:
    """
    Run Freya's real WCAG check functions against a FakePage built from
    ``page_spec`` and assemble an AccessibilityReport. Fully deterministic
    (violation ids are content hashes) and browser-free.
    """
    config = config or AccessibilityConfig()
    page = FakePage(page_spec)

    async def _run() -> AccessibilityReport:
        violations = []
        passed_checks = 0

        if config.check_images:
            img_violations, img_passed = await check_images(
                page, config.include_element_html
            )
            violations.extend(img_violations)
            passed_checks += img_passed

        if config.check_structure:
            struct_violations, struct_passed = await check_structure(page)
            violations.extend(struct_violations)
            passed_checks += struct_passed

        if config.check_forms:
            form_violations, form_passed = await check_forms(
                page, config.include_element_html
            )
            violations.extend(form_violations)
            passed_checks += form_passed

        enrich_violations_dual_axis(violations)

        total_checks = passed_checks + len(violations)
        if total_checks > 0:
            score = round((passed_checks / total_checks) * 100.0, 1)
        else:
            score = 100.0

        return AccessibilityReport(
            url=page.url,
            wcag_level=getattr(config.wcag_level, "value", config.wcag_level),
            violations=violations,
            warnings=[],
            notices=[],
            score=score,
            passed_checks=passed_checks,
            total_checks=total_checks,
        )

    return asyncio.run(_run())
