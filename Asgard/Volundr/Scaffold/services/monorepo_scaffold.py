"""
Monorepo Scaffold Service

Generates monorepo project structures with shared
infrastructure and multiple services.
"""

import hashlib
import os
from datetime import datetime
from typing import Callable, Dict, List, Optional, Protocol, Tuple, runtime_checkable

from Asgard.Volundr.Scaffold.models.scaffold_models import (
    ProjectConfig,
    ScaffoldReport,
    FileEntry,
    Language,
    CICDPlatform,
    ContainerOrchestration,
)
from Asgard.Volundr.Scaffold.services.microservice_scaffold import MicroserviceScaffold
from Asgard.Volundr.Scaffold.services.monorepo_scaffold_helpers import (
    root_readme,
    root_gitignore,
    makefile,
    pre_commit_config,
    editorconfig,
    root_docker_compose,
    root_pyproject,
    root_package_json,
    turbo_json,
    k8s_base_kustomization,
    k8s_namespace,
    k8s_overlay_kustomization,
    terraform_main,
    terraform_variables,
    terraform_outputs,
    github_actions_ci,
    github_actions_cd,
    gitlab_ci,
    codeowners,
    pr_template,
    get_next_steps,
)


def _root_files_for_python(config: ProjectConfig, name: str) -> List[FileEntry]:
    """Return the root manifest file(s) for a Python-primary monorepo."""
    return [FileEntry(path=f"{name}/pyproject.toml", content=root_pyproject(config))]


def _root_files_for_typescript(config: ProjectConfig, name: str) -> List[FileEntry]:
    """Return the root manifest file(s) for a TypeScript-primary monorepo."""
    return [
        FileEntry(path=f"{name}/package.json", content=root_package_json(config)),
        FileEntry(path=f"{name}/turbo.json", content=turbo_json(config)),
    ]


# Registry mapping Language enum values to functions that produce the
# language-specific root manifest files for a monorepo.
# To support a new language, add an entry here without touching MonorepoScaffold.
_LANGUAGE_ROOT_FILES: Dict[Language, Callable[[ProjectConfig, str], List[FileEntry]]] = {
    Language.PYTHON: _root_files_for_python,
    Language.TYPESCRIPT: _root_files_for_typescript,
}


def _cicd_files_for_github(config: ProjectConfig, name: str) -> Tuple[List[FileEntry], List[str]]:
    """Return (files, directories) for a GitHub Actions CI/CD setup."""
    files = [
        FileEntry(path=f"{name}/.github/workflows/ci.yaml", content=github_actions_ci(config)),
        FileEntry(path=f"{name}/.github/workflows/cd.yaml", content=github_actions_cd(config)),
        FileEntry(path=f"{name}/.github/CODEOWNERS", content=codeowners(config)),
        FileEntry(path=f"{name}/.github/pull_request_template.md", content=pr_template()),
    ]
    dirs = [f"{name}/.github/workflows"]
    return files, dirs


def _cicd_files_for_gitlab(config: ProjectConfig, name: str) -> Tuple[List[FileEntry], List[str]]:
    """Return (files, directories) for a GitLab CI setup."""
    files = [FileEntry(path=f"{name}/.gitlab-ci.yml", content=gitlab_ci(config))]
    return files, []


# Registry mapping CICDPlatform enum values to functions that produce the
# platform-specific CI/CD files and directories for a monorepo.
# To support a new platform, add an entry here without touching MonorepoScaffold.
_CICD_GENERATORS: Dict[
    CICDPlatform,
    Callable[[ProjectConfig, str], Tuple[List[FileEntry], List[str]]],
] = {
    CICDPlatform.GITHUB_ACTIONS: _cicd_files_for_github,
    CICDPlatform.GITLAB_CI: _cicd_files_for_gitlab,
}


@runtime_checkable
class IFileSystemWriter(Protocol):
    """
    Abstract interface for writing scaffold output to a destination.

    Decouples MonorepoScaffold from native OS file I/O (DIP), enabling
    implementations that write to S3, in-memory stores, Git repositories,
    or other destinations without modifying the scaffold service.
    """

    def write_file(self, path: str, content: str, executable: bool = False) -> None:
        """Write content to the given path, creating parent directories as needed."""
        ...

    def make_directory(self, path: str) -> None:
        """Create a directory (and any missing parents) at the given path."""
        ...


