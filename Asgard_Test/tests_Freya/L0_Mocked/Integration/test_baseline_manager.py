"""
Freya Baseline Manager Tests

Comprehensive L0 unit tests for BaselineManager service.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch, mock_open, call

from Freya.Integration.models.integration_models import BaselineConfig, BaselineEntry
from Freya.Integration.services.baseline_manager import BaselineManager


@pytest.fixture
def mock_baseline_config():
    """Create a mock BaselineConfig."""
    return BaselineConfig(
        storage_directory="/tmp/test_baselines",
        auto_update=False,
        version_baselines=True,
        max_versions=5,
        diff_threshold=0.1
    )


@pytest.fixture
def mock_baseline_entry():
    """Create a mock BaselineEntry."""
    return BaselineEntry(
        url="https://example.com",
        name="test_baseline",
        created_at="2025-01-01T00:00:00",
        updated_at="2025-01-01T00:00:00",
        screenshot_path="/tmp/test_baselines/abc123/baseline_20250101_000000.png",
        viewport_width=1920,
        viewport_height=1080,
        hash="test_hash_12345"
    )


@pytest.fixture
def mock_screenshot_result():
    """Create a mock screenshot result."""
    screenshot = Mock()
    screenshot.file_path = "/tmp/screenshots/capture.png"
    screenshot.metadata = {"format": "png"}
    screenshot.file_size_bytes = 12345
    return screenshot


@pytest.fixture
def mock_regression_result():
    """Create a mock regression result."""
    result = Mock()
    result.has_difference = False
    result.difference_percentage = 0.0
    result.diff_image_path = None
    return result


class TestBaselineManagerInit:
    """Tests for BaselineManager initialization."""

    def test_init_creates_storage_directory(self, tmp_path):
        """Test BaselineManager creates storage directory on init."""
        storage_dir = tmp_path / "test_baselines"
        config = BaselineConfig(storage_directory=str(storage_dir))

        manager = BaselineManager(config=config)

        assert storage_dir.exists()
        assert isinstance(manager.baselines, dict)

    def test_init_with_custom_config(self, tmp_path, mock_baseline_config):
        """Test BaselineManager initialization with custom config."""
        storage_dir = tmp_path / "test_baselines"
        mock_baseline_config.storage_directory = str(storage_dir)

        manager = BaselineManager(config=mock_baseline_config)

        assert manager.config == mock_baseline_config
        assert storage_dir.exists()

    def test_init_loads_existing_index(self, tmp_path):
        """Test BaselineManager loads existing index file."""
        storage_dir = tmp_path / "test_baselines"
        storage_dir.mkdir(parents=True)
        index_file = storage_dir / "baselines.json"

        index_data = {
            "abc123": {
                "url": "https://example.com",
                "name": "test",
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00",
                "screenshot_path": "/path/to/screenshot.png",
                "viewport_width": 1920,
                "viewport_height": 1080,
                "hash": "test_hash"
            }
        }

        with open(index_file, "w") as f:
            json.dump(index_data, f)

        config = BaselineConfig(storage_directory=str(storage_dir))
        manager = BaselineManager(config=config)

        assert len(manager.baselines) == 1
        assert "abc123" in manager.baselines

    def test_init_creates_empty_index_if_no_file(self, tmp_path):
        """Test BaselineManager creates empty index if file doesn't exist."""
        storage_dir = tmp_path / "test_baselines"
        config = BaselineConfig(storage_directory=str(storage_dir))

        manager = BaselineManager(config=config)

        assert manager.baselines == {}


class TestBaselineManagerLoadIndex:
    """Tests for _load_index method."""

    @patch('Freya.Integration.services.baseline_manager.Path')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_index_existing_file(self, mock_file, mock_path_class):
        """Test loading index from existing file."""
        index_data = {
            "abc123": {
                "url": "https://example.com",
                "name": "test",
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00",
                "screenshot_path": "/path/to/screenshot.png",
                "viewport_width": 1920,
                "viewport_height": 1080,
                "hash": "test_hash"
            }
        }

        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__ = lambda self, other: MagicMock(exists=lambda: True)
        mock_path_class.return_value = mock_path_instance

        mock_file.return_value.read.return_value = json.dumps(index_data)

        with patch('json.load', return_value=index_data):
            manager = BaselineManager()

            assert len(manager.baselines) == 1
            assert "abc123" in manager.baselines
            assert isinstance(manager.baselines["abc123"], BaselineEntry)

    @patch('Freya.Integration.services.baseline_manager.Path')
    def test_load_index_no_file(self, mock_path_class):
        """Test loading index when file doesn't exist."""
        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__ = lambda self, other: MagicMock(exists=lambda: False)
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()

        assert manager.baselines == {}


