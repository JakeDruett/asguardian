"""CH-0049: linters/type checkers must not load untrusted project config."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import List, Optional

import pytest

from Asgard.Bragi.Quality.models.syntax_models import SyntaxConfig
from Asgard.Bragi.Quality.models.type_check_models import TypeCheckConfig, TypeCheckReport
from Asgard.Bragi.Quality.services import _mypy_runner, _pyright_runner, _syntax_linters
from Asgard.Bragi.Quality.services._syntax_linters import (
    run_flake8,
    run_mypy,
    run_pylint,
    run_ruff,
    run_ruff_fix,
)
from Asgard.Bragi.Quality.services._tool_isolation import (
    path_is_inside,
    trusted_executable,
)


def _syntax_config(scan_path: Path) -> SyntaxConfig:
    return SyntaxConfig(scan_path=scan_path)


def _fake_run(calls: list):
    def _run(cmd, **kwargs):
        calls.append({"cmd": list(cmd), "cwd": kwargs.get("cwd"), "env": kwargs.get("env")})
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return _run


def _flag_value(cmd: List[str], flag: str) -> Optional[str]:
    try:
        return cmd[cmd.index(flag) + 1]
    except (ValueError, IndexError):
        return None


def _assert_isolated_invocation(call: dict, scan_path: Path, *path_operands: Path) -> None:
    scan = scan_path.resolve()
    cwd = Path(call["cwd"]).resolve() if call["cwd"] else None
    assert cwd is not None
    assert not path_is_inside(cwd, scan)

    cmd = call["cmd"]
    assert "--" in cmd
    after = cmd[cmd.index("--") + 1 :]
    before = cmd[: cmd.index("--")]
    for operand in path_operands:
        assert str(operand.resolve()) in after
        assert str(operand.resolve()) not in before


def _stub_trusted(monkeypatch, module, mapping: dict) -> None:
    monkeypatch.setattr(
        module,
        "trusted_executable",
        lambda name, scan: mapping.get(name, f"/usr/bin/{name}"),
    )


class TestTrustedExecutable:
    def test_rejects_binary_inside_scan_tree(self, tmp_path: Path, monkeypatch) -> None:
        fake = tmp_path / "mypy"
        fake.write_text("#!/bin/sh\necho pwned\n", encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")
        assert trusted_executable("mypy", tmp_path) is None

    def test_accepts_binary_outside_scan_tree(self, tmp_path: Path) -> None:
        found = shutil.which("python3") or shutil.which("python")
        if not found:
            pytest.skip("python3 not on PATH")
        assert trusted_executable(Path(found).name, tmp_path) is not None
        assert not path_is_inside(Path(found), tmp_path)


class TestSyntaxLinterArgv:
    def test_ruff_uses_isolated_cwd_and_config(self, tmp_path: Path, monkeypatch) -> None:
        calls: list = []
        _stub_trusted(monkeypatch, _syntax_linters, {"ruff": "/usr/bin/ruff"})
        monkeypatch.setattr(_syntax_linters.subprocess, "run", _fake_run(calls))
        run_ruff(tmp_path, _syntax_config(tmp_path))
        assert len(calls) == 1
        _assert_isolated_invocation(calls[0], tmp_path, tmp_path)
        assert "--isolated" in calls[0]["cmd"]

    def test_ruff_fix_uses_isolated_cwd(self, tmp_path: Path, monkeypatch) -> None:
        calls: list = []
        _stub_trusted(monkeypatch, _syntax_linters, {"ruff": "/usr/bin/ruff"})
        monkeypatch.setattr(_syntax_linters.subprocess, "run", _fake_run(calls))
        run_ruff_fix(tmp_path, _syntax_config(tmp_path))
        assert len(calls) == 1
        _assert_isolated_invocation(calls[0], tmp_path, tmp_path)
        assert "--isolated" in calls[0]["cmd"]
        assert "--fix" in calls[0]["cmd"]

    def test_flake8_uses_isolated_flag(self, tmp_path: Path, monkeypatch) -> None:
        calls: list = []
        _stub_trusted(monkeypatch, _syntax_linters, {"flake8": "/usr/bin/flake8"})
        monkeypatch.setattr(_syntax_linters.subprocess, "run", _fake_run(calls))
        run_flake8(tmp_path, _syntax_config(tmp_path))
        assert len(calls) == 1
        _assert_isolated_invocation(calls[0], tmp_path, tmp_path)
        assert "--isolated" in calls[0]["cmd"]

    def test_pylint_uses_asgard_rcfile_outside_tree(self, tmp_path: Path, monkeypatch) -> None:
        calls: list = []
        _stub_trusted(monkeypatch, _syntax_linters, {"pylint": "/usr/bin/pylint"})
        monkeypatch.setattr(_syntax_linters.subprocess, "run", _fake_run(calls))
        run_pylint(tmp_path, _syntax_config(tmp_path))
        assert len(calls) == 1
        _assert_isolated_invocation(calls[0], tmp_path, tmp_path)
        rcfile = _flag_value(calls[0]["cmd"], "--rcfile")
        assert rcfile is not None
        assert not path_is_inside(Path(rcfile), tmp_path)
        env = calls[0]["env"] or {}
        assert env.get("PYLINTRC") == rcfile
        assert "--init-hook=" in calls[0]["cmd"]

    def test_syntax_mypy_uses_asgard_config_file(self, tmp_path: Path, monkeypatch) -> None:
        calls: list = []
        _stub_trusted(monkeypatch, _syntax_linters, {"mypy": "/usr/bin/mypy"})
        monkeypatch.setattr(_syntax_linters.subprocess, "run", _fake_run(calls))
        run_mypy(tmp_path, _syntax_config(tmp_path))
        assert len(calls) == 1
        _assert_isolated_invocation(calls[0], tmp_path, tmp_path)
        cfg = _flag_value(calls[0]["cmd"], "--config-file")
        assert cfg is not None
        assert not path_is_inside(Path(cfg), tmp_path)
        assert "--no-incremental" in calls[0]["cmd"]


class TestMypyRunnerArgv:
    def test_cwd_and_config_outside_scan_tree(self, tmp_path: Path, monkeypatch) -> None:
        target = tmp_path / "pkg"
        target.mkdir()
        src = target / "mod.py"
        src.write_text("x = 1\n", encoding="utf-8")

        calls: list = []
        _stub_trusted(monkeypatch, _mypy_runner, {"mypy": "/usr/bin/mypy"})
        monkeypatch.setattr(_mypy_runner, "get_mypy_version", lambda _bin: "1.0.0")
        monkeypatch.setattr(_mypy_runner.subprocess, "run", _fake_run(calls))

        report = TypeCheckReport(scan_path=str(tmp_path))
        _mypy_runner.run_mypy(tmp_path, report, TypeCheckConfig())

        assert calls
        _assert_isolated_invocation(calls[0], tmp_path, src)
        cfg = _flag_value(calls[0]["cmd"], "--config-file")
        assert cfg is not None
        assert not path_is_inside(Path(cfg), tmp_path)


class TestPyrightRunnerArgv:
    def test_npx_no_install_isolated_project_and_cwd(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "mod.py").write_text("x = 1\n", encoding="utf-8")
        planted = tmp_path / "pyrightconfig.json"
        planted.write_text('{"typeCheckingMode": "off"}', encoding="utf-8")

        calls: list = []
        monkeypatch.setattr(
            _pyright_runner,
            "pyright_invocation",
            lambda npx_path, scan: [npx_path, "--no-install", "pyright"],
        )
        monkeypatch.setattr(_pyright_runner.subprocess, "run", _fake_run(calls))

        _pyright_runner.invoke_pyright(tmp_path, TypeCheckConfig(npx_path="npx"))

        assert len(calls) == 1
        _assert_isolated_invocation(calls[0], tmp_path, tmp_path)
        cmd = calls[0]["cmd"]
        assert "--no-install" in cmd
        project = _flag_value(cmd, "--project")
        assert project is not None
        assert not path_is_inside(Path(project), tmp_path)
        assert not (tmp_path / ".pyrightconfig.heimdall.json").exists()
        assert planted.exists()
        assert planted.read_text(encoding="utf-8") == '{"typeCheckingMode": "off"}'

    def test_verify_uses_no_install_and_isolated_cwd(self, tmp_path: Path, monkeypatch) -> None:
        calls: list = []
        monkeypatch.setattr(
            _pyright_runner,
            "pyright_invocation",
            lambda npx_path, scan: [npx_path, "--no-install", "pyright"],
        )
        monkeypatch.setattr(_pyright_runner.subprocess, "run", _fake_run(calls))
        _pyright_runner.verify_pyright_available(TypeCheckConfig(), tmp_path)
        assert calls
        assert "--no-install" in calls[0]["cmd"]
        assert "--version" in calls[0]["cmd"]
        cwd = Path(calls[0]["cwd"]).resolve()
        assert not path_is_inside(cwd, tmp_path.resolve())

    def test_does_not_write_config_into_scan_tree(self, tmp_path: Path, monkeypatch) -> None:
        before = {p.name for p in tmp_path.iterdir()}
        monkeypatch.setattr(
            _pyright_runner,
            "pyright_invocation",
            lambda npx_path, scan: [npx_path, "--no-install", "pyright"],
        )
        monkeypatch.setattr(_pyright_runner.subprocess, "run", _fake_run([]))
        _pyright_runner.invoke_pyright(tmp_path, TypeCheckConfig())
        after = {p.name for p in tmp_path.iterdir()}
        assert after == before


def _write_sentinel_plugin(scan: Path, sentinel: Path) -> None:
    (scan / "evil_plugin.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(sentinel)!r}).write_text('loaded')\n"
        "def plugin(version: str):\n"
        "    return None\n",
        encoding="utf-8",
    )


class TestPlantedPluginsNotExecuted:
    def test_planted_mypy_ini_plugin_not_loaded(self, tmp_path: Path) -> None:
        if not shutil.which("mypy"):
            pytest.skip("mypy not installed")

        sentinel = tmp_path / "PWNED_MYPY"
        _write_sentinel_plugin(tmp_path, sentinel)
        (tmp_path / "mypy.ini").write_text("[mypy]\nplugins = evil_plugin.py\n", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text(
            "[tool.mypy]\nplugins = 'evil_plugin.py'\n", encoding="utf-8"
        )
        target = tmp_path / "target.py"
        target.write_text("x = 1\n", encoding="utf-8")

        control = subprocess.run(
            ["mypy", str(target)],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert sentinel.exists(), (
            "fixture broken: mypy should load the planted plugin without isolation "
            f"(exit={control.returncode}, stderr={control.stderr!r})"
        )
        sentinel.unlink()

        run_mypy(tmp_path, _syntax_config(tmp_path))
        assert not sentinel.exists()

        report = TypeCheckReport(scan_path=str(tmp_path))
        _mypy_runner.run_mypy(tmp_path, report, TypeCheckConfig())
        assert not sentinel.exists()

    def test_planted_pylint_init_hook_not_executed(self, tmp_path: Path) -> None:
        if not shutil.which("pylint"):
            pytest.skip("pylint not installed")

        sentinel = tmp_path / "PWNED_PYLINT"
        hook = f"open({str(sentinel)!r}, 'w').write('loaded')"
        (tmp_path / ".pylintrc").write_text(
            f"[MAIN]\ninit-hook={hook}\n\n[MASTER]\ninit-hook={hook}\n",
            encoding="utf-8",
        )
        (tmp_path / "target.py").write_text("x = 1\n", encoding="utf-8")

        control = subprocess.run(
            ["pylint", str(tmp_path / "target.py")],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert sentinel.exists(), (
            "fixture broken: pylint should run the planted init-hook without isolation "
            f"(exit={control.returncode}, stderr={control.stderr!r})"
        )
        sentinel.unlink()

        run_pylint(tmp_path, _syntax_config(tmp_path))
        assert not sentinel.exists()

    def test_planted_flake8_local_plugin_not_loaded(self, tmp_path: Path) -> None:
        if not shutil.which("flake8"):
            pytest.skip("flake8 not installed")

        sentinel = tmp_path / "PWNED_FLAKE8"
        (tmp_path / "evil_flake8.py").write_text(
            "from pathlib import Path\n"
            f"Path({str(sentinel)!r}).write_text('loaded')\n"
            "class EvilChecker:\n"
            "    name = 'evil'\n"
            "    version = '1.0'\n"
            "    def __init__(self, tree, filename=''):\n"
            "        self.tree = tree\n"
            "    def run(self):\n"
            "        return []\n",
            encoding="utf-8",
        )
        (tmp_path / ".flake8").write_text(
            "[flake8]\n"
            "select = EVL\n"
            "[flake8:local-plugins]\n"
            "extension =\n"
            "    EVL = evil_flake8:EvilChecker\n"
            "paths =\n"
            "    .\n",
            encoding="utf-8",
        )
        (tmp_path / "target.py").write_text("x = 1\n", encoding="utf-8")

        control = subprocess.run(
            ["flake8", str(tmp_path / "target.py")],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert sentinel.exists(), (
            "fixture broken: flake8 should load the planted local plugin without isolation "
            f"(exit={control.returncode}, stderr={control.stderr!r})"
        )
        sentinel.unlink()

        run_flake8(tmp_path, _syntax_config(tmp_path))
        assert not sentinel.exists()

    def test_planted_npx_pyright_shim_not_executed(self, tmp_path: Path) -> None:
        if not shutil.which("npx"):
            pytest.skip("npx not installed")

        sentinel = tmp_path / "PWNED_PYRIGHT"
        bin_dir = tmp_path / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        shim = bin_dir / "pyright"
        shim.write_text(
            "#!/bin/sh\n"
            f"printf loaded > {str(sentinel)!r}\n",
            encoding="utf-8",
        )
        shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
        (tmp_path / "package.json").write_text(
            '{"name":"hostile","private":true}\n', encoding="utf-8"
        )
        (tmp_path / "mod.py").write_text("x = 1\n", encoding="utf-8")

        control = subprocess.run(
            ["npx", "pyright"],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if not sentinel.exists():
            pytest.skip(
                "npx did not execute the local shim "
                f"(exit={control.returncode}, stderr={control.stderr!r})"
            )
        sentinel.unlink()

        _pyright_runner.invoke_pyright(tmp_path, TypeCheckConfig(npx_path="npx"))
        assert not sentinel.exists()
