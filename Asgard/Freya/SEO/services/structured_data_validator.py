"""
Freya Structured Data Validator

Validates Schema.org structured data including JSON-LD,
microdata, and RDFa formats.
"""

import json
import re
from typing import Any, Dict, List, Optional

from playwright.async_api import Page, async_playwright

from Asgard.Freya.SEO.models.seo_models import (
    SEOConfig,
    StructuredDataItem,
    StructuredDataReport,
    StructuredDataType,
)


class StructuredDataValidator:
    """
    Validates Schema.org structured data.

    Supports JSON-LD, microdata, and RDFa formats.
    """

    # Common Schema.org types
    COMMON_SCHEMA_TYPES = {
        "Article",
        "NewsArticle",
        "BlogPosting",
        "Product",
        "Organization",
        "LocalBusiness",
        "Person",
        "Event",
        "Recipe",
        "Review",
        "FAQPage",
        "BreadcrumbList",
        "WebSite",
        "WebPage",
        "ItemList",
        "HowTo",
        "Course",
        "Book",
        "Movie",
        "VideoObject",
        "ImageObject",
    }

    # Required properties by type
    REQUIRED_PROPERTIES = {
        "Article": ["headline", "author", "datePublished"],
        "Product": ["name", "description"],
        "Organization": ["name"],
        "LocalBusiness": ["name", "address"],
        "Person": ["name"],
        "Event": ["name", "startDate", "location"],
        "Recipe": ["name", "recipeIngredient", "recipeInstructions"],
        "Review": ["itemReviewed", "reviewRating"],
        "FAQPage": ["mainEntity"],
        "BreadcrumbList": ["itemListElement"],
        "WebSite": ["name", "url"],
    }

    def __init__(self, config: Optional[SEOConfig] = None):
        """
        Initialize the structured data validator.

        Args:
            config: SEO configuration
        """
        self.config = config or SEOConfig()

    async def validate(self, url: str) -> StructuredDataReport:
        """
        Validate structured data for a URL.

        Args:
            url: URL to validate

        Returns:
            StructuredDataReport with validation results
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                return await self.validate_page(page, url)
            finally:
                await browser.close()

    async def validate_page(self, page: Page, url: str) -> StructuredDataReport:
        """
        Validate structured data on an already loaded page.

        Args:
            page: Playwright Page object
            url: URL of the page

        Returns:
            StructuredDataReport with validation results
        """
        # Extract all structured data
        json_ld_items = await self._extract_json_ld(page)
        microdata_items = await self._extract_microdata(page)

        # Combine items
        all_items = json_ld_items + microdata_items

        # Collect schema types
        schema_types = list(set(item.schema_type for item in all_items))

        # Collect all errors and warnings
        all_errors = []
        all_warnings = []
        for item in all_items:
            all_errors.extend(item.errors)
            all_warnings.extend(item.warnings)

        # Count valid/invalid
        valid_count = sum(1 for item in all_items if item.is_valid)
        invalid_count = len(all_items) - valid_count

        return StructuredDataReport(
            url=url,
            items=all_items,
            json_ld_count=len(json_ld_items),
            microdata_count=len(microdata_items),
            rdfa_count=0,  # RDFa parsing not implemented
            schema_types=schema_types,
            total_items=len(all_items),
            valid_items=valid_count,
            invalid_items=invalid_count,
            errors=all_errors,
            warnings=all_warnings,
        )

    async def _extract_json_ld(self, page: Page) -> List[StructuredDataItem]:
        """Extract and validate JSON-LD structured data."""
        items = []

        # Get all JSON-LD scripts
        json_ld_data = await page.evaluate("""
            () => {
                const scripts = document.querySelectorAll(
                    'script[type="application/ld+json"]'
                );
                const results = [];
                for (const script of scripts) {
                    try {
                        const data = JSON.parse(script.textContent);
                        results.push({ success: true, data: data });
                    } catch (e) {
                        results.push({ success: false, error: e.message });
                    }
                }
                return results;
            }
        """)

        for entry in json_ld_data:
            if not entry.get("success"):
                items.append(StructuredDataItem(
                    data_type=StructuredDataType.JSON_LD,
                    schema_type="Unknown",
                    raw_data={},
                    is_valid=False,
                    errors=[f"Invalid JSON: {entry.get('error', 'Unknown error')}"],
                ))
                continue

            data = entry.get("data", {})

            # Handle @graph structure
            if "@graph" in data:
                for graph_item in data["@graph"]:
                    item = self._validate_json_ld_item(graph_item)
                    items.append(item)
            else:
                item = self._validate_json_ld_item(data)
                items.append(item)

        return items

    def _validate_json_ld_item(self, data: Dict[str, Any]) -> StructuredDataItem:
        """Validate a single JSON-LD item."""
        errors = []
        warnings = []

        # Get type
        schema_type = data.get("@type", "Unknown")
        if isinstance(schema_type, list):
            schema_type = schema_type[0] if schema_type else "Unknown"

        # Check for @context
        context = data.get("@context", "")
        if not context:
            errors.append("Missing @context")
        elif "schema.org" not in str(context):
            warnings.append("@context should reference schema.org")

        # Check for @type
        if "@type" not in data:
            errors.append("Missing @type")

        # Check required properties for known types
        if schema_type in self.REQUIRED_PROPERTIES:
            required = self.REQUIRED_PROPERTIES[schema_type]
            for prop in required:
                if prop not in data or data[prop] is None or data[prop] == "":
                    warnings.append(f"Missing recommended property: {prop}")

        # Validate specific types
        type_errors, type_warnings = self._validate_type_specific(schema_type, data)
        errors.extend(type_errors)
        warnings.extend(type_warnings)

        is_valid = len(errors) == 0

        return StructuredDataItem(
            data_type=StructuredDataType.JSON_LD,
            schema_type=schema_type,
            raw_data=data,
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
        )

    def _validate_type_specific(
        self, schema_type: str, data: Dict[str, Any]
    ) -> tuple:
        """Validate type-specific requirements."""
        errors = []
        warnings = []

        if schema_type == "Article" or schema_type == "NewsArticle":
            # Check date format
            if "datePublished" in data:
                if not self._is_valid_date(data["datePublished"]):
                    errors.append("datePublished is not in valid ISO 8601 format")

            if "dateModified" in data:
                if not self._is_valid_date(data["dateModified"]):
                    warnings.append("dateModified is not in valid ISO 8601 format")

            # Check image
            if "image" not in data:
                warnings.append("Article should have an image")

        elif schema_type == "Product":
            # Check for offers
            if "offers" not in data:
                warnings.append("Product should have offers/pricing information")

            # Check for reviews/ratings
            if "aggregateRating" not in data and "review" not in data:
                warnings.append("Product should have reviews or ratings")

        elif schema_type == "LocalBusiness":
            # Check for contact info
            if "telephone" not in data and "email" not in data:
                warnings.append("LocalBusiness should have contact information")

            # Check for opening hours
            if "openingHoursSpecification" not in data and "openingHours" not in data:
                warnings.append("LocalBusiness should have opening hours")

        elif schema_type == "Event":
            # Check for end date
            if "endDate" not in data:
                warnings.append("Event should have an endDate")

            # Check dates
            if "startDate" in data:
                if not self._is_valid_date(data["startDate"]):
                    errors.append("startDate is not in valid ISO 8601 format")

        elif schema_type == "FAQPage":
            # Check main entity
            main_entity = data.get("mainEntity", [])
            if not main_entity:
                errors.append("FAQPage must have mainEntity with questions")
            elif isinstance(main_entity, list):
                for qa in main_entity:
                    if "@type" not in qa or qa["@type"] != "Question":
                        warnings.append("FAQPage mainEntity should be Question type")
                    if "acceptedAnswer" not in qa:
                        errors.append("Question must have acceptedAnswer")

        elif schema_type == "BreadcrumbList":
            items = data.get("itemListElement", [])
            if not items:
                errors.append("BreadcrumbList must have itemListElement")
            else:
                # Check item structure
                for i, item in enumerate(items):
                    if "position" not in item:
                        warnings.append(f"Breadcrumb item {i+1} missing position")
                    if "item" not in item and "name" not in item:
                        errors.append(f"Breadcrumb item {i+1} missing item or name")

        return errors, warnings

    def _is_valid_date(self, date_str: str) -> bool:
        """Check if a string is a valid ISO 8601 date."""
        if not isinstance(date_str, str):
            return False

        # Simple ISO 8601 patterns
        patterns = [
            r"^\d{4}-\d{2}-\d{2}$",  # 2024-01-15
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",  # 2024-01-15T10:30:00
        ]

        for pattern in patterns:
            if re.match(pattern, date_str):
                return True

        return False

    async def _extract_microdata(self, page: Page) -> List[StructuredDataItem]:
        """Extract and validate microdata structured data."""
        items = []

        # Get all microdata items
        microdata = await page.evaluate("""
            () => {
                const items = document.querySelectorAll('[itemscope]');
                const results = [];

                for (const item of items) {
                    // Skip nested items
                    if (item.closest('[itemscope]') !== item) {
                        continue;
                    }

                    const itemType = item.getAttribute('itemtype') || '';
                    const props = {};

                    const propElements = item.querySelectorAll('[itemprop]');
                    for (const propEl of propElements) {
                        const propName = propEl.getAttribute('itemprop');
                        let propValue;

                        if (propEl.hasAttribute('content')) {
                            propValue = propEl.getAttribute('content');
                        } else if (propEl.tagName === 'A') {
                            propValue = propEl.getAttribute('href');
                        } else if (propEl.tagName === 'IMG') {
                            propValue = propEl.getAttribute('src');
                        } else if (propEl.tagName === 'META') {
                            propValue = propEl.getAttribute('content');
                        } else if (propEl.tagName === 'TIME') {
                            propValue = propEl.getAttribute('datetime') ||
                                       propEl.textContent;
                        } else {
                            propValue = propEl.textContent;
                        }

                        props[propName] = propValue;
                    }

                    results.push({
                        type: itemType,
                        properties: props
                    });
                }

                return results;
            }
        """)

        for entry in microdata:
            item_type = entry.get("type", "")
            properties = entry.get("properties", {})

            # Extract schema type from URL
            schema_type = "Unknown"
            if item_type:
                # Extract type from URL like http://schema.org/Product
                match = re.search(r"schema\.org/(\w+)", item_type)
                if match:
                    schema_type = match.group(1)

            errors = []
            warnings = []

            if not item_type:
                errors.append("Missing itemtype attribute")
            elif "schema.org" not in item_type:
                warnings.append("itemtype should reference schema.org")

            is_valid = len(errors) == 0

            items.append(StructuredDataItem(
                data_type=StructuredDataType.MICRODATA,
                schema_type=schema_type,
                raw_data={"@type": schema_type, **properties},
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
            ))

        return items
