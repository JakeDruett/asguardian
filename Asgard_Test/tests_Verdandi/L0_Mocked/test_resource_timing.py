"""
Unit tests for ResourceTimingCalculator.
"""

import pytest

from Asgard.Verdandi.Web import ResourceTimingCalculator
from Asgard.Verdandi.Web.models.web_models import ResourceTimingInput


class TestResourceTimingCalculator:
    """Tests for ResourceTimingCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = ResourceTimingCalculator()

    def test_analyze_empty_resources(self):
        """Test analysis with empty resource list."""
        result = self.calculator.analyze([])

        assert result.total_resources == 0
        assert result.total_transfer_bytes == 0
        assert result.total_duration_ms == 0
        assert result.cache_hit_rate == 0
        assert len(result.recommendations) == 0

    def test_analyze_single_resource(self):
        """Test analysis with single resource."""
        resources = [
            ResourceTimingInput(
                name="main.js",
                initiator_type="script",
                start_time_ms=100,
                duration_ms=250,
                transfer_size_bytes=50000,
                encoded_body_size_bytes=50000,
                decoded_body_size_bytes=150000,
            )
        ]

        result = self.calculator.analyze(resources)

        assert result.total_resources == 1
        assert result.total_transfer_bytes == 50000
        assert result.total_duration_ms == 350

    def test_group_by_type(self):
        """Test grouping resources by type."""
        resources = [
            ResourceTimingInput(
                name="main.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=100,
                transfer_size_bytes=50000,
                encoded_body_size_bytes=50000,
                decoded_body_size_bytes=50000,
            ),
            ResourceTimingInput(
                name="util.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=150,
                transfer_size_bytes=30000,
                encoded_body_size_bytes=30000,
                decoded_body_size_bytes=30000,
            ),
            ResourceTimingInput(
                name="image.jpg",
                initiator_type="img",
                start_time_ms=0,
                duration_ms=200,
                transfer_size_bytes=100000,
                encoded_body_size_bytes=100000,
                decoded_body_size_bytes=100000,
            ),
        ]

        result = self.calculator.analyze(resources)

        assert "script" in result.by_type
        assert "img" in result.by_type
        assert result.by_type["script"]["count"] == 2
        assert result.by_type["script"]["total_bytes"] == 80000
        assert result.by_type["script"]["avg_duration_ms"] == 125
        assert result.by_type["img"]["count"] == 1

    def test_find_largest_resources(self):
        """Test finding largest resources by size."""
        resources = [
            ResourceTimingInput(
                name="small.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=50,
                transfer_size_bytes=10000,
                encoded_body_size_bytes=10000,
                decoded_body_size_bytes=10000,
            ),
            ResourceTimingInput(
                name="large.jpg",
                initiator_type="img",
                start_time_ms=0,
                duration_ms=100,
                transfer_size_bytes=500000,
                encoded_body_size_bytes=500000,
                decoded_body_size_bytes=500000,
            ),
            ResourceTimingInput(
                name="medium.css",
                initiator_type="link",
                start_time_ms=0,
                duration_ms=75,
                transfer_size_bytes=50000,
                encoded_body_size_bytes=50000,
                decoded_body_size_bytes=50000,
            ),
        ]

        result = self.calculator.analyze(resources)

        assert len(result.largest_resources) == 3
        assert result.largest_resources[0]["name"] == "large.jpg"
        assert result.largest_resources[0]["size_bytes"] == 500000

    def test_find_slowest_resources(self):
        """Test finding slowest resources by duration."""
        resources = [
            ResourceTimingInput(
                name="fast.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=50,
                transfer_size_bytes=10000,
                encoded_body_size_bytes=10000,
                decoded_body_size_bytes=10000,
            ),
            ResourceTimingInput(
                name="slow.jpg",
                initiator_type="img",
                start_time_ms=0,
                duration_ms=2000,
                transfer_size_bytes=100000,
                encoded_body_size_bytes=100000,
                decoded_body_size_bytes=100000,
            ),
            ResourceTimingInput(
                name="medium.css",
                initiator_type="link",
                start_time_ms=0,
                duration_ms=500,
                transfer_size_bytes=50000,
                encoded_body_size_bytes=50000,
                decoded_body_size_bytes=50000,
            ),
        ]

        result = self.calculator.analyze(resources)

        assert len(result.slowest_resources) == 3
        assert result.slowest_resources[0]["name"] == "slow.jpg"
        assert result.slowest_resources[0]["duration_ms"] == 2000

    def test_find_blocking_resources(self):
        """Test identifying render-blocking resources."""
        resources = [
            ResourceTimingInput(
                name="critical.js",
                initiator_type="script",
                start_time_ms=100,
                duration_ms=50,
                transfer_size_bytes=10000,
                encoded_body_size_bytes=10000,
                decoded_body_size_bytes=10000,
            ),
            ResourceTimingInput(
                name="non-blocking.js",
                initiator_type="script",
                start_time_ms=1000,
                duration_ms=50,
                transfer_size_bytes=10000,
                encoded_body_size_bytes=10000,
                decoded_body_size_bytes=10000,
            ),
            ResourceTimingInput(
                name="critical.css",
                initiator_type="link",
                start_time_ms=50,
                duration_ms=100,
                transfer_size_bytes=20000,
                encoded_body_size_bytes=20000,
                decoded_body_size_bytes=20000,
            ),
        ]

        result = self.calculator.analyze(resources)

        assert "critical.js" in result.blocking_resources
        assert "critical.css" in result.blocking_resources
        assert "non-blocking.js" not in result.blocking_resources

    def test_calculate_cache_hit_rate_all_cached(self):
        """Test cache hit rate with all resources cached."""
        resources = [
            ResourceTimingInput(
                name="cached1.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=10,
                transfer_size_bytes=0,
                encoded_body_size_bytes=50000,
                decoded_body_size_bytes=50000,
            ),
            ResourceTimingInput(
                name="cached2.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=10,
                transfer_size_bytes=0,
                encoded_body_size_bytes=30000,
                decoded_body_size_bytes=30000,
            ),
        ]

        result = self.calculator.analyze(resources)

        assert result.cache_hit_rate == 100.0

    def test_calculate_cache_hit_rate_none_cached(self):
        """Test cache hit rate with no cached resources."""
        resources = [
            ResourceTimingInput(
                name="fresh1.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=100,
                transfer_size_bytes=50000,
                encoded_body_size_bytes=50000,
                decoded_body_size_bytes=50000,
            ),
            ResourceTimingInput(
                name="fresh2.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=100,
                transfer_size_bytes=30000,
                encoded_body_size_bytes=30000,
                decoded_body_size_bytes=30000,
            ),
        ]

        result = self.calculator.analyze(resources)

        assert result.cache_hit_rate == 0.0

    def test_calculate_cache_hit_rate_partial(self):
        """Test cache hit rate with partial caching."""
        resources = [
            ResourceTimingInput(
                name="cached.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=10,
                transfer_size_bytes=0,
                encoded_body_size_bytes=50000,
                decoded_body_size_bytes=50000,
            ),
            ResourceTimingInput(
                name="fresh.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=100,
                transfer_size_bytes=30000,
                encoded_body_size_bytes=30000,
                decoded_body_size_bytes=30000,
            ),
            ResourceTimingInput(
                name="revalidated.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=50,
                transfer_size_bytes=300,
                encoded_body_size_bytes=30000,
                decoded_body_size_bytes=30000,
            ),
        ]

        result = self.calculator.analyze(resources)

        assert 50 <= result.cache_hit_rate <= 100

    def test_recommendations_many_blocking_resources(self):
        """Test recommendations when many render-blocking resources exist."""
        resources = [
            ResourceTimingInput(
                name=f"script{i}.js",
                initiator_type="script",
                start_time_ms=i * 10,
                duration_ms=50,
                transfer_size_bytes=10000,
                encoded_body_size_bytes=10000,
                decoded_body_size_bytes=10000,
            )
            for i in range(5)
        ]

        result = self.calculator.analyze(resources)

        assert any("blocking" in rec.lower() for rec in result.recommendations)

    def test_recommendations_large_resource(self):
        """Test recommendations for large resources."""
        resources = [
            ResourceTimingInput(
                name="huge.jpg",
                initiator_type="img",
                start_time_ms=0,
                duration_ms=100,
                transfer_size_bytes=1000000,
                encoded_body_size_bytes=1000000,
                decoded_body_size_bytes=1000000,
            ),
        ]

        result = self.calculator.analyze(resources)

        assert any("large" in rec.lower() or "compression" in rec.lower() for rec in result.recommendations)

    def test_recommendations_slow_resource(self):
        """Test recommendations for slow resources."""
        resources = [
            ResourceTimingInput(
                name="slow.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=5000,
                transfer_size_bytes=10000,
                encoded_body_size_bytes=10000,
                decoded_body_size_bytes=10000,
            ),
        ]

        result = self.calculator.analyze(resources)

        assert any("slow" in rec.lower() for rec in result.recommendations)

    def test_recommendations_low_cache_hit(self):
        """Test recommendations for low cache hit rate."""
        resources = [
            ResourceTimingInput(
                name=f"fresh{i}.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=100,
                transfer_size_bytes=50000,
                encoded_body_size_bytes=50000,
                decoded_body_size_bytes=50000,
            )
            for i in range(10)
        ]

        result = self.calculator.analyze(resources)

        assert any("cache" in rec.lower() for rec in result.recommendations)

    def test_recommendations_many_images(self):
        """Test recommendations when images are heavy."""
        resources = [
            ResourceTimingInput(
                name=f"image{i}.jpg",
                initiator_type="img",
                start_time_ms=0,
                duration_ms=100,
                transfer_size_bytes=200000,
                encoded_body_size_bytes=200000,
                decoded_body_size_bytes=200000,
            )
            for i in range(10)
        ]

        result = self.calculator.analyze(resources)

        assert any("image" in rec.lower() or "webp" in rec.lower() for rec in result.recommendations)

    def test_recommendations_too_many_resources(self):
        """Test recommendations when too many resources are loaded."""
        resources = [
            ResourceTimingInput(
                name=f"resource{i}.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=50,
                transfer_size_bytes=10000,
                encoded_body_size_bytes=10000,
                decoded_body_size_bytes=10000,
            )
            for i in range(150)
        ]

        result = self.calculator.analyze(resources)

        assert any("bundling" in rec.lower() or "lazy" in rec.lower() for rec in result.recommendations)

    def test_no_recommendations_optimal_page(self):
        """Test no recommendations for well-optimized page."""
        resources = [
            ResourceTimingInput(
                name="cached.js",
                initiator_type="script",
                start_time_ms=600,
                duration_ms=50,
                transfer_size_bytes=0,
                encoded_body_size_bytes=30000,
                decoded_body_size_bytes=30000,
            ),
            ResourceTimingInput(
                name="small.css",
                initiator_type="link",
                start_time_ms=600,
                duration_ms=30,
                transfer_size_bytes=5000,
                encoded_body_size_bytes=5000,
                decoded_body_size_bytes=5000,
            ),
        ]

        result = self.calculator.analyze(resources)

        assert len(result.recommendations) == 0

    def test_total_duration_calculation(self):
        """Test that total duration is calculated as max end time."""
        resources = [
            ResourceTimingInput(
                name="first.js",
                initiator_type="script",
                start_time_ms=100,
                duration_ms=200,
                transfer_size_bytes=10000,
                encoded_body_size_bytes=10000,
                decoded_body_size_bytes=10000,
            ),
            ResourceTimingInput(
                name="second.js",
                initiator_type="script",
                start_time_ms=500,
                duration_ms=600,
                transfer_size_bytes=20000,
                encoded_body_size_bytes=20000,
                decoded_body_size_bytes=20000,
            ),
        ]

        result = self.calculator.analyze(resources)

        assert result.total_duration_ms == 1100

    def test_largest_resources_limit(self):
        """Test that largest resources list is limited to top 5."""
        resources = [
            ResourceTimingInput(
                name=f"file{i}.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=50,
                transfer_size_bytes=i * 10000,
                encoded_body_size_bytes=i * 10000,
                decoded_body_size_bytes=i * 10000,
            )
            for i in range(1, 11)
        ]

        result = self.calculator.analyze(resources)

        assert len(result.largest_resources) == 5
        assert result.largest_resources[0]["size_bytes"] == 90000

    def test_slowest_resources_limit(self):
        """Test that slowest resources list is limited to top 5."""
        resources = [
            ResourceTimingInput(
                name=f"file{i}.js",
                initiator_type="script",
                start_time_ms=0,
                duration_ms=i * 100,
                transfer_size_bytes=10000,
                encoded_body_size_bytes=10000,
                decoded_body_size_bytes=10000,
            )
            for i in range(1, 11)
        ]

        result = self.calculator.analyze(resources)

        assert len(result.slowest_resources) == 5
        assert result.slowest_resources[0]["duration_ms"] == 1000
