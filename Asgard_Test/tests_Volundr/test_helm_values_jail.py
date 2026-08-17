"""CHC-0013: helm values --environment must stay under output_dir."""

from argparse import Namespace
from pathlib import Path

from Asgard.Volundr.cli.handlers_gitops import run_helm_values


def test_helm_values_rejects_path_environment(tmp_path: Path, monkeypatch):
    args = Namespace(
        output_dir=str(tmp_path),
        image="repo/app",
        environment="../../tmp/x",
        dry_run=False,
    )

    class _Stub:
        def generate_yaml(self, **kwargs):
            return "image: x\n"

    monkeypatch.setattr(
        "Asgard.Volundr.cli.handlers_gitops.ValuesGenerator",
        lambda output_dir=None: _Stub(),
    )
    assert run_helm_values(args) == 1
    assert list(tmp_path.iterdir()) == []
    assert not (tmp_path.parent / "tmp").exists()
