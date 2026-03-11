"""
Freya Breakpoint Tester

Tests responsive layouts across different viewport sizes.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from playwright.async_api import async_playwright, Page

from Asgard.Freya.Responsive.models.responsive_models import (
    Breakpoint,
    BreakpointIssue,
    BreakpointIssueType,
    BreakpointReport,
    BreakpointTestResult,
    COMMON_BREAKPOINTS,
)


class BreakpointTester:
    """
    Breakpoint testing service.

    Tests responsive layouts across different viewport sizes.
    """

    def __init__(self, output_directory: str = "./breakpoint_tests"):
        """
        Initialize the Breakpoint Tester.

        Args:
            output_directory: Directory for screenshots
        """
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)

    async def test(
        self,
        url: str,
        breakpoints: Optional[List[Breakpoint]] = None,
        capture_screenshots: bool = True
    ) -> BreakpointReport:
        """
        Test a page across breakpoints.

        Args:
            url: URL to test
            breakpoints: List of breakpoints to test
            capture_screenshots: Whether to capture screenshots

        Returns:
            BreakpointReport with findings
        """
        if breakpoints is None:
            breakpoints = COMMON_BREAKPOINTS

        results = []
        all_issues = {}
        screenshots = {}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            for bp in breakpoints:
                context = await browser.new_context(
                    viewport={"width": bp.width, "height": bp.height},
                    device_scale_factor=bp.device_scale_factor,
                    is_mobile=bp.is_mobile,
                    has_touch=bp.is_mobile,
                )
                page = await context.new_page()

                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)

                    issues = []

                    scroll_issues = await self._check_horizontal_scroll(page, bp)
                    issues.extend(scroll_issues)

                    overflow_issues = await self._check_content_overflow(page, bp)
                    issues.extend(overflow_issues)

                    overlap_issues = await self._check_overlapping_elements(page, bp)
                    issues.extend(overlap_issues)

                    text_issues = await self._check_text_truncation(page, bp)
                    issues.extend(text_issues)

                    page_width = await page.evaluate(
                        "() => document.documentElement.scrollWidth"
                    )
                    has_scroll = page_width > bp.width

                    screenshot_path = None
                    if capture_screenshots:
                        screenshot_path = str(
                            self.output_directory / f"{bp.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        )
                        await page.screenshot(path=screenshot_path, full_page=True)
                        screenshots[bp.name] = screenshot_path

                    result = BreakpointTestResult(
                        breakpoint=bp,
                        issues=issues,
                        screenshot_path=screenshot_path,
                        page_width=page_width,
                        has_horizontal_scroll=has_scroll,
                    )
                    results.append(result)
                    all_issues[bp.name] = issues

                finally:
                    await context.close()

            await browser.close()

        total_issues = sum(len(issues) for issues in all_issues.values())

        return BreakpointReport(
            url=url,
            tested_at=datetime.now().isoformat(),
            breakpoints_tested=[bp.name for bp in breakpoints],
            total_issues=total_issues,
            results=results,
            breakpoint_issues=all_issues,
            screenshots=screenshots,
        )

    async def _check_horizontal_scroll(
        self,
        page: Page,
        breakpoint: Breakpoint
    ) -> List[BreakpointIssue]:
        """Check for horizontal scrolling."""
        issues = []

        scroll_width = await page.evaluate(
            "() => document.documentElement.scrollWidth"
        )

        if scroll_width > breakpoint.width:
            overflow_elements = await page.evaluate(f"""
                () => {{
                    const results = [];
                    const elements = document.querySelectorAll('*');
                    for (const el of elements) {{
                        const rect = el.getBoundingClientRect();
                        if (rect.right > {breakpoint.width}) {{
                            const selector = el.id ? '#' + el.id :
                                              el.className ? el.tagName.toLowerCase() + '.' + el.className.split(' ')[0] :
                                              el.tagName.toLowerCase();
                            results.push({{
                                selector: selector,
                                right: rect.right,
                                width: rect.width
                            }});
                        }}
                    }}
                    return results.slice(0, 5);
                }}
            """)

            for elem in overflow_elements:
                issues.append(BreakpointIssue(
                    issue_type=BreakpointIssueType.HORIZONTAL_SCROLL,
                    breakpoint=breakpoint.name,
                    viewport_width=breakpoint.width,
                    element_selector=elem["selector"],
                    description=f"Element extends beyond viewport (right: {elem['right']:.0f}px)",
                    severity="serious",
                    suggested_fix="Use max-width: 100% or adjust element width",
                ))

        return issues

    async def _check_content_overflow(
        self,
        page: Page,
        breakpoint: Breakpoint
    ) -> List[BreakpointIssue]:
        """Check for content overflow issues."""
        issues = []

        try:
            overflows = await page.evaluate("""
                () => {
                    const results = [];
                    const elements = document.querySelectorAll('*');

                    for (const el of elements) {
                        const style = getComputedStyle(el);

                        if (el.scrollWidth > el.clientWidth &&
                            style.overflowX !== 'scroll' &&
                            style.overflowX !== 'auto' &&
                            style.overflowX !== 'hidden' &&
                            el.clientWidth > 0) {

                            const selector = el.id ? '#' + el.id :
                                              el.tagName.toLowerCase();

                            results.push({
                                selector: selector,
                                scrollWidth: el.scrollWidth,
                                clientWidth: el.clientWidth
                            });
                        }
                    }

                    return results.slice(0, 5);
                }
            """)

            for overflow in overflows:
                issues.append(BreakpointIssue(
                    issue_type=BreakpointIssueType.CONTENT_OVERFLOW,
                    breakpoint=breakpoint.name,
                    viewport_width=breakpoint.width,
                    element_selector=overflow["selector"],
                    description=f"Content overflows container ({overflow['scrollWidth']}px > {overflow['clientWidth']}px)",
                    severity="moderate",
                    suggested_fix="Add overflow: hidden/auto or use word-wrap/overflow-wrap",
                ))

        except Exception:
            pass

        return issues

    async def _check_overlapping_elements(
        self,
        page: Page,
        breakpoint: Breakpoint
    ) -> List[BreakpointIssue]:
        """Check for overlapping interactive elements."""
        issues = []

        try:
            overlaps = await page.evaluate("""
                () => {
                    const results = [];
                    const interactive = document.querySelectorAll('a, button, input, select');
                    const checked = new Set();

                    for (let i = 0; i < interactive.length && i < 50; i++) {
                        for (let j = i + 1; j < interactive.length && j < 50; j++) {
                            const rect1 = interactive[i].getBoundingClientRect();
                            const rect2 = interactive[j].getBoundingClientRect();

                            if (rect1.width === 0 || rect1.height === 0 ||
                                rect2.width === 0 || rect2.height === 0) continue;

                            const overlap = !(rect1.right < rect2.left ||
                                             rect1.left > rect2.right ||
                                             rect1.bottom < rect2.top ||
                                             rect1.top > rect2.bottom);

                            if (overlap) {
                                const sel1 = interactive[i].tagName.toLowerCase();
                                const sel2 = interactive[j].tagName.toLowerCase();
                                const key = sel1 + '-' + sel2;

                                if (!checked.has(key)) {
                                    checked.add(key);
                                    results.push({
                                        selector1: sel1,
                                        selector2: sel2
                                    });
                                }
                            }
                        }
                    }

                    return results.slice(0, 5);
                }
            """)

            for overlap in overlaps:
                issues.append(BreakpointIssue(
                    issue_type=BreakpointIssueType.OVERLAPPING_ELEMENTS,
                    breakpoint=breakpoint.name,
                    viewport_width=breakpoint.width,
                    element_selector=overlap["selector1"],
                    description=f"Interactive elements overlap: {overlap['selector1']} and {overlap['selector2']}",
                    severity="serious",
                    suggested_fix="Adjust layout or use media queries to prevent overlap",
                ))

        except Exception:
            pass

        return issues

    async def _check_text_truncation(
        self,
        page: Page,
        breakpoint: Breakpoint
    ) -> List[BreakpointIssue]:
        """Check for unintended text truncation."""
        issues = []

        try:
            truncated = await page.evaluate("""
                () => {
                    const results = [];
                    const textElements = document.querySelectorAll('h1, h2, h3, h4, button, a');

                    for (const el of textElements) {
                        const style = getComputedStyle(el);

                        // Check for ellipsis
                        if (style.textOverflow === 'ellipsis' &&
                            el.scrollWidth > el.clientWidth) {

                            const selector = el.id ? '#' + el.id :
                                              el.tagName.toLowerCase();

                            results.push({
                                selector: selector,
                                text: el.textContent.substring(0, 50)
                            });
                        }
                    }

                    return results.slice(0, 5);
                }
            """)

            for item in truncated:
                issues.append(BreakpointIssue(
                    issue_type=BreakpointIssueType.TEXT_TRUNCATION,
                    breakpoint=breakpoint.name,
                    viewport_width=breakpoint.width,
                    element_selector=item["selector"],
                    description=f"Text is truncated: '{item['text'][:30]}...'",
                    severity="minor",
                    suggested_fix="Consider using responsive font sizes or allowing text to wrap",
                ))

        except Exception:
            pass

        return issues
