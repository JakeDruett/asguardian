"""
Heimdall Quality - Code Quality Analysis

This module provides code quality analysis tools including:
- File length analysis (line count thresholds)
- Cyclomatic complexity analysis
- Cognitive complexity analysis
- Code duplication detection
- Code smell detection (Martin Fowler's taxonomy)
- Technical debt calculation
- Maintainability index (Microsoft formula)
- Comment density and documentation coverage
- Naming convention enforcement (PEP 8)

Usage:
    python -m Heimdall quality analyze ./src
    python -m Heimdall quality file-length ./src
    python -m Heimdall quality complexity ./src
    python -m Heimdall quality duplication ./src
    python -m Heimdall quality smells ./src
    python -m Heimdall quality debt ./src
    python -m Heimdall quality maintainability ./src
    python -m Heimdall quality documentation ./src
    python -m Heimdall quality naming ./src

Programmatic Usage:
    from Asgard.Heimdall.Quality import FileAnalyzer, AnalysisConfig
    from Asgard.Heimdall.Quality import ComplexityAnalyzer, ComplexityConfig
    from Asgard.Heimdall.Quality import DuplicationDetector, DuplicationConfig
    from Asgard.Heimdall.Quality import CodeSmellDetector, SmellConfig
    from Asgard.Heimdall.Quality import TechnicalDebtAnalyzer, DebtConfig
    from Asgard.Heimdall.Quality import MaintainabilityAnalyzer, MaintainabilityConfig

    # File length analysis
    config = AnalysisConfig(threshold=300)
    analyzer = FileAnalyzer(config)
    result = analyzer.analyze()

    for violation in result.violations:
        print(f"{violation.relative_path}: {violation.line_count} lines")

    # Complexity analysis
    complexity_config = ComplexityConfig(cyclomatic_threshold=10)
    complexity_analyzer = ComplexityAnalyzer(complexity_config)
    complexity_result = complexity_analyzer.analyze()

    for violation in complexity_result.violations:
        print(f"{violation.qualified_name}: CC={violation.cyclomatic_complexity}")

    # Duplication detection
    dup_config = DuplicationConfig(min_block_size=6)
    dup_detector = DuplicationDetector(dup_config)
    dup_result = dup_detector.analyze()

    for family in dup_result.clone_families:
        print(f"Clone family with {family.block_count} blocks")

    # Code smell detection
    smell_config = SmellConfig()
    smell_detector = CodeSmellDetector(smell_config)
    smell_result = smell_detector.analyze(Path("./src"))

    for smell in smell_result.detected_smells:
        print(f"{smell.name} at {smell.location}")

    # Technical debt analysis
    debt_config = DebtConfig()
    debt_analyzer = TechnicalDebtAnalyzer(debt_config)
    debt_result = debt_analyzer.analyze(Path("./src"))

    print(f"Total debt: {debt_result.total_debt_hours} hours")

    # Maintainability index
    mi_config = MaintainabilityConfig()
    mi_analyzer = MaintainabilityAnalyzer(mi_config)
    mi_result = mi_analyzer.analyze(Path("./src"))

    print(f"Overall MI: {mi_result.overall_index:.2f}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Heimdall.Quality.models.analysis_models import (
    AnalysisConfig,
    AnalysisResult,
    FileAnalysis,
    SeverityLevel,
)
from Asgard.Heimdall.Quality.models.complexity_models import (
    ComplexityConfig,
    ComplexityResult,
    ComplexitySeverity,
    FileComplexityAnalysis,
    FunctionComplexity,
)
from Asgard.Heimdall.Quality.models.duplication_models import (
    CloneFamily,
    CodeBlock,
    DuplicationConfig,
    DuplicationMatch,
    DuplicationResult,
    DuplicationSeverity,
    DuplicationType,
)
from Asgard.Heimdall.Quality.models.smell_models import (
    CodeSmell,
    SmellCategory,
    SmellConfig,
    SmellReport,
    SmellSeverity,
    SmellThresholds,
)
from Asgard.Heimdall.Quality.models.debt_models import (
    DebtConfig,
    DebtItem,
    DebtReport,
    DebtSeverity,
    DebtType,
    EffortModels,
    InterestRates,
    ROIAnalysis,
    TimeHorizon,
    TimeProjection,
)
from Asgard.Heimdall.Quality.models.maintainability_models import (
    FileMaintainability,
    FunctionMaintainability,
    HalsteadMetrics,
    LanguageProfile,
    LanguageWeights,
    MaintainabilityConfig,
    MaintainabilityLevel,
    MaintainabilityReport,
    MaintainabilityThresholds,
)
from Asgard.Heimdall.Quality.models.lazy_import_models import (
    LazyImport,
    LazyImportConfig,
    LazyImportReport,
    LazyImportSeverity,
    LazyImportType,
)
from Asgard.Heimdall.Quality.models.env_fallback_models import (
    EnvFallbackConfig,
    EnvFallbackReport,
    EnvFallbackSeverity,
    EnvFallbackType,
    EnvFallbackViolation,
)
from Asgard.Heimdall.Quality.models.syntax_models import (
    FileAnalysis as SyntaxFileAnalysis,
    LinterType,
    SyntaxConfig,
    SyntaxIssue,
    SyntaxResult,
    SyntaxSeverity,
)
from Asgard.Heimdall.Quality.services.file_length_analyzer import FileAnalyzer
from Asgard.Heimdall.Quality.services.complexity_analyzer import ComplexityAnalyzer
from Asgard.Heimdall.Quality.services.duplication_detector import DuplicationDetector
from Asgard.Heimdall.Quality.services.code_smell_detector import CodeSmellDetector
from Asgard.Heimdall.Quality.services.technical_debt_analyzer import TechnicalDebtAnalyzer
from Asgard.Heimdall.Quality.services.maintainability_analyzer import MaintainabilityAnalyzer
from Asgard.Heimdall.Quality.services.lazy_import_scanner import LazyImportScanner
from Asgard.Heimdall.Quality.services.env_fallback_scanner import EnvFallbackScanner
from Asgard.Heimdall.Quality.services.syntax_checker import SyntaxChecker
from Asgard.Heimdall.Quality.models.documentation_models import (
    DocumentationConfig,
    FileDocumentation,
    DocumentationReport,
    FunctionDocumentation as DocFunctionDocumentation,
    ClassDocumentation as DocClassDocumentation,
)
from Asgard.Heimdall.Quality.models.naming_models import (
    NamingConfig,
    NamingConvention,
    NamingViolation,
    NamingReport,
)
from Asgard.Heimdall.Quality.services.documentation_scanner import DocumentationScanner
from Asgard.Heimdall.Quality.services.naming_convention_scanner import NamingConventionScanner

__all__ = [
    # File length analysis
    "AnalysisConfig",
    "AnalysisResult",
    "FileAnalysis",
    "FileAnalyzer",
    "SeverityLevel",
    # Complexity analysis
    "ComplexityAnalyzer",
    "ComplexityConfig",
    "ComplexityResult",
    "ComplexitySeverity",
    "FileComplexityAnalysis",
    "FunctionComplexity",
    # Duplication detection
    "CloneFamily",
    "CodeBlock",
    "DuplicationConfig",
    "DuplicationDetector",
    "DuplicationMatch",
    "DuplicationResult",
    "DuplicationSeverity",
    "DuplicationType",
    # Code smell detection
    "CodeSmell",
    "CodeSmellDetector",
    "SmellCategory",
    "SmellConfig",
    "SmellReport",
    "SmellSeverity",
    "SmellThresholds",
    # Technical debt analysis
    "DebtConfig",
    "DebtItem",
    "DebtReport",
    "DebtSeverity",
    "DebtType",
    "EffortModels",
    "InterestRates",
    "ROIAnalysis",
    "TechnicalDebtAnalyzer",
    "TimeHorizon",
    "TimeProjection",
    # Maintainability analysis
    "FileMaintainability",
    "FunctionMaintainability",
    "HalsteadMetrics",
    "LanguageProfile",
    "LanguageWeights",
    "MaintainabilityAnalyzer",
    "MaintainabilityConfig",
    "MaintainabilityLevel",
    "MaintainabilityReport",
    "MaintainabilityThresholds",
    # Lazy import analysis
    "LazyImport",
    "LazyImportConfig",
    "LazyImportReport",
    "LazyImportScanner",
    "LazyImportSeverity",
    "LazyImportType",
    # Environment fallback analysis
    "EnvFallbackConfig",
    "EnvFallbackReport",
    "EnvFallbackScanner",
    "EnvFallbackSeverity",
    "EnvFallbackType",
    "EnvFallbackViolation",
    # Syntax analysis
    "LinterType",
    "SyntaxChecker",
    "SyntaxConfig",
    "SyntaxFileAnalysis",
    "SyntaxIssue",
    "SyntaxResult",
    "SyntaxSeverity",
    # Documentation analysis
    "DocumentationConfig",
    "DocumentationReport",
    "DocumentationScanner",
    "DocClassDocumentation",
    "DocFunctionDocumentation",
    "FileDocumentation",
    # Naming convention analysis
    "NamingConfig",
    "NamingConvention",
    "NamingConventionScanner",
    "NamingReport",
    "NamingViolation",
]
