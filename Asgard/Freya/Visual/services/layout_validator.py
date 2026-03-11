"""
Freya Layout Validator

Validates element layout including overflow, overlap,
alignment, and spacing issues.
"""

from datetime import datetime
from typing import List, Optional, Tuple

from playwright.async_api import async_playwright, Page

from Asgard.Freya.Visual.models.visual_models import (
    LayoutReport,
    LayoutIssue,
    LayoutIssueType,
    ElementBox,
)


class LayoutValidator:
    """
    Layout validation service.

    Detects overflow, overlap, alignment, and spacing issues.
    """

    def __init__(self):
        """Initialize the Layout Validator."""
        pass

    async def validate(
        self,
        url: str,
        viewport_width: int = 1920,
        viewport_height: int = 1080
    ) -> LayoutReport:
        """
        Validate layout on a page.

        Args:
            url: URL to validate
            viewport_width: Viewport width
            viewport_height: Viewport height

        Returns:
            LayoutReport with findings
        """
        issues = []
        overflow_elements = []
        overlapping_elements = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height}
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)

                overflow_issues, overflow = await self._check_overflow(page)
                issues.extend(overflow_issues)
                overflow_elements = overflow

                overlap_issues, overlaps = await self._check_overlap(page)
                issues.extend(overlap_issues)
                overlapping_elements = overlaps

                alignment_issues = await self._check_alignment(page)
                issues.extend(alignment_issues)

                spacing_issues = await self._check_spacing(page)
                issues.extend(spacing_issues)

                visibility_issues = await self._check_visibility(page)
                issues.extend(visibility_issues)

                total_elements = await page.evaluate("() => document.querySelectorAll('*').length")

            finally:
                await browser.close()

        return LayoutReport(
            url=url,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            tested_at=datetime.now().isoformat(),
            total_elements=total_elements,
            issues=issues,
            overflow_elements=overflow_elements,
            overlapping_elements=overlapping_elements,
        )

    async def _check_overflow(self, page: Page) -> Tuple[List[LayoutIssue], List[str]]:
        """Check for elements that overflow their containers."""
        issues = []
        overflow_elements = []

        try:
            overflows = await page.evaluate("""
                () => {
                    const results = [];
                    const elements = document.querySelectorAll('*');

                    for (const el of elements) {
                        const style = getComputedStyle(el);
                        const rect = el.getBoundingClientRect();

                        // Check horizontal overflow
                        if (el.scrollWidth > el.clientWidth &&
                            style.overflowX !== 'scroll' &&
                            style.overflowX !== 'auto' &&
                            style.overflowX !== 'hidden') {

                            const selector = el.id ? '#' + el.id :
                                              el.className ? el.tagName.toLowerCase() + '.' + el.className.split(' ')[0] :
                                              el.tagName.toLowerCase();

                            results.push({
                                selector: selector,
                                type: 'horizontal',
                                scrollWidth: el.scrollWidth,
                                clientWidth: el.clientWidth,
                                x: rect.x,
                                y: rect.y,
                                width: rect.width,
                                height: rect.height
                            });
                        }

                        // Check if element extends beyond viewport
                        if (rect.right > window.innerWidth || rect.left < 0) {
                            const selector = el.id ? '#' + el.id :
                                              el.className ? el.tagName.toLowerCase() + '.' + el.className.split(' ')[0] :
                                              el.tagName.toLowerCase();

                            results.push({
                                selector: selector,
                                type: 'viewport',
                                left: rect.left,
                                right: rect.right,
                                viewportWidth: window.innerWidth,
                                x: rect.x,
                                y: rect.y,
                                width: rect.width,
                                height: rect.height
                            });
                        }
                    }

                    return results.slice(0, 20);  // Limit results
                }
            """)

            for overflow in overflows:
                selector = overflow["selector"]
                overflow_elements.append(selector)

                if overflow["type"] == "horizontal":
                    description = f"Element overflows horizontally ({overflow['scrollWidth']}px > {overflow['clientWidth']}px)"
                else:
                    description = f"Element extends beyond viewport"

                issues.append(LayoutIssue(
                    issue_type=LayoutIssueType.OVERFLOW,
                    element_selector=selector,
                    description=description,
                    severity="moderate",
                    affected_area=ElementBox(
                        x=overflow["x"],
                        y=overflow["y"],
                        width=overflow["width"],
                        height=overflow["height"],
                        selector=selector,
                    ),
                    suggested_fix="Add overflow: hidden/auto or adjust element width",
                ))

        except Exception:
            pass

        return issues, overflow_elements

    async def _check_overlap(self, page: Page) -> Tuple[List[LayoutIssue], List[Tuple[str, str]]]:
        """Check for overlapping elements."""
        issues = []
        overlapping_pairs = []

        try:
            overlaps = await page.evaluate("""
                () => {
                    const results = [];
                    const interactive = document.querySelectorAll('a, button, input, select, textarea, [role="button"]');

                    for (let i = 0; i < interactive.length; i++) {
                        for (let j = i + 1; j < interactive.length; j++) {
                            const rect1 = interactive[i].getBoundingClientRect();
                            const rect2 = interactive[j].getBoundingClientRect();

                            if (rect1.width === 0 || rect1.height === 0 ||
                                rect2.width === 0 || rect2.height === 0) continue;

                            const overlap = !(rect1.right < rect2.left ||
                                             rect1.left > rect2.right ||
                                             rect1.bottom < rect2.top ||
                                             rect1.top > rect2.bottom);

                            if (overlap) {
                                const sel1 = interactive[i].id ? '#' + interactive[i].id :
                                             interactive[i].tagName.toLowerCase();
                                const sel2 = interactive[j].id ? '#' + interactive[j].id :
                                             interactive[j].tagName.toLowerCase();

                                results.push({
                                    selector1: sel1,
                                    selector2: sel2,
                                    rect1: { x: rect1.x, y: rect1.y, width: rect1.width, height: rect1.height },
                                    rect2: { x: rect2.x, y: rect2.y, width: rect2.width, height: rect2.height }
                                });
                            }
                        }
                    }

                    return results.slice(0, 10);
                }
            """)

            for overlap in overlaps:
                pair = (overlap["selector1"], overlap["selector2"])
                overlapping_pairs.append(pair)

                issues.append(LayoutIssue(
                    issue_type=LayoutIssueType.OVERLAP,
                    element_selector=overlap["selector1"],
                    description=f"Element overlaps with {overlap['selector2']}",
                    severity="serious",
                    related_elements=[overlap["selector2"]],
                    suggested_fix="Adjust positioning or z-index to prevent overlap",
                ))

        except Exception:
            pass

        return issues, overlapping_pairs

    async def _check_alignment(self, page: Page) -> List[LayoutIssue]:
        """Check for alignment issues."""
        issues = []

        try:
            misaligned = await page.evaluate("""
                () => {
                    const results = [];
                    const containers = document.querySelectorAll('[class*="row"], [class*="flex"], [class*="grid"]');

                    for (const container of containers) {
                        const children = Array.from(container.children);
                        if (children.length < 2) continue;

                        const tops = children.map(c => c.getBoundingClientRect().top);
                        const uniqueTops = [...new Set(tops.map(t => Math.round(t)))];

                        // If elements on same row but tops vary by more than 5px
                        if (uniqueTops.length > 1) {
                            const variance = Math.max(...tops) - Math.min(...tops);
                            if (variance > 5 && variance < 50) {
                                const selector = container.id ? '#' + container.id :
                                                 container.className ? container.tagName.toLowerCase() + '.' + container.className.split(' ')[0] :
                                                 container.tagName.toLowerCase();
                                results.push({
                                    selector: selector,
                                    variance: variance
                                });
                            }
                        }
                    }

                    return results.slice(0, 10);
                }
            """)

            for item in misaligned:
                issues.append(LayoutIssue(
                    issue_type=LayoutIssueType.MISALIGNMENT,
                    element_selector=item["selector"],
                    description=f"Children have inconsistent vertical alignment (variance: {item['variance']:.1f}px)",
                    severity="minor",
                    suggested_fix="Use align-items or consistent margins to align children",
                ))

        except Exception:
            pass

        return issues

    async def _check_spacing(self, page: Page) -> List[LayoutIssue]:
        """Check for spacing issues."""
        issues = []

        try:
            spacing_issues = await page.evaluate("""
                () => {
                    const results = [];
                    const textElements = document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, span, div');

                    for (const el of textElements) {
                        const style = getComputedStyle(el);
                        const rect = el.getBoundingClientRect();

                        if (rect.width === 0 || rect.height === 0) continue;

                        const lineHeight = parseFloat(style.lineHeight);
                        const fontSize = parseFloat(style.fontSize);

                        // Check if line-height is too tight
                        if (!isNaN(lineHeight) && !isNaN(fontSize) && lineHeight < fontSize * 1.2) {
                            const selector = el.id ? '#' + el.id :
                                              el.tagName.toLowerCase();
                            results.push({
                                selector: selector,
                                type: 'line-height',
                                lineHeight: lineHeight,
                                fontSize: fontSize
                            });
                        }
                    }

                    return results.slice(0, 10);
                }
            """)

            for item in spacing_issues:
                issues.append(LayoutIssue(
                    issue_type=LayoutIssueType.SPACING,
                    element_selector=item["selector"],
                    description=f"Line height ({item['lineHeight']}px) is too tight for font size ({item['fontSize']}px)",
                    severity="minor",
                    suggested_fix="Increase line-height to at least 1.5x the font size for readability",
                ))

        except Exception:
            pass

        return issues

    async def _check_visibility(self, page: Page) -> List[LayoutIssue]:
        """Check for visibility issues."""
        issues = []

        try:
            visibility_issues = await page.evaluate("""
                () => {
                    const results = [];
                    const interactive = document.querySelectorAll('a[href], button, input, select');

                    for (const el of interactive) {
                        const style = getComputedStyle(el);
                        const rect = el.getBoundingClientRect();

                        // Check for elements that are too small
                        if (rect.width < 24 || rect.height < 24) {
                            if (rect.width > 0 && rect.height > 0) {
                                const selector = el.id ? '#' + el.id :
                                                  el.tagName.toLowerCase();
                                results.push({
                                    selector: selector,
                                    type: 'too_small',
                                    width: rect.width,
                                    height: rect.height
                                });
                            }
                        }

                        // Check for zero opacity
                        if (style.opacity === '0') {
                            const selector = el.id ? '#' + el.id :
                                              el.tagName.toLowerCase();
                            results.push({
                                selector: selector,
                                type: 'invisible'
                            });
                        }
                    }

                    return results.slice(0, 10);
                }
            """)

            for item in visibility_issues:
                if item["type"] == "too_small":
                    issues.append(LayoutIssue(
                        issue_type=LayoutIssueType.VISIBILITY,
                        element_selector=item["selector"],
                        description=f"Interactive element is too small ({item['width']}x{item['height']}px)",
                        severity="moderate",
                        suggested_fix="Increase element size to at least 44x44px for touch targets",
                    ))
                elif item["type"] == "invisible":
                    issues.append(LayoutIssue(
                        issue_type=LayoutIssueType.VISIBILITY,
                        element_selector=item["selector"],
                        description="Interactive element has zero opacity",
                        severity="serious",
                        suggested_fix="Ensure interactive elements are visible to users",
                    ))

        except Exception:
            pass

        return issues
