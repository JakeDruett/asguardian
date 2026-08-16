"""CH-0078: Heimdall security walkers must not follow symlinks out of the scan root."""

from pathlib import Path

from Asgard.Heimdall.cli.handlers._security_dispatch import (
    _iter_code_files,
    count_lines_of_code,
)
from Asgard.Heimdall.Security.services.config_secrets_scanner import ConfigSecretsScanner
from Asgard.Heimdall.Security.services.dependency_vulnerability_service import (
    DependencyVulnerabilityService,
)
from Asgard.Heimdall.Security.models.security_models import SecurityScanConfig
from Asgard.Heimdall.Security.services.secrets_detection_service import (
    SecretsDetectionService,
)
from Asgard.Heimdall.Security.utilities._scan_utils import (
    is_confined_scan_path,
    iter_confined_files,
    scan_directory_for_security,
)

OUTSIDE_KEY = "AKIACH0078OUT000001"
INSIDE_KEY = "AKIACH0078INS000001"
OUTSIDE_PKG = "ch0078-outside-canary==9.9.9"
INSIDE_PKG = "ch0078-inside-canary==1.0.0"
OUTSIDE_PASSWORD = "ch0078-outside-password-value"
INSIDE_PASSWORD = "ch0078-inside-password-value"


def _layout(tmp_path: Path) -> tuple[Path, Path]:
    """Plant a secret tree outside the scan root and a real tree inside it."""
    outside = tmp_path / "outside"
    root = tmp_path / "scan"
    outside.mkdir()
    root.mkdir()

    (outside / "secret.py").write_text(f'AWS_ACCESS_KEY = "{OUTSIDE_KEY}"\n')
    (outside / "requirements.txt").write_text(f"{OUTSIDE_PKG}\n")
    (outside / "secrets.yaml").write_text(f"password: {OUTSIDE_PASSWORD}\n")

    (root / "app.py").write_text(f'AWS_ACCESS_KEY = "{INSIDE_KEY}"\n')
    (root / "requirements.txt").write_text(f"{INSIDE_PKG}\n")
    (root / "config.yaml").write_text(f"password: {INSIDE_PASSWORD}\n")

    (root / "leak.py").symlink_to(outside / "secret.py")
    (root / "leak_reqs.txt").symlink_to(outside / "requirements.txt")
    (root / "leak.yaml").symlink_to(outside / "secrets.yaml")
    (root / "escape").symlink_to(outside)
    return root, outside


def _same_file(path: Path, target: Path) -> bool:
    try:
        return path.resolve() == target.resolve()
    except (OSError, RuntimeError):
        return False


def _resolves_outside(paths: list[Path], outside: Path) -> bool:
    outside_resolved = outside.resolve()
    for path in paths:
        try:
            if path.resolve().is_relative_to(outside_resolved):
                return True
        except (OSError, RuntimeError, ValueError):
            continue
    return False


class TestScanDirectoryForSecuritySymlinks:
    def test_file_symlink_to_outside_secret_is_not_yielded(self, tmp_path: Path):
        root, outside = _layout(tmp_path)
        files = list(scan_directory_for_security(root))
        assert not _resolves_outside(files, outside)
        assert not any(path.is_symlink() for path in files)
        assert (root / "leak.py") not in files

    def test_dir_symlink_escape_is_not_walked(self, tmp_path: Path):
        root, outside = _layout(tmp_path)
        files = list(scan_directory_for_security(root))
        names = {path.name for path in files}
        assert "secret.py" not in names
        assert not any("escape" in path.parts for path in files)
        assert not _resolves_outside(files, outside)

    def test_real_files_inside_root_are_scanned(self, tmp_path: Path):
        root, _outside = _layout(tmp_path)
        files = list(scan_directory_for_security(root))
        names = {path.name for path in files}
        assert "app.py" in names
        assert any(path.resolve() == (root / "app.py").resolve() for path in files)


class TestIterConfinedFiles:
    def test_skips_file_and_dir_symlinks(self, tmp_path: Path):
        root, outside = _layout(tmp_path)
        files = list(iter_confined_files(root))
        assert not _resolves_outside(files, outside)
        assert not any(path.is_symlink() for path in files)

    def test_cycle_dir_symlink_does_not_recurse(self, tmp_path: Path):
        root = tmp_path / "scan"
        root.mkdir()
        (root / "ok.py").write_text("x = 1\n")
        (root / "loop").symlink_to(root)
        files = list(iter_confined_files(root))
        assert [path.name for path in files] == ["ok.py"]

    def test_in_tree_symlink_is_rejected_even_if_target_is_inside(self, tmp_path: Path):
        root = tmp_path / "scan"
        root.mkdir()
        target = root / "real.py"
        target.write_text("x = 1\n")
        link = root / "alias.py"
        link.symlink_to(target)
        assert is_confined_scan_path(target, root) is True
        assert is_confined_scan_path(link, root) is False


