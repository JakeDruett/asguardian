"""
Linter Initializer Service

Detects project type and generates appropriate linting configuration files
based on GAIA coding standards. Also generates VSCode editor settings and
checks for required tool/extension availability.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from Asgard.Heimdall.Init.templates import (
    PYTHON_TEMPLATES,
    PYTHON_TOOL_REQUIREMENTS,
    TYPESCRIPT_NPM_REQUIREMENTS,
    TYPESCRIPT_TEMPLATES,
    TYPESCRIPT_TOOL_REQUIREMENTS,
    VSCODE_EXTENSIONS_PYTHON,
    VSCODE_EXTENSIONS_TYPESCRIPT,
    VSCODE_SETTINGS_PYTHON,
    VSCODE_SETTINGS_TYPESCRIPT,
)


class LinterInitializer:
    """Generates linting configuration files for new projects."""

    PYTHON_INDICATORS = [
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "requirements.txt",
        "Pipfile",
    ]

    TYPESCRIPT_INDICATORS = [
        "package.json",
        "tsconfig.json",
    ]

    def __init__(self, project_path: Path, project_name: Optional[str] = None, force: bool = False):
        self.project_path = project_path.resolve()
        self.project_name = project_name or self.project_path.name
        self.force = force

    def detect_project_type(self) -> tuple[bool, bool]:
        """Detect whether the project is Python, TypeScript/JS, or both.

        Returns:
            Tuple of (is_python, is_typescript).
        """
        is_python = False
        is_typescript = False

        for indicator in self.PYTHON_INDICATORS:
            if (self.project_path / indicator).exists():
                is_python = True
                break

        if not is_python:
            py_files = list(self.project_path.glob("**/*.py"))
            if py_files:
                is_python = True

        for indicator in self.TYPESCRIPT_INDICATORS:
            if (self.project_path / indicator).exists():
                is_typescript = True
                break

        if not is_typescript:
            ts_files = list(self.project_path.glob("**/*.ts")) + list(self.project_path.glob("**/*.tsx"))
            if ts_files:
                is_typescript = True

        return is_python, is_typescript

    def _has_existing_section(self, filepath: Path, section_marker: str) -> bool:
        """Check if a pyproject.toml already contains a given TOML section header."""
        if not filepath.exists():
            return False
        content = filepath.read_text(encoding="utf-8")
        return section_marker in content

    def _write_file(self, filename: str, content: str, mode: str) -> tuple[str, str]:
        """Write a config file.

        Args:
            filename: Target filename.
            content: File content with {project_name} placeholders.
            mode: "create" for new files, "append" to append to existing.

        Returns:
            Tuple of (filename, status) where status is "created", "appended", "skipped", or "exists".
        """
        filepath = self.project_path / filename
        rendered = content.replace("{project_name}", self.project_name)

        if mode == "append":
            if filepath.exists():
                for line in rendered.strip().splitlines():
                    stripped = line.strip()
                    if stripped.startswith("[tool."):
                        if self._has_existing_section(filepath, stripped):
                            if not self.force:
                                return filename, "skipped (section exists)"
                            break
                        break

                with open(filepath, "a", encoding="utf-8") as f:
                    f.write(rendered)
                return filename, "appended"
            else:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(rendered)
                return filename, "created"
        else:
            if filepath.exists() and not self.force:
                return filename, "exists (use --force to overwrite)"
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(rendered)
            return filename, "created"

    def _write_json_file(self, filename: str, data: dict, merge: bool = True) -> tuple[str, str]:
        """Write a JSON config file, optionally merging with existing content.

        Args:
            filename: Target filename relative to project_path.
            data: Dictionary to write as JSON.
            merge: If True and file exists, merge new keys into existing JSON.

        Returns:
            Tuple of (filename, status).
        """
        filepath = self.project_path / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if filepath.exists() and not self.force:
            if merge:
                existing = json.loads(filepath.read_text(encoding="utf-8"))
                existing.update(data)
                data = existing
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                    f.write("\n")
                return filename, "merged"
            else:
                return filename, "exists (use --force to overwrite)"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        return filename, "created"

    def init_python(self) -> list[tuple[str, str]]:
        """Generate Python linting configs (ruff, mypy, pre-commit).

        Returns:
            List of (filename, status) tuples.
        """
        results = []
        has_pyproject = (self.project_path / "pyproject.toml").exists()

        for name, template in PYTHON_TEMPLATES.items():
            if name == "ruff" and not has_pyproject:
                result = self._write_file(
                    template["standalone_filename"],
                    template["standalone_content"],
                    "create",
                )
                results.append(result)
                continue

            result = self._write_file(
                template["filename"],
                template["content"],
                template["mode"],
            )
            results.append(result)

        return results

    def init_typescript(self) -> list[tuple[str, str]]:
        """Generate TypeScript/JS linting configs (eslint, tsconfig, prettier).

        Returns:
            List of (filename, status) tuples.
        """
        results = []

        for _name, template in TYPESCRIPT_TEMPLATES.items():
            result = self._write_file(
                template["filename"],
                template["content"],
                template["mode"],
            )
            results.append(result)

        return results

    def init_vscode(self, is_python: bool, is_typescript: bool) -> list[tuple[str, str]]:
        """Generate .vscode/settings.json and .vscode/extensions.json.

        Args:
            is_python: Whether to include Python editor settings.
            is_typescript: Whether to include TypeScript editor settings.

        Returns:
            List of (filename, status) tuples.
        """
        results = []

        # Build merged settings
        settings: dict = {}
        if is_python:
            settings.update(VSCODE_SETTINGS_PYTHON)
        if is_typescript:
            settings.update(VSCODE_SETTINGS_TYPESCRIPT)

        if settings:
            results.append(self._write_json_file(".vscode/settings.json", settings, merge=True))

        # Build extension recommendations
        extensions: list[str] = []
        if is_python:
            extensions.extend(VSCODE_EXTENSIONS_PYTHON)
        if is_typescript:
            extensions.extend(VSCODE_EXTENSIONS_TYPESCRIPT)

        if extensions:
            ext_data = {"recommendations": sorted(set(extensions))}
            results.append(self._write_json_file(".vscode/extensions.json", ext_data, merge=False))

        return results

    def check_tools(self, is_python: bool, is_typescript: bool) -> list[dict]:
        """Check which required CLI tools and packages are missing.

        Args:
            is_python: Whether to check Python tools.
            is_typescript: Whether to check TypeScript tools.

        Returns:
            List of dicts with keys: name, installed (bool), install, purpose.
        """
        results = []

        if is_python:
            for tool in PYTHON_TOOL_REQUIREMENTS:
                installed = shutil.which(tool["command"]) is not None
                results.append({
                    "name": tool["name"],
                    "installed": installed,
                    "install": tool["install"],
                    "purpose": tool["purpose"],
                })

        if is_typescript:
            for tool in TYPESCRIPT_TOOL_REQUIREMENTS:
                installed = shutil.which(tool["command"]) is not None
                results.append({
                    "name": tool["name"],
                    "installed": installed,
                    "install": tool["install"],
                    "purpose": tool["purpose"],
                })

            # Check npm packages in project's node_modules
            npx_available = shutil.which("npx") is not None
            if npx_available:
                for pkg in TYPESCRIPT_NPM_REQUIREMENTS:
                    pkg_path = self.project_path / "node_modules" / pkg["package"]
                    installed = pkg_path.exists()
                    results.append({
                        "name": pkg["name"],
                        "installed": installed,
                        "install": pkg["install"],
                        "purpose": pkg["purpose"],
                    })
            else:
                for pkg in TYPESCRIPT_NPM_REQUIREMENTS:
                    results.append({
                        "name": pkg["name"],
                        "installed": False,
                        "install": pkg["install"],
                        "purpose": pkg["purpose"],
                    })

        return results

    def check_vscode_extensions(self, is_python: bool, is_typescript: bool) -> list[dict]:
        """Check which recommended VSCode extensions are installed.

        Args:
            is_python: Whether to check Python extensions.
            is_typescript: Whether to check TypeScript extensions.

        Returns:
            List of dicts with keys: extension_id, installed (bool), name.
        """
        results = []
        extension_ids = []
        if is_python:
            extension_ids.extend(VSCODE_EXTENSIONS_PYTHON)
        if is_typescript:
            extension_ids.extend(VSCODE_EXTENSIONS_TYPESCRIPT)

        if not extension_ids:
            return results

        # Try to get installed extensions from 'code' CLI
        installed_extensions: set[str] = set()
        code_cmd = shutil.which("code")
        if code_cmd:
            try:
                proc = subprocess.run(
                    [code_cmd, "--list-extensions"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if proc.returncode == 0:
                    installed_extensions = {ext.strip().lower() for ext in proc.stdout.splitlines()}
            except (subprocess.TimeoutExpired, OSError):
                pass

        for ext_id in sorted(set(extension_ids)):
            installed = ext_id.lower() in installed_extensions
            results.append({
                "extension_id": ext_id,
                "installed": installed,
            })

        return results

    def init_all(self, project_type: Optional[str] = None) -> list[tuple[str, str]]:
        """Initialize linting configs based on detected or specified project type.

        Args:
            project_type: Force a specific type: "python", "typescript", or "both".
                         If None, auto-detects from project contents.

        Returns:
            List of (filename, status) tuples.
        """
        results = []

        if project_type == "python":
            is_python, is_typescript = True, False
        elif project_type == "typescript":
            is_python, is_typescript = False, True
        elif project_type == "both":
            is_python, is_typescript = True, True
        else:
            is_python, is_typescript = self.detect_project_type()

        if not is_python and not is_typescript:
            return [("(none)", "no project type detected - use --type to specify")]

        if is_python:
            results.extend(self.init_python())

        if is_typescript:
            results.extend(self.init_typescript())

        # Generate VSCode editor integration
        results.extend(self.init_vscode(is_python, is_typescript))

        return results
