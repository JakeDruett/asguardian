"""
Heimdall Requirements Checker Service

Validates that all imported packages are listed in requirements files
and identifies unused packages.
"""

import ast
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from Asgard.Heimdall.Dependencies.models.requirements_models import (
    ImportInfo,
    PackageInfo,
    RequirementsConfig,
    RequirementsIssue,
    RequirementsIssueType,
    RequirementsResult,
    RequirementsSeverity,
)


# Common import name to package name mappings
# When import name differs from pip package name
IMPORT_TO_PACKAGE_MAP = {
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    "jose": "python-jose",
    "jwt": "PyJWT",
    "dotenv": "python-dotenv",
    "multipart": "python-multipart",
    "magic": "python-magic",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "cx_Oracle": "cx-Oracle",
    "google": "google-api-python-client",
    "googleapiclient": "google-api-python-client",
    "msal": "msal",
    "azure": "azure-identity",
    "botocore": "botocore",
    "boto3": "boto3",
    "redis": "redis",
    "celery": "celery",
    "flask": "Flask",
    "django": "Django",
    "fastapi": "fastapi",
    "starlette": "starlette",
    "uvicorn": "uvicorn",
    "pydantic": "pydantic",
    "sqlalchemy": "SQLAlchemy",
    "alembic": "alembic",
    "psycopg2": "psycopg2-binary",
    "pymysql": "PyMySQL",
    "httpx": "httpx",
    "aiohttp": "aiohttp",
    "requests": "requests",
    "websockets": "websockets",
    "numpy": "numpy",
    "pandas": "pandas",
    "scipy": "scipy",
    "matplotlib": "matplotlib",
    "seaborn": "seaborn",
    "pytest": "pytest",
    "coverage": "coverage",
    "mock": "mock",
    "freezegun": "freezegun",
    "faker": "Faker",
    "factory": "factory-boy",
    "hypothesis": "hypothesis",
    "locust": "locust",
    "playwright": "playwright",
    "anthropic": "anthropic",
    "openai": "openai",
    "tiktoken": "tiktoken",
    "transformers": "transformers",
    "torch": "torch",
    "tensorflow": "tensorflow",
    "keras": "keras",
    "jinja2": "Jinja2",
    "markdown": "Markdown",
    "pygments": "Pygments",
    "passlib": "passlib",
    "cryptography": "cryptography",
    "fernet": "cryptography",
    "hvac": "hvac",
    "kubernetes": "kubernetes",
    "docker": "docker",
    "paramiko": "paramiko",
    "fabric": "fabric",
    "invoke": "invoke",
}

# Standard library modules to exclude from checks
STDLIB_MODULES = {
    "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
    "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
    "binhex", "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb",
    "chunk", "cmath", "cmd", "code", "codecs", "codeop", "collections",
    "colorsys", "compileall", "concurrent", "configparser", "contextlib",
    "contextvars", "copy", "copyreg", "cProfile", "crypt", "csv",
    "ctypes", "curses", "dataclasses", "datetime", "dbm", "decimal",
    "difflib", "dis", "distutils", "doctest", "email", "encodings",
    "enum", "errno", "faulthandler", "fcntl", "filecmp", "fileinput",
    "fnmatch", "fractions", "ftplib", "functools", "gc", "getopt",
    "getpass", "gettext", "glob", "graphlib", "grp", "gzip", "hashlib",
    "heapq", "hmac", "html", "http", "idlelib", "imaplib", "imghdr",
    "imp", "importlib", "inspect", "io", "ipaddress", "itertools",
    "json", "keyword", "lib2to3", "linecache", "locale", "logging",
    "lzma", "mailbox", "mailcap", "marshal", "math", "mimetypes",
    "mmap", "modulefinder", "multiprocessing", "netrc", "nis",
    "nntplib", "numbers", "operator", "optparse", "os", "ossaudiodev",
    "parser", "pathlib", "pdb", "pickle", "pickletools", "pipes",
    "pkgutil", "platform", "plistlib", "poplib", "posix", "posixpath",
    "pprint", "profile", "pstats", "pty", "pwd", "py_compile",
    "pyclbr", "pydoc", "queue", "quopri", "random", "re", "readline",
    "reprlib", "resource", "rlcompleter", "runpy", "sched", "secrets",
    "select", "selectors", "shelve", "shlex", "shutil", "signal",
    "site", "smtpd", "smtplib", "sndhdr", "socket", "socketserver",
    "spwd", "sqlite3", "ssl", "stat", "statistics", "string", "stringprep",
    "struct", "subprocess", "sunau", "symtable", "sys", "sysconfig",
    "syslog", "tabnanny", "tarfile", "telnetlib", "tempfile", "termios",
    "test", "textwrap", "threading", "time", "timeit", "tkinter",
    "token", "tokenize", "trace", "traceback", "tracemalloc", "tty",
    "turtle", "turtledemo", "types", "typing", "typing_extensions",
    "unicodedata", "unittest", "urllib", "uu", "uuid", "venv",
    "warnings", "wave", "weakref", "webbrowser", "winreg", "winsound",
    "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport",
    "zlib", "_thread", "__future__",
}