class TestBaselineManagerSaveIndex:
    """Tests for _save_index method."""

    @patch('Freya.Integration.services.baseline_manager.Path')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_save_index(self, mock_json_dump, mock_file, mock_path_class, mock_baseline_entry):
        """Test saving index to file."""
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()
        manager.baselines = {"abc123": mock_baseline_entry}
        manager._save_index()

        mock_json_dump.assert_called_once()
        call_args = mock_json_dump.call_args
        saved_data = call_args[0][0]
        assert "abc123" in saved_data


class TestBaselineManagerCreateBaseline:
    """Tests for create_baseline method."""

    @patch('Freya.Integration.services.baseline_manager.Path')
    @patch('Freya.Integration.services.baseline_manager.ScreenshotCapture')
    @patch('Freya.Integration.services.baseline_manager.shutil.copy')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test_image_data')
    def test_create_baseline_without_device(
        self, mock_file, mock_copy, mock_screenshot_class, mock_path_class, mock_screenshot_result
    ):
        """Test creating baseline without device."""
        mock_screenshot_instance = AsyncMock()
        mock_screenshot_instance.capture_full_page = AsyncMock(return_value=mock_screenshot_result)
        mock_screenshot_class.return_value = mock_screenshot_instance

        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()
        manager._save_index = Mock()

        import asyncio
        result = asyncio.run(manager.create_baseline(
            url="https://example.com",
            name="test_baseline"
        ))

        assert isinstance(result, BaselineEntry)
        assert result.url == "https://example.com"
        assert result.name == "test_baseline"
        assert result.viewport_width == 1920
        assert result.viewport_height == 1080
        mock_screenshot_instance.capture_full_page.assert_called_once()
        manager._save_index.assert_called_once()

    @patch('Freya.Integration.services.baseline_manager.Path')
    @patch('Freya.Integration.services.baseline_manager.ScreenshotCapture')
    @patch('Freya.Integration.services.baseline_manager.shutil.copy')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test_image_data')
    def test_create_baseline_with_device(
        self, mock_file, mock_copy, mock_screenshot_class, mock_path_class, mock_screenshot_result
    ):
        """Test creating baseline with device."""
        mock_screenshot_instance = AsyncMock()
        mock_screenshot_instance.capture_with_devices = AsyncMock(return_value=[mock_screenshot_result])
        mock_screenshot_class.return_value = mock_screenshot_instance

        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()
        manager._save_index = Mock()

        import asyncio
        result = asyncio.run(manager.create_baseline(
            url="https://example.com",
            name="test_baseline",
            device="iphone-14"
        ))

        assert result.device == "iphone-14"
        mock_screenshot_instance.capture_with_devices.assert_called_once_with(
            "https://example.com",
            devices=["iphone-14"]
        )

    @patch('Freya.Integration.services.baseline_manager.Path')
    @patch('Freya.Integration.services.baseline_manager.ScreenshotCapture')
    def test_create_baseline_device_not_found(self, mock_screenshot_class, mock_path_class):
        """Test creating baseline with invalid device."""
        mock_screenshot_instance = AsyncMock()
        mock_screenshot_instance.capture_with_devices = AsyncMock(return_value=[])
        mock_screenshot_class.return_value = mock_screenshot_instance

        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()

        import asyncio
        with pytest.raises(ValueError, match="Device 'invalid-device' not found"):
            asyncio.run(manager.create_baseline(
                url="https://example.com",
                name="test_baseline",
                device="invalid-device"
            ))

    @patch('Freya.Integration.services.baseline_manager.Path')
    @patch('Freya.Integration.services.baseline_manager.ScreenshotCapture')
    @patch('Freya.Integration.services.baseline_manager.shutil.copy')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test_image_data')
    def test_create_baseline_with_versioning(
        self, mock_file, mock_copy, mock_screenshot_class, mock_path_class, mock_screenshot_result
    ):
        """Test creating baseline with versioning enabled."""
        mock_screenshot_instance = AsyncMock()
        mock_screenshot_instance.capture_full_page = AsyncMock(return_value=mock_screenshot_result)
        mock_screenshot_class.return_value = mock_screenshot_instance

        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        config = BaselineConfig(version_baselines=True)
        manager = BaselineManager(config=config)
        manager._save_index = Mock()
        manager._version_baseline = Mock()

        import asyncio
        result = asyncio.run(manager.create_baseline(
            url="https://example.com",
            name="test_baseline"
        ))

        manager._version_baseline.assert_called_once()


