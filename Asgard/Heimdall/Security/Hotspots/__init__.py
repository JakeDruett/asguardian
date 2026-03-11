"""
Heimdall Security Hotspots - Security Hotspot Detection

Detects security-sensitive code patterns in Python source files that require
manual review. Hotspots are not confirmed vulnerabilities but areas where
developer attention is needed.

Detected categories:
- Cookie configuration (secure=False, httponly=False)
- Cryptographic code usage (flag for algorithm review)
- Dynamic code execution (eval, exec, compile, __import__)
- Regex DoS patterns (nested quantifiers)
- XML External Entity (XXE) usage
- Insecure deserialization (pickle, marshal, unsafe yaml.load)
- SSRF patterns (requests with variable URLs)
- Insecure random (use of random instead of secrets)
- Permission checks (os.chmod, os.access)
- TLS verification disabled (verify=False)

Usage:
    from Asgard.Heimdall.Security.Hotspots import HotspotDetector, HotspotConfig

    detector = HotspotDetector()
    report = detector.scan(Path("./src"))
    print(f"Total hotspots: {report.total_hotspots}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Heimdall.Security.Hotspots.models.hotspot_models import (
    HotspotCategory,
    HotspotConfig,
    HotspotReport,
    ReviewPriority,
    ReviewStatus,
    SecurityHotspot,
)
from Asgard.Heimdall.Security.Hotspots.services.hotspot_detector import HotspotDetector

__all__ = [
    "HotspotCategory",
    "HotspotConfig",
    "HotspotDetector",
    "HotspotReport",
    "ReviewPriority",
    "ReviewStatus",
    "SecurityHotspot",
]
