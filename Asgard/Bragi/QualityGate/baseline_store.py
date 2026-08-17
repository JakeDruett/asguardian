"""
Fingerprint Baseline Store — per-branch finding fingerprint sets.

Persists the set of finding fingerprints observed on a reference branch
(typically `main`), keyed by commit, so differential gate evaluation can
classify PR findings as NEW vs PRE-EXISTING.

Discipline (RESEARCH_15 / SonarQube cache rules):
    - Only reference-branch scans write the baseline; PR evaluations load it
      read-only and never write back.
    - `ratchet_update` is one-way: fixed findings leave the baseline forever;
      new findings never enter it implicitly. Debt can only go down.

Storage is a plain JSON file under `.asgard_cache/` in the project root —
no network, no external services.
"""

import hashlib
import hmac
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from pydantic import BaseModel, Field

_HMAC_ENV = "ASGARD_QG_HMAC_KEY"


class BranchBaseline(BaseModel):
    """Fingerprint set for one branch at one commit."""
    branch: str = Field(..., description="Branch name")
    commit: str = Field("", description="Commit sha the baseline was captured at")
    captured_at: datetime = Field(default_factory=datetime.now)
    fingerprints: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True

    @property
    def fingerprint_set(self) -> Set[str]:
        """Fingerprints as a set for O(1) membership checks."""
        return set(self.fingerprints)


class FingerprintBaselineStore:
    """
    Loads and saves per-branch fingerprint baselines.

    Usage:
        store = FingerprintBaselineStore(project_path)
        store.capture("main", commit_sha, fingerprints)     # main-branch scan
        baseline = store.load("main")                        # PR evaluation
        removed = store.ratchet_update("main", sha, current) # one-way ratchet
    """

    DEFAULT_RELATIVE_PATH = Path(".asgard_cache") / "bragi_fingerprint_baseline.json"

    def __init__(self, project_path: Optional[Path] = None,
                 store_path: Optional[Path] = None):
        self.project_path = Path(project_path or Path.cwd())
        self.store_path = store_path or (self.project_path / self.DEFAULT_RELATIVE_PATH)

    # -- persistence ------------------------------------------------------

    def _key_path(self) -> Path:
        return self.store_path.with_name(self.store_path.name + ".key")

    def _read_nofollow(self, path: Path) -> bytes:
        if path.is_symlink():
            raise ValueError(f"quality-gate path must not be a symlink: {path}")
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

    def _hmac_key(self) -> bytes:
        from Asgard.common._hmac_env import hmac_key_from_env

        env = hmac_key_from_env(_HMAC_ENV)
        if env is not None:
            return env
        if getattr(self, "_ephemeral_hmac", None) is None:
            self._ephemeral_hmac = os.urandom(32)
        return self._ephemeral_hmac

    def _sign_branches(self, branches: Dict[str, dict]) -> str:
        payload = json.dumps(branches, sort_keys=True, separators=(",", ":"), default=str)
        return hmac.new(self._hmac_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def _read_all(self) -> Dict[str, dict]:
        if not self.store_path.exists() or self.store_path.is_symlink():
            return {}
        try:
            data = json.loads(self._read_nofollow(self.store_path).decode("utf-8"))
            branches = data.get("branches", {})
            if not isinstance(branches, dict):
                return {}
            expected = data.get("hmac")
            if not isinstance(expected, str) or not hmac.compare_digest(
                expected, self._sign_branches(branches)
            ):
                return {}
            return branches
        except (OSError, json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
            return {}

    def _write_all(self, branches: Dict[str, dict]) -> None:
        if self.store_path.is_symlink():
            raise ValueError("quality-gate baseline path must not be a symlink")
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "1.0.0",
            "branches": branches,
            "hmac": self._sign_branches(branches),
        }
        raw = json.dumps(payload, indent=2, default=str).encode("utf-8")
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.store_path, flags, 0o600)
        try:
            os.write(fd, raw)
        finally:
            os.close(fd)
        os.chmod(self.store_path, 0o600)

    # -- API ---------------------------------------------------------------

    def load(self, branch: str) -> Optional[BranchBaseline]:
        """Load the baseline for a branch (read-only; returns None if absent)."""
        raw = self._read_all().get(branch)
        if raw is None:
            return None
        try:
            return BranchBaseline(**raw)
        except (TypeError, ValueError):
            return None

    def capture(self, branch: str, commit: str,
                fingerprints: Iterable[str]) -> BranchBaseline:
        """
        Capture (or overwrite) the baseline for a branch. Intended for
        reference-branch scans only — never call from a PR evaluation.
        """
        baseline = BranchBaseline(
            branch=branch,
            commit=commit,
            fingerprints=sorted(set(fingerprints)),
        )
        branches = self._read_all()
        branches[branch] = json.loads(baseline.model_dump_json())
        self._write_all(branches)
        return baseline

    def ratchet_update(self, branch: str, commit: str,
                       current_fingerprints: Iterable[str]) -> int:
        """
        One-way baseline ratchet: intersect the stored baseline with the
        currently observed fingerprints. Fixed findings leave the baseline
        permanently; nothing new is ever added.

        Returns the number of fingerprints retired from the baseline.
        Raises ValueError when no baseline exists (use capture() first).
        """
        existing = self.load(branch)
        if existing is None:
            raise ValueError(
                f"No baseline exists for branch '{branch}'; capture one first."
            )
        current = set(current_fingerprints)
        kept = existing.fingerprint_set & current
        removed = len(existing.fingerprint_set) - len(kept)
        baseline = BranchBaseline(
            branch=branch, commit=commit, fingerprints=sorted(kept)
        )
        branches = self._read_all()
        branches[branch] = json.loads(baseline.model_dump_json())
        self._write_all(branches)
        return removed

    def delete(self, branch: str) -> bool:
        """Delete a branch baseline. Returns True if one existed."""
        branches = self._read_all()
        if branch in branches:
            del branches[branch]
            self._write_all(branches)
            return True
        return False

    def branches(self) -> List[str]:
        """List branches with stored baselines."""
        return sorted(self._read_all().keys())
