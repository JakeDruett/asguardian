"""CH-0078 leftover: leftover walkers must not follow parent-dir file/dir symlinks."""

from Asgard.Bragi.Quality.languages._confined_walk import iter_confined_regular_files
from Asgard.Heimdall.Security.utilities._scan_utils import iter_confined_files


def test_confined_files_skip_symlink_to_parent(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    root = tmp_path / "scan"
    root.mkdir()
    (root / "ok.py").write_text("x = 1\n")
    (root / "escape").symlink_to(outside)
    names = {p.name for p in iter_confined_files(root)}
    assert "ok.py" in names
    assert "escape" not in names
    assert "outside.txt" not in names


def test_quality_walk_skips_dir_symlink(tmp_path):
    outside = tmp_path / "out"
    outside.mkdir()
    (outside / "evil.py").write_text("x=1\n")
    root = tmp_path / "scan"
    root.mkdir()
    (root / "ok.py").write_text("x=1\n")
    (root / "link").symlink_to(outside)
    names = {p.name for p in iter_confined_regular_files(root)}
    assert names == {"ok.py"}
