"""File integrity checker — baseline creation and verification via cryptographic hashes."""

import hashlib
import hmac
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from Asgard.Heimdall.Security.FileIntegrity.models.file_integrity_models import (
    FileIntegrityReport,
    FileModification,
    FileRecord,
    PermissionChange,
)

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
_SKIP_EXTS = {".pyc", ".pyo", ".so", ".dylib", ".o"}
_HMAC_ENV = "ASGARD_INTEGRITY_HMAC_KEY"


class FileIntegrityChecker:
    """Creates and verifies file integrity baselines using MD5 and SHA-256 hashes."""

    def __init__(self, baseline_file: str = ".file_integrity_baseline.json") -> None:
        self.baseline_file = Path(baseline_file)
        self._baseline: Dict[str, FileRecord] = {}

    # ── public API ─────────────────────────────────────────────────────────────

    def create_baseline(self, directory: Path, patterns: Optional[List[str]] = None) -> int:
        self._baseline = self._scan_directory(directory, patterns)
        self._save_baseline()
        return len(self._baseline)

    def verify_integrity(self, directory: Path, patterns: Optional[List[str]] = None) -> FileIntegrityReport:
        if not self._load_baseline():
            raise FileNotFoundError(f"No baseline found at {self.baseline_file}. Run create_baseline() first.")

        current = self._scan_directory(directory, patterns)
        now = datetime.now().isoformat()
        report = FileIntegrityReport(
            verified_at=now,
            total_baseline_files=len(self._baseline),
            total_current_files=len(current),
        )

        for path, baseline_rec in self._baseline.items():
            if path in current:
                cur = current[path]
                if cur.sha256 != baseline_rec.sha256:
                    report.modified.append(FileModification(
                        path=path,
                        old_hash=baseline_rec.sha256[:16] + "...",
                        new_hash=cur.sha256[:16] + "...",
                        old_size=baseline_rec.size,
                        new_size=cur.size,
                    ))
                elif cur.permissions != baseline_rec.permissions:
                    report.permission_changes.append(PermissionChange(
                        path=path,
                        old_perms=baseline_rec.permissions,
                        new_perms=cur.permissions,
                    ))
                else:
                    report.ok_count += 1
            else:
                report.deleted.append({"path": path, "size": baseline_rec.size})

        for path, rec in current.items():
            if path not in self._baseline:
                report.added.append({"path": path, "size": rec.size})

        return report

    def hash_file(self, file_path: Path) -> Optional[FileRecord]:
        return self._get_record(file_path)

    # ── private helpers ────────────────────────────────────────────────────────

    def _scan_directory(self, directory: Path, patterns: Optional[List[str]] = None) -> Dict[str, FileRecord]:
        records: Dict[str, FileRecord] = {}
        skip_names = {self.baseline_file.name, self.baseline_file.name + ".key"}
        for root, dirs, files in os.walk(directory, followlinks=False):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for name in files:
                if name in skip_names:
                    continue
                fp = Path(root) / name
                if fp.suffix in _SKIP_EXTS:
                    continue
                if patterns and not any(fp.match(p) for p in patterns):
                    continue
                rec = self._get_record(fp)
                if rec:
                    records[rec.path] = rec
        return records

    def _get_record(self, file_path: Path) -> Optional[FileRecord]:
        try:
            if file_path.is_symlink():
                return None
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(file_path, flags)
            try:
                stat = os.fstat(fd)
                md5_h = hashlib.md5()
                sha256_h = hashlib.sha256()
                while True:
                    chunk = os.read(fd, 8192)
                    if not chunk:
                        break
                    md5_h.update(chunk)
                    sha256_h.update(chunk)
            finally:
                os.close(fd)
            return FileRecord(
                path=str(file_path.absolute()),
                size=stat.st_size,
                md5=md5_h.hexdigest(),
                sha256=sha256_h.hexdigest(),
                modified_time=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                permissions=oct(stat.st_mode)[-3:],
            )
        except OSError:
            return None

    def _read_nofollow(self, path: Path) -> bytes:
        if path.is_symlink():
            raise ValueError(f"integrity path must not be a symlink: {path}")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            chunks: List[bytes] = []
            while True:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks)
        finally:
            os.close(fd)

    def _key_path(self) -> Path:
        return self.baseline_file.with_name(self.baseline_file.name + ".key")

    def _hmac_key(self, *, create: bool) -> Optional[bytes]:
        from Asgard.common._hmac_env import hmac_key_from_env, persisted_hmac_key

        env = hmac_key_from_env(_HMAC_ENV)
        if env is not None:
            return env
        return persisted_hmac_key(self._key_path(), create=create)

    def _sign_files(self, files: dict, *, create: bool) -> Optional[str]:
        key = self._hmac_key(create=create)
        if key is None:
            return None
        payload = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(key, payload, hashlib.sha256).hexdigest()

    def _save_baseline(self) -> None:
        if self.baseline_file.is_symlink():
            raise ValueError("integrity baseline path must not be a symlink")
        files = {path: rec.model_dump() for path, rec in self._baseline.items()}
        data = {
            "created": datetime.now().isoformat(),
            "files": files,
            "hmac": self._sign_files(files, create=True),
        }
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        payload = json.dumps(data, indent=2).encode("utf-8")
        fd = os.open(self.baseline_file, flags, 0o600)
        try:
            os.write(fd, payload)
        finally:
            os.close(fd)
        os.chmod(self.baseline_file, 0o600)

    def _load_baseline(self) -> bool:
        if not self.baseline_file.exists() or self.baseline_file.is_symlink():
            return False
        try:
            data = json.loads(self._read_nofollow(self.baseline_file).decode("utf-8"))
            files = data["files"]
            expected = data.get("hmac")
            computed = self._sign_files(files, create=False)
            if (
                not isinstance(expected, str)
                or computed is None
                or not hmac.compare_digest(expected, computed)
            ):
                return False
            self._baseline = {path: FileRecord(**rec) for path, rec in files.items()}
            return True
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, UnicodeDecodeError):
            return False
