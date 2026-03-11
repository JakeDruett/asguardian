"""
Freya Robots Analyzer

Analyzes robots.txt and sitemap.xml files for SEO compliance.
"""

import re
import xml.etree.ElementTree as ET
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import httpx

from Asgard.Freya.SEO.models.seo_models import (
    RobotDirective,
    RobotsTxtReport,
    SEOConfig,
    SitemapEntry,
    SitemapReport,
)


class RobotsAnalyzer:
    """
    Analyzes robots.txt and sitemap.xml files.

    Checks for proper configuration and identifies potential issues.
    """

    def __init__(self, config: Optional[SEOConfig] = None):
        """
        Initialize the robots analyzer.

        Args:
            config: SEO configuration
        """
        self.config = config or SEOConfig()
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; FreyaBot/1.0; "
                        "+https://github.com/JakeDruett/asgard)"
                    )
                },
            )
        return self._http_client

    async def analyze_robots(self, url: str) -> RobotsTxtReport:
        """
        Analyze robots.txt for a site.

        Args:
            url: Site URL (robots.txt will be fetched from root)

        Returns:
            RobotsTxtReport with analysis results
        """
        # Build robots.txt URL
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        report = RobotsTxtReport(url=url, robots_url=robots_url)

        try:
            client = await self._get_client()
            response = await client.get(robots_url)

            report.status_code = response.status_code

            if response.status_code == 200:
                report.exists = True
                report.is_accessible = True
                report.content_length = len(response.text)

                # Parse robots.txt
                self._parse_robots_txt(response.text, report)

                # Analyze for issues
                self._analyze_robots_issues(report)

            elif response.status_code == 404:
                report.exists = False
                report.is_accessible = True
                report.issues.append("robots.txt file does not exist")
                report.suggestions.append("Create a robots.txt file to control crawler access")

            else:
                report.exists = False
                report.is_accessible = False
                report.issues.append(
                    f"robots.txt returned HTTP {response.status_code}"
                )

        except httpx.HTTPError as e:
            report.exists = False
            report.is_accessible = False
            report.issues.append(f"Failed to fetch robots.txt: {str(e)}")

        return report

    def _parse_robots_txt(self, content: str, report: RobotsTxtReport) -> None:
        """Parse robots.txt content."""
        current_user_agent = None
        line_number = 0

        for line in content.split("\n"):
            line_number += 1
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse directive
            match = re.match(r"^([^:]+):\s*(.*)$", line, re.IGNORECASE)
            if not match:
                continue

            directive = match.group(1).lower()
            value = match.group(2).strip()

            if directive == "user-agent":
                current_user_agent = value
                if value not in report.user_agents:
                    report.user_agents.append(value)

            elif directive == "allow":
                report.allow_directives.append(RobotDirective(
                    directive="Allow",
                    value=value,
                    line_number=line_number,
                ))

            elif directive == "disallow":
                report.disallow_directives.append(RobotDirective(
                    directive="Disallow",
                    value=value,
                    line_number=line_number,
                ))

            elif directive == "sitemap":
                if value not in report.sitemap_urls:
                    report.sitemap_urls.append(value)

            elif directive == "crawl-delay":
                try:
                    report.crawl_delay = float(value)
                except ValueError:
                    report.warnings.append(
                        f"Invalid crawl-delay value on line {line_number}"
                    )

    def _analyze_robots_issues(self, report: RobotsTxtReport) -> None:
        """Analyze robots.txt for potential issues."""
        # Check for wildcard disallow
        for directive in report.disallow_directives:
            if directive.value == "/" and "*" in report.user_agents:
                report.issues.append(
                    "All crawlers are blocked from the entire site (Disallow: /)"
                )

        # Check for sitemap
        if not report.sitemap_urls:
            report.warnings.append("No sitemap URL specified in robots.txt")
            report.suggestions.append(
                "Add Sitemap: directive to help crawlers find your sitemap"
            )

        # Check crawl delay
        if report.crawl_delay and report.crawl_delay > 10:
            report.warnings.append(
                f"Crawl-delay of {report.crawl_delay}s is quite high"
            )

        # Check for common patterns
        for directive in report.disallow_directives:
            if "/admin" in directive.value or "/wp-admin" in directive.value:
                pass  # Common and expected
            elif "/api" in directive.value:
                report.warnings.append(
                    "API endpoints are blocked - this may affect SEO for API-driven content"
                )

    async def analyze_sitemap(self, url: str) -> SitemapReport:
        """
        Analyze sitemap.xml for a site.

        Args:
            url: Site URL (sitemap.xml will be fetched from root)

        Returns:
            SitemapReport with analysis results
        """
        # Build sitemap URL
        parsed = urlparse(url)
        sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"

        report = SitemapReport(url=url, sitemap_url=sitemap_url)

        try:
            client = await self._get_client()
            response = await client.get(sitemap_url)

            report.status_code = response.status_code

            if response.status_code == 200:
                report.exists = True
                report.is_accessible = True

                # Parse sitemap XML
                self._parse_sitemap(response.text, report)

                # Analyze for issues
                self._analyze_sitemap_issues(report)

            elif response.status_code == 404:
                report.exists = False
                report.is_accessible = True
                report.issues.append("sitemap.xml file does not exist")

            else:
                report.exists = False
                report.is_accessible = False
                report.issues.append(
                    f"sitemap.xml returned HTTP {response.status_code}"
                )

        except httpx.HTTPError as e:
            report.exists = False
            report.is_accessible = False
            report.issues.append(f"Failed to fetch sitemap.xml: {str(e)}")

        return report

    def _parse_sitemap(self, content: str, report: SitemapReport) -> None:
        """Parse sitemap XML content."""
        try:
            root = ET.fromstring(content)
            report.is_valid_xml = True

            # Define namespace
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Check if it's a sitemap index
            if root.tag.endswith("sitemapindex"):
                report.is_sitemap_index = True

                # Extract child sitemap URLs
                for sitemap in root.findall(".//sm:sitemap/sm:loc", ns):
                    if sitemap.text:
                        report.child_sitemaps.append(sitemap.text)

                report.total_urls = len(report.child_sitemaps)

            else:
                # Regular sitemap
                report.is_sitemap_index = False

                # Extract URL entries
                for url_elem in root.findall(".//sm:url", ns):
                    entry = SitemapEntry(
                        loc=self._get_elem_text(url_elem, "sm:loc", ns) or ""
                    )

                    lastmod = self._get_elem_text(url_elem, "sm:lastmod", ns)
                    if lastmod:
                        entry.lastmod = lastmod
                        report.urls_with_lastmod += 1

                    changefreq = self._get_elem_text(url_elem, "sm:changefreq", ns)
                    if changefreq:
                        entry.changefreq = changefreq

                    priority = self._get_elem_text(url_elem, "sm:priority", ns)
                    if priority:
                        try:
                            entry.priority = float(priority)
                            report.urls_with_priority += 1
                        except ValueError:
                            pass

                    report.entries.append(entry)

                report.total_urls = len(report.entries)

        except ET.ParseError as e:
            report.is_valid_xml = False
            report.issues.append(f"Invalid XML: {str(e)}")

    def _get_elem_text(
        self, parent: ET.Element, tag: str, ns: dict
    ) -> Optional[str]:
        """Get text content of a child element."""
        elem = parent.find(tag, ns)
        return elem.text if elem is not None else None

    def _analyze_sitemap_issues(self, report: SitemapReport) -> None:
        """Analyze sitemap for potential issues."""
        if not report.is_valid_xml:
            return

        # Check URL count
        if report.total_urls == 0:
            report.issues.append("Sitemap contains no URLs")
        elif report.total_urls > 50000:
            report.warnings.append(
                f"Sitemap has {report.total_urls} URLs - consider using sitemap index"
            )

        # Check for lastmod
        if report.total_urls > 0:
            lastmod_ratio = report.urls_with_lastmod / report.total_urls
            if lastmod_ratio < 0.5:
                report.warnings.append(
                    f"Only {report.urls_with_lastmod}/{report.total_urls} URLs have lastmod"
                )

        # Check for priority usage
        if report.urls_with_priority > 0:
            # Check if all priorities are the same
            priorities = set(
                e.priority for e in report.entries if e.priority is not None
            )
            if len(priorities) == 1:
                report.warnings.append(
                    "All URLs have the same priority - consider differentiating"
                )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
