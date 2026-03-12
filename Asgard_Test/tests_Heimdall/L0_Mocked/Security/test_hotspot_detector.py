"""
Tests for Heimdall Hotspot Detector Service

Unit tests for security hotspot detection. Tests write real Python code to
temporary files and run the HotspotDetector against them.
"""

import tempfile
from pathlib import Path

import pytest

from Asgard.Heimdall.Security.Hotspots.models.hotspot_models import (
    HotspotCategory,
    HotspotConfig,
    HotspotReport,
    ReviewPriority,
    ReviewStatus,
    SecurityHotspot,
)
from Asgard.Heimdall.Security.Hotspots.services.hotspot_detector import HotspotDetector


class TestHotspotDetectorInitialization:
    """Tests for HotspotDetector initialization."""

    def test_default_initialization(self):
        """Test that detector initializes with default config."""
        detector = HotspotDetector()
        assert detector.config is not None

    def test_custom_config_initialization(self):
        """Test that detector accepts a custom config."""
        config = HotspotConfig(min_priority=ReviewPriority.HIGH)
        detector = HotspotDetector(config=config)
        assert detector.config.min_priority == ReviewPriority.HIGH.value

    def test_scan_nonexistent_path_raises(self):
        """Test that scanning a nonexistent path raises FileNotFoundError."""
        detector = HotspotDetector()
        with pytest.raises(FileNotFoundError):
            detector.scan(Path("/nonexistent/path/that/does/not/exist"))


class TestHotspotDetectorEmptyInputs:
    """Tests for edge cases with empty or minimal inputs."""

    def test_empty_directory_returns_empty_report(self):
        """Test that an empty directory yields a report with zero hotspots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = HotspotDetector()
            report = detector.scan(Path(tmpdir))

            assert report.total_hotspots == 0
            assert report.hotspots == []

    def test_empty_file_returns_empty_report(self):
        """Test that an empty Python file yields no hotspots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "empty.py").write_text("")

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            assert report.total_hotspots == 0

    def test_scan_returns_hotspot_report_type(self):
        """Test that scan always returns a HotspotReport."""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = HotspotDetector()
            report = detector.scan(Path(tmpdir))

            assert isinstance(report, HotspotReport)


class TestDynamicCodeExecutionDetection:
    """Tests for DYNAMIC_EXECUTION hotspot detection."""

    def test_eval_usage_detected(self):
        """Test that eval() usage is detected as a DYNAMIC_EXECUTION hotspot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "code.py").write_text(
                "def run_code(user_input):\n"
                "    result = eval(user_input)\n"
                "    return result\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            assert report.total_hotspots > 0
            categories = [h.category for h in report.hotspots]
            assert HotspotCategory.DYNAMIC_EXECUTION.value in categories

    def test_exec_usage_detected(self):
        """Test that exec() usage is detected as a DYNAMIC_EXECUTION hotspot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "exec_code.py").write_text(
                "def execute_code(script):\n"
                "    exec(script)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            dynamic_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.DYNAMIC_EXECUTION.value
            ]
            assert len(dynamic_hotspots) > 0

    def test_eval_hotspot_has_high_priority(self):
        """Test that eval() hotspot has HIGH review priority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "eval_code.py").write_text(
                "x = eval(user_data)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            dynamic_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.DYNAMIC_EXECUTION.value
            ]
            assert len(dynamic_hotspots) > 0
            assert dynamic_hotspots[0].review_priority == ReviewPriority.HIGH.value

    def test_eval_hotspot_has_owasp_category(self):
        """Test that eval() hotspot includes OWASP category reference."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "eval_use.py").write_text(
                "result = eval(expression)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            dynamic_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.DYNAMIC_EXECUTION.value
            ]
            assert len(dynamic_hotspots) > 0
            assert dynamic_hotspots[0].owasp_category is not None
            assert dynamic_hotspots[0].cwe_id is not None