class TestBaselineManagerUpdateBaseline:
    """Tests for update_baseline method."""

    @patch('Freya.Integration.services.baseline_manager.Path')
    def test_update_baseline_existing(self, mock_path_class, mock_baseline_entry):
        """Test updating existing baseline."""
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()
        manager.baselines = {"abc123": mock_baseline_entry}
        manager.create_baseline = AsyncMock(return_value=mock_baseline_entry)

        import asyncio
        result = asyncio.run(manager.update_baseline(
            url="https://example.com",
            name="test_baseline"
        ))

        manager.create_baseline.assert_called_once()
        call_args = manager.create_baseline.call_args
        assert call_args[1]["viewport_width"] == 1920
        assert call_args[1]["viewport_height"] == 1080

    @patch('Freya.Integration.services.baseline_manager.Path')
    def test_update_baseline_new(self, mock_path_class):
        """Test updating baseline that doesn't exist."""
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()
        manager.baselines = {}
        manager.create_baseline = AsyncMock(return_value=Mock())

        import asyncio
        result = asyncio.run(manager.update_baseline(
            url="https://example.com",
            name="new_baseline"
        ))

        manager.create_baseline.assert_called_once()
        call_args = manager.create_baseline.call_args
        assert call_args[1]["viewport_width"] == 1920


class TestBaselineManagerCompareToBaseline:
    """Tests for compare_to_baseline method."""

    @patch('Freya.Integration.services.baseline_manager.Path')
    def test_compare_to_baseline_not_found(self, mock_path_class):
        """Test comparing when baseline doesn't exist."""
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()
        manager.baselines = {}

        import asyncio
        result = asyncio.run(manager.compare_to_baseline(
            url="https://example.com",
            name="nonexistent"
        ))

        assert result["success"] is False
        assert "Baseline not found" in result["error"]

    @patch('Freya.Integration.services.baseline_manager.Path')
    @patch('Freya.Integration.services.baseline_manager.ScreenshotCapture')
    @patch('Freya.Integration.services.baseline_manager.VisualRegressionTester')
    def test_compare_to_baseline_no_difference(
        self, mock_regression_class, mock_screenshot_class, mock_path_class,
        mock_baseline_entry, mock_screenshot_result, mock_regression_result
    ):
        """Test comparing with no differences."""
        mock_screenshot_instance = AsyncMock()
        mock_screenshot_instance.capture = AsyncMock(return_value=mock_screenshot_result)
        mock_screenshot_class.return_value = mock_screenshot_instance

        mock_regression_instance = Mock()
        mock_regression_instance.compare = Mock(return_value=mock_regression_result)
        mock_regression_class.return_value = mock_regression_instance

        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()
        manager.baselines = {"abc123": mock_baseline_entry}
        manager._generate_key = Mock(return_value="abc123")

        import asyncio
        result = asyncio.run(manager.compare_to_baseline(
            url="https://example.com",
            name="test_baseline"
        ))

        assert result["success"] is True
        assert result["has_difference"] is False
        assert result["passed"] is True
        assert result["difference_percentage"] == 0.0

    @patch('Freya.Integration.services.baseline_manager.Path')
    @patch('Freya.Integration.services.baseline_manager.ScreenshotCapture')
    @patch('Freya.Integration.services.baseline_manager.VisualRegressionTester')
    def test_compare_to_baseline_with_difference(
        self, mock_regression_class, mock_screenshot_class, mock_path_class,
        mock_baseline_entry, mock_screenshot_result
    ):
        """Test comparing with differences."""
        regression_result = Mock()
        regression_result.has_difference = True
        regression_result.difference_percentage = 5.2
        regression_result.diff_image_path = "/tmp/diff.png"

        mock_screenshot_instance = AsyncMock()
        mock_screenshot_instance.capture = AsyncMock(return_value=mock_screenshot_result)
        mock_screenshot_class.return_value = mock_screenshot_instance

        mock_regression_instance = Mock()
        mock_regression_instance.compare = Mock(return_value=regression_result)
        mock_regression_class.return_value = mock_regression_instance

        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()
        manager.baselines = {"abc123": mock_baseline_entry}
        manager._generate_key = Mock(return_value="abc123")

        import asyncio
        result = asyncio.run(manager.compare_to_baseline(
            url="https://example.com",
            name="test_baseline"
        ))

        assert result["success"] is True
        assert result["has_difference"] is True
        assert result["passed"] is False
        assert result["difference_percentage"] == 5.2

    @patch('Freya.Integration.services.baseline_manager.Path')
    @patch('Freya.Integration.services.baseline_manager.ScreenshotCapture')
    @patch('Freya.Integration.services.baseline_manager.VisualRegressionTester')
    def test_compare_to_baseline_auto_update(
        self, mock_regression_class, mock_screenshot_class, mock_path_class,
        mock_baseline_entry, mock_screenshot_result
    ):
        """Test comparing with auto-update enabled."""
        regression_result = Mock()
        regression_result.has_difference = True
        regression_result.difference_percentage = 5.2
        regression_result.diff_image_path = "/tmp/diff.png"

        mock_screenshot_instance = AsyncMock()
        mock_screenshot_instance.capture = AsyncMock(return_value=mock_screenshot_result)
        mock_screenshot_class.return_value = mock_screenshot_instance

        mock_regression_instance = Mock()
        mock_regression_instance.compare = Mock(return_value=regression_result)
        mock_regression_class.return_value = mock_regression_instance

        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        config = BaselineConfig(auto_update=True)
        manager = BaselineManager(config=config)
        manager.baselines = {"abc123": mock_baseline_entry}
        manager._generate_key = Mock(return_value="abc123")
        manager.update_baseline = AsyncMock()

        import asyncio
        result = asyncio.run(manager.compare_to_baseline(
            url="https://example.com",
            name="test_baseline"
        ))

        manager.update_baseline.assert_called_once()


