"""Tests for ParallelScanner context stamping and CH-0053 spawn safety."""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from Asgard.Bragi.Quality.services.parallel_scanner import (
    MAX_WORKERS,
    ParallelConfig,
    ParallelScanner,
    _kill_executor_workers,
    _process_file_wrapper,
    analyzer_import_path,
    get_optimal_worker_count,
    load_named_analyzer,
    stamp_context,
)


@dataclass
class _Result:
    file_path: str
    context: str = "production"


def _named_analyze(file_path: Path, config: dict) -> _Result:
    return _Result(file_path=str(file_path))


class TestStampContext:
    def test_stamps_test_context_for_test_path(self) -> None:
        result = stamp_context("tests/test_foo.py", _Result(file_path="tests/test_foo.py"))
        assert result.context == "test"

    def test_leaves_production_default_for_normal_path(self) -> None:
        result = stamp_context("src/foo.py", _Result(file_path="src/foo.py"))
        assert result.context == "production"

    def test_none_result_passes_through(self) -> None:
        assert stamp_context("src/foo.py", None) is None

    def test_result_without_context_attr_passes_through(self) -> None:
        assert stamp_context("src/foo.py", 42) == 42


class TestParallelScannerStampsContext:
    def test_sequential_scan_stamps_context(self, tmp_path: Path) -> None:
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        f = test_dir / "test_thing.py"
        f.write_text("def test_x(): pass\n")

        def analyze(file_path: Path, config: dict) -> _Result:
            return _Result(file_path=str(file_path))

        scanner: ParallelScanner = ParallelScanner(analyze, ParallelConfig(enabled=False))
        chunked = scanner.scan([f])
        assert len(chunked.results) == 1
        assert chunked.results[0].context == "test"


