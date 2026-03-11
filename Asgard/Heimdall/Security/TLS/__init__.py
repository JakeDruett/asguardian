"""
Heimdall Security TLS - TLS/SSL Security Analysis

This module provides TLS/SSL security validation including:
- Deprecated protocol detection (TLS 1.0, 1.1, SSLv2, SSLv3)
- Weak cipher suite detection (DES, 3DES, RC4, NULL, EXPORT)
- Certificate validation issues (verify=False, CERT_NONE)
- Hostname verification bypass detection

Usage:
    python -m Heimdall security tls ./src

Example:
    from Asgard.Heimdall.Security.TLS import TLSAnalyzer, TLSConfig

    analyzer = TLSAnalyzer(TLSConfig(scan_path="./src"))
    report = analyzer.analyze()
    print(f"TLS Issues: {report.total_issues}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Heimdall.Security.TLS.models.tls_models import (
    TLSConfig,
    TLSFinding,
    TLSFindingType,
    TLSReport,
)
from Asgard.Heimdall.Security.TLS.services.tls_analyzer import TLSAnalyzer
from Asgard.Heimdall.Security.TLS.services.protocol_analyzer import ProtocolAnalyzer
from Asgard.Heimdall.Security.TLS.services.cipher_validator import CipherValidator
from Asgard.Heimdall.Security.TLS.services.certificate_validator import CertificateValidator

__all__ = [
    "TLSAnalyzer",
    "TLSConfig",
    "TLSFinding",
    "TLSFindingType",
    "TLSReport",
    "ProtocolAnalyzer",
    "CipherValidator",
    "CertificateValidator",
]
