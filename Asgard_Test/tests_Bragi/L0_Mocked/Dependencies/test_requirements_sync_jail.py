"""CH-0035: RequirementsChecker.sync must stay under the scan root."""

from datetime import datetime
from pathlib import Path

import pytest

from Asgard.Bragi.Dependencies.models.requirements_models import (
    RequirementsConfig,
    RequirementsResult,
)
from Asgard.Bragi.Dependencies.services.requirements_checker import (
    RequirementsChecker,
    confine_sync_target,
)


def _result(scan_path: Path) -> RequirementsResult:
    config = RequirementsConfig(scan_path=scan_path)
    return RequirementsResult(
        scan_path=str(scan_path),
        scanned_at=datetime.now(),
        scan_duration_seconds=0.0,
        config=config,
    )


def test_absolute_target_file_is_rejected(tmp_path: Path):
    checker = RequirementsChecker(RequirementsConfig(scan_path=tmp_path))
    with pytest.raises(ValueError, match="scan root"):
        checker.sync(_result(tmp_path), target_file="/tmp/x")


def test_parent_target_file_is_rejected(tmp_path: Path):
    checker = RequirementsChecker(RequirementsConfig(scan_path=tmp_path))
    with pytest.raises(ValueError, match="scan root"):
        checker.sync(_result(tmp_path), target_file="../x")


def test_relative_target_stays_under_scan_root(tmp_path: Path):
    dest = confine_sync_target(tmp_path, "requirements.txt")
    assert dest == (tmp_path / "requirements.txt").resolve()
    assert dest.is_relative_to(tmp_path.resolve())
