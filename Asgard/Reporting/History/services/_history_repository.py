"""
Asgard History - repository abstraction.

Defines the IHistoryRepository protocol (abstract interface) and the
SQLiteHistoryRepository concrete implementation. Services depend on
the protocol, not on the SQLite concrete type, satisfying DIP.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Protocol, cast, runtime_checkable

from Asgard.Reporting.History.infrastructure.persistence.history_schema import (
    connect,
    ensure_db,
    get_default_db_path,
    row_to_snapshot,
)
from Asgard.Reporting.History.models.history_models import AnalysisSnapshot


@runtime_checkable
class IHistoryRepository(Protocol):
    """
    Abstract interface for snapshot persistence operations.

    Implementations may back this with SQLite, an in-memory store,
    a remote API, or any other provider without changing consumers.
    """

    def save_snapshot(self, snapshot: AnalysisSnapshot) -> str:
        """Persist an analysis snapshot and return its snapshot_id."""
        ...

    def get_snapshots(
        self, project_path: str, limit: int = 50
    ) -> List[AnalysisSnapshot]:
        """Return stored snapshots for a project in reverse chronological order."""
        ...

    def get_latest_snapshot(self, project_path: str) -> Optional[AnalysisSnapshot]:
        """Return the most recent snapshot for a project, or None."""
        ...


class SQLiteHistoryRepository:
    """
    SQLite-backed implementation of IHistoryRepository.

    All raw sqlite3 interactions are contained here, keeping consumers
    free from direct database driver coupling.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or get_default_db_path()
        ensure_db(self._db_path)

    def save_snapshot(self, snapshot: AnalysisSnapshot) -> str:
        """
        Persist an analysis snapshot to the database.

        Args:
            snapshot: The snapshot to store. If snapshot_id is empty a new UUID
                      is assigned automatically.

        Returns:
            The snapshot_id of the stored record.
        """
        if not snapshot.snapshot_id:
            snapshot = snapshot.copy(update={"snapshot_id": str(uuid.uuid4())})

        metrics_data = [
            {"metric_name": m.metric_name, "value": m.value, "unit": m.unit}
            for m in snapshot.metrics
        ]

        with connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO snapshots
                    (id, project_path, scan_timestamp, git_commit, git_branch,
                     quality_gate_status, ratings_json, metrics_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.snapshot_id,
                    str(Path(snapshot.project_path).resolve()),
                    snapshot.scan_timestamp.isoformat(),
                    snapshot.git_commit,
                    snapshot.git_branch,
                    snapshot.quality_gate_status,
                    json.dumps(snapshot.ratings),
                    json.dumps(metrics_data),
                ),
            )

        return cast(str, snapshot.snapshot_id)

    def get_snapshots(
        self, project_path: str, limit: int = 50
    ) -> List[AnalysisSnapshot]:
        """
        Return stored snapshots for a project in reverse chronological order.

        Args:
            project_path: Absolute path to the project root.
            limit: Maximum number of snapshots to return.

        Returns:
            List of AnalysisSnapshot objects (newest first).
        """
        resolved = str(Path(project_path).resolve())

        with connect(self._db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id, project_path, scan_timestamp, git_commit, git_branch,
                       quality_gate_status, ratings_json, metrics_json
                FROM snapshots
                WHERE project_path = ?
                ORDER BY scan_timestamp DESC
                LIMIT ?
                """,
                (resolved, limit),
            )
            rows = cursor.fetchall()

        return [row_to_snapshot(row) for row in rows]

    def get_latest_snapshot(self, project_path: str) -> Optional[AnalysisSnapshot]:
        """
        Return the most recent snapshot for a project, or None.

        Args:
            project_path: Absolute path to the project root.

        Returns:
            Most recent AnalysisSnapshot or None if no history exists.
        """
        results = self.get_snapshots(project_path, limit=1)
        return results[0] if results else None
