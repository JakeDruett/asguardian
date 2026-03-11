"""
Freya Touch Target Validator

Validates touch target sizes for mobile accessibility.
WCAG 2.5.5 recommends 44x44px minimum for touch targets.
"""

from datetime import datetime
from typing import List

from playwright.async_api import async_playwright, Page

from Asgard.Freya.Responsive.models.responsive_models import (
    TouchTargetIssue,
    TouchTargetReport,
)


class TouchTargetValidator:
    """
    Touch target validation service.

    Validates that interactive elements meet minimum
    touch target size requirements.
    """

    def __init__(self, min_touch_size: int = 44):
        """
        Initialize the Touch Target Validator.

        Args:
            min_touch_size: Minimum touch target size in pixels
        """
        self.min_touch_size = min_touch_size

    async def validate(
        self,
        url: str,
        viewport_width: int = 375,
        viewport_height: int = 667
    ) -> TouchTargetReport:
        """
        Validate touch targets on a page.

        Args:
            url: URL to validate
            viewport_width: Mobile viewport width
            viewport_height: Mobile viewport height

        Returns:
            TouchTargetReport with findings
        """
        issues = []
        total_interactive = 0
        passing_count = 0
        failing_count = 0

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height},
                is_mobile=True,
                has_touch=True,
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)

                elements = await page.evaluate(f"""
                    () => {{
                        const results = [];
                        const interactive = document.querySelectorAll(
                            'a[href], button, input:not([type="hidden"]), select, textarea, ' +
                            '[role="button"], [role="link"], [role="checkbox"], [role="radio"], ' +
                            '[role="tab"], [onclick], [tabindex]:not([tabindex="-1"])'
                        );

                        for (const el of interactive) {{
                            const rect = el.getBoundingClientRect();
                            const style = getComputedStyle(el);

                            if (style.display === 'none' || style.visibility === 'hidden') {{
                                continue;
                            }}

                            if (rect.width === 0 || rect.height === 0) {{
                                continue;
                            }}

                            const selector = el.id ? '#' + el.id :
                                              el.className ? el.tagName.toLowerCase() + '.' + el.className.split(' ')[0] :
                                              el.tagName.toLowerCase();

                            results.push({{
                                selector: selector,
                                type: el.tagName.toLowerCase(),
                                role: el.getAttribute('role'),
                                width: rect.width,
                                height: rect.height,
                                text: (el.textContent || el.value || '').substring(0, 30)
                            }});
                        }}

                        return results;
                    }}
                """)

                total_interactive = len(elements)

                for elem in elements:
                    width = elem["width"]
                    height = elem["height"]

                    if width >= self.min_touch_size and height >= self.min_touch_size:
                        passing_count += 1
                    else:
                        failing_count += 1

                        min_dimension = min(width, height)
                        max_dimension = max(width, height)

                        if min_dimension < 24:
                            severity = "critical"
                        elif min_dimension < 32:
                            severity = "serious"
                        elif min_dimension < self.min_touch_size:
                            severity = "moderate"
                        else:
                            severity = "minor"

                        element_type = elem.get("role") or elem["type"]

                        issues.append(TouchTargetIssue(
                            element_selector=elem["selector"],
                            element_type=element_type,
                            width=width,
                            height=height,
                            min_required=self.min_touch_size,
                            description=f"{element_type} touch target too small ({width:.0f}x{height:.0f}px)",
                            severity=severity,
                            suggested_fix=f"Increase element size to at least {self.min_touch_size}x{self.min_touch_size}px",
                        ))

            finally:
                await browser.close()

        return TouchTargetReport(
            url=url,
            tested_at=datetime.now().isoformat(),
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            total_interactive_elements=total_interactive,
            passing_count=passing_count,
            failing_count=failing_count,
            issues=issues,
            min_touch_size=self.min_touch_size,
        )

    async def validate_element(
        self,
        page: Page,
        selector: str
    ) -> TouchTargetIssue:
        """
        Validate a specific element's touch target size.

        Args:
            page: Playwright page
            selector: Element selector

        Returns:
            TouchTargetIssue if element is too small, None otherwise
        """
        element = await page.query_selector(selector)
        if not element:
            return None

        box = await element.bounding_box()
        if not box:
            return None

        width = box["width"]
        height = box["height"]

        if width >= self.min_touch_size and height >= self.min_touch_size:
            return None

        tag = await element.evaluate("el => el.tagName.toLowerCase()")

        return TouchTargetIssue(
            element_selector=selector,
            element_type=tag,
            width=width,
            height=height,
            min_required=self.min_touch_size,
            description=f"Touch target too small ({width:.0f}x{height:.0f}px)",
            severity="moderate",
            suggested_fix=f"Increase to at least {self.min_touch_size}x{self.min_touch_size}px",
        )
