"""
Heimdall Quality - Bug Detection

Detects potential runtime bugs using symbolic execution subsets:
- Null dereference: accessing attributes/methods on potentially None values
- Unreachable code: code blocks that can never execute
- Always-false/always-true conditions
- Division by zero

Usage:
    python -m Heimdall quality bugs ./src
    python -m Heimdall quality bugs ./src --null-only
    python -m Heimdall quality bugs ./src --unreachable-only

Programmatic Usage:
    from Asgard.Heimdall.Quality.BugDetection import BugDetector, BugDetectionConfig
    from pathlib import Path

    config = BugDetectionConfig(scan_path=Path("./src"))
    detector = BugDetector(config)
    report = detector.scan(Path("./src"))
    print(f"Bugs found: {report.total_bugs}")
"""

from Asgard.Heimdall.Quality.BugDetection.models.bug_models import (
    BugCategory,
    BugDetectionConfig,
    BugFinding,
    BugReport,
    BugSeverity,
)
from Asgard.Heimdall.Quality.BugDetection.services.null_dereference_detector import NullDereferenceDetector
from Asgard.Heimdall.Quality.BugDetection.services.unreachable_code_detector import UnreachableCodeDetector
from Asgard.Heimdall.Quality.BugDetection.services.bug_detector import BugDetector

__all__ = [
    "BugCategory",
    "BugDetectionConfig",
    "BugDetector",
    "BugFinding",
    "BugReport",
    "BugSeverity",
    "NullDereferenceDetector",
    "UnreachableCodeDetector",
]