def _secrets_service() -> SecretsDetectionService:
    # Default exclude_patterns include `test_*`, which matches pytest tmp dirs.
    return SecretsDetectionService(SecurityScanConfig(exclude_patterns=[]))


class TestSecretsServiceDoesNotReadOutside:
    def test_file_symlink_secret_is_not_read(self, tmp_path: Path, monkeypatch):
        root, outside = _layout(tmp_path)
        planted = (outside / "secret.py").resolve()
        opened: list[Path] = []
        real_open = open

        def _spy(path, *args, **kwargs):
            opened.append(Path(path))
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", _spy)
        report = _secrets_service().scan(root)
        assert report.total_files_scanned >= 1
        assert not any(_same_file(path, planted) for path in opened)
        assert not any(Path(finding.file_path).name in {"leak.py", "secret.py"}
                       for finding in report.findings)

    def test_inside_file_is_still_scanned(self, tmp_path: Path):
        root, _outside = _layout(tmp_path)
        report = _secrets_service().scan(root)
        scanned = list(scan_directory_for_security(root, exclude_patterns=[]))
        assert report.total_files_scanned == len(scanned)
        assert any(path.name == "app.py" for path in scanned)


class TestDispatchWalkerSymlinks:
    def test_file_symlink_is_not_yielded(self, tmp_path: Path):
        root, outside = _layout(tmp_path)
        files = list(_iter_code_files(root, ()))
        assert not _resolves_outside(files, outside)
        assert not any(path.name == "leak.py" for path in files)

    def test_dir_symlink_escape_is_not_walked(self, tmp_path: Path):
        root, outside = _layout(tmp_path)
        files = list(_iter_code_files(root, ()))
        assert not any("escape" in path.parts for path in files)
        assert not _resolves_outside(files, outside)

    def test_real_inside_file_is_counted(self, tmp_path: Path):
        root, _outside = _layout(tmp_path)
        files = list(_iter_code_files(root, ()))
        assert any(path.name == "app.py" for path in files)
        assert count_lines_of_code(root) == 1


class TestDependencyWalkerSymlinks:
    def test_file_and_dir_symlink_manifests_are_ignored(self, tmp_path: Path):
        root, _outside = _layout(tmp_path)
        service = DependencyVulnerabilityService()
        found = service._find_requirements_files(root)
        names = {path.name for path in found}
        assert "requirements.txt" in names
        assert "leak_reqs.txt" not in names
        assert not any("escape" in path.parts for path in found)
        report = service.scan(root)
        joined = " ".join(report.requirements_files)
        assert "requirements.txt" in joined
        assert "escape" not in joined
        assert OUTSIDE_PKG.split("==")[0] not in joined


class TestConfigSecretsWalkerSymlinks:
    def test_file_symlink_outside_secret_is_not_read(self, tmp_path: Path):
        root, outside = _layout(tmp_path)
        report = ConfigSecretsScanner().analyze(root)
        blob = " ".join(
            f"{finding.masked_value} {finding.context_description}"
            for finding in report.detected_findings
        )
        assert OUTSIDE_PASSWORD not in blob
        assert not any(
            Path(finding.file_path).resolve().is_relative_to(outside.resolve())
            for finding in report.detected_findings
        )
        assert not any(
            Path(finding.file_path).name in {"leak.yaml", "secrets.yaml"}
            for finding in report.detected_findings
        )

    def test_dir_symlink_escape_is_not_walked(self, tmp_path: Path):
        root, outside = _layout(tmp_path)
        report = ConfigSecretsScanner().analyze(root)
        assert not any(
            Path(finding.file_path).resolve().is_relative_to(outside.resolve())
            for finding in report.detected_findings
        )
        assert not any(
            "escape" in Path(finding.file_path).parts
            for finding in report.detected_findings
        )

    def test_real_inside_config_is_scanned(self, tmp_path: Path):
        root, _outside = _layout(tmp_path)
        report = ConfigSecretsScanner().analyze(root)
        assert report.files_scanned >= 1
        assert any(
            Path(finding.file_path).name == "config.yaml"
            for finding in report.detected_findings
        )
