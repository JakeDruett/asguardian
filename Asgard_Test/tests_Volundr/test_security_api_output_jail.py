"""CH-0115: SecurityAPI -o stays under CWD unless --allow-abs."""

from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

_MOD = SourceFileLoader(
    "security_api",
    str(Path(__file__).resolve().parents[2] / "_FutureItems-Security" / "Tools_Security" / "security_api.py"),
).load_module()


def test_absolute_output_is_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        _MOD.confine_output_path("/tmp/x.json")


def test_parent_output_is_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        _MOD.confine_output_path("../../etc/cron.d/x.json")


def test_wrong_suffix_is_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        _MOD.confine_output_path("out.txt")


def test_relative_json_stays_under_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    dest = _MOD.confine_output_path("out.json")
    assert dest == (tmp_path / "out.json").resolve()
    assert dest.is_relative_to(tmp_path.resolve())
