"""CH-0101: critical-path walks must terminate on cyclic parent_span_id."""

from datetime import datetime, timezone

from Asgard.Verdandi.APM.models.apm_models import Span, Trace
from Asgard.Verdandi.APM.services.service_map_builder import ServiceMapBuilder
from Asgard.Verdandi.Tracing.models.tracing_models import TraceSpan
from Asgard.Verdandi.Tracing.services._path_helpers import find_critical_path


def _span(span_id: str, parent: str | None, duration_ms: float = 10.0) -> Span:
    now = datetime.now(timezone.utc)
    return Span(
        trace_id="t1",
        span_id=span_id,
        parent_span_id=parent,
        operation_name=span_id,
        service_name="svc",
        start_time=now,
        end_time=now,
        duration_ms=duration_ms,
    )


def test_service_map_critical_path_breaks_a_b_a_cycle():
    a = _span("A", None, 5.0)
    b = _span("B", "A", 20.0)
    a_as_child = _span("A", "B", 5.0)
    trace = Trace(trace_id="t1", root_span=a, spans=[a, b, a_as_child])
    path = ServiceMapBuilder().find_critical_path(trace)
    ids = [s.span_id for s in path]
    assert ids[0] == "A"
    assert ids.count("A") == 1
    assert len(ids) <= 3


def test_path_helper_breaks_a_b_a_cycle():
    a = TraceSpan(
        trace_id="t1",
        span_id="A",
        parent_span_id=None,
        operation_name="A",
        service_name="svc",
        start_time_unix_nano=0,
        end_time_unix_nano=10,
        duration_ms=5.0,
    )
    b = TraceSpan(
        trace_id="t1",
        span_id="B",
        parent_span_id="A",
        operation_name="B",
        service_name="svc",
        start_time_unix_nano=1,
        end_time_unix_nano=20,
        duration_ms=20.0,
    )
    children = {"A": [b], "B": [a]}
    path = find_critical_path(a, children)
    ids = [s.span_id for s in path]
    assert ids == ["A", "B"]