class TestBaselineManagerListBaselines:
    """Tests for list_baselines method."""

    @patch('Freya.Integration.services.baseline_manager.Path')
    def test_list_baselines_all(self, mock_path_class, mock_baseline_entry):
        """Test listing all baselines."""
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        entry2 = BaselineEntry(
            url="https://different.com",
            name="other",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            screenshot_path="/path/to/other.png",
            viewport_width=1920,
            viewport_height=1080,
            hash="other_hash"
        )

        manager = BaselineManager()
        manager.baselines = {"abc123": mock_baseline_entry, "def456": entry2}

        results = manager.list_baselines()

        assert len(results) == 2

    @patch('Freya.Integration.services.baseline_manager.Path')
    def test_list_baselines_filtered_by_url(self, mock_path_class, mock_baseline_entry):
        """Test listing baselines filtered by URL."""
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        entry2 = BaselineEntry(
            url="https://different.com",
            name="other",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            screenshot_path="/path/to/other.png",
            viewport_width=1920,
            viewport_height=1080,
            hash="other_hash"
        )

        manager = BaselineManager()
        manager.baselines = {"abc123": mock_baseline_entry, "def456": entry2}

        results = manager.list_baselines(url="https://example.com")

        assert len(results) == 1
        assert results[0].url == "https://example.com"


class TestBaselineManagerGetBaseline:
    """Tests for get_baseline method."""

    @patch('Freya.Integration.services.baseline_manager.Path')
    def test_get_baseline_exists(self, mock_path_class, mock_baseline_entry):
        """Test getting existing baseline."""
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()
        manager.baselines = {"abc123": mock_baseline_entry}
        manager._generate_key = Mock(return_value="abc123")

        result = manager.get_baseline("https://example.com", "test_baseline")

        assert result == mock_baseline_entry

    @patch('Freya.Integration.services.baseline_manager.Path')
    def test_get_baseline_not_exists(self, mock_path_class):
        """Test getting non-existent baseline."""
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()
        manager.baselines = {}
        manager._generate_key = Mock(return_value="abc123")

        result = manager.get_baseline("https://example.com", "nonexistent")

        assert result is None