class ImportVisitor(ast.NodeVisitor):
    """AST visitor that extracts import statements."""

    def __init__(self):
        self.imports: List[Dict] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import X' statements."""
        for alias in node.names:
            self.imports.append({
                "package_name": alias.name.split(".")[0],
                "import_statement": f"import {alias.name}",
                "line_number": node.lineno,
                "import_type": "import",
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle 'from X import Y' statements."""
        if node.module:
            package_name = node.module.split(".")[0]
            names = ", ".join(a.name for a in node.names if a.name != "*")
            self.imports.append({
                "package_name": package_name,
                "import_statement": f"from {node.module} import {names}",
                "line_number": node.lineno,
                "import_type": "from_import",
            })
        self.generic_visit(node)


class RequirementsChecker:
    """
    Validates requirements.txt against actual imports in the codebase.

    Features:
    - Detects missing packages (imported but not in requirements)
    - Detects unused packages (in requirements but not imported)
    - Handles import name to package name mapping
    - Supports multiple requirements files
    """

    def __init__(self, config: RequirementsConfig):
        """Initialize the requirements checker."""
        self.config = config
        self._import_to_package = IMPORT_TO_PACKAGE_MAP.copy()

    def analyze(self) -> RequirementsResult:
        """
        Run requirements analysis on the configured path.

        Returns:
            RequirementsResult with all findings
        """
        start_time = time.time()
        scan_path = Path(self.config.scan_path).resolve()

        if not scan_path.exists():
            raise FileNotFoundError(f"Path not found: {scan_path}")

        # Parse requirements files
        requirements, req_files = self._parse_requirements(scan_path)

        # Scan imports
        imports, files_scanned = self._scan_imports(scan_path)

        # Compare and find issues
        issues = self._find_issues(requirements, imports)

        duration = time.time() - start_time

        return RequirementsResult(
            scan_path=str(scan_path),
            scanned_at=datetime.now(),
            scan_duration_seconds=duration,
            config=self.config,
            requirements=requirements,
            requirements_files_found=req_files,
            imports=imports,
            files_scanned=files_scanned,
            issues=issues,
            import_to_package_map=self._import_to_package,
        )

    def sync(self, result: RequirementsResult, target_file: str = "requirements.txt") -> int:
        """
        Synchronize requirements.txt based on analysis.

        Returns number of changes made.
        """
        scan_path = Path(self.config.scan_path).resolve()
        req_file = scan_path / target_file

        changes = 0

        # Read existing requirements
        existing_lines = []
        if req_file.exists():
            existing_lines = req_file.read_text().strip().split("\n")

        # Get packages to add
        additions = result.get_suggested_additions()
        for pkg in additions:
            if not any(pkg.lower() in line.lower() for line in existing_lines):
                existing_lines.append(pkg)
                changes += 1

        # Get packages to remove (if check_unused is enabled)
        if self.config.check_unused:
            removals = set(result.get_suggested_removals())
            new_lines = []
            for line in existing_lines:
                # Parse package name from line
                pkg_name = self._parse_package_name_from_line(line)
                if pkg_name and pkg_name.lower() in [r.lower() for r in removals]:
                    changes += 1
                    continue
                new_lines.append(line)
            existing_lines = new_lines

        # Write back
        if changes > 0:
            req_file.write_text("\n".join(existing_lines) + "\n")

        return changes

    def _parse_requirements(self, scan_path: Path) -> tuple[List[PackageInfo], List[str]]:
        """Parse all requirements files."""
        packages = []
        found_files = []

        for req_file in self.config.requirements_files:
            req_path = scan_path / req_file
            if req_path.exists():
                found_files.append(req_file)
                packages.extend(self._parse_requirements_file(req_path))

        return packages, found_files

    def _parse_requirements_file(self, req_path: Path) -> List[PackageInfo]:
        """Parse a single requirements file."""
        packages = []
        content = req_path.read_text()

        for line_num, line in enumerate(content.split("\n"), 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Skip -r includes and -e editable installs for now
            if line.startswith("-r") or line.startswith("--requirement"):
                continue

            is_editable = line.startswith("-e") or line.startswith("--editable")
            if is_editable:
                line = line.split(None, 1)[1] if " " in line else ""

            # Parse package name and version
            pkg_info = self._parse_package_line(line, str(req_path), line_num, is_editable)
            if pkg_info:
                packages.append(pkg_info)

        return packages

    def _parse_package_line(
        self, line: str, source_file: str, line_number: int, is_editable: bool
    ) -> Optional[PackageInfo]:
        """Parse a single package line from requirements."""
        if not line:
            return None

        # Handle extras [extra1,extra2]
        extras = []
        extras_match = re.search(r"\[([^\]]+)\]", line)
        if extras_match:
            extras = [e.strip() for e in extras_match.group(1).split(",")]
            line = line[:extras_match.start()] + line[extras_match.end():]

        # Handle version specifiers
        version = None
        version_spec = None
        for op in ["===", "~=", "==", ">=", "<=", "!=", ">", "<"]:
            if op in line:
                parts = line.split(op, 1)
                name = parts[0].strip()
                version_spec = op + parts[1].split(";")[0].strip()  # Remove environment markers
                version = parts[1].split(";")[0].strip()
                break
        else:
            name = line.split(";")[0].strip()  # Handle environment markers

        if not name:
            return None

        return PackageInfo(
            name=name.lower(),
            version=version,
            version_spec=version_spec,
            source_file=source_file,
            line_number=line_number,
            extras=extras,
            is_editable=is_editable,
        )

    def _parse_package_name_from_line(self, line: str) -> Optional[str]:
        """Extract package name from a requirements line."""
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            return None

        # Remove extras
        if "[" in line:
            line = line.split("[")[0]

        # Remove version spec
        for op in ["===", "~=", "==", ">=", "<=", "!=", ">", "<"]:
            if op in line:
                line = line.split(op)[0]
                break

        # Remove environment markers
        if ";" in line:
            line = line.split(";")[0]

        return line.strip()

    def _scan_imports(self, scan_path: Path) -> tuple[List[ImportInfo], int]:
        """Scan all Python files for imports."""
        imports = []
        files_scanned = 0

        for ext in self.config.include_extensions:
            pattern = f"**/*{ext}"
            for file_path in scan_path.glob(pattern):
                if self._should_include_file(file_path):
                    file_imports = self._extract_imports(file_path, scan_path)
                    imports.extend(file_imports)
                    files_scanned += 1

        return imports, files_scanned

    def _should_include_file(self, file_path: Path) -> bool:
        """Check if a file should be included in analysis."""
        path_str = str(file_path)

        for pattern in self.config.exclude_patterns:
            if pattern in path_str:
                return False

        return True

    def _extract_imports(self, file_path: Path, scan_path: Path) -> List[ImportInfo]:
        """Extract imports from a single file."""
        imports = []

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
            visitor = ImportVisitor()
            visitor.visit(tree)

            rel_path = str(file_path.relative_to(scan_path))

            for imp in visitor.imports:
                imports.append(ImportInfo(
                    package_name=imp["package_name"],
                    import_statement=imp["import_statement"],
                    file_path=rel_path,
                    line_number=imp["line_number"],
                    import_type=imp["import_type"],
                ))
        except (SyntaxError, UnicodeDecodeError):
            pass

        return imports

    def _find_issues(
        self, requirements: List[PackageInfo], imports: List[ImportInfo]
    ) -> List[RequirementsIssue]:
        """Find discrepancies between requirements and imports."""
        issues = []

        # Build sets for comparison
        req_packages = {pkg.name.lower() for pkg in requirements}

        # Get unique imported packages (excluding stdlib)
        imported_packages: Set[str] = set()
        import_locations: Dict[str, List[str]] = {}

        for imp in imports:
            pkg = imp.package_name.lower()

            # Skip stdlib
            if pkg in STDLIB_MODULES:
                continue

            # Map import name to package name
            mapped_pkg = self._import_to_package.get(pkg, pkg).lower()
            imported_packages.add(mapped_pkg)

            # Track where package is imported
            if mapped_pkg not in import_locations:
                import_locations[mapped_pkg] = []
            import_locations[mapped_pkg].append(f"{imp.file_path}:{imp.line_number}")

        # Find missing packages (imported but not in requirements)
        for pkg in imported_packages:
            if pkg not in req_packages:
                # Double-check it's not a local package
                if not self._is_local_package(pkg, Path(self.config.scan_path)):
                    locations = import_locations.get(pkg, [])
                    issues.append(RequirementsIssue(
                        issue_type=RequirementsIssueType.MISSING,
                        severity=RequirementsSeverity.ERROR,
                        package_name=pkg,
                        message=f"Package '{pkg}' is imported but not in requirements",
                        details={
                            "locations": locations[:5],  # First 5 locations
                            "total_imports": len(locations),
                        },
                    ))

        # Find unused packages (in requirements but not imported)
        if self.config.check_unused:
            for pkg in requirements:
                pkg_name = pkg.name.lower()

                # Check if any import maps to this package
                is_used = pkg_name in imported_packages

                # Also check original import names
                for import_name, package_name in self._import_to_package.items():
                    if package_name.lower() == pkg_name and import_name.lower() in {
                        i.package_name.lower() for i in imports
                    }:
                        is_used = True
                        break

                if not is_used:
                    issues.append(RequirementsIssue(
                        issue_type=RequirementsIssueType.UNUSED,
                        severity=RequirementsSeverity.WARNING,
                        package_name=pkg_name,
                        message=f"Package '{pkg_name}' in requirements but not imported",
                        details={
                            "file": pkg.source_file,
                            "line": pkg.line_number,
                        },
                    ))

        return issues

    def _is_local_package(self, package_name: str, scan_path: Path) -> bool:
        """Check if a package name corresponds to a local package/module."""
        # Check for directory with __init__.py
        pkg_dir = scan_path / package_name
        if pkg_dir.is_dir() and (pkg_dir / "__init__.py").exists():
            return True

        # Check for single module file
        pkg_file = scan_path / f"{package_name}.py"
        if pkg_file.exists():
            return True

        return False

    def generate_report(self, result: RequirementsResult, output_format: str = "text") -> str:
        """Generate a formatted report."""
        if output_format == "json":
            return self._generate_json_report(result)
        elif output_format == "markdown":
            return self._generate_markdown_report(result)
        else:
            return self._generate_text_report(result)

    def _generate_text_report(self, result: RequirementsResult) -> str:
        """Generate text format report."""
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("  HEIMDALL REQUIREMENTS CHECK REPORT")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"  Scan Path:           {result.scan_path}")
        lines.append(f"  Scanned At:          {result.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  Duration:            {result.scan_duration_seconds:.2f}s")
        lines.append(f"  Files Scanned:       {result.files_scanned}")
        lines.append(f"  Requirements Files:  {', '.join(result.requirements_files_found) or 'None found'}")
        lines.append("")

        if result.has_issues:
            lines.append("-" * 70)
            lines.append("  ISSUES FOUND")
            lines.append("-" * 70)
            lines.append("")

            # Missing packages
            missing = result.missing_packages
            if missing:
                lines.append(f"  [ERROR] Missing Packages ({len(missing)}):")
                lines.append("")
                for issue in missing:
                    lines.append(f"    - {issue.package_name}")
                    locs = issue.details.get("locations", [])[:3]
                    for loc in locs:
                        lines.append(f"        Imported at: {loc}")
                    if issue.details.get("total_imports", 0) > 3:
                        lines.append(f"        ... and {issue.details['total_imports'] - 3} more")
                lines.append("")

            # Unused packages
            unused = result.unused_packages
            if unused:
                lines.append(f"  [WARNING] Unused Packages ({len(unused)}):")
                lines.append("")
                for issue in unused:
                    lines.append(f"    - {issue.package_name}")
                    if "file" in issue.details:
                        lines.append(f"        In: {issue.details['file']}:{issue.details.get('line', '')}")
                lines.append("")
        else:
            lines.append("  All requirements are in sync!")
            lines.append("")

        lines.append("-" * 70)
        lines.append("  SUMMARY")
        lines.append("-" * 70)
        lines.append("")
        lines.append(f"  Total Requirements:  {result.total_requirements}")
        lines.append(f"  Unique Imports:      {result.total_imports}")
        lines.append(f"  Missing Packages:    {result.missing_count}")
        lines.append(f"  Unused Packages:     {result.unused_count}")
        lines.append("")
        lines.append("=" * 70)
        lines.append("")

        return "\n".join(lines)

    def _generate_json_report(self, result: RequirementsResult) -> str:
        """Generate JSON format report."""
        output = {
            "scan_path": result.scan_path,
            "scanned_at": result.scanned_at.isoformat(),
            "scan_duration_seconds": result.scan_duration_seconds,
            "files_scanned": result.files_scanned,
            "requirements_files": result.requirements_files_found,
            "summary": {
                "total_requirements": result.total_requirements,
                "unique_imports": result.total_imports,
                "missing_count": result.missing_count,
                "unused_count": result.unused_count,
                "has_issues": result.has_issues,
            },
            "issues": [
                {
                    "type": i.issue_type.value,
                    "severity": i.severity.value,
                    "package": i.package_name,
                    "message": i.message,
                    "details": i.details,
                }
                for i in result.issues
            ],
            "suggested_additions": result.get_suggested_additions(),
            "suggested_removals": result.get_suggested_removals(),
        }

        return json.dumps(output, indent=2)

    def _generate_markdown_report(self, result: RequirementsResult) -> str:
        """Generate Markdown format report."""
        lines = []
        lines.append("# Heimdall Requirements Check Report")
        lines.append("")
        lines.append(f"- **Scan Path:** `{result.scan_path}`")
        lines.append(f"- **Scanned At:** {result.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **Duration:** {result.scan_duration_seconds:.2f}s")
        lines.append(f"- **Files Scanned:** {result.files_scanned}")
        lines.append(f"- **Requirements Files:** {', '.join(result.requirements_files_found) or 'None found'}")
        lines.append("")

        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Requirements:** {result.total_requirements}")
        lines.append(f"- **Unique Imports:** {result.total_imports}")
        lines.append(f"- **Missing Packages:** {result.missing_count}")
        lines.append(f"- **Unused Packages:** {result.unused_count}")
        lines.append("")

        if result.has_issues:
            lines.append("## Issues")
            lines.append("")

            missing = result.missing_packages
            if missing:
                lines.append("### Missing Packages")
                lines.append("")
                lines.append("| Package | Imported At |")
                lines.append("|---------|-------------|")
                for issue in missing:
                    locs = ", ".join(issue.details.get("locations", [])[:2])
                    lines.append(f"| `{issue.package_name}` | {locs} |")
                lines.append("")

            unused = result.unused_packages
            if unused:
                lines.append("### Unused Packages")
                lines.append("")
                lines.append("| Package | Location |")
                lines.append("|---------|----------|")
                for issue in unused:
                    loc = f"{issue.details.get('file', '')}:{issue.details.get('line', '')}"
                    lines.append(f"| `{issue.package_name}` | {loc} |")
                lines.append("")

            # Suggestions
            if missing:
                lines.append("## Suggested Additions")
                lines.append("")
                lines.append("```")
                for pkg in result.get_suggested_additions():
                    lines.append(pkg)
                lines.append("```")
                lines.append("")

        lines.append("")

        return "\n".join(lines)
