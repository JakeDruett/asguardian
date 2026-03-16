"""
Backend initialization service.

Scaffolds a standard backend project structure with opinionated defaults.
"""

from pathlib import Path
from typing import Optional

from Asgard.BackendInit.templates import (
    APIS_INIT,
    CODING_STANDARDS,
    ENV_EXAMPLE,
    GITIGNORE_ENTRIES,
    GITIGNORE_FULL,
    MODELS_ENUMS,
    MODELS_INIT,
    PROMPTS_INIT,
    README,
    SERVICES_INIT,
    TESTS_INIT,
    UTILITIES_INIT,
)


def _write_if_absent(path: Path, content: str) -> bool:
    """Write content to path only if the file does not already exist.

    Returns True if the file was written, False if it was skipped.
    """
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def _ensure_gitignore(path: Path) -> None:
    """Create or update .gitignore to include required exclusions."""
    required = list(GITIGNORE_ENTRIES)

    if not path.exists():
        path.write_text(GITIGNORE_FULL, encoding="utf-8")
        print(f"  Created  {path.name}")
        return

    existing = path.read_text(encoding="utf-8")
    lines = existing.splitlines()

    missing = []
    for entry in required:
        # Match the entry itself or with a trailing slash for directories.
        if not any(line.strip() in (entry, entry + "/") for line in lines):
            missing.append(entry)

    if not missing:
        print(f"  Skipped  {path.name}  (already up to date)")
        return

    additions = "\n".join(missing)
    separator = "\n" if existing.endswith("\n") else "\n\n"
    updated = existing + separator + "# Added by asgard init-backend\n" + additions + "\n"
    path.write_text(updated, encoding="utf-8")
    print(f"  Updated  {path.name}  (added: {', '.join(missing)})")


def init_backend(folder_name: str, base_dir: Optional[Path] = None) -> int:
    """Scaffold a standard backend project structure.

    Args:
        folder_name: Name of the target directory to create or populate.
        base_dir: Base directory in which to place the folder.
                  Defaults to the current working directory.

    Returns:
        Exit code (0 on success, 1 on error).
    """
    root = (base_dir or Path.cwd()) / folder_name
    root.mkdir(parents=True, exist_ok=True)

    print(f"Initializing backend project in: {root}")
    print()

    directories = [
        ("apis", APIS_INIT),
        ("models", MODELS_INIT),
        ("services", SERVICES_INIT),
        ("prompts", PROMPTS_INIT),
        ("tests", TESTS_INIT),
        ("utilities", UTILITIES_INIT),
    ]

    for dir_name, init_content in directories:
        directory = root / dir_name
        directory.mkdir(exist_ok=True)

        init_file = directory / "__init__.py"
        written = _write_if_absent(init_file, init_content)
        status = "Created " if written else "Skipped "
        print(f"  {status}  {dir_name}/__init__.py")

    # Extra file for models/enums.py
    enums_file = root / "models" / "enums.py"
    written = _write_if_absent(enums_file, MODELS_ENUMS)
    status = "Created " if written else "Skipped "
    print(f"  {status}  models/enums.py")

    print()

    # Top-level files (skip if already present)
    top_level = [
        ("coding_standards.md", CODING_STANDARDS),
        ("readme.md", README),
        (".env.example", ENV_EXAMPLE),
        (".env", ""),
    ]

    for filename, content in top_level:
        file_path = root / filename
        written = _write_if_absent(file_path, content)
        status = "Created " if written else "Skipped "
        print(f"  {status}  {filename}")

    # .gitignore has special merge logic
    _ensure_gitignore(root / ".gitignore")

    print()
    print("Backend project initialized successfully.")
    return 0