class TestCH0053SpawnSafety:
    def test_worker_count_is_capped(self, monkeypatch) -> None:
        assert ParallelConfig(workers=10_000).worker_count == MAX_WORKERS
        assert MAX_WORKERS == 32
        monkeypatch.setattr(
            "Asgard.Bragi.Quality.services.parallel_scanner.os.cpu_count",
            lambda: 256,
        )
        assert ParallelConfig(workers=None).worker_count == MAX_WORKERS

    def test_optimal_worker_count_is_capped(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "Asgard.Bragi.Quality.services.parallel_scanner.os.cpu_count",
            lambda: 256,
        )
        assert get_optimal_worker_count(10_000) == MAX_WORKERS
        assert get_optimal_worker_count(10_000, max_workers=10_000) == MAX_WORKERS

    def test_analyzer_import_path_rejects_lambda(self) -> None:
        with pytest.raises(ValueError, match="named module-level"):
            analyzer_import_path(lambda path, config: None)

    def test_analyzer_import_path_rejects_nested(self) -> None:
        def nested(path: Path, config: dict) -> None:
            return None

        with pytest.raises(ValueError, match="named module-level"):
            analyzer_import_path(nested)

    def test_analyzer_import_path_roundtrip(self) -> None:
        ref = analyzer_import_path(_named_analyze)
        assert ref.endswith(":_named_analyze")
        assert ":" in ref
        assert load_named_analyzer(ref) is _named_analyze

    def test_load_named_analyzer_rejects_callable_payload(self) -> None:
        with pytest.raises(ValueError, match="invalid analyzer reference"):
            load_named_analyzer(_named_analyze)  # type: ignore[arg-type]

    def test_wrapper_does_not_invoke_callable_payload(self) -> None:
        called = {"n": 0}

        def sneaky(path: Path, config: dict) -> str:
            called["n"] += 1
            return "pwned"

        path, result, error = _process_file_wrapper(("/tmp/x.py", sneaky, {}))
        assert called["n"] == 0
        assert result is None
        assert error

    def test_wrapper_imports_named_analyzer(self, tmp_path: Path) -> None:
        f = tmp_path / "tests" / "test_a.py"
        f.parent.mkdir()
        f.write_text("x = 1\n")
        path, result, error = _process_file_wrapper(
            (str(f), analyzer_import_path(_named_analyze), {})
        )
        assert error is None
        assert path == str(f)
        assert result is not None
        assert result.context == "test"

    def test_parallel_rejects_unnamed_callable(self, tmp_path: Path) -> None:
        files = []
        for i in range(3):
            f = tmp_path / f"f{i}.py"
            f.write_text("x = 1\n")
            files.append(f)

        def nested(path: Path, config: dict) -> _Result:
            return _Result(file_path=str(path))

        scanner = ParallelScanner(
            nested,
            ParallelConfig(enabled=True, workers=2, chunk_size=1),
        )
        with pytest.raises(ValueError, match="named module-level"):
            scanner.scan(files)

    def test_scan_parallel_uses_spawn_and_named_ref(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        captured: dict[str, Any] = {}

        class FakeFuture:
            def result(self, timeout: float | None = None) -> tuple:
                return (str(tmp_path / "f0.py"), _Result(file_path="f0.py"), None)

        class FakeExecutor:
            def __init__(self, max_workers=None, mp_context=None):
                captured["max_workers"] = max_workers
                captured["mp_context"] = mp_context
                self._processes = {}

            def submit(self, fn, item):
                captured.setdefault("items", []).append(item)
                captured["fn"] = fn
                return FakeFuture()

            def shutdown(self, wait=True, cancel_futures=False):
                captured["shutdown"] = (wait, cancel_futures)

        def fake_wait(pending, timeout=None, return_when=None):
            assert return_when is FIRST_COMPLETED
            return set(pending), set()

        monkeypatch.setattr(
            "Asgard.Bragi.Quality.services.parallel_scanner.ProcessPoolExecutor",
            FakeExecutor,
        )
        monkeypatch.setattr(
            "Asgard.Bragi.Quality.services.parallel_scanner.wait",
            fake_wait,
        )

        files = []
        for i in range(3):
            f = tmp_path / f"f{i}.py"
            f.write_text("x = 1\n")
            files.append(f)

        scanner = ParallelScanner(
            _named_analyze,
            ParallelConfig(enabled=True, workers=2, chunk_size=1, timeout_per_file=5),
        )
        chunked = scanner.scan(files)
        assert len(chunked.results) == 3
        assert captured["mp_context"].get_start_method() == "spawn"
        assert captured["max_workers"] == 2
        assert captured["fn"] is _process_file_wrapper
        assert captured["shutdown"] == (False, True)
        for item in captured["items"]:
            file_path, analyzer_ref, _config = item
            assert isinstance(file_path, str)
            assert isinstance(analyzer_ref, str)
            assert not callable(analyzer_ref)
            assert analyzer_ref.endswith(":_named_analyze")

    def test_timeout_kills_workers(self, tmp_path: Path, monkeypatch) -> None:
        class FakeProc:
            def __init__(self) -> None:
                self.killed = False
                self._alive = True

            def is_alive(self) -> bool:
                return self._alive

            def kill(self) -> None:
                self.killed = True
                self._alive = False

        proc = FakeProc()

        class FakeFuture:
            def result(self, timeout: float | None = None) -> tuple:
                raise AssertionError("hung future must not be collected")

        class FakeExecutor:
            def __init__(self, max_workers=None, mp_context=None):
                self._processes = {1: proc}

            def submit(self, fn, item):
                return FakeFuture()

            def shutdown(self, wait=True, cancel_futures=False):
                return None

        def fake_wait(pending, timeout=None, return_when=None):
            return set(), set(pending)

        monkeypatch.setattr(
            "Asgard.Bragi.Quality.services.parallel_scanner.ProcessPoolExecutor",
            FakeExecutor,
        )
        monkeypatch.setattr(
            "Asgard.Bragi.Quality.services.parallel_scanner.wait",
            fake_wait,
        )

        files = []
        for i in range(3):
            f = tmp_path / f"f{i}.py"
            f.write_text("x = 1\n")
            files.append(f)

        scanner = ParallelScanner(
            _named_analyze,
            ParallelConfig(enabled=True, workers=2, chunk_size=1, timeout_per_file=0.01),
        )
        chunked = scanner.scan(files)
        assert proc.killed is True
        assert len(chunked.results) == 0
        assert len(chunked.errors) == 3
        assert all(err == "timeout" for err in chunked.errors.values())

    def test_kill_helper_ignores_dead_workers(self) -> None:
        class Dead:
            def is_alive(self) -> bool:
                return False

            def kill(self) -> None:
                raise AssertionError("must not kill a dead worker")

        class Raising:
            def is_alive(self) -> bool:
                raise OSError("gone")

            def kill(self) -> None:
                raise AssertionError("must not kill")

        class FakeExecutor:
            _processes = {1: Dead(), 2: Raising(), 3: None}

        _kill_executor_workers(FakeExecutor())  # type: ignore[arg-type]
