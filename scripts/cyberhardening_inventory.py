#!/usr/bin/env python3
"""CyberHardening inventory: discover code files and maintain the scan todo list.

Run from the repository root:

    python scripts/cyberhardening_inventory.py init
    python scripts/cyberhardening_inventory.py status
    python scripts/cyberhardening_inventory.py next [N]
    python scripts/cyberhardening_inventory.py done PATH [--disposition findings|clean] [--finding-ids ID,ID]
    python scripts/cyberhardening_inventory.py remaining
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

VERSION = 1

# Planning folder resolution order from prompt.md
PLANNING_CANDIDATES = (
    "Planning",
    "_Docs/Planning",
    "docs/Planning",
    "Docs/Planning",
)

CODE_EXTENSIONS = {
    # application / library
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".kts",
    ".scala",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".swift",
    ".m",
    ".mm",
    ".rb",
    ".php",
    ".pl",
    ".pm",
    ".lua",
    ".r",
    ".jl",
    ".ex",
    ".exs",
    ".erl",
    ".hs",
    ".clj",
    ".cljs",
    ".groovy",
    ".dart",
    ".zig",
    ".nim",
    ".v",
    ".ml",
    ".mli",
    ".fs",
    ".fsx",
    ".vb",
    ".pas",
    ".asm",
    ".s",
    # shell / automation
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".psm1",
    ".bat",
    ".cmd",
    ".command",
    # web / query / templates
    ".html",
    ".htm",
    ".vue",
    ".svelte",
    ".astro",
    ".ejs",
    ".hbs",
    ".jinja",
    ".j2",
    ".erb",
    ".haml",
    ".pug",
    ".sql",
    ".graphql",
    ".gql",
    # IaC / policy
    ".tf",
    ".tfvars",
    ".hcl",
    ".bicep",
    ".nix",
    ".rego",
    # YAML/YML: include when unsure (CI, IaC, fixtures-as-code)
    ".yml",
    ".yaml",
    # other executable-adjacent
    ".in",
}

# Exact filenames (case-insensitive match on the basename)
WELL_KNOWN_FILENAMES = {
    "dockerfile",
    "containerfile",
    "makefile",
    "gnumakefile",
    "justfile",
    "rakefile",
    "jenkinsfile",
    "vagrantfile",
    "procfile",
    "gunicorn.conf.py",
    "caddyfile",
    "sudoers",
    "crontab",
    "gemfile",
    "berksfile",
    "fastfile",
    "podfile",
    "brewfile",
}

WELL_KNOWN_PREFIXES = (
    "dockerfile.",
    "containerfile.",
    "docker-compose",
    "compose.",
)

WELL_KNOWN_SUFFIXES = (
    ".dockerfile",
    ".containerfile",
    ".service",
    ".socket",
    ".timer",
    ".path",
    ".mount",
    ".automount",
    ".target",
    "sudoers",
)

WELL_KNOWN_CONTAINS = (
    "gulpfile.",
    "webpack.config.",
    "vite.config.",
    "esbuild.config.",
    "rollup.config.",
    "jest.config.",
)

# Directory names skipped entirely (vendor / VCS / artifacts / caches)
EXCLUDE_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".claude",
    "node_modules",
    "vendor",
    ".venv",
    "venv",
    "env",
    "ENV",
    "__pypackages__",
    ".tox",
    ".nox",
    "bower_components",
    "third_party",
    "dist",
    "build",
    "out",
    "target",
    "coverage",
    "htmlcov",
    ".next",
    ".nuxt",
    ".cache",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".pytype",
    ".pyre",
    ".eggs",
    "sdist",
    "wheels",
    ".asgard_cache",
    ".asgard",
    ".benchmarks",
    ".ipynb_checkpoints",
    "asguardian.egg-info",
}

EXCLUDE_DIR_SUFFIXES = (".egg-info",)

# File suffixes that are never code
EXCLUDE_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".class",
    ".o",
    ".a",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".wasm",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".bmp",
    ".svg",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".eot",
    ".mp3",
    ".mp4",
    ".wav",
    ".ogg",
    ".webm",
    ".mov",
    ".avi",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".lock",
}

LOCKFILE_NAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "cargo.lock",
    "go.sum",
    "composer.lock",
    "gemfile.lock",
    "pipfile.lock",
    "uv.lock",
}

ENV_FILE_PREFIXES = (".env",)
ENV_FILE_ALLOWLIST = {".env.example", ".env.sample", ".env.template"}

BINARY_MEDIA = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".bmp",
    ".tiff",
    ".tif",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def repo_root() -> Path:
    return Path.cwd().resolve()


def posix_rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def resolve_planning_dir(root: Path) -> Path:
    for candidate in PLANNING_CANDIDATES:
        p = root / candidate
        if p.is_dir():
            return p
    created = root / "Planning"
    created.mkdir(parents=True, exist_ok=True)
    return created


def resolve_paths(root: Path) -> dict[str, Path]:
    planning = resolve_planning_dir(root)
    workspace = planning / "CyberHardening"
    workspace.mkdir(parents=True, exist_ok=True)
    plan_md = planning / "CyberHardening.md"
    plan_alt = workspace / "00_Plan.md"
    if plan_md.is_file():
        plan = plan_md
    elif plan_alt.is_file():
        plan = plan_alt
    else:
        plan = plan_md
    return {
        "planning": planning,
        "workspace": workspace,
        "plan": plan,
        "todo": workspace / "todo.json",
        "ledger": workspace / "ledger.jsonl",
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_entry(root: Path, path: Path) -> dict[str, Any]:
    st = path.stat()
    return {
        "path": posix_rel(root, path),
        "bytes": int(st.st_size),
        "sha256": sha256_file(path),
        "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
    }


def git_tracked(root: Path) -> set[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()
    return {p for p in proc.stdout.decode("utf-8", "surrogateescape").split("\0") if p}


def git_ignored(root: Path, rel_paths: list[str]) -> set[str]:
    """Return the subset of rel_paths that git considers ignored."""
    if not rel_paths:
        return set()
    ignored: set[str] = set()
    chunk = 2000
    for i in range(0, len(rel_paths), chunk):
        batch = rel_paths[i : i + chunk]
        try:
            proc = subprocess.run(
                ["git", "-C", str(root), "check-ignore", "-z", "--stdin"],
                input=("\0".join(batch) + "\0").encode("utf-8", "surrogateescape"),
                capture_output=True,
                check=False,
            )
        except FileNotFoundError:
            return set()
        ignored.update(
            p for p in proc.stdout.decode("utf-8", "surrogateescape").split("\0") if p
        )
    return ignored


def has_shebang(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            start = fh.read(256)
    except OSError:
        return False
    if not start.startswith(b"#!"):
        return False
    # reject binary-looking shebang files
    if b"\0" in start:
        return False
    return True


def is_min_js_with_source(path: Path) -> bool:
    name = path.name
    if not name.endswith(".min.js"):
        return False
    stem = name[: -len(".min.js")]
    for ext in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"):
        if (path.parent / f"{stem}{ext}").is_file():
            return True
    return False


def looks_like_code(path: Path) -> bool:
    name = path.name
    lower = name.lower()
    suffix = path.suffix.lower()

    if suffix in EXCLUDE_FILE_SUFFIXES:
        return False
    if lower in LOCKFILE_NAMES:
        return False
    if lower.startswith(ENV_FILE_PREFIXES) and lower not in ENV_FILE_ALLOWLIST:
        return False
    if suffix == ".min.js" and is_min_js_with_source(path):
        return False

    if suffix in CODE_EXTENSIONS:
        return True
    if lower in WELL_KNOWN_FILENAMES:
        return True
    if any(lower.startswith(p) for p in WELL_KNOWN_PREFIXES):
        return True
    if any(lower.endswith(s) for s in WELL_KNOWN_SUFFIXES):
        return True
    if any(token in lower for token in WELL_KNOWN_CONTAINS):
        return True

    # extensionless / unusual names: shebang only
    if suffix == "" or "." not in name:
        return has_shebang(path)
    return False


def should_skip_dir(name: str) -> bool:
    if name in EXCLUDE_DIR_NAMES:
        return True
    if any(name.endswith(sfx) for sfx in EXCLUDE_DIR_SUFFIXES):
        return True
    return False


def iter_candidate_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if not should_skip_dir(d))
        for fname in sorted(filenames):
            yield Path(dirpath) / fname


def discover(root: Path) -> list[dict[str, Any]]:
    tracked = git_tracked(root)
    candidates: list[Path] = []
    rels: list[str] = []
    for path in iter_candidate_files(root):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            rel = posix_rel(root, path)
        except ValueError:
            continue
        if not looks_like_code(path):
            continue
        candidates.append(path)
        rels.append(rel)

    ignored = git_ignored(root, rels)
    entries: list[dict[str, Any]] = []
    for path, rel in zip(candidates, rels):
        is_tracked = rel in tracked
        if (not is_tracked) and rel in ignored:
            continue
        try:
            entries.append(file_entry(root, path))
        except OSError:
            continue
    entries.sort(key=lambda e: e["path"])
    return entries


def empty_todo(root: Path, paths: dict[str, Path]) -> dict[str, Any]:
    now = utc_now()
    return {
        "version": VERSION,
        "repo_root": ".",
        "generated_at": now,
        "updated_at": now,
        "planning_dir": posix_rel(root, paths["planning"]),
        "plan_path": posix_rel(root, paths["plan"]),
        "total_discovered": 0,
        "remaining": [],
        "completed": [],
    }


def load_todo(todo_path: Path, root: Path, paths: dict[str, Path]) -> dict[str, Any]:
    if not todo_path.is_file():
        return empty_todo(root, paths)
    with todo_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise SystemExit(f"corrupt todo file: {todo_path}")
    data.setdefault("version", VERSION)
    data.setdefault("remaining", [])
    data.setdefault("completed", [])
    return data


def save_todo(todo_path: Path, data: dict[str, Any]) -> None:
    data["updated_at"] = utc_now()
    tmp = todo_path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=False)
        fh.write("\n")
    tmp.replace(todo_path)


def cmd_init(root: Path, paths: dict[str, Path]) -> int:
    todo_path = paths["todo"]
    data = load_todo(todo_path, root, paths)
    if "generated_at" not in data:
        data["generated_at"] = utc_now()
    data["repo_root"] = "."
    data["planning_dir"] = posix_rel(root, paths["planning"])
    data["plan_path"] = posix_rel(root, paths["plan"])

    discovered = discover(root)
    completed_paths = {c["path"] for c in data.get("completed", [])}
    remaining_by_path = {r["path"]: r for r in data.get("remaining", [])}

    new_remaining: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in discovered:
        p = entry["path"]
        seen.add(p)
        if p in completed_paths:
            continue
        # refresh metadata for remaining items
        new_remaining.append(entry)
        remaining_by_path.pop(p, None)

    # keep remaining entries that disappeared from the tree only if still listed;
    # drop vanished paths so the todo reflects the current inventory
    new_remaining.sort(key=lambda e: e["path"])
    data["remaining"] = new_remaining
    data["total_discovered"] = len(discovered)
    save_todo(todo_path, data)

    # ensure ledger file exists
    paths["ledger"].touch(exist_ok=True)

    print(
        f"init: discovered={data['total_discovered']} "
        f"remaining={len(data['remaining'])} "
        f"completed={len(data.get('completed', []))} "
        f"todo={posix_rel(root, todo_path)}"
    )
    return 0


def cmd_status(root: Path, paths: dict[str, Path]) -> int:
    data = load_todo(paths["todo"], root, paths)
    remaining = len(data.get("remaining", []))
    completed = len(data.get("completed", []))
    total = data.get("total_discovered", remaining + completed)
    print(f"total={total} remaining={remaining} completed={completed}")
    print(f"todo={posix_rel(root, paths['todo'])}")
    print(f"plan={data.get('plan_path', posix_rel(root, paths['plan']))}")
    return 0


def cmd_next(root: Path, paths: dict[str, Path], n: int) -> int:
    data = load_todo(paths["todo"], root, paths)
    remaining = data.get("remaining", [])
    for item in remaining[: max(n, 0)]:
        print(item["path"])
    return 0


def cmd_remaining(root: Path, paths: dict[str, Path]) -> int:
    data = load_todo(paths["todo"], root, paths)
    for item in data.get("remaining", []):
        print(item["path"])
    return 0


def cmd_done(
    root: Path,
    paths: dict[str, Path],
    target: str,
    disposition: str,
    finding_ids: list[str],
) -> int:
    data = load_todo(paths["todo"], root, paths)
    norm = target.replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    if norm.startswith("/"):
        print(f"error: path must be repo-relative: {target}", file=sys.stderr)
        return 1
    remaining = data.get("remaining", [])
    match_idx = None
    for i, item in enumerate(remaining):
        if item["path"] == norm:
            match_idx = i
            break
    if match_idx is None:
        print(f"error: not remaining: {norm}", file=sys.stderr)
        return 1
    item = remaining.pop(match_idx)
    completed = {
        "path": item["path"],
        "completed_at": utc_now(),
        "finding_ids": finding_ids,
        "disposition": disposition,
        "bytes": item.get("bytes"),
        "sha256": item.get("sha256"),
    }
    data["completed"].append(completed)
    save_todo(paths["todo"], data)
    print(f"done: {norm} disposition={disposition} finding_ids={finding_ids}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CyberHardening inventory / todo manager")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="discover files; create/merge todo.json")
    sub.add_parser("status", help="print total / remaining / completed")
    nxt = sub.add_parser("next", help="print next N remaining paths")
    nxt.add_argument("n", nargs="?", default=1, type=int)
    sub.add_parser("remaining", help="print every remaining path")
    done = sub.add_parser("done", help="pop PATH from remaining after the plan is updated")
    done.add_argument("path")
    done.add_argument(
        "--disposition",
        choices=("findings", "clean"),
        default="clean",
    )
    done.add_argument(
        "--finding-ids",
        default="",
        help="comma-separated finding IDs recorded for this file",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    paths = resolve_paths(root)
    if args.cmd == "init":
        return cmd_init(root, paths)
    if args.cmd == "status":
        return cmd_status(root, paths)
    if args.cmd == "next":
        return cmd_next(root, paths, args.n)
    if args.cmd == "remaining":
        return cmd_remaining(root, paths)
    if args.cmd == "done":
        ids = [x for x in args.finding_ids.split(",") if x]
        return cmd_done(root, paths, args.path, args.disposition, ids)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
