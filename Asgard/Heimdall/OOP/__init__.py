"""
Heimdall OOP - Object-Oriented Programming Metrics

This module provides OOP metrics analysis tools including:
- Coupling Between Objects (CBO, Ca, Ce, Instability)
- Depth of Inheritance Tree (DIT) and Number of Children (NOC)
- Lack of Cohesion of Methods (LCOM, LCOM4)
- Response for a Class (RFC) and Weighted Methods per Class (WMC)

Usage:
    python -m Heimdall oop analyze ./src
    python -m Heimdall oop coupling ./src
    python -m Heimdall oop inheritance ./src
    python -m Heimdall oop cohesion ./src

Programmatic Usage:
    from Asgard.Heimdall.OOP import OOPAnalyzer, OOPConfig
    from Asgard.Heimdall.OOP import CouplingAnalyzer, InheritanceAnalyzer
    from Asgard.Heimdall.OOP import CohesionAnalyzer, RFCAnalyzer

    # Full OOP analysis
    config = OOPConfig(scan_path="./src")
    analyzer = OOPAnalyzer(config)
    result = analyzer.analyze()

    for cls in result.class_metrics:
        print(f"{cls.name}: CBO={cls.cbo}, DIT={cls.dit}, LCOM={cls.lcom}")

    # Coupling analysis only
    coupling_analyzer = CouplingAnalyzer()
    coupling_result = coupling_analyzer.analyze(Path("./src"))

    for cls in coupling_result.classes:
        print(f"{cls.name}: CBO={cls.cbo}, Ca={cls.ca}, Ce={cls.ce}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Heimdall.OOP.models.oop_models import (
    ClassCouplingMetrics,
    ClassCohesionMetrics,
    ClassInheritanceMetrics,
    ClassOOPMetrics,
    CohesionLevel,
    CouplingLevel,
    OOPConfig,
    OOPReport,
    OOPSeverity,
)
from Asgard.Heimdall.OOP.services.coupling_analyzer import CouplingAnalyzer
from Asgard.Heimdall.OOP.services.inheritance_analyzer import InheritanceAnalyzer
from Asgard.Heimdall.OOP.services.cohesion_analyzer import CohesionAnalyzer
from Asgard.Heimdall.OOP.services.rfc_analyzer import RFCAnalyzer
from Asgard.Heimdall.OOP.services.oop_analyzer import OOPAnalyzer

__all__ = [
    # Models
    "ClassCouplingMetrics",
    "ClassCohesionMetrics",
    "ClassInheritanceMetrics",
    "ClassOOPMetrics",
    "CohesionLevel",
    "CouplingLevel",
    "OOPConfig",
    "OOPReport",
    "OOPSeverity",
    # Services
    "CohesionAnalyzer",
    "CouplingAnalyzer",
    "InheritanceAnalyzer",
    "OOPAnalyzer",
    "RFCAnalyzer",
]
