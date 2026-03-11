"""
Freya SEO Models

Pydantic models for SEO analysis including meta tags,
structured data, and robots/sitemap validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SEOSeverity(str, Enum):
    """SEO issue severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    PASS = "pass"


class MetaTagType(str, Enum):
    """Types of meta tags."""
    TITLE = "title"
    DESCRIPTION = "description"
    KEYWORDS = "keywords"
    CANONICAL = "canonical"
    ROBOTS = "robots"
    VIEWPORT = "viewport"
    OG_TITLE = "og:title"
    OG_DESCRIPTION = "og:description"
    OG_IMAGE = "og:image"
    OG_URL = "og:url"
    OG_TYPE = "og:type"
    OG_SITE_NAME = "og:site_name"
    TWITTER_CARD = "twitter:card"
    TWITTER_TITLE = "twitter:title"
    TWITTER_DESCRIPTION = "twitter:description"
    TWITTER_IMAGE = "twitter:image"
    TWITTER_SITE = "twitter:site"
    TWITTER_CREATOR = "twitter:creator"


class MetaTag(BaseModel):
    """A single meta tag with its value and analysis."""
    tag_type: MetaTagType = Field(..., description="Type of meta tag")
    value: Optional[str] = Field(None, description="Tag value")
    is_present: bool = Field(False, description="Whether tag is present")
    is_valid: bool = Field(True, description="Whether value is valid")
    length: int = Field(0, description="Character length")
    issues: List[str] = Field(default_factory=list, description="Issues found")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions")


class MetaTagReport(BaseModel):
    """Report of meta tag analysis."""
    url: str = Field(..., description="URL analyzed")
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Core meta tags
    title: Optional[MetaTag] = Field(None, description="Title tag")
    description: Optional[MetaTag] = Field(None, description="Meta description")
    keywords: Optional[MetaTag] = Field(None, description="Meta keywords")
    canonical: Optional[MetaTag] = Field(None, description="Canonical URL")
    robots: Optional[MetaTag] = Field(None, description="Robots directive")
    viewport: Optional[MetaTag] = Field(None, description="Viewport meta")

    # Open Graph tags
    og_tags: Dict[str, MetaTag] = Field(default_factory=dict, description="OG tags")

    # Twitter Card tags
    twitter_tags: Dict[str, MetaTag] = Field(
        default_factory=dict, description="Twitter tags"
    )

    # Summary
    total_tags: int = Field(0, description="Total meta tags found")
    valid_tags: int = Field(0, description="Valid meta tags")
    missing_required: List[str] = Field(
        default_factory=list, description="Missing required tags"
    )
    issues: List[str] = Field(default_factory=list, description="All issues found")
    score: float = Field(0, description="SEO score 0-100")

    @property
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return len(self.issues) > 0 or len(self.missing_required) > 0


class StructuredDataType(str, Enum):
    """Types of structured data."""
    JSON_LD = "json-ld"
    MICRODATA = "microdata"
    RDFA = "rdfa"


