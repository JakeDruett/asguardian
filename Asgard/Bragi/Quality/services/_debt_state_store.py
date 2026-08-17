"""
Bragi Debt State Store (Plan 02 Phase E / RESEARCH_15)

Content-hash keyed per-file debt cache: on re-scan, only files whose
SHA-256 changed are re-analyzed; project totals are updated arithmetically
(`total += sum(new_file_debt) - sum(old_file_debt)`) instead of rescanning
the world. Persisted under `.asgard_cache/bragi_debt_state.json` (per scan
root) and is a prerequisite for Plan 06's PR-differential gating.
"""

import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from pydantic import BaseModel, Field

from Asgard.Bragi.Quality.models.debt_models import DebtItem

STATE_RELATIVE_PATH = Path(".asgard_cache") / "bragi_debt_state.json"
STATE_SCHEMA_VERSION = 1
_HMAC_ENV = "ASGARD_DEBT_HMAC_KEY"


class FileDebtState(BaseModel):
    """Cached per-file debt state: content hash + the items it produced."""
    content_hash: str = Field(..., description="SHA-256 of the file's bytes at last scan")
    debt_minutes: float = Field(0.0, ge=0.0, description="Total remediation minutes for this file")
    item_count: int = Field(0, ge=0, description="Number of debt items last recorded for this file")

    class Config:
        use_enum_values = True


class DebtState(BaseModel):
    """Persisted per-scan-root debt cache."""
    schema_version: int = Field(STATE_SCHEMA_VERSION)
    scan_root: str = Field("", description="Root path this state was computed for")
    files: Dict[str, FileDebtState] = Field(default_factory=dict)
    total_debt_minutes: float = Field(0.0, ge=0.0)

    class Config:
        use_enum_values = True


class DeltaResult(BaseModel):
    """Result of an incremental delta analysis."""
    changed_files: List[str] = Field(default_factory=list, description="Files re-analyzed this run")
    unchanged_files: int = Field(0, ge=0, description="Files skipped because content was unchanged")
    added_or_changed_minutes: float = Field(0.0, description="Debt minutes added by new/changed files")
    removed_minutes: float = Field(0.0, description="Debt minutes removed (deleted/fixed files)")
    total_debt_minutes: float = Field(0.0, ge=0.0, description="Updated project total after the delta")

    class Config:
        use_enum_values = True


def content_hash(file_path: Path) -> Optional[str]:
    """SHA-256 of a file's bytes; None when the file cannot be read or is a symlink."""
    path = Path(file_path)
    if path.is_symlink():
        return None
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            digest = hashlib.sha256()
            while True:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                digest.update(chunk)
            return digest.hexdigest()
        finally:
            os.close(fd)
    except OSError:
        return None


def _state_path(scan_root: Path) -> Path:
    return Path(scan_root) / STATE_RELATIVE_PATH


def _key_path(scan_root: Path) -> Path:
    path = _state_path(scan_root)
    return path.with_name(path.name + ".key")


