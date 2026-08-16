"""
Parallel Scanner Infrastructure

Provides multiprocessing support for file analysis to improve performance
on large codebases.

CH-0053: spawn workers (no fork FD/secret copy); import the analyzer by
name (do not pickle callables); kill hung workers on timeout; cap workers.
"""

import importlib
import multiprocessing
import os
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, TypeVar

from Asgard.Bragi.common.context_classifier import classify

# Type variables
T = TypeVar('T')  # Input type
R = TypeVar('R')  # Result type

# CWE-400: unbounded workers can exhaust process table / RAM.
MAX_WORKERS = 32


def stamp_context(file_path: "str | Path", result: Any) -> Any:
    """
    Classify `file_path` (Plan 04 Phase A) and stamp the code context onto
    `result` if it exposes a settable `context` attribute, so scanner
    entry points get context-awareness "for free" without re-guessing it
    themselves. Results without a `context` slot (e.g. plain scalars) pass
    through unchanged; classification failures never raise - the context
    is simply left unset.
    """
    if result is None or not hasattr(result, "context"):
        return result
    try:
        context = classify(file_path).value
    except Exception:
        return result
    try:
        setattr(result, "context", context)
    except (AttributeError, TypeError, ValueError):
        # Immutable / validated models (e.g. frozen dataclasses, strict
        # pydantic models with an unexpected type) simply keep their
        # existing context rather than erroring the scan.
        pass
    return result


@dataclass
class ParallelConfig:
    """Configuration for parallel scanning."""
    enabled: bool = False
    workers: Optional[int] = None  # None = CPU count - 1
    chunk_size: int = 10
    timeout_per_file: float = 30.0

    @property
    def worker_count(self) -> int:
        """Get the actual number of workers to use (capped at MAX_WORKERS)."""
        if self.workers is not None:
            requested = max(1, self.workers)
        else:
            requested = max(1, (os.cpu_count() or 1) - 1)
        return min(requested, MAX_WORKERS)


@dataclass
class ChunkedResult(Generic[R]):
    """Result from processing a chunk of files."""
    results: List[R]
    errors: Dict[str, str]
    files_processed: int


def chunk_files(files: List[Path], chunk_size: int) -> Iterator[List[Path]]:
    """
    Split a list of files into chunks for parallel processing.

    Args:
        files: List of file paths
        chunk_size: Number of files per chunk

    Yields:
        Chunks of file paths
    """
    for i in range(0, len(files), chunk_size):
        yield files[i:i + chunk_size]


def analyzer_import_path(func: Callable[..., Any]) -> str:
    """Return ``module:name`` for a module-level function (spawn-safe)."""
    module = getattr(func, "__module__", None)
    qualname = getattr(func, "__qualname__", None)
    if (
        not isinstance(module, str)
        or not isinstance(qualname, str)
        or not module
        or not qualname
        or "<" in qualname
        or "." in qualname
        or not qualname.isidentifier()
        or "/" in module
        or "\\" in module
    ):
        raise ValueError("parallel analyzer must be a named module-level function")
    return f"{module}:{qualname}"


def load_named_analyzer(ref: str) -> Callable[..., Any]:
    """Import a module-level analyzer from a ``module:name`` reference."""
    if not isinstance(ref, str) or ref.count(":") != 1:
        raise ValueError("invalid analyzer reference")
    module_name, qualname = ref.split(":", 1)
    if (
        not module_name
        or not qualname
        or "." in qualname
        or "<" in qualname
        or not qualname.isidentifier()
        or "/" in module_name
        or "\\" in module_name
    ):
        raise ValueError("invalid analyzer reference")
    module = importlib.import_module(module_name)
    func = getattr(module, qualname)
    if not callable(func):
        raise TypeError(f"analyzer {ref!r} is not callable")
    return func


def _kill_executor_workers(executor: ProcessPoolExecutor) -> None:
    """SIGKILL / TerminateProcess every live worker (timeout_per_file)."""
    processes = getattr(executor, "_processes", None) or {}
    for proc in list(processes.values()):
        try:
            if proc is not None and proc.is_alive():
                proc.kill()
        except (ProcessLookupError, AttributeError, OSError):
            continue


def _process_file_wrapper(args: tuple) -> tuple:
    """
    Named spawn worker: import the analyzer by ``module:name`` and run it.

    Args:
        args: Tuple of (file_path, analyzer_ref, config_dict)

    Returns:
        Tuple of (file_path, result, error)
    """
    file_path, analyzer_ref, config_dict = args
    try:
        analyzer_func = load_named_analyzer(analyzer_ref)
        result = analyzer_func(Path(file_path), config_dict)
        result = stamp_context(file_path, result)
        return (str(file_path), result, None)
    except Exception as e:
        return (str(file_path), None, str(e))