class TestBaselineManagerDeleteBaseline:
    """Tests for delete_baseline method."""

    @patch('Freya.Integration.services.baseline_manager.Path')
    @patch('Freya.Integration.services.baseline_manager.shutil.rmtree')
    def test_delete_baseline_exists(self, mock_rmtree, mock_path_class, mock_baseline_entry):
        """Test deleting existing baseline."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.unlink = Mock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()
        manager.baselines = {"abc123": mock_baseline_entry}
        manager._generate_key = Mock(return_value="abc123")
        manager._save_index = Mock()

        result = manager.delete_baseline("https://example.com", "test_baseline")

        assert result is True
        assert "abc123" not in manager.baselines
        manager._save_index.assert_called_once()

    @patch('Freya.Integration.services.baseline_manager.Path')
    def test_delete_baseline_not_exists(self, mock_path_class):
        """Test deleting non-existent baseline."""
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()
        manager.baselines = {}
        manager._generate_key = Mock(return_value="abc123")

        result = manager.delete_baseline("https://example.com", "nonexistent")

        assert result is False


class TestBaselineManagerGetVersions:
    """Tests for get_versions method."""

    @patch('Freya.Integration.services.baseline_manager.Path')
    def test_get_versions_exist(self, mock_path_class):
        """Test getting versions when they exist."""
        mock_version_dir = MagicMock()
        mock_version_dir.exists.return_value = True
        mock_version_files = [
            MagicMock(name="v_20250101_000000.png"),
            MagicMock(name="v_20250102_000000.png")
        ]
        mock_version_dir.glob.return_value = sorted(mock_version_files)

        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__ = Mock(return_value=mock_version_dir)
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()
        manager._generate_key = Mock(return_value="abc123")

        results = manager.get_versions("https://example.com", "test_baseline")

        assert len(results) == 2

    @patch('Freya.Integration.services.baseline_manager.Path')
    def test_get_versions_not_exist(self, mock_path_class):
        """Test getting versions when directory doesn't exist."""
        mock_version_dir = MagicMock()
        mock_version_dir.exists.return_value = False

        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__ = Mock(return_value=mock_version_dir)
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()
        manager._generate_key = Mock(return_value="abc123")

        results = manager.get_versions("https://example.com", "test_baseline")

        assert results == []


class TestBaselineManagerPrivateMethods:
    """Tests for private helper methods."""

    @patch('Freya.Integration.services.baseline_manager.Path')
    def test_generate_key_without_device(self, mock_path_class):
        """Test generating key without device."""
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()

        key = manager._generate_key("https://example.com", "test_baseline", None)

        assert isinstance(key, str)
        assert len(key) == 16

    @patch('Freya.Integration.services.baseline_manager.Path')
    def test_generate_key_with_device(self, mock_path_class):
        """Test generating key with device."""
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()

        key1 = manager._generate_key("https://example.com", "test_baseline", None)
        key2 = manager._generate_key("https://example.com", "test_baseline", "iphone-14")

        assert key1 != key2

    @patch('Freya.Integration.services.baseline_manager.Path')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test_image_data')
    def test_calculate_hash(self, mock_file, mock_path_class):
        """Test calculating image hash."""
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()

        hash_value = manager._calculate_hash("/path/to/image.png")

        assert isinstance(hash_value, str)
        assert len(hash_value) == 32

    @patch('Freya.Integration.services.baseline_manager.Path')
    @patch('Freya.Integration.services.baseline_manager.shutil.copy')
    def test_version_baseline(self, mock_copy, mock_path_class):
        """Test creating versioned baseline."""
        mock_version_dir = MagicMock()
        mock_version_dir.glob.return_value = []

        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__ = Mock(return_value=mock_version_dir)
        mock_path_class.return_value = mock_path_instance

        manager = BaselineManager()

        manager._version_baseline("abc123", "/path/to/screenshot.png")

        mock_version_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_copy.assert_called_once()

    @patch('Freya.Integration.services.baseline_manager.Path')
    @patch('Freya.Integration.services.baseline_manager.shutil.copy')
    def test_version_baseline_max_versions(self, mock_copy, mock_path_class):
        """Test versioning with max versions limit."""
        mock_old_versions = [MagicMock() for _ in range(10)]
        for i, version in enumerate(mock_old_versions):
            version.unlink = Mock()

        mock_version_dir = MagicMock()
        mock_version_dir.glob.return_value = sorted(mock_old_versions)

        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__ = Mock(return_value=mock_version_dir)
        mock_path_class.return_value = mock_path_instance

        config = BaselineConfig(max_versions=5)
        manager = BaselineManager(config=config)

        manager._version_baseline("abc123", "/path/to/screenshot.png")

        for old_version in mock_old_versions[:5]:
            old_version.unlink.assert_called_once()