def _read_nofollow(path: Path) -> bytes:
    if path.is_symlink():
        raise ValueError(f"debt-state path must not be a symlink: {path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        chunks = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _hmac_key(scan_root: Path) -> bytes:
    from Asgard.common._hmac_env import hmac_key_from_env

    env = hmac_key_from_env(_HMAC_ENV)
    if env is not None:
        return env
    return os.urandom(32)


def _canonical_payload(data: dict) -> dict:
    payload = dict(data)
    payload.pop("hmac", None)
    files = payload.get("files")
    if isinstance(files, dict):
        payload["files"] = dict(sorted(files.items()))
    return payload


def _sign_state(scan_root: Path, data: dict) -> str:
    canonical = json.dumps(_canonical_payload(data), sort_keys=True, separators=(",", ":"), default=str)
    return hmac.new(_hmac_key(scan_root), canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def load_state(scan_root: Path) -> DebtState:
    """Load signed debt state. Unsigned, forged, or missing files are empty (full rescan)."""
    empty = DebtState(scan_root=str(scan_root))
    path = _state_path(scan_root)
    if not path.exists() or path.is_symlink():
        return empty
    try:
        data = json.loads(_read_nofollow(path).decode("utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != STATE_SCHEMA_VERSION:
            return empty
        expected = data.get("hmac")
        if not isinstance(expected, str) or not hmac.compare_digest(
            expected, _sign_state(scan_root, data)
        ):
            return empty
        data.pop("hmac", None)
        return DebtState(**data)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
        return empty


def save_state(scan_root: Path, state: DebtState) -> None:
    """Persist signed `state` to `.asgard_cache/bragi_debt_state.json` under `scan_root`."""
    path = _state_path(scan_root)
    if path.is_symlink():
        raise ValueError("debt-state path must not be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(state.model_dump_json())
    payload["files"] = dict(sorted(payload.get("files", {}).items()))
    payload["hmac"] = _sign_state(scan_root, payload)
    raw = (json.dumps(payload, indent=2, sort_keys=False) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, raw)
    finally:
        os.close(fd)
    os.chmod(path, 0o600)


def changed_files(scan_root: Path, candidate_files: Iterable[Path], state: Optional[DebtState] = None) -> List[Path]:
    """
    Files among `candidate_files` whose content hash differs from (or is
    absent from) the persisted state - i.e. the set that needs re-analysis.
    """
    state = state or load_state(scan_root)
    result: List[Path] = []
    for file_path in candidate_files:
        rel = _relative_key(scan_root, file_path)
        current_hash = content_hash(file_path)
        if current_hash is None:
            continue
        if rel is None:
            result.append(file_path)
            continue
        cached = state.files.get(rel)
        if cached is None or cached.content_hash != current_hash:
            result.append(file_path)
    return result


def _relative_key(scan_root: Path, file_path: Path) -> Optional[str]:
    """Relative key under scan_root, or None if the path escapes the root."""
    try:
        resolved = Path(file_path).resolve()
        root = Path(scan_root).resolve()
        if not resolved.is_relative_to(root):
            return None
        return str(resolved.relative_to(root))
    except (OSError, ValueError):
        return None


def _confined_rel(scan_root: Path, rel: str) -> Optional[str]:
    if not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        return None
    return _relative_key(scan_root, Path(scan_root) / rel)


def apply_delta(
    scan_root: Path,
    state: DebtState,
    file_items: Dict[str, List[DebtItem]],
    all_current_files: Iterable[str],
) -> DeltaResult:
    """
    Update `state` arithmetically from freshly-computed `file_items` (only
    for files that were actually re-analyzed) and return the delta.

    `all_current_files` is the full current file set (relative keys) used
    to detect deletions: any cached file absent from it has its debt
    removed from the total.
    """
    all_current = {key for key in all_current_files if _confined_rel(scan_root, key)}
    removed_minutes = 0.0
    for rel, cached in list(state.files.items()):
        if _confined_rel(scan_root, rel) is None or rel not in all_current:
            removed_minutes += cached.debt_minutes
            del state.files[rel]

    added_or_changed_minutes = 0.0
    applied: List[str] = []
    for rel, items in file_items.items():
        confined = _confined_rel(scan_root, rel)
        if confined is None:
            continue
        old_minutes = state.files.get(confined).debt_minutes if confined in state.files else 0.0
        new_minutes = sum(_item_minutes(item) for item in items)
        full_path = Path(scan_root) / confined
        new_hash = content_hash(full_path) or ""
        state.files[confined] = FileDebtState(
            content_hash=new_hash, debt_minutes=new_minutes, item_count=len(items),
        )
        added_or_changed_minutes += new_minutes - old_minutes
        applied.append(confined)

    state.total_debt_minutes = max(
        state.total_debt_minutes + added_or_changed_minutes - removed_minutes, 0.0
    )
    state.scan_root = str(scan_root)

    return DeltaResult(
        changed_files=sorted(applied),
        unchanged_files=max(len(all_current) - len(applied), 0),
        added_or_changed_minutes=added_or_changed_minutes,
        removed_minutes=removed_minutes,
        total_debt_minutes=state.total_debt_minutes,
    )


def _item_minutes(item: DebtItem) -> float:
    """Minutes for one debt item, preferring the effort interval midpoint."""
    if item.effort_interval is not None:
        return item.effort_interval.midpoint_minutes
    return item.effort_hours * 60.0