class ParallelScanner(Generic[T, R]):
    """
    Generic parallel scanner that distributes file analysis across processes.

    Usage:
        def analyze_file(file_path: Path, config: dict) -> Result:
            # Module-level function (imported by name in spawn workers)
            return result

        scanner = ParallelScanner(analyze_file, config)
        results = scanner.scan(files)
    """

    def __init__(
        self,
        analyze_func: Callable[[Path, Dict], R],
        config: ParallelConfig,
    ):
        """
        Initialize the parallel scanner.

        Args:
            analyze_func: Function to analyze a single file
            config: Parallel configuration
        """
        self.analyze_func = analyze_func
        self.config = config

    def scan(
        self,
        files: List[Path],
        config_dict: Optional[Dict] = None,
    ) -> ChunkedResult[R]:
        """
        Scan files in parallel.

        Args:
            files: List of file paths to analyze
            config_dict: Configuration dictionary to pass to analyzer

        Returns:
            ChunkedResult containing all results and any errors
        """
        if not self.config.enabled or len(files) <= self.config.chunk_size:
            # Fall back to sequential processing for small file sets
            return self._scan_sequential(files, config_dict or {})

        return self._scan_parallel(files, config_dict or {})

    def _scan_sequential(
        self,
        files: List[Path],
        config_dict: Dict,
    ) -> ChunkedResult[R]:
        """Process files sequentially."""
        results = []
        errors = {}

        for file_path in files:
            try:
                result = self.analyze_func(file_path, config_dict)
                result = stamp_context(file_path, result)
                if result is not None:
                    results.append(result)
            except Exception as e:
                errors[str(file_path)] = str(e)

        return ChunkedResult(
            results=results,
            errors=errors,
            files_processed=len(files),
        )

    def _scan_parallel(
        self,
        files: List[Path],
        config_dict: Dict,
    ) -> ChunkedResult[R]:
        """Process files in a spawn pool; kill the pool if a file times out."""
        results = []
        errors = {}
        analyzer_ref = analyzer_import_path(self.analyze_func)
        work_items = [
            (str(file_path), analyzer_ref, config_dict)
            for file_path in files
        ]

        ctx = multiprocessing.get_context("spawn")
        executor = ProcessPoolExecutor(
            max_workers=self.config.worker_count,
            mp_context=ctx,
        )
        try:
            futures = {
                executor.submit(_process_file_wrapper, item): item[0]
                for item in work_items
            }
            pending = set(futures)
            started = {fut: time.monotonic() for fut in pending}
            timeout = max(0.0, float(self.config.timeout_per_file))

            while pending:
                now = time.monotonic()
                remaining = min(
                    max(0.0, timeout - (now - started[fut])) for fut in pending
                )
                done, pending = wait(
                    pending, timeout=remaining, return_when=FIRST_COMPLETED
                )
                now = time.monotonic()
                if not done:
                    for fut in pending:
                        errors[futures[fut]] = "timeout"
                    _kill_executor_workers(executor)
                    break

                for future in done:
                    file_path = futures[future]
                    try:
                        path, result, error = future.result(timeout=0)
                        if error:
                            errors[path] = error
                        elif result is not None:
                            results.append(result)
                    except Exception as e:
                        errors[str(file_path)] = str(e)

                overdue = [fut for fut in pending if now - started[fut] >= timeout]
                if overdue:
                    for fut in pending:
                        errors[futures[fut]] = "timeout"
                    _kill_executor_workers(executor)
                    break
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        return ChunkedResult(
            results=results,
            errors=errors,
            files_processed=len(files),
        )


class ParallelScannerMixin:
    """
    Mixin class to add parallel scanning capabilities to existing scanners.

    Usage:
        class MyScanner(ParallelScannerMixin):
            def __init__(self, config):
                self.config = config
                self.parallel_config = ParallelConfig(
                    enabled=config.parallel,
                    workers=config.workers,
                )

            def analyze(self, path: Path):
                files = self._discover_files(path)
                if self.parallel_config.enabled:
                    # analyze_func must be a named module-level function
                    return self._analyze_parallel(files, analyze_one_file)
                return self._analyze_sequential(files)
    """

    parallel_config: ParallelConfig

    def _analyze_parallel(
        self,
        files: List[Path],
        analyze_func: Callable[[Path, Dict], R],
        config_dict: Optional[Dict] = None,
    ) -> ChunkedResult[R]:
        """
        Analyze files in parallel.

        Args:
            files: Files to analyze
            analyze_func: Function to analyze each file
            config_dict: Configuration to pass to analyzer

        Returns:
            ChunkedResult with all results
        """
        scanner: ParallelScanner = ParallelScanner(analyze_func, self.parallel_config)
        return scanner.scan(files, config_dict)


def get_optimal_worker_count(file_count: int, max_workers: Optional[int] = None) -> int:
    """
    Calculate the optimal number of workers based on file count and CPU cores.

    Args:
        file_count: Number of files to process
        max_workers: Soft cap before the hard MAX_WORKERS limit (None = CPU-derived)

    Returns:
        Optimal worker count
    """
    cpu_count = os.cpu_count() or 1

    # Don't use more workers than files
    optimal = min(file_count, cpu_count - 1)

    # Ensure at least 1 worker
    optimal = max(1, optimal)

    # Apply caller limit, then the hard CWE-400 cap
    if max_workers is not None:
        optimal = min(optimal, max_workers)
        optimal = max(1, optimal)

    return min(optimal, MAX_WORKERS)


def should_use_parallel(file_count: int, threshold: int = 20) -> bool:
    """
    Determine if parallel processing would be beneficial.

    Args:
        file_count: Number of files to process
        threshold: Minimum files to benefit from parallelization

    Returns:
        True if parallel processing is recommended
    """
    # Don't parallelize for small file counts due to overhead
    if file_count < threshold:
        return False

    # Check if multiprocessing is available
    cpu_count = os.cpu_count()
    if cpu_count is None or cpu_count < 2:
        return False

    return True
