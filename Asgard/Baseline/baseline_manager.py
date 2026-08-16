"""
Baseline Manager

Manages creating, loading, and filtering violations against baseline.
"""

import hashlib
import hmac
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, TypeVar, cast

_HMAC_ENV = "ASGARD_BASELINE_HMAC_KEY"

from Asgard.Baseline._baseline_helpers import (
    generate_violation_id,
    hash_violation_message,
    persistable_violation_message,
    relative_path,
)
from Asgard.Baseline._baseline_operations import (
    create_from_violations as _create_from_violations,
    filter_violations as _filter_violations,
)
from Asgard.Baseline._baseline_report import (
    format_json_report,
    format_markdown_report,
    format_text_report,
)
from Asgard.Baseline.models import (
    BaselineEntry,
    BaselineFile,
    BaselineStats,
)

T = TypeVar('T')


class BaselineManager:
    """
    Manages baseline files for suppressing known violations.

    Usage:
        manager = BaselineManager(project_path)

        # Create baseline from current violations
        manager.create_from_violations(violations, "lazy_import")

        # Filter violations against baseline
        filtered = manager.filter_violations(violations, "lazy_import")

        # Show baseline stats
        stats = manager.get_stats()
    """

    DEFAULT_BASELINE_FILE = ".asgard-baseline.json"

    def __init__(
        self,
        project_path: Optional[Path] = None,
        baseline_file: Optional[str] = None,
    ):
        self.project_path = Path(project_path or Path.cwd()).resolve()
        self.baseline_file = baseline_file or self.DEFAULT_BASELINE_FILE
        self.baseline_path = self._confined_baseline_path(self.project_path, self.baseline_file)
        self._baseline: Optional[BaselineFile] = None

    @staticmethod
    def _confined_baseline_path(project_path: Path, baseline_file: str) -> Path:
        raw = Path(baseline_file)
        if raw.is_absolute() or ".." in raw.parts:
            raise ValueError("baseline_file must stay under the project path")
        dest = project_path / raw
        resolved = dest.resolve()
        if not resolved.is_relative_to(project_path.resolve()):
            raise ValueError("baseline_file must stay under the project path")
        # Unfollowed dest so load/save can refuse a planted dest symlink.
        return dest

    def _key_path(self) -> Path:
        return self.baseline_path.with_name(self.baseline_path.name + ".key")

    def _hmac_key(self) -> bytes:
        env = os.environ.get(_HMAC_ENV, "").strip()
        if env:
            return env.encode("utf-8")
        key_path = self._key_path()
        if key_path.is_symlink():
            raise ValueError("baseline key path must not be a symlink")
        if key_path.exists():
            return key_path.read_bytes()
        key = os.urandom(32)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(key_path, flags, 0o600)
        try:
            os.write(fd, key)
        finally:
            os.close(fd)
        os.chmod(key_path, 0o600)
        return key

    def _sign_payload(self, payload: dict) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hmac.new(self._hmac_key(), canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def load(self) -> BaselineFile:
        """Load the baseline file. HMAC mismatch fail-closes to an empty baseline."""
        if self._baseline is not None:
            return self._baseline

        if self.baseline_path.is_symlink():
            raise ValueError("baseline path must not be a symlink")

        try:
            with open(self.baseline_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                self._baseline = BaselineFile(project_path=str(self.project_path))
                return self._baseline
            expected = data.pop("hmac", None)
            if not isinstance(expected, str) or not hmac.compare_digest(
                expected, self._sign_payload(data)
            ):
                self._baseline = BaselineFile(project_path=str(self.project_path))
                return self._baseline
            self._baseline = BaselineFile(**data)
            for entry in self._baseline.entries:
                entry.message = hash_violation_message(entry.message)
        except FileNotFoundError:
            self._baseline = BaselineFile(project_path=str(self.project_path))
        except (json.JSONDecodeError, TypeError, ValueError, OSError):
            self._baseline = BaselineFile(project_path=str(self.project_path))

        return self._baseline

    def save(self) -> None:
        """Save the baseline file to disk with an HMAC sidecar field."""
        if self._baseline is None:
            return

        dest = self.baseline_path
        if dest.is_symlink():
            raise ValueError("baseline path must not be a symlink")

        self._baseline.updated_at = datetime.now()
        for entry in self._baseline.entries:
            entry.message = hash_violation_message(entry.message)
        payload = self._baseline.model_dump(mode='json')
        payload["hmac"] = self._sign_payload(payload)

        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{dest.name}.",
            suffix=".tmp",
            dir=str(dest.parent),
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, default=str)
            os.replace(tmp_name, dest)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def create_from_violations(
        self,
        violations: List[Any],
        violation_type: str,
        reason: str = "Initial baseline",
        created_by: str = "asgard",
    ) -> int:
        """Create baseline entries from a list of violations."""
        return _create_from_violations(
            violations,
            violation_type,
            self.load(),
            self.project_path,
            self.save,
            reason,
            created_by,
        )

    def filter_violations(
        self,
        violations: List[T],
        violation_type: str,
        use_fuzzy_matching: bool = False,
    ) -> List[T]:
        """Filter violations against the baseline."""
        return _filter_violations(
            violations,
            violation_type,
            self.load(),
            self.project_path,
            use_fuzzy_matching,
        )

    def get_baselined_count(
        self,
        violations: List[Any],
        violation_type: str,
    ) -> int:
        """Count how many violations are baselined."""
        total = len(violations)
        new = len(self.filter_violations(violations, violation_type))
        return total - new

    def add_entry(
        self,
        file_path: str,
        line_number: int,
        violation_type: str,
        message: str = "",
        reason: str = "",
        created_by: str = "asgard",
    ) -> bool:
        """
        Manually add a baseline entry.

        Returns:
            True if entry was added, False if already exists
        """
        baseline = self.load()

        rel_path = relative_path(self.project_path, file_path)
        violation_id = generate_violation_id(rel_path, line_number, violation_type, message)
        message = persistable_violation_message(message, violation_id)
        if baseline.find_match(rel_path, line_number, violation_type, message, violation_id):
            return False

        entry = BaselineEntry(
            file_path=rel_path,
            line_number=line_number,
            violation_type=violation_type,
            violation_id=violation_id,
            message=message,
            reason=reason,
            created_by=created_by,
        )

        baseline.add_entry(entry)
        self.save()
        return True

    def remove_entry(self, violation_id: str) -> bool:
        """Remove a baseline entry by ID."""
        baseline = self.load()
        result = baseline.remove_entry(violation_id)
        if result:
            self.save()
        return cast(bool, result)

    def clean_expired(self) -> int:
        """Remove expired baseline entries."""
        baseline = self.load()
        count = baseline.clean_expired()
        if count > 0:
            self.save()
        return cast(int, count)

    def get_stats(self) -> BaselineStats:
        """Get statistics about the baseline."""
        return self.load().get_stats()

    def list_entries(
        self,
        violation_type: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> List[BaselineEntry]:
        """List baseline entries with optional filtering."""
        baseline = self.load()
        entries = baseline.entries

        if violation_type:
            entries = [e for e in entries if e.violation_type == violation_type]

        if file_path:
            rel_path = relative_path(self.project_path, file_path)
            entries = [e for e in entries if e.file_path == rel_path]

        return cast(List[Any], entries)

    def generate_report(self, output_format: str = "text") -> str:
        """Generate a report of baseline entries."""
        baseline = self.load()
        stats = baseline.get_stats()

        if output_format == "json":
            return format_json_report(baseline)

        elif output_format == "markdown":
            return format_markdown_report(baseline, stats, self.baseline_path)

        else:
            return format_text_report(baseline, stats, self.baseline_path)
