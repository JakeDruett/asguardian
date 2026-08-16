"""
CLI handlers for the Wave-1/2 Verdandi APIs:

- web cwv-assess          distribution-based Core Web Vitals (p75) assessment
- slo burn-rate-policy    three-tier multi-window burn-rate alert policy
- cache warmup            post-deploy hit-rate trajectory classification
- db pool-signature       pool-exhaustion bimodal signature detection

All are thin wrappers over the existing services: JSON metrics file in,
JSON or human-readable text out.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


_MAX_SKETCH_FILES = 256
_MAX_SKETCH_JSON_BYTES = 8 * 1024 * 1024


def _load_json(path: str, max_bytes: Optional[int] = None) -> Optional[Any]:
    file_path = Path(path)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return None
    try:
        if max_bytes is not None and file_path.stat().st_size > max_bytes:
            print(
                f"Error: {file_path} exceeds the {max_bytes} byte sketch limit."
            )
            return None
        return json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error: Could not parse JSON from {file_path}: {e}")
        return None


def _confine_cli_path(raw: str) -> Path:
    cwd = Path.cwd().resolve()
    dest = Path(raw)
    resolved = dest.resolve() if dest.is_absolute() else (cwd / dest).resolve()
    if not resolved.is_relative_to(cwd):
        raise ValueError(
            f"output path {raw!r} is outside the working directory"
        )
    return resolved


def _dump(model: Any) -> Any:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


def run_cwv_assess(args, output_format: str = "text") -> int:
    """`verdandi web cwv-assess <metrics.json>`.

    Input: {"lcp": [ms...], "inp": [ms...], "cls": [...], "ttfb": [...]}
    — raw RUM sample arrays per metric.
    """
    from Asgard.Verdandi.Web.services.vitals_calculator import (
        CoreWebVitalsCalculator,
    )

    data = _load_json(args.metrics_file)
    if data is None:
        return 1
    if not isinstance(data, dict) or not data:
        print("Error: Expected a JSON object of {metric: [samples...]}.")
        return 1

    calculator = CoreWebVitalsCalculator()
    try:
        assessment = calculator.assess_page(data)
    except (ValueError, TypeError) as e:
        print(f"Error: {e}")
        return 1

    if output_format == "json":
        print(json.dumps(_dump(assessment), indent=2, default=str))
    else:
        lines = ["", "CORE WEB VITALS ASSESSMENT (p75, distribution-based)",
                 "=" * 60]
        for name in ("lcp", "inp", "cls"):
            r = getattr(assessment, name)
            if r is None:
                lines.append(f"  {name.upper():5} : not provided")
                continue
            rating = getattr(r.rating, "value", r.rating)
            p75 = f"{r.p75:g}" if r.p75 is not None else "n/a"
            lines.append(
                f"  {name.upper():5} : {rating}  (p75={p75}, "
                f"n={r.sample_count})"
            )
        passing = assessment.core_passing
        verdict = ("PASS" if passing else
                   "FAIL" if passing is False else "UNDETERMINED")
        lines.append(f"  Core Web Vitals: {verdict}")
        for name, r in sorted(assessment.diagnostics.items()):
            rating = getattr(r.rating, "value", r.rating)
            lines.append(f"  {name.upper():5} : {rating} (diagnostic)")
        for rec in assessment.recommendations:
            lines.append(f"  - {rec}")
        print("\n".join(lines))

    return 0 if assessment.core_passing else 1


def run_burn_rate_policy(args, output_format: str = "text") -> int:
    """`verdandi slo burn-rate-policy <metrics.json>`.

    Input: {"slo": {"name", "type", "target"},
            "metrics": [{"timestamp", "good_events", "total_events"}, ...]}
    """
    from Asgard.Verdandi.SLO.models.slo_models import (
        SLIMetric,
        SLODefinition,
        SLOType,
    )
    from Asgard.Verdandi.SLO.services.burn_rate_analyzer import (
        BurnRateAnalyzer,
    )

    data = _load_json(args.metrics_file)
    if data is None:
        return 1

    try:
        slo_spec = data.get("slo", {}) if isinstance(data, dict) else {}
        slo = SLODefinition(
            name=slo_spec.get("name", "cli-slo"),
            service_name=slo_spec.get(
                "service_name", slo_spec.get("name", "cli-slo")
            ),
            slo_type=SLOType(slo_spec.get("type", "availability")),
            target=float(
                args.target if args.target is not None
                else slo_spec.get("target", 99.9)
            ),
        )
        metrics = [
            SLIMetric(
                timestamp=datetime.fromisoformat(m["timestamp"]),
                service_name=m.get("service_name", slo.name),
                slo_type=slo.slo_type,
                good_events=int(m.get("good_events", 0)),
                total_events=int(m.get("total_events", 0)),
            )
            for m in (data.get("metrics", []) if isinstance(data, dict) else data)
        ]
    except (KeyError, TypeError, ValueError) as e:
        print(f"Error: Invalid burn-rate input: {e}")
        return 1

    now = None
    if getattr(args, "at", None):
        try:
            now = datetime.fromisoformat(args.at)
        except ValueError:
            print(f"Error: Invalid --at timestamp: {args.at}")
            return 1

    alerts = BurnRateAnalyzer().evaluate_alert_policy(
        slo, metrics, current_time=now
    )

    if output_format == "json":
        print(json.dumps([_dump(a) for a in alerts], indent=2, default=str))
    else:
        lines = ["", f"BURN-RATE ALERT POLICY  (target {slo.target}%)",
                 "=" * 60]
        for a in alerts:
            state = ("FIRED" if a.fired else
                     "insufficient traffic" if a.insufficient_traffic
                     else "quiet")
            lines.append(
                f"  {a.tier:10} [{state}]  long {a.long_window_hours:g}h="
                f"{a.long_burn_rate:.2f}x  short "
                f"{a.short_window_hours * 60:.0f}m={a.short_burn_rate:.2f}x  "
                f"threshold {a.threshold:g}x"
            )
            for rec in a.recommendations:
                lines.append(f"    - {rec}")
        print("\n".join(lines))

    return 1 if any(a.fired for a in alerts) else 0


def run_cache_warmup(args, output_format: str = "text") -> int:
    """`verdandi cache warmup <buckets.json>`.

    Input: [{"hits": int, "misses": int}, ...] in time order, or
    {"buckets": [...], "db_load": [...]} to add the DB-load correlate.
    """
    from Asgard.Verdandi.Cache.services.warmup_analyzer import WarmupAnalyzer

    data = _load_json(args.metrics_file)
    if data is None:
        return 1

    if isinstance(data, dict):
        buckets = data.get("buckets", [])
        db_load = data.get("db_load")
    else:
        buckets, db_load = data, None
    if not isinstance(buckets, list) or not buckets:
        print("Error: Expected a JSON array of {hits, misses} buckets.")
        return 1

    result = WarmupAnalyzer().analyze(buckets, db_load_series=db_load)

    if output_format == "json":
        print(json.dumps(_dump(result), indent=2, default=str))
    else:
        state = getattr(result.state, "value", result.state)
        lines = ["", "CACHE WARM-UP TRAJECTORY", "=" * 60,
                 f"  State:    {state}",
                 f"  Severity: {result.severity}",
                 f"  Alert suppressed: {result.suppress_alert}"]
        for note in result.notes:
            lines.append(f"  - {note}")
        print("\n".join(lines))

    return 1 if result.severity == "critical" else 0


def run_cache_stampede(args, output_format: str = "text") -> int:
    """`verdandi cache stampede <access_log.json>`.

    Input: JSON array of {key, t, hit, recompute_ms?, ttl_s?} access-log
    records.
    """
    from Asgard.Verdandi.Cache.services.stampede_analyzer import StampedeAnalyzer

    data = _load_json(args.metrics_file)
    if data is None:
        return 1
    records = data.get("access_log", data) if isinstance(data, dict) else data
    if not isinstance(records, list) or not records:
        print("Error: Expected a non-empty JSON array of access-log records.")
        return 1

    analyzer = StampedeAnalyzer()
    kwargs = {}
    beta = getattr(args, "beta", None)
    if beta is not None:
        kwargs["beta"] = beta

    try:
        report = analyzer.analyze(records, **kwargs)
    except (TypeError, ValueError) as e:
        print(f"Error: {e}")
        return 1

    if output_format == "json":
        print(json.dumps(_dump(report), indent=2, default=str))
    else:
        lines = ["", "CACHE STAMPEDE ANALYSIS", "=" * 60,
                 f"  Status: {report.status}",
                 f"  Keys analyzed: {report.total_keys_analyzed}",
                 f"  Flagged keys:  {len(report.flagged_keys)}"]
        for rec in report.recommendations:
            lines.append(f"  ! {rec}")
        for note in report.notes:
            lines.append(f"  - {note}")
        print("\n".join(lines))

    return 1 if report.status == "critical" else 0


def run_cache_slo(args, output_format: str = "text") -> int:
    """`verdandi cache slo <latencies.json>`.

    Input: {"hit_latencies_ms": [...], "miss_latencies_ms": [...],
    "baseline_hit_median_ms"?: float, "baseline_hit_mad_ms"?: float}
    for labeled samples, or {"latencies_ms": [...]} (unlabeled — split via
    the bimodality guard, honestly marked labeled=false).
    """
    from Asgard.Verdandi.Cache.services.segmented_slo import SegmentedSloAnalyzer

    data = _load_json(args.metrics_file)
    if data is None:
        return 1
    if not isinstance(data, dict):
        print(
            "Error: Expected a JSON object with hit_latencies_ms/"
            "miss_latencies_ms (labeled) or latencies_ms (unlabeled)."
        )
        return 1

    kwargs = {}
    hit_threshold = getattr(args, "hit_threshold", None)
    if hit_threshold is not None:
        kwargs["hit_threshold_ms"] = hit_threshold
    miss_threshold = getattr(args, "miss_threshold", None)
    if miss_threshold is not None:
        kwargs["miss_threshold_ms"] = miss_threshold
    analyzer = SegmentedSloAnalyzer(**kwargs)

    baseline_median = data.get("baseline_hit_median_ms")
    baseline_mad = data.get("baseline_hit_mad_ms")

    hits = data.get("hit_latencies_ms")
    misses = data.get("miss_latencies_ms")
    unlabeled = data.get("latencies_ms")
    try:
        if hits is not None or misses is not None:
            result = analyzer.analyze(
                hit_latencies_ms=hits or [],
                miss_latencies_ms=misses or [],
                baseline_hit_median_ms=baseline_median,
                baseline_hit_mad_ms=baseline_mad,
            )
        elif unlabeled:
            result = analyzer.analyze_unlabeled(
                unlabeled,
                baseline_hit_median_ms=baseline_median,
                baseline_hit_mad_ms=baseline_mad,
            )
        else:
            print(
                "Error: Provide hit_latencies_ms/miss_latencies_ms or a "
                "non-empty latencies_ms array."
            )
            return 1
    except (TypeError, ValueError) as e:
        print(f"Error: {e}")
        return 1

    if output_format == "json":
        print(json.dumps(_dump(result), indent=2, default=str))
    else:
        lines = ["", "SEGMENTED CACHE SLO", "=" * 60,
                 f"  Labeled samples: {result.labeled}"]
        if result.hit_sli is not None:
            lines.append(
                f"  Hit SLI:  {result.hit_sli:.4f} "
                f"({result.hit_good}/{result.hit_total} <= "
                f"{result.hit_threshold_ms:g} ms)"
            )
        if result.miss_sli is not None:
            lines.append(
                f"  Miss SLI: {result.miss_sli:.4f} "
                f"({result.miss_good}/{result.miss_total} <= "
                f"{result.miss_threshold_ms:g} ms)"
            )
        if result.hit_ratio is not None:
            lines.append(f"  Hit ratio: {result.hit_ratio:.4f}")
        if result.hit_median_ms is not None:
            lines.append(f"  Hit-mode median: {result.hit_median_ms:g} ms")
        lines.append(f"  Mode-shift alert: {result.mode_shift_alert}")
        for note in result.notes:
            lines.append(f"  - {note}")
        print("\n".join(lines))

    return 1 if result.mode_shift_alert else 0


def run_pool_signature(args, output_format: str = "text") -> int:
    """`verdandi db pool-signature <latencies.json>`.

    Input: [latency_ms, ...] or
    {"latencies_ms": [...], "acquisition_waits_ms": [...]}.
    """
    from Asgard.Verdandi.Database.services.pool_signature_detector import (
        PoolSignatureDetector,
    )

    data = _load_json(args.metrics_file)
    if data is None:
        return 1

    if isinstance(data, dict):
        latencies = data.get("latencies_ms", [])
        waits = data.get("acquisition_waits_ms")
    else:
        latencies, waits = data, None
    if not isinstance(latencies, list) or not latencies:
        print("Error: Expected a JSON array of latencies in ms.")
        return 1

    signature = PoolSignatureDetector().detect(
        latencies, acquisition_wait_samples=waits
    )

    if output_format == "json":
        print(json.dumps(_dump(signature), indent=2, default=str))
    else:
        classification = getattr(
            signature.classification, "value", signature.classification
        )
        lines = ["", "DB POOL-EXHAUSTION SIGNATURE", "=" * 60,
                 f"  Classification: {classification}",
                 f"  Confidence:     {signature.confidence}"]
        if signature.mean_queue_wait_ms is not None:
            lines.append(
                f"  Mean queue wait: {signature.mean_queue_wait_ms:.1f} ms"
            )
        for w in signature.warnings:
            lines.append(f"  ! {w}")
        for rec in signature.recommendations:
            lines.append(f"  - {rec}")
        print("\n".join(lines))

    classification = str(getattr(
        signature.classification, "value", signature.classification
    ))
    return 1 if classification == "pool_exhaustion" else 0


def run_db_budget(args, output_format: str = "text") -> int:
    """`verdandi db budget <input.json>`.

    Input: {"config": {...QueryBudgetConfig fields...},
            "durations_ms": [...], "units": [...]}
    """
    from Asgard.Verdandi.Database.models.database_models import QueryBudgetConfig
    from Asgard.Verdandi.Database.services.query_budget import QueryBudgetAnalyzer

    data = _load_json(args.metrics_file)
    if data is None:
        return 1
    if not isinstance(data, dict):
        print("Error: Expected a JSON object.")
        return 1

    durations = data.get("durations_ms")
    units = data.get("units")
    if not isinstance(durations, list) or not isinstance(units, list):
        print("Error: 'durations_ms' and 'units' arrays are required.")
        return 1

    try:
        config = QueryBudgetConfig.model_validate(data.get("config", {}))
    except (TypeError, ValueError) as e:
        print(f"Error: Invalid budget config: {e}")
        return 1

    result = QueryBudgetAnalyzer().evaluate(config, durations, units)

    if output_format == "json":
        print(json.dumps(_dump(result), indent=2, default=str))
    else:
        lines = ["", "DATABASE QUERY BUDGET EVALUATION", "=" * 60,
                 f"  Passed: {result.good}/{result.total}"]
        if result.sli_passed_fraction is not None:
            lines.append(f"  SLI passed fraction: {result.sli_passed_fraction:.4f}")
        lines.append(f"  Violations: {len(result.violations)}")
        for note in result.notes:
            lines.append(f"  - {note}")
        print("\n".join(lines))

    return 1 if result.violations else 0


def run_db_queries_per_class(args, output_format: str = "text") -> int:
    """`verdandi db queries <input.json> --per-class`.

    Input: {"queries": [...QueryMetricsInput...], "baseline": {fingerprint:
            [durations_ms...]}?} or a bare JSON array of queries.
    """
    from Asgard.Verdandi.Database.models.database_models import QueryMetricsInput
    from Asgard.Verdandi.Database.services.query_metrics import (
        QueryMetricsCalculator,
    )

    data = _load_json(args.metrics_file)
    if data is None:
        return 1

    if isinstance(data, dict):
        raw_queries = data.get("queries", [])
        baseline = data.get("baseline")
    else:
        raw_queries, baseline = data, None
    if not isinstance(raw_queries, list) or not raw_queries:
        print("Error: Expected a non-empty array of queries.")
        return 1

    try:
        queries = [QueryMetricsInput.model_validate(q) for q in raw_queries]
    except (TypeError, ValueError) as e:
        print(f"Error: Invalid query input: {e}")
        return 1

    threshold = getattr(args, "slow_threshold", None) or 100.0
    calculator = QueryMetricsCalculator(slow_query_threshold_ms=threshold)
    classes = calculator.analyze_by_fingerprint(queries, baseline=baseline)

    if output_format == "json":
        print(json.dumps([_dump(c) for c in classes], indent=2, default=str))
    else:
        lines = ["", "DATABASE QUERY METRICS BY CLASS (fingerprint)", "=" * 60]
        for c in classes:
            lines.append(
                f"  {c.fingerprint[:60]:<60} n={c.count:<5} "
                f"p50={c.p50_ms:.1f}ms p95={c.p95_ms:.1f}ms "
                f"shift={c.shift_detected}"
            )
            for note in c.shift_notes:
                lines.append(f"      ! {note}")
        print("\n".join(lines))

    return 1 if any(c.shift_detected for c in classes) else 0


def run_sketch_merge(args, output_format: str = "text") -> int:
    """`verdandi analyze sketch-merge <sketch.json> [<sketch.json> ...]`.

    Merges serialized quantile sketches (all t-digest or all DDSketch) and
    queries percentiles on the merged sketch — the sanctioned cross-source
    aggregation path (RESEARCH_15: never average per-host percentiles).
    """
    from Asgard.Verdandi.Analysis.services.quantile_sketch import (
        DDSketch,
        TDigest,
    )

    loaders = {"tdigest": TDigest.from_dict, "ddsketch": DDSketch.from_dict}
    sketches = []
    sketch_type = None
    if len(args.sketch_files) > _MAX_SKETCH_FILES:
        print(
            f"Error: At most {_MAX_SKETCH_FILES} sketch files can be merged."
        )
        return 1
    for path in args.sketch_files:
        data = _load_json(path, max_bytes=_MAX_SKETCH_JSON_BYTES)
        if data is None:
            return 1
        if not isinstance(data, dict) or data.get("type") not in loaders:
            print(
                f"Error: {path} is not a serialized sketch "
                "(expected a JSON object with type 'tdigest' or 'ddsketch')."
            )
            return 1
        if sketch_type is None:
            sketch_type = data["type"]
        elif data["type"] != sketch_type:
            print(
                f"Error: Cannot merge mixed sketch types "
                f"({sketch_type} vs {data['type']} in {path})."
            )
            return 1
        try:
            sketches.append(loaders[data["type"]](data))
        except (KeyError, TypeError, ValueError) as e:
            print(f"Error: Could not deserialize sketch from {path}: {e}")
            return 1

    try:
        percentiles = [float(q) for q in args.quantiles.split(",") if q.strip()]
    except ValueError:
        print(f"Error: Invalid --quantiles value: {args.quantiles}")
        return 1
    if not percentiles or any(not (0 < q < 100) for q in percentiles):
        print("Error: --quantiles values must be between 0 and 100 (exclusive).")
        return 1

    merged = sketches[0]
    for sketch in sketches[1:]:
        merged.merge(sketch)

    estimates = {f"p{q:g}": merged.percentile(q) for q in percentiles}

    if args.output:
        try:
            out_path = _confine_cli_path(args.output)
            out_path.write_text(
                json.dumps(merged.to_dict(), indent=2), encoding="utf-8"
            )
        except ValueError as e:
            print(f"Error: {e}")
            return 1
        except OSError as e:
            print(f"Error: Could not write merged sketch to {args.output}: {e}")
            return 1

    if output_format == "json":
        print(json.dumps({
            "sketch_type": sketch_type,
            "sources": len(sketches),
            "count": merged.count,
            "percentiles": estimates,
            "output": args.output,
        }, indent=2))
    else:
        lines = ["", "MERGED QUANTILE SKETCH (cross-source union)", "=" * 60,
                 f"  Sketch type: {sketch_type}",
                 f"  Sources:     {len(sketches)}",
                 f"  Count:       {merged.count:g}"]
        for label, value in estimates.items():
            lines.append(f"  {label:6}: {value:.4f}")
        if args.output:
            lines.append(f"  Merged sketch written to: {args.output}")
        print("\n".join(lines))

    return 0


def run_co_check(args, output_format: str = "text") -> int:
    """`verdandi analyze co-check <metrics.json>`.

    Coordinated-omission quality analysis: Tene heuristic, Little's-law
    sanity check, and (with --correct) HDR-style expected-interval backfill.
    Exit code 1 when the dataset is suspect.
    """
    from Asgard.Verdandi.Analysis.services import coordinated_omission

    data = _load_json(args.metrics_file)
    if data is None:
        return 1
    if not isinstance(data, dict):
        print("Error: Expected a JSON object with samples_ms and duration_ms.")
        return 1
    samples = data.get("samples_ms")
    duration = data.get("duration_ms")
    if not isinstance(samples, list) or not samples:
        print("Error: samples_ms must be a non-empty array of latencies (ms).")
        return 1
    if not isinstance(duration, (int, float)) or duration <= 0:
        print("Error: duration_ms must be a positive number.")
        return 1

    expected_interval = data.get("expected_interval_ms")
    if args.correct and not expected_interval:
        print(
            "Error: --correct requires expected_interval_ms in the "
            "metrics file (1000 / target_throughput_rps)."
        )
        return 1

    report = coordinated_omission.analyze(
        samples,
        duration,
        expected_interval_ms=expected_interval,
        throughput_rps=data.get("throughput_rps"),
        max_concurrency=data.get("max_concurrency"),
        apply_correction=args.correct,
    )

    corrected = report.corrected_samples_ms
    if output_format == "json":
        print(json.dumps({
            "suspect": report.suspect,
            "quality_flags": report.quality_flags,
            "implied_concurrency": report.implied_concurrency,
            "original_sample_count": len(samples),
            "corrected_sample_count": (
                len(corrected) if corrected is not None else None
            ),
            "corrected_samples_ms": corrected,
        }, indent=2))
    else:
        lines = ["", "COORDINATED-OMISSION CHECK", "=" * 60,
                 f"  Samples:       {len(samples)}",
                 f"  Duration (ms): {duration:g}",
                 f"  Suspect:       {report.suspect}",
                 f"  Quality flags: {', '.join(report.quality_flags) or 'none'}"]
        if report.implied_concurrency is not None:
            lines.append(
                f"  Implied concurrency: {report.implied_concurrency:.2f}"
            )
        if corrected is not None:
            lines.append(
                f"  Backfill-corrected samples: {len(corrected)} "
                f"(+{len(corrected) - len(samples)} synthesized)"
            )
        print("\n".join(lines))

    return 1 if report.suspect else 0
