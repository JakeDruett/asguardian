"""
Heimdall OOP Models

Data models for object-oriented programming metrics analysis.

Metrics included:
- CBO (Coupling Between Objects): Count of classes this class is coupled to
- Ca (Afferent Coupling): Classes that depend on this class
- Ce (Efferent Coupling): Classes this class depends on
- I (Instability): Ce / (Ca + Ce) - ranges from 0 (stable) to 1 (unstable)
- DIT (Depth of Inheritance Tree): Maximum path from class to root
- NOC (Number of Children): Direct subclasses count
- LCOM (Lack of Cohesion of Methods): Measures class cohesion
- RFC (Response for a Class): Methods + methods called by methods
- WMC (Weighted Methods per Class): Sum of cyclomatic complexity
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set


class OOPSeverity(str, Enum):
    """Severity levels for OOP metric violations."""
    CRITICAL = "critical"    # Severe design problem
    HIGH = "high"            # Significant issue
    MODERATE = "moderate"    # Notable concern
    LOW = "low"              # Minor issue
    INFO = "info"            # Informational


class CouplingLevel(str, Enum):
    """Classification of coupling levels."""
    EXCELLENT = "excellent"  # CBO <= 3
    GOOD = "good"            # CBO <= 6
    MODERATE = "moderate"    # CBO <= 10
    HIGH = "high"            # CBO <= 15
    CRITICAL = "critical"    # CBO > 15


class CohesionLevel(str, Enum):
    """Classification of cohesion levels."""
    EXCELLENT = "excellent"  # LCOM <= 0.2
    GOOD = "good"            # LCOM <= 0.4
    MODERATE = "moderate"    # LCOM <= 0.6
    LOW = "low"              # LCOM <= 0.8
    CRITICAL = "critical"    # LCOM > 0.8


@dataclass
class OOPConfig:
    """Configuration for OOP analysis."""
    scan_path: Path = field(default_factory=lambda: Path("."))

    # Thresholds
    cbo_threshold: int = 10              # Coupling Between Objects
    dit_threshold: int = 5               # Depth of Inheritance Tree
    noc_threshold: int = 10              # Number of Children
    lcom_threshold: float = 0.8          # Lack of Cohesion (0-1)
    rfc_threshold: int = 50              # Response for a Class
    wmc_threshold: int = 50              # Weighted Methods per Class

    # Options
    include_tests: bool = False
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "__pycache__", ".git", ".venv", "venv", "node_modules",
        ".pytest_cache", ".mypy_cache", "dist", "build",
    ])
    include_extensions: List[str] = field(default_factory=lambda: [".py"])
    output_format: str = "text"
    verbose: bool = False

    def __post_init__(self):
        if isinstance(self.scan_path, str):
            self.scan_path = Path(self.scan_path)


@dataclass
class ClassCouplingMetrics:
    """Coupling metrics for a single class."""
    class_name: str
    file_path: str
    relative_path: str
    line_number: int

    # Core coupling metrics
    cbo: int = 0                         # Coupling Between Objects
    afferent_coupling: int = 0           # Ca - incoming dependencies
    efferent_coupling: int = 0           # Ce - outgoing dependencies
    instability: float = 0.0             # I = Ce / (Ca + Ce)

    # Coupled classes
    coupled_to: Set[str] = field(default_factory=set)
    coupled_from: Set[str] = field(default_factory=set)

    # Classification
    coupling_level: CouplingLevel = CouplingLevel.EXCELLENT
    severity: OOPSeverity = OOPSeverity.INFO

    @staticmethod
    def calculate_coupling_level(cbo: int) -> CouplingLevel:
        """Determine coupling level from CBO value."""
        if cbo <= 3:
            return CouplingLevel.EXCELLENT
        elif cbo <= 6:
            return CouplingLevel.GOOD
        elif cbo <= 10:
            return CouplingLevel.MODERATE
        elif cbo <= 15:
            return CouplingLevel.HIGH
        else:
            return CouplingLevel.CRITICAL

    @staticmethod
    def calculate_severity(cbo: int, threshold: int) -> OOPSeverity:
        """Determine severity based on CBO vs threshold."""
        if cbo <= threshold * 0.5:
            return OOPSeverity.INFO
        elif cbo <= threshold * 0.75:
            return OOPSeverity.LOW
        elif cbo <= threshold:
            return OOPSeverity.MODERATE
        elif cbo <= threshold * 1.5:
            return OOPSeverity.HIGH
        else:
            return OOPSeverity.CRITICAL


@dataclass
class ClassInheritanceMetrics:
    """Inheritance metrics for a single class."""
    class_name: str
    file_path: str
    relative_path: str
    line_number: int

    # Inheritance metrics
    dit: int = 0                         # Depth of Inheritance Tree
    noc: int = 0                         # Number of Children (direct subclasses)

    # Hierarchy info
    base_classes: List[str] = field(default_factory=list)
    direct_subclasses: List[str] = field(default_factory=list)
    all_ancestors: List[str] = field(default_factory=list)

    # Classification
    severity: OOPSeverity = OOPSeverity.INFO

    @staticmethod
    def calculate_severity(dit: int, noc: int, dit_threshold: int, noc_threshold: int) -> OOPSeverity:
        """Determine severity based on DIT and NOC vs thresholds."""
        max_ratio = max(
            dit / dit_threshold if dit_threshold > 0 else 0,
            noc / noc_threshold if noc_threshold > 0 else 0
        )

        if max_ratio <= 0.5:
            return OOPSeverity.INFO
        elif max_ratio <= 0.75:
            return OOPSeverity.LOW
        elif max_ratio <= 1.0:
            return OOPSeverity.MODERATE
        elif max_ratio <= 1.5:
            return OOPSeverity.HIGH
        else:
            return OOPSeverity.CRITICAL


@dataclass
class ClassCohesionMetrics:
    """Cohesion metrics for a single class."""
    class_name: str
    file_path: str
    relative_path: str
    line_number: int

    # Cohesion metrics
    lcom: float = 0.0                    # Lack of Cohesion of Methods (0-1)
    lcom4: float = 0.0                   # LCOM Henderson-Sellers variant

    # Method/attribute info
    method_count: int = 0
    attribute_count: int = 0
    method_attribute_usage: Dict[str, Set[str]] = field(default_factory=dict)

    # Classification
    cohesion_level: CohesionLevel = CohesionLevel.EXCELLENT
    severity: OOPSeverity = OOPSeverity.INFO

    @staticmethod
    def calculate_cohesion_level(lcom: float) -> CohesionLevel:
        """Determine cohesion level from LCOM value."""
        if lcom <= 0.2:
            return CohesionLevel.EXCELLENT
        elif lcom <= 0.4:
            return CohesionLevel.GOOD
        elif lcom <= 0.6:
            return CohesionLevel.MODERATE
        elif lcom <= 0.8:
            return CohesionLevel.LOW
        else:
            return CohesionLevel.CRITICAL

    @staticmethod
    def calculate_severity(lcom: float, threshold: float) -> OOPSeverity:
        """Determine severity based on LCOM vs threshold."""
        if lcom <= threshold * 0.5:
            return OOPSeverity.INFO
        elif lcom <= threshold * 0.75:
            return OOPSeverity.LOW
        elif lcom <= threshold:
            return OOPSeverity.MODERATE
        elif lcom <= threshold * 1.25:
            return OOPSeverity.HIGH
        else:
            return OOPSeverity.CRITICAL


@dataclass
class ClassRFCMetrics:
    """Response for Class and Weighted Methods per Class metrics."""
    class_name: str
    file_path: str
    relative_path: str
    line_number: int

    # RFC/WMC metrics
    rfc: int = 0                         # Response for a Class
    wmc: int = 0                         # Weighted Methods per Class

    # Method details
    method_count: int = 0
    methods_called: Set[str] = field(default_factory=set)
    method_complexities: Dict[str, int] = field(default_factory=dict)

    # Classification
    severity: OOPSeverity = OOPSeverity.INFO

    @staticmethod
    def calculate_severity(rfc: int, wmc: int, rfc_threshold: int, wmc_threshold: int) -> OOPSeverity:
        """Determine severity based on RFC and WMC vs thresholds."""
        max_ratio = max(
            rfc / rfc_threshold if rfc_threshold > 0 else 0,
            wmc / wmc_threshold if wmc_threshold > 0 else 0
        )

        if max_ratio <= 0.5:
            return OOPSeverity.INFO
        elif max_ratio <= 0.75:
            return OOPSeverity.LOW
        elif max_ratio <= 1.0:
            return OOPSeverity.MODERATE
        elif max_ratio <= 1.5:
            return OOPSeverity.HIGH
        else:
            return OOPSeverity.CRITICAL


@dataclass
class ClassOOPMetrics:
    """Combined OOP metrics for a single class."""
    class_name: str
    file_path: str
    relative_path: str
    line_number: int
    end_line: int = 0

    # Coupling metrics
    cbo: int = 0
    afferent_coupling: int = 0
    efferent_coupling: int = 0
    instability: float = 0.0

    # Inheritance metrics
    dit: int = 0
    noc: int = 0

    # Cohesion metrics
    lcom: float = 0.0
    lcom4: float = 0.0

    # RFC/WMC metrics
    rfc: int = 0
    wmc: int = 0

    # Method/attribute counts
    method_count: int = 0
    attribute_count: int = 0

    # Hierarchy info
    base_classes: List[str] = field(default_factory=list)

    # Classification
    coupling_level: CouplingLevel = CouplingLevel.EXCELLENT
    cohesion_level: CohesionLevel = CohesionLevel.EXCELLENT
    overall_severity: OOPSeverity = OOPSeverity.INFO

    # Issues
    violations: List[str] = field(default_factory=list)

    @property
    def qualified_name(self) -> str:
        """Get the qualified class name with file location."""
        return f"{self.relative_path}:{self.class_name}"

    def calculate_overall_severity(self, config: OOPConfig) -> OOPSeverity:
        """Calculate overall severity based on all metrics."""
        severities = [
            ClassCouplingMetrics.calculate_severity(self.cbo, config.cbo_threshold),
            ClassInheritanceMetrics.calculate_severity(
                self.dit, self.noc, config.dit_threshold, config.noc_threshold
            ),
            ClassCohesionMetrics.calculate_severity(self.lcom, config.lcom_threshold),
            ClassRFCMetrics.calculate_severity(
                self.rfc, self.wmc, config.rfc_threshold, config.wmc_threshold
            ),
        ]

        # Return the worst severity
        severity_order = [
            OOPSeverity.INFO, OOPSeverity.LOW, OOPSeverity.MODERATE,
            OOPSeverity.HIGH, OOPSeverity.CRITICAL
        ]

        max_idx = max(severity_order.index(s) for s in severities)
        return severity_order[max_idx]


@dataclass
class FileOOPAnalysis:
    """OOP analysis for a single file."""
    file_path: str
    relative_path: str

    # Classes in this file
    classes: List[ClassOOPMetrics] = field(default_factory=list)

    # File-level aggregates
    total_classes: int = 0
    total_methods: int = 0
    average_cbo: float = 0.0
    average_dit: float = 0.0
    average_lcom: float = 0.0
    max_cbo: int = 0
    max_dit: int = 0
    max_lcom: float = 0.0

    # Violations
    violations: List[ClassOOPMetrics] = field(default_factory=list)

    def add_class(self, cls: ClassOOPMetrics) -> None:
        """Add a class analysis to this file."""
        self.classes.append(cls)
        self.total_classes = len(self.classes)
        self.total_methods += cls.method_count

        # Recalculate averages
        if self.total_classes > 0:
            self.average_cbo = sum(c.cbo for c in self.classes) / self.total_classes
            self.average_dit = sum(c.dit for c in self.classes) / self.total_classes
            self.average_lcom = sum(c.lcom for c in self.classes) / self.total_classes

        # Update maxes
        self.max_cbo = max(c.cbo for c in self.classes)
        self.max_dit = max(c.dit for c in self.classes)
        self.max_lcom = max(c.lcom for c in self.classes)

    def add_violation(self, cls: ClassOOPMetrics) -> None:
        """Add a class that violates thresholds."""
        self.violations.append(cls)


@dataclass
class OOPReport:
    """Complete OOP analysis report."""
    scan_path: str
    scanned_at: datetime = field(default_factory=datetime.now)
    scan_duration_seconds: float = 0.0

    # Configuration
    cbo_threshold: int = 10
    dit_threshold: int = 5
    noc_threshold: int = 10
    lcom_threshold: float = 0.8
    rfc_threshold: int = 50
    wmc_threshold: int = 50

    # File analyses
    file_analyses: List[FileOOPAnalysis] = field(default_factory=list)

    # All classes
    class_metrics: List[ClassOOPMetrics] = field(default_factory=list)

    # Violations
    violations: List[ClassOOPMetrics] = field(default_factory=list)

    # Aggregates
    total_files_scanned: int = 0
    total_classes_analyzed: int = 0
    total_violations: int = 0

    # Averages
    average_cbo: float = 0.0
    average_dit: float = 0.0
    average_lcom: float = 0.0
    average_rfc: float = 0.0
    average_wmc: float = 0.0

    # Maxes
    max_cbo: int = 0
    max_dit: int = 0
    max_lcom: float = 0.0
    max_rfc: int = 0
    max_wmc: int = 0

    @property
    def has_violations(self) -> bool:
        """Check if any violations exist."""
        return self.total_violations > 0

    @property
    def has_issues(self) -> bool:
        """Check if any violations exist (alias for has_violations)."""
        return self.has_violations

    @property
    def compliance_rate(self) -> float:
        """Calculate the percentage of classes that comply with thresholds."""
        if self.total_classes_analyzed == 0:
            return 100.0
        return ((self.total_classes_analyzed - self.total_violations) /
                self.total_classes_analyzed * 100)

    def add_file_analysis(self, analysis: FileOOPAnalysis) -> None:
        """Add a file analysis to the report."""
        self.file_analyses.append(analysis)
        self.class_metrics.extend(analysis.classes)
        self.violations.extend(analysis.violations)

        self.total_files_scanned = len(self.file_analyses)
        self.total_classes_analyzed = len(self.class_metrics)
        self.total_violations = len(self.violations)

        # Recalculate averages and maxes
        if self.total_classes_analyzed > 0:
            self.average_cbo = sum(c.cbo for c in self.class_metrics) / self.total_classes_analyzed
            self.average_dit = sum(c.dit for c in self.class_metrics) / self.total_classes_analyzed
            self.average_lcom = sum(c.lcom for c in self.class_metrics) / self.total_classes_analyzed
            self.average_rfc = sum(c.rfc for c in self.class_metrics) / self.total_classes_analyzed
            self.average_wmc = sum(c.wmc for c in self.class_metrics) / self.total_classes_analyzed

            self.max_cbo = max((c.cbo for c in self.class_metrics), default=0)
            self.max_dit = max((c.dit for c in self.class_metrics), default=0)
            self.max_lcom = max((c.lcom for c in self.class_metrics), default=0.0)
            self.max_rfc = max((c.rfc for c in self.class_metrics), default=0)
            self.max_wmc = max((c.wmc for c in self.class_metrics), default=0)

    def get_violations_by_severity(self) -> Dict[str, List[ClassOOPMetrics]]:
        """Group violations by severity level."""
        result = {
            OOPSeverity.CRITICAL.value: [],
            OOPSeverity.HIGH.value: [],
            OOPSeverity.MODERATE.value: [],
            OOPSeverity.LOW.value: [],
            OOPSeverity.INFO.value: [],
        }

        for v in self.violations:
            result[v.overall_severity.value].append(v)

        return result

    def get_coupling_violations(self) -> List[ClassOOPMetrics]:
        """Get classes that violate coupling thresholds."""
        return [c for c in self.class_metrics if c.cbo > self.cbo_threshold]

    def get_inheritance_violations(self) -> List[ClassOOPMetrics]:
        """Get classes that violate inheritance thresholds."""
        return [c for c in self.class_metrics
                if c.dit > self.dit_threshold or c.noc > self.noc_threshold]

    def get_cohesion_violations(self) -> List[ClassOOPMetrics]:
        """Get classes that violate cohesion thresholds."""
        return [c for c in self.class_metrics if c.lcom > self.lcom_threshold]

    def get_rfc_violations(self) -> List[ClassOOPMetrics]:
        """Get classes that violate RFC/WMC thresholds."""
        return [c for c in self.class_metrics
                if c.rfc > self.rfc_threshold or c.wmc > self.wmc_threshold]
