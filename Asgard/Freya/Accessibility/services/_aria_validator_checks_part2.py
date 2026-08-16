"""
Freya ARIA Validator check functions - part 2.

Additional check functions extracted from _aria_validator_checks.py.
"""

from typing import Dict, List, Optional, cast

from playwright.async_api import Page

from Asgard.Freya.Accessibility.models.accessibility_models import (
    ARIAViolation,
    ARIAViolationType,
    ViolationSeverity,
)
from Asgard.Freya.Accessibility.services._aria_validator_checks import (
    get_selector,
)

# Static evaluate body. Page IDs are the argument, never source (CH-0070).
_ID_EXISTS_JS = "(id) => document.getElementById(id) !== null"


async def validate_hidden_focusable(page: Page) -> List[ARIAViolation]:
    """Validate that aria-hidden elements don't contain focusable content."""
    violations = []

    try:
        hidden_elements = await page.query_selector_all('[aria-hidden="true"]')

        for elem in hidden_elements:
            focusable = await elem.query_selector(
                'a[href], button:not([disabled]), input:not([disabled]), '
                'select:not([disabled]), textarea:not([disabled]), '
                '[tabindex]:not([tabindex="-1"])'
            )

            if focusable:
                selector = await get_selector(page, elem)
                violations.append(ARIAViolation(
                    violation_type=ARIAViolationType.HIDDEN_FOCUSABLE,
                    element_selector=selector,
                    description="Element with aria-hidden='true' contains focusable content",
                    severity=ViolationSeverity.CRITICAL,
                    wcag_reference="4.1.2",
                    suggested_fix="Either remove aria-hidden or add tabindex='-1' to focusable children",
                    aria_attribute="aria-hidden",
                ))

    except Exception:
        pass

    return violations


async def validate_aria_ids(page: Page) -> List[ARIAViolation]:
    """Validate that aria-labelledby and aria-describedby reference existing IDs."""
    violations = []

    try:
        elements = await page.query_selector_all(
            "[aria-labelledby], [aria-describedby], [aria-controls], [aria-owns]"
        )

        for elem in elements:
            for attr in ["aria-labelledby", "aria-describedby", "aria-controls", "aria-owns"]:
                id_refs = await elem.get_attribute(attr)
                if not id_refs:
                    continue

                for id_ref in id_refs.split():
                    exists = await page.evaluate(_ID_EXISTS_JS, id_ref)

                    if not exists:
                        selector = await get_selector(page, elem)
                        violations.append(ARIAViolation(
                            violation_type=ARIAViolationType.INVALID_ATTRIBUTE_VALUE,
                            element_selector=selector,
                            description=f'{attr} references non-existent ID: "{id_ref}"',
                            severity=ViolationSeverity.SERIOUS,
                            wcag_reference="4.1.2",
                            suggested_fix=f'Ensure an element with id="{id_ref}" exists',
                            aria_attribute=attr,
                        ))

    except Exception:
        pass

    return violations


async def count_aria_elements(page: Page) -> int:
    """Count total elements with ARIA attributes or roles."""
    try:
        return cast(int, await page.evaluate("""
            () => document.querySelectorAll('[role], [aria-label], [aria-labelledby], [aria-describedby]').length
        """))
    except Exception:
        return 0