class TestInsecureDeserializationDetection:
    """Tests for INSECURE_DESERIALIZATION hotspot detection."""

    def test_pickle_loads_detected(self):
        """Test that pickle.loads() is detected as INSECURE_DESERIALIZATION hotspot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "deser.py").write_text(
                "import pickle\n"
                "\n"
                "def load_data(raw_bytes):\n"
                "    obj = pickle.loads(raw_bytes)\n"
                "    return obj\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            deser_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.INSECURE_DESERIALIZATION.value
            ]
            assert len(deser_hotspots) > 0

    def test_pickle_load_detected(self):
        """Test that pickle.load() is detected as INSECURE_DESERIALIZATION hotspot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "pickle_load.py").write_text(
                "import pickle\n"
                "\n"
                "def read_pickle(f):\n"
                "    return pickle.load(f)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            deser_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.INSECURE_DESERIALIZATION.value
            ]
            assert len(deser_hotspots) > 0

    def test_pickle_hotspot_has_high_priority(self):
        """Test that pickle.loads() hotspot has HIGH priority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "pickle_use.py").write_text(
                "import pickle\n"
                "data = pickle.loads(raw)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            deser_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.INSECURE_DESERIALIZATION.value
            ]
            assert len(deser_hotspots) > 0
            assert deser_hotspots[0].review_priority == ReviewPriority.HIGH.value

    def test_yaml_load_without_safe_loader_detected(self):
        """Test that yaml.load() without SafeLoader is detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "yaml_parse.py").write_text(
                "import yaml\n"
                "\n"
                "def parse_config(data):\n"
                "    return yaml.load(data)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            deser_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.INSECURE_DESERIALIZATION.value
            ]
            assert len(deser_hotspots) > 0

    def test_yaml_safe_load_not_detected(self):
        """Test that yaml.safe_load() does NOT trigger an INSECURE_DESERIALIZATION hotspot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "safe_yaml.py").write_text(
                "import yaml\n"
                "\n"
                "def parse_config(data):\n"
                "    return yaml.safe_load(data)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            deser_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.INSECURE_DESERIALIZATION.value
            ]
            assert len(deser_hotspots) == 0

    def test_yaml_load_with_safe_loader_not_detected(self):
        """Test that yaml.load() with Loader=yaml.SafeLoader is not flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "safe_yaml2.py").write_text(
                "import yaml\n"
                "\n"
                "def parse_config(data):\n"
                "    return yaml.load(data, Loader=yaml.SafeLoader)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            deser_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.INSECURE_DESERIALIZATION.value
            ]
            assert len(deser_hotspots) == 0


class TestSSRFDetection:
    """Tests for SSRF hotspot detection."""

    def test_requests_get_with_variable_url_detected(self):
        """Test that requests.get() with a variable URL argument is detected as SSRF."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "api_call.py").write_text(
                "import requests\n"
                "\n"
                "def fetch(url):\n"
                "    response = requests.get(url)\n"
                "    return response.text\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            ssrf_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.SSRF.value
            ]
            assert len(ssrf_hotspots) > 0

    def test_requests_post_with_variable_url_detected(self):
        """Test that requests.post() with a variable URL is detected as SSRF."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "post_call.py").write_text(
                "import requests\n"
                "\n"
                "def send_data(endpoint):\n"
                "    requests.post(endpoint, json={'key': 'value'})\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            ssrf_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.SSRF.value
            ]
            assert len(ssrf_hotspots) > 0

    def test_ssrf_hotspot_has_high_priority(self):
        """Test that SSRF hotspots have HIGH review priority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "ssrf_code.py").write_text(
                "import requests\n"
                "resp = requests.get(target_url)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            ssrf_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.SSRF.value
            ]
            assert len(ssrf_hotspots) > 0
            assert ssrf_hotspots[0].review_priority == ReviewPriority.HIGH.value

    def test_requests_get_with_literal_url_not_ssrf(self):
        """Test that requests.get() with a string literal URL does not trigger SSRF."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "safe_call.py").write_text(
                "import requests\n"
                "\n"
                "def fetch_api():\n"
                "    return requests.get('https://api.example.com/data')\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            ssrf_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.SSRF.value
            ]
            assert len(ssrf_hotspots) == 0


