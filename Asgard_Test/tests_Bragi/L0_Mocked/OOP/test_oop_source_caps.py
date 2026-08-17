"""CHC-0007: Python OOP parse/walk/LCOM stay bounded."""

from pathlib import Path

from Asgard.Bragi.Architecture.evaluators._lcom4 import MAX_LCOM4_METHODS
from Asgard.Bragi.OOP.services._cohesion_helpers import calculate_lcom_ck
from Asgard.Bragi.OOP.utilities._class_functions import (
    MAX_OOP_SOURCE_BYTES,
    extract_classes_from_file,
    extract_classes_from_source,
)


def test_oversize_source_is_skipped():
    huge = "x = 1\n" + ("a" * (MAX_OOP_SOURCE_BYTES + 10))
    assert extract_classes_from_source(huge) == []


def test_oversize_file_is_skipped(tmp_path: Path):
    path = tmp_path / "huge.py"
    path.write_bytes(b"x=1\n" + b"a" * (MAX_OOP_SOURCE_BYTES + 10))
    assert extract_classes_from_file(path) == []


def test_symlink_file_is_skipped(tmp_path: Path):
    real = tmp_path / "real.py"
    real.write_text("class A:\n    pass\n")
    link = tmp_path / "link.py"
    link.symlink_to(real)
    assert extract_classes_from_file(link) == []


def test_lcom_skips_more_than_128_methods():
    usage = {f"m{i}": {f"a{i}"} for i in range(MAX_LCOM4_METHODS + 1)}
    assert calculate_lcom_ck(usage) == 0.0
