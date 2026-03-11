"""
Heimdall Security Auth - Authentication Analysis

This module provides authentication mechanism validation including:
- JWT token security analysis
- OAuth flow verification
- Session management security
- Password handling validation

Usage:
    python -m Heimdall security auth ./src

Example:
    from Asgard.Heimdall.Security.Auth import AuthAnalyzer, AuthConfig

    analyzer = AuthAnalyzer(AuthConfig(scan_path="./src"))
    report = analyzer.analyze()
    print(f"Auth Issues: {report.total_issues}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Heimdall.Security.Auth.models.auth_models import (
    AuthConfig,
    AuthFinding,
    AuthFindingType,
    AuthReport,
)
from Asgard.Heimdall.Security.Auth.services.auth_analyzer import AuthAnalyzer
from Asgard.Heimdall.Security.Auth.services.jwt_validator import JWTValidator
from Asgard.Heimdall.Security.Auth.services.session_analyzer import SessionAnalyzer
from Asgard.Heimdall.Security.Auth.services.password_analyzer import PasswordAnalyzer

__all__ = [
    "AuthAnalyzer",
    "AuthConfig",
    "AuthFinding",
    "AuthFindingType",
    "AuthReport",
    "JWTValidator",
    "PasswordAnalyzer",
    "SessionAnalyzer",
]
