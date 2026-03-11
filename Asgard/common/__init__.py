"""
Asgard Common Infrastructure

Shared utilities for parallel processing, incremental scanning,
baseline management, and output formatting.

These can be used by any Asgard module (Heimdall, Freya, Forseti,
Verdandi, Volundr) to add consistent functionality.
"""

__version__ = "1.0.0"

from Asgard.common.parallel import (
    ParallelConfig,
    ParallelRunner,
    ParallelRunnerMixin,
    ChunkedResult,
    chunk_items,
    get_optimal_worker_count,
    should_use_parallel,
)

from Asgard.common.incremental import (
    IncrementalConfig,
    FileHashCache,
    IncrementalMixin,
    HashEntry,
)

from Asgard.common.baseline import (
    BaselineConfig,
    BaselineEntry,
    BaselineFile,
    BaselineManager,
    BaselineMixin,
    BaselineStats,
)

from Asgard.common.output_formatter import (
    OutputFormat,
    UnifiedFormatter,
    FormattedResult,
    Severity,
)

from Asgard.common.progress import (
    ProgressReporter,
    ProgressConfig,
    ProgressStyle,
)

__all__ = [
    # Version
    "__version__",
    # Parallel
    "ParallelConfig",
    "ParallelRunner",
    "ParallelRunnerMixin",
    "ChunkedResult",
    "chunk_items",
    "get_optimal_worker_count",
    "should_use_parallel",
    # Incremental
    "IncrementalConfig",
    "FileHashCache",
    "IncrementalMixin",
    "HashEntry",
    # Baseline
    "BaselineConfig",
    "BaselineEntry",
    "BaselineFile",
    "BaselineManager",
    "BaselineMixin",
    "BaselineStats",
    # Output
    "OutputFormat",
    "UnifiedFormatter",
    "FormattedResult",
    "Severity",
    # Progress
    "ProgressReporter",
    "ProgressConfig",
    "ProgressStyle",
]
