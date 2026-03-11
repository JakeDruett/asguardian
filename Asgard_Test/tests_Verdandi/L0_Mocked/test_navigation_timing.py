"""
Unit tests for NavigationTimingCalculator.
"""

import pytest

from Asgard.Verdandi.Web import NavigationTimingCalculator
from Asgard.Verdandi.Web.models.web_models import NavigationTimingInput


class TestNavigationTimingCalculator:
    """Tests for NavigationTimingCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = NavigationTimingCalculator()

    def test_calculate_basic_navigation(self):
        """Test basic navigation timing calculation."""
        input_data = NavigationTimingInput(
            dns_start_ms=0,
            dns_end_ms=10,
            connect_start_ms=10,
            connect_end_ms=30,
            request_start_ms=30,
            response_start_ms=150,
            response_end_ms=250,
            dom_interactive_ms=250,
            dom_complete_ms=400,
            load_event_start_ms=400,
            load_event_end_ms=450,
        )

        result = self.calculator.calculate(input_data)

        assert result.dns_lookup_ms == 10
        assert result.tcp_connection_ms == 20
        assert result.ttfb_ms == 120
        assert result.content_download_ms == 100
        assert result.dom_processing_ms == 150
        assert result.page_load_ms == 450
        assert result.backend_time_ms == 150
        assert result.frontend_time_ms == 200

    def test_calculate_with_ssl(self):
        """Test navigation timing with SSL handshake."""
        input_data = NavigationTimingInput(
            dns_start_ms=0,
            dns_end_ms=5,
            connect_start_ms=5,
            connect_end_ms=20,
            ssl_start_ms=20,
            ssl_end_ms=50,
            request_start_ms=50,
            response_start_ms=100,
            response_end_ms=150,
            dom_interactive_ms=150,
            dom_complete_ms=200,
            load_event_start_ms=200,
            load_event_end_ms=220,
        )

        result = self.calculator.calculate(input_data)

        assert result.dns_lookup_ms == 5
        assert result.tcp_connection_ms == 15
        assert result.ssl_handshake_ms == 30
        assert result.ttfb_ms == 50
        assert result.backend_time_ms == 100

    def test_calculate_without_ssl(self):
        """Test navigation timing without SSL (HTTP)."""
        input_data = NavigationTimingInput(
            dns_start_ms=0,
            dns_end_ms=8,
            connect_start_ms=8,
            connect_end_ms=25,
            request_start_ms=25,
            response_start_ms=75,
            response_end_ms=125,
            dom_interactive_ms=125,
            dom_complete_ms=180,
            load_event_start_ms=180,
            load_event_end_ms=200,
        )

        result = self.calculator.calculate(input_data)

        assert result.ssl_handshake_ms is None
        assert result.dns_lookup_ms == 8
        assert result.tcp_connection_ms == 17

    def test_identify_bottleneck_ttfb(self):
        """Test bottleneck identification when TTFB is slowest."""
        input_data = NavigationTimingInput(
            dns_start_ms=0,
            dns_end_ms=5,
            connect_start_ms=5,
            connect_end_ms=15,
            request_start_ms=15,
            response_start_ms=815,
            response_end_ms=865,
            dom_interactive_ms=865,
            dom_complete_ms=900,
            load_event_start_ms=900,
            load_event_end_ms=920,
        )

        result = self.calculator.calculate(input_data)

        assert result.bottleneck == "TTFB (Server Response)"

    def test_identify_bottleneck_frontend(self):
        """Test bottleneck identification when frontend rendering is slowest."""
        input_data = NavigationTimingInput(
            dns_start_ms=0,
            dns_end_ms=5,
            connect_start_ms=5,
            connect_end_ms=15,
            request_start_ms=15,
            response_start_ms=65,
            response_end_ms=115,
            dom_interactive_ms=115,
            dom_complete_ms=150,
            load_event_start_ms=150,
            load_event_end_ms=1650,
        )

        result = self.calculator.calculate(input_data)

        assert result.bottleneck == "Frontend Rendering"

    def test_identify_bottleneck_dns(self):
        """Test bottleneck identification when DNS is slowest."""
        input_data = NavigationTimingInput(
            dns_start_ms=0,
            dns_end_ms=200,
            connect_start_ms=200,
            connect_end_ms=210,
            request_start_ms=210,
            response_start_ms=220,
            response_end_ms=230,
            dom_interactive_ms=230,
            dom_complete_ms=240,
            load_event_start_ms=240,
            load_event_end_ms=250,
        )

        result = self.calculator.calculate(input_data)

        assert result.bottleneck == "DNS Lookup"

    def test_recommendations_slow_dns(self):
        """Test recommendations when DNS is slow."""
        input_data = NavigationTimingInput(
            dns_start_ms=0,
            dns_end_ms=100,
            connect_start_ms=100,
            connect_end_ms=110,
            request_start_ms=110,
            response_start_ms=120,
            response_end_ms=130,
            dom_interactive_ms=130,
            dom_complete_ms=140,
            load_event_start_ms=140,
            load_event_end_ms=150,
        )

        result = self.calculator.calculate(input_data)

        assert len(result.recommendations) > 0
        assert any("DNS" in rec or "dns" in rec.lower() for rec in result.recommendations)

    def test_recommendations_slow_ttfb(self):
        """Test recommendations when TTFB is high."""
        input_data = NavigationTimingInput(
            dns_start_ms=0,
            dns_end_ms=10,
            connect_start_ms=10,
            connect_end_ms=20,
            request_start_ms=20,
            response_start_ms=720,
            response_end_ms=730,
            dom_interactive_ms=730,
            dom_complete_ms=740,
            load_event_start_ms=740,
            load_event_end_ms=750,
        )

        result = self.calculator.calculate(input_data)

        assert len(result.recommendations) > 0
        assert any("TTFB" in rec for rec in result.recommendations)

    def test_recommendations_slow_ssl(self):
        """Test recommendations when SSL handshake is slow."""
        input_data = NavigationTimingInput(
            dns_start_ms=0,
            dns_end_ms=5,
            connect_start_ms=5,
            connect_end_ms=15,
            ssl_start_ms=15,
            ssl_end_ms=165,
            request_start_ms=165,
            response_start_ms=175,
            response_end_ms=185,
            dom_interactive_ms=185,
            dom_complete_ms=195,
            load_event_start_ms=195,
            load_event_end_ms=205,
        )

        result = self.calculator.calculate(input_data)

        assert any("SSL" in rec or "TLS" in rec for rec in result.recommendations)

    def test_recommendations_slow_download(self):
        """Test recommendations when content download is slow."""
        input_data = NavigationTimingInput(
            dns_start_ms=0,
            dns_end_ms=5,
            connect_start_ms=5,
            connect_end_ms=15,
            request_start_ms=15,
            response_start_ms=65,
            response_end_ms=665,
            dom_interactive_ms=665,
            dom_complete_ms=675,
            load_event_start_ms=675,
            load_event_end_ms=685,
        )

        result = self.calculator.calculate(input_data)

        assert any("download" in rec.lower() or "compression" in rec.lower() for rec in result.recommendations)

    def test_recommendations_slow_dom(self):
        """Test recommendations when DOM processing is slow."""
        input_data = NavigationTimingInput(
            dns_start_ms=0,
            dns_end_ms=5,
            connect_start_ms=5,
            connect_end_ms=15,
            request_start_ms=15,
            response_start_ms=65,
            response_end_ms=115,
            dom_interactive_ms=115,
            dom_complete_ms=715,
            load_event_start_ms=715,
            load_event_end_ms=725,
        )

        result = self.calculator.calculate(input_data)

        assert any("DOM" in rec for rec in result.recommendations)

    def test_no_recommendations_fast_page(self):
        """Test no recommendations for fast page load."""
        input_data = NavigationTimingInput(
            dns_start_ms=0,
            dns_end_ms=5,
            connect_start_ms=5,
            connect_end_ms=15,
            request_start_ms=15,
            response_start_ms=65,
            response_end_ms=115,
            dom_interactive_ms=115,
            dom_complete_ms=165,
            load_event_start_ms=165,
            load_event_end_ms=185,
        )

        result = self.calculator.calculate(input_data)

        assert len(result.recommendations) == 0

    def test_rounding_precision(self):
        """Test that values are rounded to 2 decimal places."""
        input_data = NavigationTimingInput(
            dns_start_ms=0,
            dns_end_ms=10.123456,
            connect_start_ms=10.123456,
            connect_end_ms=30.987654,
            request_start_ms=30.987654,
            response_start_ms=150.555555,
            response_end_ms=250.777777,
            dom_interactive_ms=250.777777,
            dom_complete_ms=400.999999,
            load_event_start_ms=400.999999,
            load_event_end_ms=450.123456,
        )

        result = self.calculator.calculate(input_data)

        assert result.dns_lookup_ms == pytest.approx(10.12, abs=0.01)
        assert result.tcp_connection_ms == pytest.approx(20.86, abs=0.01)

    def test_zero_values(self):
        """Test handling of zero-duration phases."""
        input_data = NavigationTimingInput(
            dns_start_ms=0,
            dns_end_ms=0,
            connect_start_ms=0,
            connect_end_ms=0,
            request_start_ms=0,
            response_start_ms=100,
            response_end_ms=100,
            dom_interactive_ms=100,
            dom_complete_ms=100,
            load_event_start_ms=100,
            load_event_end_ms=100,
        )

        result = self.calculator.calculate(input_data)

        assert result.dns_lookup_ms == 0
        assert result.tcp_connection_ms == 0
        assert result.content_download_ms == 0

    def test_complex_real_world_scenario(self):
        """Test with realistic timing values."""
        input_data = NavigationTimingInput(
            dns_start_ms=0,
            dns_end_ms=23,
            connect_start_ms=23,
            connect_end_ms=145,
            ssl_start_ms=145,
            ssl_end_ms=267,
            request_start_ms=267,
            response_start_ms=512,
            response_end_ms=1894,
            dom_interactive_ms=1894,
            dom_complete_ms=2345,
            load_event_start_ms=2345,
            load_event_end_ms=2678,
        )

        result = self.calculator.calculate(input_data)

        assert result.dns_lookup_ms == 23
        assert result.tcp_connection_ms == 122
        assert result.ssl_handshake_ms == 122
        assert result.ttfb_ms == 245
        assert result.content_download_ms == 1382
        assert result.dom_processing_ms == 451
        assert result.page_load_ms == 2678
        assert result.bottleneck in ["Content Download", "DOM Processing"]
