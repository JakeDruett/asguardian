"""CH-0091: evaluation corpus manifest paths stay under the corpus root."""

from pathlib import Path

import pytest

from Asgard.Heimdall.evaluation.corpus import confine_eval_path, ground_truth_from_taint_manifest


def test_parent_file_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="corpus root"):
        confine_eval_path(tmp_path, "../../etc/passwd")


def test_absolute_file_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="corpus root"):
        confine_eval_path(tmp_path, "/etc/passwd")


def test_hostile_manifest_entry_is_not_read(tmp_path: Path):
    with pytest.raises(ValueError, match="corpus root"):
        ground_truth_from_taint_manifest(
            tmp_path,
            [{"file": "../../etc/passwd", "expect": "flow", "cwe": "CWE-22"}],
        )