class TestCryptoUsageDetection:
    """Tests for CRYPTO_USAGE hotspot detection."""

    def test_hashlib_import_detected(self):
        """Test that importing hashlib is detected as a CRYPTO_USAGE hotspot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "crypto_code.py").write_text(
                "import hashlib\n"
                "\n"
                "def hash_password(password):\n"
                "    return hashlib.md5(password.encode()).hexdigest()\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            crypto_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.CRYPTO_USAGE.value
            ]
            assert len(crypto_hotspots) > 0

    def test_crypto_hotspot_has_low_priority(self):
        """Test that cryptographic import hotspots have LOW review priority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "hmac_use.py").write_text(
                "import hmac\n"
                "\n"
                "key = b'secret'\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            crypto_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.CRYPTO_USAGE.value
            ]
            assert len(crypto_hotspots) > 0
            assert crypto_hotspots[0].review_priority == ReviewPriority.LOW.value

    def test_cryptography_import_from_detected(self):
        """Test that from cryptography import ... is detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "crypto_from.py").write_text(
                "from cryptography.fernet import Fernet\n"
                "\n"
                "key = Fernet.generate_key()\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            crypto_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.CRYPTO_USAGE.value
            ]
            assert len(crypto_hotspots) > 0


class TestCleanCodeProducesNoHotspots:
    """Tests that clean code does not produce false positives."""

    def test_clean_code_no_hotspots(self):
        """Test that code with no security-sensitive patterns yields no hotspots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "clean.py").write_text(
                "def add(a, b):\n"
                "    return a + b\n"
                "\n"
                "def greet(name):\n"
                "    return f'Hello, {name}'\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            assert report.total_hotspots == 0


class TestReviewPriorityClassification:
    """Tests for review priority classification."""

    def test_high_priority_hotspots_counted(self):
        """Test that HIGH priority hotspots are counted correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "high_risk.py").write_text(
                "import pickle\n"
                "data = pickle.loads(raw_bytes)\n"
                "result = eval(expression)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            assert report.high_priority_count > 0

    def test_medium_priority_hotspots_counted(self):
        """Test that MEDIUM priority hotspots are counted correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "medium_risk.py").write_text(
                "import random\n"
                "\n"
                "token = random.randint(0, 999999)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            assert report.medium_priority_count > 0

    def test_low_priority_hotspots_counted(self):
        """Test that LOW priority hotspots are counted correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "low_risk.py").write_text(
                "import hashlib\n"
                "\n"
                "digest = hashlib.sha256(data).hexdigest()\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            assert report.low_priority_count > 0

    def test_min_priority_filter_excludes_low(self):
        """Test that min_priority=HIGH excludes LOW and MEDIUM hotspots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # hashlib import triggers LOW; no HIGH hotspots
            (tmpdir_path / "low_only.py").write_text(
                "import hashlib\n"
                "digest = hashlib.sha256(b'data').hexdigest()\n"
            )

            config = HotspotConfig(min_priority=ReviewPriority.HIGH)
            detector = HotspotDetector(config=config)
            report = detector.scan(tmpdir_path)

            # All returned hotspots must be HIGH
            for hotspot in report.hotspots:
                assert hotspot.review_priority == ReviewPriority.HIGH.value

    def test_min_priority_high_still_reports_high_hotspots(self):
        """Test that min_priority=HIGH still reports HIGH hotspots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "eval_use.py").write_text(
                "result = eval(user_input)\n"
            )

            config = HotspotConfig(min_priority=ReviewPriority.HIGH)
            detector = HotspotDetector(config=config)
            report = detector.scan(tmpdir_path)

            assert report.total_hotspots > 0


class TestHotspotReportMetadata:
    """Tests for hotspot report metadata and structure."""

    def test_report_scan_path_set(self):
        """Test that the report records the scan path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            assert str(tmpdir_path) in report.scan_path

    def test_report_scan_duration_non_negative(self):
        """Test that scan duration is a non-negative float."""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = HotspotDetector()
            report = detector.scan(Path(tmpdir))

            assert report.scan_duration_seconds >= 0.0

    def test_hotspot_includes_code_snippet(self):
        """Test that detected hotspots include a code snippet."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "eval_use.py").write_text(
                "x = eval(code)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            assert report.total_hotspots > 0
            for hotspot in report.hotspots:
                assert hotspot.code_snippet != ""

    def test_hotspot_includes_review_guidance(self):
        """Test that hotspots include review guidance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "pickle_use.py").write_text(
                "import pickle\n"
                "data = pickle.loads(raw)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            deser_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.INSECURE_DESERIALIZATION.value
            ]
            assert len(deser_hotspots) > 0
            assert deser_hotspots[0].review_guidance != ""

    def test_hotspot_review_status_defaults_to_to_review(self):
        """Test that newly detected hotspots have TO_REVIEW status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "eval_use.py").write_text(
                "result = eval(expr)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            assert report.total_hotspots > 0
            for hotspot in report.hotspots:
                assert hotspot.review_status == ReviewStatus.TO_REVIEW.value

    def test_hotspots_by_category_populated(self):
        """Test that hotspots_by_category dict is populated after scan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "multi.py").write_text(
                "import pickle\n"
                "data = pickle.loads(raw)\n"
                "result = eval(expr)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            assert len(report.hotspots_by_category) > 0

    def test_hotspot_line_number_positive(self):
        """Test that all hotspot line numbers are positive integers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "code.py").write_text(
                "import hashlib\n"
                "import pickle\n"
                "data = pickle.loads(raw)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            for hotspot in report.hotspots:
                assert hotspot.line_number > 0


class TestInsecureRandomDetection:
    """Tests for INSECURE_RANDOM hotspot detection."""

    def test_random_import_detected(self):
        """Test that importing random module is detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "random_use.py").write_text(
                "import random\n"
                "\n"
                "session_id = random.randint(0, 1000000)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            random_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.INSECURE_RANDOM.value
            ]
            assert len(random_hotspots) > 0

    def test_random_import_has_medium_priority(self):
        """Test that random import hotspot has MEDIUM priority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "random_import.py").write_text(
                "import random\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            random_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.INSECURE_RANDOM.value
            ]
            assert len(random_hotspots) > 0
            assert random_hotspots[0].review_priority == ReviewPriority.MEDIUM.value


class TestCookieConfigDetection:
    """Tests for COOKIE_CONFIG hotspot detection."""

    def test_secure_false_detected(self):
        """Test that secure=False in cookie configuration is detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "cookie_config.py").write_text(
                "response.set_cookie('session', value, secure=False)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            cookie_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.COOKIE_CONFIG.value
            ]
            assert len(cookie_hotspots) > 0

    def test_httponly_false_detected(self):
        """Test that httponly=False in cookie configuration is detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "httponly_config.py").write_text(
                "response.set_cookie('session', value, httponly=False)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            cookie_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.COOKIE_CONFIG.value
            ]
            assert len(cookie_hotspots) > 0


class TestTLSVerificationDetection:
    """Tests for TLS_VERIFICATION hotspot detection."""

    def test_verify_false_detected(self):
        """Test that verify=False is detected as a TLS_VERIFICATION hotspot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "tls_skip.py").write_text(
                "import requests\n"
                "response = requests.get('https://example.com', verify=False)\n"
            )

            detector = HotspotDetector()
            report = detector.scan(tmpdir_path)

            tls_hotspots = [
                h for h in report.hotspots
                if h.category == HotspotCategory.TLS_VERIFICATION.value
            ]
            assert len(tls_hotspots) > 0