class StructuredDataItem(BaseModel):
    """A single structured data item."""
    data_type: StructuredDataType = Field(..., description="Format type")
    schema_type: str = Field(..., description="Schema.org type")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Raw data")
    is_valid: bool = Field(True, description="Whether data is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


class StructuredDataReport(BaseModel):
    """Report of structured data analysis."""
    url: str = Field(..., description="URL analyzed")
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Found items
    items: List[StructuredDataItem] = Field(default_factory=list)
    json_ld_count: int = Field(0, description="Number of JSON-LD blocks")
    microdata_count: int = Field(0, description="Number of microdata items")
    rdfa_count: int = Field(0, description="Number of RDFa items")

    # Schema types found
    schema_types: List[str] = Field(default_factory=list, description="Schema types found")

    # Validation summary
    total_items: int = Field(0, description="Total structured data items")
    valid_items: int = Field(0, description="Valid items")
    invalid_items: int = Field(0, description="Invalid items")
    errors: List[str] = Field(default_factory=list, description="All errors")
    warnings: List[str] = Field(default_factory=list, description="All warnings")

    @property
    def has_structured_data(self) -> bool:
        """Check if page has any structured data."""
        return self.total_items > 0

    @property
    def has_errors(self) -> bool:
        """Check if there are validation errors."""
        return len(self.errors) > 0


class RobotDirective(BaseModel):
    """A robots.txt directive."""
    directive: str = Field(..., description="Directive type")
    value: str = Field(..., description="Directive value")
    line_number: int = Field(0, description="Line number in file")


class RobotsTxtReport(BaseModel):
    """Report of robots.txt analysis."""
    url: str = Field(..., description="Site URL")
    robots_url: str = Field(..., description="robots.txt URL")
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Status
    exists: bool = Field(False, description="Whether robots.txt exists")
    is_accessible: bool = Field(False, description="Whether file is accessible")
    status_code: int = Field(0, description="HTTP status code")
    content_length: int = Field(0, description="File size in bytes")

    # Directives
    user_agents: List[str] = Field(default_factory=list, description="User-agents found")
    allow_directives: List[RobotDirective] = Field(default_factory=list)
    disallow_directives: List[RobotDirective] = Field(default_factory=list)
    sitemap_urls: List[str] = Field(default_factory=list, description="Sitemap URLs")
    crawl_delay: Optional[float] = Field(None, description="Crawl delay in seconds")

    # Analysis
    issues: List[str] = Field(default_factory=list, description="Issues found")
    warnings: List[str] = Field(default_factory=list, description="Warnings")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions")

    @property
    def has_issues(self) -> bool:
        """Check if there are issues."""
        return len(self.issues) > 0


class SitemapEntry(BaseModel):
    """A single sitemap URL entry."""
    loc: str = Field(..., description="URL location")
    lastmod: Optional[str] = Field(None, description="Last modification date")
    changefreq: Optional[str] = Field(None, description="Change frequency")
    priority: Optional[float] = Field(None, description="Priority 0-1")


class SitemapReport(BaseModel):
    """Report of sitemap.xml analysis."""
    url: str = Field(..., description="Site URL")
    sitemap_url: str = Field(..., description="sitemap.xml URL")
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Status
    exists: bool = Field(False, description="Whether sitemap exists")
    is_accessible: bool = Field(False, description="Whether file is accessible")
    status_code: int = Field(0, description="HTTP status code")
    is_valid_xml: bool = Field(False, description="Whether XML is valid")
    is_sitemap_index: bool = Field(False, description="Whether this is a sitemap index")

    # Content
    entries: List[SitemapEntry] = Field(default_factory=list)
    total_urls: int = Field(0, description="Total URLs in sitemap")
    child_sitemaps: List[str] = Field(
        default_factory=list, description="Child sitemap URLs if index"
    )

    # Analysis
    urls_with_lastmod: int = Field(0, description="URLs with lastmod")
    urls_with_priority: int = Field(0, description="URLs with priority")
    issues: List[str] = Field(default_factory=list, description="Issues found")
    warnings: List[str] = Field(default_factory=list, description="Warnings")

    @property
    def has_issues(self) -> bool:
        """Check if there are issues."""
        return len(self.issues) > 0


class SEOIssue(BaseModel):
    """A single SEO issue."""
    issue_type: str = Field(..., description="Type of issue")
    severity: SEOSeverity = Field(..., description="Issue severity")
    category: str = Field(..., description="Issue category")
    description: str = Field(..., description="Issue description")
    element: Optional[str] = Field(None, description="Related element")
    current_value: Optional[str] = Field(None, description="Current value")
    expected_value: Optional[str] = Field(None, description="Expected value")
    suggested_fix: str = Field(..., description="How to fix")
    help_url: Optional[str] = Field(None, description="Help documentation URL")


class SEOReport(BaseModel):
    """Complete SEO analysis report."""
    url: str = Field(..., description="URL analyzed")
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Overall score
    seo_score: float = Field(0, description="Overall SEO score 0-100")

    # Component reports
    meta_tag_report: Optional[MetaTagReport] = Field(None)
    structured_data_report: Optional[StructuredDataReport] = Field(None)
    robots_report: Optional[RobotsTxtReport] = Field(None)
    sitemap_report: Optional[SitemapReport] = Field(None)

    # Issues summary
    issues: List[SEOIssue] = Field(default_factory=list)
    critical_count: int = Field(0, description="Critical issues")
    warning_count: int = Field(0, description="Warning issues")
    info_count: int = Field(0, description="Info issues")

    # Quick checks
    has_title: bool = Field(False, description="Has title tag")
    has_description: bool = Field(False, description="Has meta description")
    has_canonical: bool = Field(False, description="Has canonical URL")
    has_og_tags: bool = Field(False, description="Has Open Graph tags")
    has_twitter_cards: bool = Field(False, description="Has Twitter Cards")
    has_structured_data: bool = Field(False, description="Has structured data")
    has_sitemap: bool = Field(False, description="Has sitemap")
    has_robots: bool = Field(False, description="Has robots.txt")
    is_mobile_friendly: bool = Field(False, description="Has viewport meta")

    # Metadata
    analysis_duration_ms: float = Field(0, description="Analysis time in ms")

    @property
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return len(self.issues) > 0


class SEOConfig(BaseModel):
    """Configuration for SEO analysis."""
    # Title constraints
    min_title_length: int = Field(30, description="Minimum title length")
    max_title_length: int = Field(60, description="Maximum title length")

    # Description constraints
    min_description_length: int = Field(50, description="Minimum description length")
    max_description_length: int = Field(160, description="Maximum description length")

    # Checks to perform
    check_meta_tags: bool = Field(True, description="Check meta tags")
    check_og_tags: bool = Field(True, description="Check Open Graph tags")
    check_twitter_cards: bool = Field(True, description="Check Twitter Cards")
    check_structured_data: bool = Field(True, description="Check structured data")
    check_robots: bool = Field(True, description="Check robots.txt")
    check_sitemap: bool = Field(True, description="Check sitemap.xml")

    # Validation strictness
    require_og_tags: bool = Field(True, description="Require OG tags")
    require_twitter_cards: bool = Field(False, description="Require Twitter Cards")
    require_structured_data: bool = Field(False, description="Require structured data")

    # Output
    output_format: str = Field("text", description="Output format")