class LocalFileSystemWriter:
    """
    IFileSystemWriter implementation backed by the native OS filesystem.

    All os.makedirs / open() / os.chmod calls are contained here, keeping
    MonorepoScaffold free from direct file-system coupling.
    """

    def write_file(self, path: str, content: str, executable: bool = False) -> None:
        """Write content to path, creating parent directories as needed."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        if executable:
            os.chmod(path, 0o755)

    def make_directory(self, path: str) -> None:
        """Create a directory at path."""
        os.makedirs(path, exist_ok=True)


class MonorepoScaffold:
    """Generates monorepo project structures."""

    def __init__(
        self,
        output_dir: Optional[str] = None,
        file_system_writer: Optional[IFileSystemWriter] = None,
    ):
        self.output_dir = output_dir or "."
        self.microservice_scaffold = MicroserviceScaffold()
        self._writer: IFileSystemWriter = (
            file_system_writer if file_system_writer is not None else LocalFileSystemWriter()
        )

    def generate(self, config: ProjectConfig) -> ScaffoldReport:
        scaffold_id = hashlib.sha256(config.model_dump_json().encode()).hexdigest()[:16]

        files: List[FileEntry] = []
        directories: List[str] = []
        messages: List[str] = []

        directories.extend([
            config.name,
            f"{config.name}/services",
            f"{config.name}/packages",
            f"{config.name}/infrastructure",
            f"{config.name}/infrastructure/kubernetes",
            f"{config.name}/infrastructure/terraform",
            f"{config.name}/scripts",
            f"{config.name}/docs",
        ])

        files.extend(self._generate_root_files(config))
        files.extend(self._generate_infrastructure_files(config))
        directories.extend(self._get_infrastructure_directories(config))

        if config.cicd_platform != CICDPlatform.NONE:
            files.extend(self._generate_cicd_files(config))
            directories.extend(self._get_cicd_directories(config))

        for service in config.services:
            service_report = self.microservice_scaffold.generate(service)

            for file_entry in service_report.files:
                files.append(FileEntry(
                    path=f"{config.name}/services/{file_entry.path}",
                    content=file_entry.content,
                    executable=file_entry.executable,
                ))

            for directory in service_report.directories:
                directories.append(f"{config.name}/services/{directory}")

        next_steps = get_next_steps(config)

        return ScaffoldReport(
            id=f"monorepo-{scaffold_id}",
            project_name=config.name,
            project_type="monorepo",
            files=files,
            directories=directories,
            total_files=len(files),
            total_directories=len(directories),
            created_at=datetime.now(),
            messages=messages,
            next_steps=next_steps,
        )

    def _generate_root_files(self, config: ProjectConfig) -> List[FileEntry]:
        files: List[FileEntry] = []

        files.append(FileEntry(path=f"{config.name}/README.md", content=root_readme(config)))
        files.append(FileEntry(path=f"{config.name}/.gitignore", content=root_gitignore(config)))

        if config.include_makefile:
            files.append(FileEntry(path=f"{config.name}/Makefile", content=makefile(config)))

        if config.include_pre_commit:
            files.append(FileEntry(
                path=f"{config.name}/.pre-commit-config.yaml",
                content=pre_commit_config(config),
            ))

        files.append(FileEntry(path=f"{config.name}/.editorconfig", content=editorconfig()))
        files.append(FileEntry(
            path=f"{config.name}/docker-compose.yaml",
            content=root_docker_compose(config),
        ))

        primary_lang = self._get_primary_language(config)
        lang_generator = _LANGUAGE_ROOT_FILES.get(primary_lang)
        if lang_generator is not None:
            files.extend(lang_generator(config, config.name))

        return files

    def _generate_infrastructure_files(self, config: ProjectConfig) -> List[FileEntry]:
        files: List[FileEntry] = []

        if config.orchestration == ContainerOrchestration.KUBERNETES:
            files.append(FileEntry(
                path=f"{config.name}/infrastructure/kubernetes/base/kustomization.yaml",
                content=k8s_base_kustomization(config),
            ))
            files.append(FileEntry(
                path=f"{config.name}/infrastructure/kubernetes/base/namespace.yaml",
                content=k8s_namespace(config),
            ))

            for env in ["development", "staging", "production"]:
                files.append(FileEntry(
                    path=f"{config.name}/infrastructure/kubernetes/overlays/{env}/kustomization.yaml",
                    content=k8s_overlay_kustomization(config, env),
                ))

        files.append(FileEntry(
            path=f"{config.name}/infrastructure/terraform/main.tf",
            content=terraform_main(config),
        ))
        files.append(FileEntry(
            path=f"{config.name}/infrastructure/terraform/variables.tf",
            content=terraform_variables(config),
        ))
        files.append(FileEntry(
            path=f"{config.name}/infrastructure/terraform/outputs.tf",
            content=terraform_outputs(config),
        ))

        return files

    def _get_infrastructure_directories(self, config: ProjectConfig) -> List[str]:
        return [
            f"{config.name}/infrastructure/kubernetes/base",
            f"{config.name}/infrastructure/kubernetes/overlays/development",
            f"{config.name}/infrastructure/kubernetes/overlays/staging",
            f"{config.name}/infrastructure/kubernetes/overlays/production",
        ]

    def _generate_cicd_files(self, config: ProjectConfig) -> List[FileEntry]:
        generator = _CICD_GENERATORS.get(config.cicd_platform)
        if generator is None:
            return []
        files, _ = generator(config, config.name)
        return files

    def _get_cicd_directories(self, config: ProjectConfig) -> List[str]:
        generator = _CICD_GENERATORS.get(config.cicd_platform)
        if generator is None:
            return []
        _, dirs = generator(config, config.name)
        return dirs

    def _get_primary_language(self, config: ProjectConfig) -> Language:
        if not config.services:
            return Language.PYTHON
        lang_counts: Dict[Language, int] = {}
        for service in config.services:
            lang_counts[service.language] = lang_counts.get(service.language, 0) + 1
        return max(lang_counts, key=lambda k: lang_counts[k])

    def save_to_directory(
        self, report: ScaffoldReport, output_dir: Optional[str] = None
    ) -> str:
        target_dir = output_dir or self.output_dir

        for directory in report.directories:
            dir_path = os.path.join(target_dir, directory)
            self._writer.make_directory(dir_path)

        for file_entry in report.files:
            file_path = os.path.join(target_dir, file_entry.path)
            self._writer.write_file(file_path, file_entry.content, file_entry.executable)

        return os.path.join(target_dir, report.project_name)
