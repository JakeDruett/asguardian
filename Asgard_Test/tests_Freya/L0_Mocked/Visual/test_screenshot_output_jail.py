"""CH-0072: screenshot/regression output names stay under the output directory."""

from pathlib import Path

import pytest

from Asgard.Freya.Visual.services._screenshot_capture_helpers import (
    confine_output_path,
    sanitize_output_name,
    url_to_filename,
)


def test_parent_filename_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        confine_output_path(tmp_path, "../x")


def test_absolute_filename_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        confine_output_path(tmp_path, "/tmp/x")


def test_safe_name_stays_under_output_dir(tmp_path: Path):
    dest = confine_output_path(tmp_path, "page.png")
    assert dest == (tmp_path / "page.png").resolve()
    assert dest.is_relative_to(tmp_path.resolve())


def test_url_to_filename_is_sanitized():
    name = url_to_filename("https://example.com/a/b?x=1")
    assert "/" not in name
    assert ".." not in name
    assert sanitize_output_name(name)
