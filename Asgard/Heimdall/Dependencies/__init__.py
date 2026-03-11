"""
Heimdall Dependencies - Dependency Analysis and Cycle Detection

This module provides dependency analysis tools including:
- Import mapping and dependency extraction
- Dependency graph construction with NetworkX
- Circular dependency detection
- Modularity and boundary analysis

Usage:
    python -m Heimdall deps analyze ./src
    python -m Heimdall deps cycles ./src
    python -m Heimdall deps graph ./src --output deps.png
    python -m Heimdall deps modularity ./src

Programmatic Usage:
    from Asgard.Heimdall.Dependencies import DependencyAnalyzer, DependencyConfig
    from Asgard.Heimdall.Dependencies import CycleDetector, ImportAnalyzer

    # Full dependency analysis
    config = DependencyConfig(scan_path="./src")
    analyzer = DependencyAnalyzer(config)
    result = analyzer.analyze()

    if result.has_cycles:
        for cycle in result.circular_dependencies:
            print(f"Cycle: {' -> '.join(cycle)}")

    # Just cycle detection
    detector = CycleDetector()
    cycles = detector.detect(Path("./src"))
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Heimdall.Dependencies.models.dependency_models import (
    CircularDependency,
    DependencyConfig,
    DependencyInfo,
    DependencyReport,
    DependencySeverity,
    DependencyType,
    ModularityMetrics,
    ModuleDependencies,
)
from Asgard.Heimdall.Dependencies.services.import_analyzer import ImportAnalyzer
from Asgard.Heimdall.Dependencies.services.graph_builder import GraphBuilder
from Asgard.Heimdall.Dependencies.services.cycle_detector import CycleDetector
from Asgard.Heimdall.Dependencies.services.modularity_analyzer import ModularityAnalyzer
from Asgard.Heimdall.Dependencies.services.dependency_analyzer import DependencyAnalyzer

__all__ = [
    # Models
    "CircularDependency",
    "DependencyConfig",
    "DependencyInfo",
    "DependencyReport",
    "DependencySeverity",
    "DependencyType",
    "ModularityMetrics",
    "ModuleDependencies",
    # Services
    "CycleDetector",
    "DependencyAnalyzer",
    "GraphBuilder",
    "ImportAnalyzer",
    "ModularityAnalyzer",
]
