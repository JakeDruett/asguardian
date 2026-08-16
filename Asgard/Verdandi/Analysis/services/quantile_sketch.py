"""
Mergeable Quantile Sketches (pure Python, stdlib only)

Provides t-digest (merging variant) and DDSketch implementations so that
percentiles can be aggregated across hosts/pages/windows correctly.

Why this exists: per-host (or per-page) percentiles CANNOT be averaged --
the mean of p99s is not the p99 of the union (RESEARCH_15). The sanctioned
cross-source aggregation path is: build one sketch per source, merge the
sketches, then query quantiles on the merged sketch.
"""

import math
import sys
from typing import Any, Dict, Iterable, List, Sequence, Tuple

# CWE-400: untrusted sketch JSON must not allocate or exponentiate without bound.
MAX_TDIGEST_COMPRESSION = 10_000.0
MIN_TDIGEST_COMPRESSION = 20.0
MAX_TDIGEST_CENTROIDS = 20_000
MAX_DDSKETCH_BUCKETS = 20_000
MIN_DDSKETCH_RELATIVE_ACCURACY = 1e-4


def _require_finite(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be a finite number")
    return parsed


def _require_positive_weight(name: str, value: Any) -> float:
    parsed = _require_finite(name, value)
    if parsed <= 0.0:
        raise ValueError(f"{name} must be positive")
    return parsed


def _max_safe_bucket_index(log_gamma: float) -> int:
    """Largest |index| for which gamma**index stays finite."""
    if log_gamma <= 0.0 or not math.isfinite(log_gamma):
        raise ValueError("invalid sketch gamma")
    # Leave headroom for 2 * gamma**i / (gamma + 1) in quantile().
    return max(1, int(math.log(sys.float_info.max / 4.0) / log_gamma) - 1)


class TDigest:
    """
    t-digest quantile sketch (merging variant, Dunning & Ertl).

    Centroids are (mean, weight) pairs whose maximum weight is bounded by
    the scale function k(q) = (delta / 2*pi) * asin(2q - 1), giving high
    resolution at the distribution tails and coarse resolution in the middle.

    Supports add(), merge(), quantile(), and dict serialization; sketches
    built on different hosts merge without loss of the accuracy guarantee.

    Example:
        d = TDigest()
        for v in samples:
            d.add(v)
        d.merge(other_host_digest)
        p99 = d.quantile(0.99)
    """

    def __init__(self, compression: float = 100.0):
        """
        Args:
            compression: delta parameter; higher = more centroids = more
                accuracy and memory. Accuracy is in RANK space: with
                compression 100 the estimated quantile sits within roughly
                1 rank-percentile of the true one (tighter at the tails).
                The corresponding VALUE-space error depends on the local
                density of the distribution and can exceed 1% relative on
                heavy tails; use DDSketch when a guaranteed relative
                value-space error is required.
        """
        compression = _require_finite("compression", compression)
        if not MIN_TDIGEST_COMPRESSION <= compression <= MAX_TDIGEST_COMPRESSION:
            raise ValueError(
                f"compression must be in "
                f"[{MIN_TDIGEST_COMPRESSION:g}, {MAX_TDIGEST_COMPRESSION:g}]"
            )
        self.compression = compression
        self._centroids: List[Tuple[float, float]] = []  # (mean, weight), sorted
        self._buffer: List[Tuple[float, float]] = []
        self._buffer_limit = int(10 * compression)
        self.count = 0.0
        self.min_value = math.inf
        self.max_value = -math.inf

    def add(self, value: float, weight: float = 1.0) -> None:
        """Add a single value (optionally weighted) to the sketch."""
        value = _require_finite("value", value)
        weight = _require_positive_weight("weight", weight)
        next_count = self.count + weight
        if not math.isfinite(next_count):
            raise ValueError("weight overflow")
        self._buffer.append((value, weight))
        self.count = next_count
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)
        if len(self._buffer) >= self._buffer_limit:
            self._compress()

    def add_batch(self, values: Iterable[float]) -> None:
        """Add many values."""
        for v in values:
            self.add(v)

    def merge(self, other: "TDigest") -> None:
        """
        Merge another t-digest into this one.

        The merged sketch approximates the sketch of the concatenated
        underlying samples -- this is the only correct way to combine
        per-host percentile state (never average per-host percentiles).
        """
        other._compress()
        self._buffer.extend(other._centroids)
        self.count += other.count
        if other.count > 0:
            self.min_value = min(self.min_value, other.min_value)
            self.max_value = max(self.max_value, other.max_value)
        self._compress()

    def _k(self, q: float) -> float:
        q = min(1.0, max(0.0, q))
        return (self.compression / (2.0 * math.pi)) * math.asin(2.0 * q - 1.0)

    def _compress(self) -> None:
        if not self._buffer and len(self._centroids) <= self.compression:
            return
        points = sorted(self._centroids + self._buffer, key=lambda c: c[0])
        self._buffer = []
        if not points:
            return

        total = sum(w for _, w in points)
        merged: List[Tuple[float, float]] = []
        cur_mean, cur_weight = points[0]
        weight_so_far = 0.0
        k_lower = self._k(0.0)

        for mean, weight in points[1:]:
            q_candidate = (weight_so_far + cur_weight + weight) / total
            if self._k(q_candidate) - k_lower <= 1.0:
                new_weight = cur_weight + weight
                cur_mean = (cur_mean * cur_weight + mean * weight) / new_weight
                cur_weight = new_weight
            else:
                merged.append((cur_mean, cur_weight))
                weight_so_far += cur_weight
                k_lower = self._k(weight_so_far / total)
                cur_mean, cur_weight = mean, weight

        merged.append((cur_mean, cur_weight))
        self._centroids = merged

    def quantile(self, q: float) -> float:
        """
        Estimate the q-quantile (q in [0, 1]) via centroid interpolation.

        Raises:
            ValueError: if the sketch is empty or q out of range.
        """
        if not 0.0 <= q <= 1.0:
            raise ValueError(f"q must be in [0, 1], got {q}")
        self._compress()
        if not self._centroids or self.count <= 0:
            raise ValueError("Cannot query quantile of an empty sketch")

        if len(self._centroids) == 1:
            return self._centroids[0][0]

        target = q * self.count
        cumulative = 0.0
        prev_mean, prev_weight = self._centroids[0]
        prev_center = prev_weight / 2.0
        if target <= prev_center:
            # Interpolate between the min and the first centroid.
            frac = target / prev_center if prev_center > 0 else 0.0
            return self.min_value + frac * (prev_mean - self.min_value)

        cumulative = prev_center
        for mean, weight in self._centroids[1:]:
            center = cumulative + prev_weight / 2.0 + weight / 2.0
            if target <= center:
                frac = (target - cumulative) / (center - cumulative)
                return prev_mean + frac * (mean - prev_mean)
            cumulative = center
            prev_mean, prev_weight = mean, weight

        # Interpolate between the last centroid and the max.
        remaining = self.count - cumulative
        frac = (target - cumulative) / remaining if remaining > 0 else 1.0
        return prev_mean + min(1.0, frac) * (self.max_value - prev_mean)

    def percentile(self, pct: float) -> float:
        """Estimate a percentile (0-100)."""
        return self.quantile(pct / 100.0)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        self._compress()
        return {
            "type": "tdigest",
            "compression": self.compression,
            "count": self.count,
            "min": self.min_value if self.count else None,
            "max": self.max_value if self.count else None,
            "centroids": [[m, w] for m, w in self._centroids],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TDigest":
        """Deserialize a sketch produced by to_dict()."""
        if not isinstance(data, dict) or data.get("type") != "tdigest":
            raise ValueError("Not a serialized t-digest")
        try:
            compression = data["compression"]
            raw_centroids = data["centroids"]
        except KeyError as exc:
            raise ValueError(f"missing sketch field: {exc}") from exc
        if not isinstance(raw_centroids, list):
            raise ValueError("centroids must be a list")
        if len(raw_centroids) > MAX_TDIGEST_CENTROIDS:
            raise ValueError(
                f"centroid count exceeds {MAX_TDIGEST_CENTROIDS}"
            )

        digest = cls(compression=compression)
        parsed: List[Tuple[float, float]] = []
        weight_sum = 0.0
        for item in raw_centroids:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise ValueError("centroid must be [mean, weight]")
            mean = _require_finite("centroid mean", item[0])
            weight = _require_positive_weight("centroid weight", item[1])
            weight_sum += weight
            if not math.isfinite(weight_sum):
                raise ValueError("centroid weight overflow")
            parsed.append((mean, weight))
        parsed.sort(key=lambda c: c[0])

        if "count" in data:
            count = _require_finite("count", data["count"])
            if count < 0.0:
                raise ValueError("count must be non-negative")
            if not math.isclose(count, weight_sum, rel_tol=1e-6, abs_tol=1e-6):
                raise ValueError("count does not match centroid weights")
        digest._centroids = parsed
        digest.count = weight_sum

        if data.get("min") is not None:
            digest.min_value = _require_finite("min", data["min"])
        elif parsed:
            digest.min_value = parsed[0][0]
        if data.get("max") is not None:
            digest.max_value = _require_finite("max", data["max"])
        elif parsed:
            digest.max_value = parsed[-1][0]
        if (
            parsed
            and math.isfinite(digest.min_value)
            and math.isfinite(digest.max_value)
            and digest.min_value > digest.max_value
        ):
            raise ValueError("min must be <= max")
        return digest


class DDSketch:
    """
    DDSketch: quantile sketch with a RELATIVE-error guarantee.

    Values are placed in geometric buckets index = ceil(log_gamma(x)) with
    gamma = (1 + alpha) / (1 - alpha); any quantile estimate is within
    alpha relative error of the true value. Fully mergeable.

    Only positive values are bucketed; zeros/negatives are counted in a
    dedicated zero bucket (latencies are non-negative by nature).
    """

    def __init__(self, relative_accuracy: float = 0.01):
        relative_accuracy = _require_finite("relative_accuracy", relative_accuracy)
        if not MIN_DDSKETCH_RELATIVE_ACCURACY <= relative_accuracy < 1.0:
            raise ValueError(
                f"relative_accuracy must be in "
                f"[{MIN_DDSKETCH_RELATIVE_ACCURACY}, 1)"
            )
        self.relative_accuracy = relative_accuracy
        self._gamma = (1.0 + relative_accuracy) / (1.0 - relative_accuracy)
        self._log_gamma = math.log(self._gamma)
        self._buckets: Dict[int, float] = {}
        self._zero_count = 0.0
        self.count = 0.0

    def add(self, value: float, weight: float = 1.0) -> None:
        """Add a value to the sketch."""
        weight = _require_positive_weight("weight", weight)
        value = _require_finite("value", value)
        next_count = self.count + weight
        if not math.isfinite(next_count):
            raise ValueError("weight overflow")
        if value <= 0:
            next_zero = self._zero_count + weight
            if not math.isfinite(next_zero):
                raise ValueError("weight overflow")
            self._zero_count = next_zero
        else:
            index = math.ceil(math.log(value) / self._log_gamma)
            max_index = _max_safe_bucket_index(self._log_gamma)
            if index > max_index:
                index = max_index
            elif index < -max_index:
                index = -max_index
            if index not in self._buckets and len(self._buckets) >= MAX_DDSKETCH_BUCKETS:
                raise ValueError(f"bucket count exceeds {MAX_DDSKETCH_BUCKETS}")
            self._buckets[index] = self._buckets.get(index, 0.0) + weight
        self.count = next_count

    def add_batch(self, values: Iterable[float]) -> None:
        """Add many values."""
        for v in values:
            self.add(v)

    def merge(self, other: "DDSketch") -> None:
        """Merge another DDSketch (must share relative_accuracy)."""
        if abs(other.relative_accuracy - self.relative_accuracy) > 1e-12:
            raise ValueError("Cannot merge DDSketches with different accuracies")
        for index, weight in other._buckets.items():
            if index not in self._buckets and len(self._buckets) >= MAX_DDSKETCH_BUCKETS:
                raise ValueError(f"bucket count exceeds {MAX_DDSKETCH_BUCKETS}")
            self._buckets[index] = self._buckets.get(index, 0.0) + weight
        next_zero = self._zero_count + other._zero_count
        next_count = self.count + other.count
        if not math.isfinite(next_zero) or not math.isfinite(next_count):
            raise ValueError("weight overflow")
        self._zero_count = next_zero
        self.count = next_count

    def quantile(self, q: float) -> float:
        """Estimate the q-quantile (q in [0, 1])."""
        if not 0.0 <= q <= 1.0:
            raise ValueError(f"q must be in [0, 1], got {q}")
        if self.count <= 0:
            raise ValueError("Cannot query quantile of an empty sketch")

        rank = q * (self.count - 1)
        if rank < self._zero_count:
            return 0.0

        cumulative = self._zero_count
        for index in sorted(self._buckets):
            cumulative += self._buckets[index]
            if cumulative > rank:
                # Bucket midpoint in value space: 2*gamma^i / (gamma + 1)
                return 2.0 * self._gamma ** index / (self._gamma + 1.0)
        last_index = max(self._buckets)
        return 2.0 * self._gamma ** last_index / (self._gamma + 1.0)

    def percentile(self, pct: float) -> float:
        """Estimate a percentile (0-100)."""
        return self.quantile(pct / 100.0)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "type": "ddsketch",
            "relative_accuracy": self.relative_accuracy,
            "zero_count": self._zero_count,
            "count": self.count,
            "buckets": {str(k): v for k, v in self._buckets.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DDSketch":
        """Deserialize a sketch produced by to_dict()."""
        if not isinstance(data, dict) or data.get("type") != "ddsketch":
            raise ValueError("Not a serialized DDSketch")
        try:
            relative_accuracy = data["relative_accuracy"]
            raw_buckets = data["buckets"]
        except KeyError as exc:
            raise ValueError(f"missing sketch field: {exc}") from exc
        if not isinstance(raw_buckets, dict):
            raise ValueError("buckets must be an object")
        if len(raw_buckets) > MAX_DDSKETCH_BUCKETS:
            raise ValueError(f"bucket count exceeds {MAX_DDSKETCH_BUCKETS}")

        sketch = cls(relative_accuracy=relative_accuracy)
        max_index = _max_safe_bucket_index(sketch._log_gamma)
        parsed: Dict[int, float] = {}
        weight_sum = 0.0
        for key, raw_weight in raw_buckets.items():
            if isinstance(key, bool):
                raise ValueError("invalid bucket index")
            if isinstance(key, str) and len(key) > 32:
                raise ValueError("bucket index too large")
            try:
                index = int(key)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid bucket index: {key!r}") from exc
            if index > max_index:
                index = max_index
            elif index < -max_index:
                index = -max_index
            weight = _require_positive_weight("bucket weight", raw_weight)
            weight_sum += weight
            if not math.isfinite(weight_sum):
                raise ValueError("bucket weight overflow")
            parsed[index] = parsed.get(index, 0.0) + weight

        zero_count = _require_finite("zero_count", data.get("zero_count", 0.0))
        if zero_count < 0.0:
            raise ValueError("zero_count must be non-negative")
        weight_sum += zero_count
        if not math.isfinite(weight_sum):
            raise ValueError("bucket weight overflow")

        if "count" in data:
            count = _require_finite("count", data["count"])
            if count < 0.0:
                raise ValueError("count must be non-negative")
            if not math.isclose(count, weight_sum, rel_tol=1e-6, abs_tol=1e-6):
                raise ValueError("count does not match bucket weights")
        sketch._buckets = parsed
        sketch._zero_count = zero_count
        sketch.count = weight_sum
        return sketch


def sketch_from_values(
    values: Sequence[float],
    compression: float = 100.0,
) -> TDigest:
    """Build a t-digest from raw samples."""
    digest = TDigest(compression=compression)
    digest.add_batch(values)
    return digest
