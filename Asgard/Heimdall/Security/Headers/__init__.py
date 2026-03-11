"""
Heimdall Security Headers - Security Header Analysis

This module provides security header analysis tools including:
- Content-Security-Policy analysis
- CORS configuration validation
- Missing security header detection
- Cookie security flag verification
- HSTS configuration analysis

Usage:
    python -m Heimdall security headers ./src

Example:
    from Asgard.Heimdall.Security.Headers import HeadersAnalyzer, HeaderConfig

    analyzer = HeadersAnalyzer(HeaderConfig(scan_path="./src"))
    report = analyzer.analyze()
    print(f"Header Issues: {report.total_issues}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Heimdall.Security.Headers.models.header_models import (
    HeaderConfig,
    HeaderFinding,
    HeaderFindingType,
    HeaderReport,
)
from Asgard.Heimdall.Security.Headers.services.cors_analyzer import CORSAnalyzer
from Asgard.Heimdall.Security.Headers.services.csp_analyzer import CSPAnalyzer
from Asgard.Heimdall.Security.Headers.services.header_validator import HeaderValidator
from Asgard.Heimdall.Security.Headers.services.headers_analyzer import HeadersAnalyzer

__all__ = [
    "CORSAnalyzer",
    "CSPAnalyzer",
    "HeaderConfig",
    "HeaderFinding",
    "HeaderFindingType",
    "HeaderReport",
    "HeadersAnalyzer",
    "HeaderValidator",
]
