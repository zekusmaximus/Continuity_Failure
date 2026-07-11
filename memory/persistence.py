"""Durable SQLite boundary for campaigns and advisory model-run records.

The deterministic engine knows nothing about this module. Complete, versioned
campaign documents rebuild plain engine dataclasses on read. Turn snapshots
are separate append-only records and cannot be replaced by later saves.

Turn resolution needs more than a single durable write: it must read the
campaign, resolve it, save the authoritative document, append the immutable
snapshot, and record the idempotency result as one indivisible unit.
:meth:`SQLiteRepository.transaction` exposes that unit. Everything a caller
does through the yielded :class:`RepositoryTransaction` commits together or
rolls back together.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import types
from contextlib import contextmanager
from dataclasses import MISSING, asdict, fields, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Protocol, Union, get_args, get_origin, get_type_hints

from engine.models import Campaign


SCHEMA_VERSION = 3
DOCUMENT_VERSION = 1


class StorageError(RuntimeError):
    """Base class for repository failures that callers may report cleanly."""


class CorruptRecordError(StorageError):
    """A stored JSON document cannot be validated as its typed record."""


class ImmutableSnapshotError(StorageError):
    """A save attempted to change an already-recorded turn snapshot."""


class ImmutablePresentationError(StorageError):
    """A resolved-turn presentation record was changed after insertion."""


class DuplicateIdempotencyKeyError(StorageError):
    """A (campaign_id, idempotency_key) pair was inserted twice."""


class RepositoryBusyError(StorageError):
    """The write lock could not be acquired before the busy timeout expired.

    Raised only while acquiring or releasing the transaction's write lock, so no
    statement in the unit of work has been applied. The caller may retry with
    the same idempotency key.
    """


class CampaignRepository(Protocol):
    """Narrow persistence contract used by the orchestration service."""

    def put(self, campaign: Campaign, snapshot_turn: Optional[int] = None) -> None: ...
    def get(self, campaign_id: str) -> Optional[Campaign]: ...
    def list_recent(self, limit: int = 5) -> List[dict]: ...
    def add_model_run(self, payload: Mapping[str, Any]) -> None: ...
    def model_runs_for_campaign(self, campaign_id: str) -> List[dict]: ...
    def pending_turn_presentation(self, campaign_id: str) -> Optional[dict]: ...
    def acknowledge_turn_presentation(
        self, campaign_id: str, turn_number: int
    ) -> bool: ...
    def transaction(self) -> Any: ...


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_document(kind: str, value: Any) -> str:
    return json.dumps(
        {"document_version": DOCUMENT_VERSION, "kind": kind, "data": value},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _read_document(raw: str, expected_kind: str) -> Any:
    try:
        document = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise CorruptRecordError(f"Invalid JSON for {expected_kind}") from exc
    if not isinstance(document, dict):
        raise CorruptRecordError(f"Invalid {expected_kind} document envelope")
    if document.get("document_version") != DOCUMENT_VERSION:
        raise CorruptRecordError(
            f"Unsupported {expected_kind} document version: "
            f"{document.get('document_version')!r}"
        )
    if document.get("kind") != expected_kind or "data" not in document:
        raise CorruptRecordError(f"Invalid {expected_kind} document envelope")
    return document["data"]


def _convert(value: Any, annotation: Any, path: str) -> Any:
    """Strictly rebuild nested engine dataclasses from decoded JSON."""
    if annotation is Any:
        return value

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (Union, types.UnionType):
        if value is None and type(None) in args:
            return None
        failures = []
        for option in args:
            if option is type(None):
                continue
            try:
                return _convert(value, option, path)
            except CorruptRecordError as exc:
                failures.append(str(exc))
        raise CorruptRecordError(f"{path} does not match its declared union: {failures}")

    if origin in (list, List):
        if not isinstance(value, list):
            raise CorruptRecordError(f"{path} must be a list")
        item_type = args[0] if args else Any
        return [
            _convert(item, item_type, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]

    if origin in (dict, Dict):
        if not isinstance(value, dict):
            raise CorruptRecordError(f"{path} must be an object")
        key_type, item_type = args if args else (Any, Any)
        result = {}
        for key, item in value.items():
            converted_key = (
                int(key)
                if key_type is int and isinstance(key, str)
                else _convert(key, key_type, f"{path}.<key>")
            )
            result[converted_key] = _convert(item, item_type, f"{path}.{key}")
        return result

    if isinstance(annotation, type) and is_dataclass(annotation):
        if not isinstance(value, dict):
            raise CorruptRecordError(f"{path} must be an object")
        hints = get_type_hints(annotation)
        kwargs = {}
        for field in fields(annotation):
            if field.name in value:
                kwargs[field.name] = _convert(
                    value[field.name], hints[field.name], f"{path}.{field.name}"
                )
            elif field.default is MISSING and field.default_factory is MISSING:
                raise CorruptRecordError(f"Missing required field {path}.{field.name}")
        try:
            return annotation(**kwargs)
        except (TypeError, ValueError) as exc:
            raise CorruptRecordError(f"Invalid {path}: {exc}") from exc

    if annotation is bool:
        if type(value) is not bool:
            raise CorruptRecordError(f"{path} must be a boolean")
        return value
    if annotation is int:
        if type(value) is not int:
            raise CorruptRecordError(f"{path} must be an integer")
        return value
    if annotation is float:
        if type(value) not in (int, float):
            raise CorruptRecordError(f"{path} must be a number")
        return float(value)
    if annotation is str:
        if not isinstance(value, str):
            raise CorruptRecordError(f"{path} must be a string")
        return value
    if value is None and annotation is type(None):
        return None
    return value


def encode_campaign(campaign: Campaign) -> str:
    return _json_document("campaign", asdict(campaign))


def decode_campaign(raw: str) -> Campaign:
    return _convert(_read_document(raw, "campaign"), Campaign, "campaign")


def _load_campaign(connection: sqlite3.Connection, campaign_id: str) -> Optional[Campaign]:
    row = connection.execute(
        "SELECT payload_json FROM campaigns WHERE id = ?", (campaign_id,)
    ).fetchone()
    if row is None:
        return None
    try:
        campaign = decode_campaign(row["payload_json"])
    except CorruptRecordError as exc:
        raise CorruptRecordError(f"Campaign {campaign_id} is corrupt: {exc}") from exc
    if campaign.id != campaign_id:
        raise CorruptRecordError(
            f"Campaign {campaign_id} is corrupt: payload identity mismatch"
        )
    return campaign


def _save_campaign(
    connection: sqlite3.Connection,
    campaign: Campaign,
    snapshot_turn: Optional[int],
) -> None:
    payload = encode_campaign(campaign)
    now = _utc_now()
    # The live campaign document is convenient for reconstruction, but its
    # embedded history may not contradict an existing immutable snapshot. This
    # prevents an ordinary re-save from rewriting truth merely because snapshots
    # live in a separate table.
    historical = connection.execute(
        "SELECT turn_number, snapshot_json FROM turn_snapshots "
        "WHERE campaign_id = ? ORDER BY turn_number",
        (campaign.id,),
    ).fetchall()
    results_by_turn = {turn.turn_number: asdict(turn) for turn in campaign.turn_history}
    canon_by_id = {entry.id: asdict(entry) for entry in campaign.canon}
    for row in historical:
        turn_number = int(row["turn_number"])
        snapshot_data = _read_document(row["snapshot_json"], "turn_snapshot")
        try:
            stored_campaign = snapshot_data["campaign"]
            stored_result = stored_campaign["turn_history"][-1]
        except (KeyError, IndexError, TypeError) as exc:
            raise CorruptRecordError(
                f"Turn {turn_number} snapshot for campaign {campaign.id} is corrupt"
            ) from exc
        if results_by_turn.get(turn_number) != stored_result:
            raise ImmutableSnapshotError(
                f"Turn {turn_number} history for campaign {campaign.id} is immutable"
            )
        for stored_entry in stored_campaign.get("canon", []):
            if canon_by_id.get(stored_entry.get("id")) != stored_entry:
                raise ImmutableSnapshotError(
                    f"Canon entry {stored_entry.get('id')} for campaign "
                    f"{campaign.id} is immutable"
                )
    connection.execute(
        """
        INSERT INTO campaigns(
            id, name, scenario_id, status, turn_number, max_turns,
            failure_reason, created_at, updated_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            scenario_id=excluded.scenario_id,
            status=excluded.status,
            turn_number=excluded.turn_number,
            max_turns=excluded.max_turns,
            failure_reason=excluded.failure_reason,
            updated_at=excluded.updated_at,
            payload_json=excluded.payload_json
        """,
        (
            campaign.id,
            campaign.name,
            campaign.scenario_id,
            campaign.status,
            campaign.turn_number,
            campaign.max_turns,
            campaign.failure_reason,
            campaign.created_at,
            now,
            payload,
        ),
    )
    if snapshot_turn is None:
        return
    if not campaign.turn_history or campaign.turn_history[-1].turn_number != snapshot_turn:
        raise StorageError(
            f"Snapshot turn {snapshot_turn} is not the latest resolved turn"
        )
    snapshot = _json_document(
        "turn_snapshot",
        {
            "campaign_id": campaign.id,
            "turn_number": snapshot_turn,
            "campaign": asdict(campaign),
        },
    )
    existing = connection.execute(
        "SELECT snapshot_json FROM turn_snapshots "
        "WHERE campaign_id = ? AND turn_number = ?",
        (campaign.id, snapshot_turn),
    ).fetchone()
    if existing is None:
        connection.execute(
            "INSERT INTO turn_snapshots"
            "(campaign_id, turn_number, created_at, snapshot_json) "
            "VALUES (?, ?, ?, ?)",
            (campaign.id, snapshot_turn, now, snapshot),
        )
    elif existing["snapshot_json"] != snapshot:
        raise ImmutableSnapshotError(
            f"Turn {snapshot_turn} snapshot for campaign {campaign.id} is immutable"
        )


class RepositoryTransaction:
    """Handle for reads and writes inside one open SQLite transaction.

    Nothing here commits. The owning :meth:`SQLiteRepository.transaction`
    context manager commits once on clean exit and rolls back on any exception,
    so a failure anywhere in a turn resolution leaves no authoritative change.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        return _load_campaign(self._connection, campaign_id)

    def save_campaign(
        self, campaign: Campaign, snapshot_turn: Optional[int] = None
    ) -> None:
        _save_campaign(self._connection, campaign, snapshot_turn)

    def get_idempotency_record(
        self, campaign_id: str, idempotency_key: str
    ) -> Optional[dict]:
        row = self._connection.execute(
            "SELECT request_fingerprint, expected_turn, resulting_turn, response_json "
            "FROM turn_idempotency WHERE campaign_id = ? AND idempotency_key = ?",
            (campaign_id, idempotency_key),
        ).fetchone()
        if row is None:
            return None
        return {
            "request_fingerprint": str(row["request_fingerprint"]),
            "expected_turn": int(row["expected_turn"]),
            "resulting_turn": int(row["resulting_turn"]),
            "response": _read_document(row["response_json"], "turn_idempotency"),
        }

    def save_idempotency_record(
        self,
        *,
        campaign_id: str,
        idempotency_key: str,
        request_fingerprint: str,
        expected_turn: int,
        resulting_turn: int,
        response: Any,
    ) -> None:
        try:
            self._connection.execute(
                "INSERT INTO turn_idempotency("
                "campaign_id, idempotency_key, request_fingerprint, expected_turn, "
                "resulting_turn, created_at, response_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    campaign_id,
                    idempotency_key,
                    request_fingerprint,
                    expected_turn,
                    resulting_turn,
                    _utc_now(),
                    _json_document("turn_idempotency", response),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateIdempotencyKeyError(
                f"Idempotency key already recorded for campaign {campaign_id}"
            ) from exc

    def save_turn_presentation(
        self,
        *,
        campaign_id: str,
        turn_number: int,
        current_turn: Mapping[str, Any],
        result: Mapping[str, Any],
    ) -> None:
        """Append the exact resolved-turn UI checkpoint inside the turn transaction."""
        payload = _json_document(
            "turn_presentation",
            {
                "campaign_id": campaign_id,
                "turn_number": turn_number,
                "current_turn": dict(current_turn),
                "result": dict(result),
            },
        )
        existing = self._connection.execute(
            "SELECT payload_json FROM turn_presentations "
            "WHERE campaign_id = ? AND turn_number = ?",
            (campaign_id, turn_number),
        ).fetchone()
        if existing is None:
            self._connection.execute(
                "INSERT INTO turn_presentations("
                "campaign_id, turn_number, created_at, acknowledged_at, payload_json) "
                "VALUES (?, ?, ?, NULL, ?)",
                (campaign_id, turn_number, _utc_now(), payload),
            )
        elif existing["payload_json"] != payload:
            raise ImmutablePresentationError(
                f"Turn {turn_number} presentation for campaign {campaign_id} is immutable"
            )

    def pending_turn_presentation(self, campaign_id: str) -> Optional[dict]:
        row = self._connection.execute(
            "SELECT payload_json FROM turn_presentations "
            "WHERE campaign_id = ? AND acknowledged_at IS NULL "
            "ORDER BY turn_number LIMIT 1",
            (campaign_id,),
        ).fetchone()
        if row is None:
            return None
        return _read_document(row["payload_json"], "turn_presentation")

    def acknowledge_turn_presentation(
        self, campaign_id: str, turn_number: int
    ) -> bool:
        row = self._connection.execute(
            "SELECT acknowledged_at FROM turn_presentations "
            "WHERE campaign_id = ? AND turn_number = ?",
            (campaign_id, turn_number),
        ).fetchone()
        if row is None:
            return False
        if row["acknowledged_at"] is not None:
            return True
        pending = self._connection.execute(
            "SELECT MIN(turn_number) AS turn_number FROM turn_presentations "
            "WHERE campaign_id = ? AND acknowledged_at IS NULL",
            (campaign_id,),
        ).fetchone()
        if pending is None or pending["turn_number"] != turn_number:
            return False
        self._connection.execute(
            "UPDATE turn_presentations SET acknowledged_at = ? "
            "WHERE campaign_id = ? AND turn_number = ?",
            (_utc_now(), campaign_id, turn_number),
        )
        return True


class SQLiteRepository:
    """SQLite implementation of the campaign/model-run storage boundary."""

    def __init__(self, database_path: str | Path) -> None:
        self.path = Path(database_path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _migrate(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
            ).fetchone()
            current = int(row["version"])
            if current > SCHEMA_VERSION:
                raise StorageError(
                    f"Database schema {current} is newer than supported {SCHEMA_VERSION}"
                )
            if current < 1:
                connection.executescript(
                    """
                    CREATE TABLE campaigns (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        scenario_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        turn_number INTEGER NOT NULL,
                        max_turns INTEGER NOT NULL,
                        failure_reason TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        payload_json TEXT NOT NULL
                    );
                    CREATE INDEX campaigns_recent_idx ON campaigns(updated_at DESC);

                    CREATE TABLE turn_snapshots (
                        campaign_id TEXT NOT NULL,
                        turn_number INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        snapshot_json TEXT NOT NULL,
                        PRIMARY KEY (campaign_id, turn_number),
                        FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
                    );

                    CREATE TABLE model_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        campaign_id TEXT,
                        turn_number INTEGER,
                        created_at TEXT NOT NULL,
                        payload_json TEXT NOT NULL
                    );
                    CREATE INDEX model_runs_campaign_idx
                        ON model_runs(campaign_id, id);
                    """
                )
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (1, _utc_now()),
                )
            if current < 2:
                # One resolved turn per (campaign, idempotency key). The primary
                # key is the durable uniqueness guarantee: a retry that races the
                # original insert is rejected by SQLite, not merely by a prior
                # read inside the application.
                connection.executescript(
                    """
                    CREATE TABLE turn_idempotency (
                        campaign_id TEXT NOT NULL,
                        idempotency_key TEXT NOT NULL,
                        request_fingerprint TEXT NOT NULL,
                        expected_turn INTEGER NOT NULL,
                        resulting_turn INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        response_json TEXT NOT NULL,
                        PRIMARY KEY (campaign_id, idempotency_key),
                        FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
                            ON DELETE CASCADE
                    );
                    """
                )
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (2, _utc_now()),
                )
            if current < 3:
                # Presentation checkpoints are application workflow state, not
                # WorldState. They preserve the exact resolved turn across a
                # refresh until the player explicitly acknowledges Next Call.
                connection.executescript(
                    """
                    CREATE TABLE turn_presentations (
                        campaign_id TEXT NOT NULL,
                        turn_number INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        acknowledged_at TEXT,
                        payload_json TEXT NOT NULL,
                        PRIMARY KEY (campaign_id, turn_number),
                        FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
                            ON DELETE CASCADE
                    );
                    CREATE INDEX turn_presentations_pending_idx
                        ON turn_presentations(campaign_id, acknowledged_at, turn_number);
                    """
                )
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (3, _utc_now()),
                )

    @contextmanager
    def transaction(self) -> Iterator["RepositoryTransaction"]:
        """Run a unit of work that commits in full or not at all.

        The instance lock serializes writers inside this process; ``BEGIN
        IMMEDIATE`` takes SQLite's write lock so a second process cannot
        interleave. Callers must use only the yielded handle: invoking
        :meth:`put` or :meth:`get` from inside an open transaction opens a
        second connection and would block against this one.
        """
        with self._lock:
            connection = self._connect()
            try:
                try:
                    connection.execute("BEGIN IMMEDIATE")
                except sqlite3.OperationalError as exc:
                    # Another process held the write lock past the busy timeout.
                    # Nothing was applied; the caller may retry with the same key.
                    raise RepositoryBusyError(
                        "The engagement record is busy; retry the request."
                    ) from exc
                yield RepositoryTransaction(connection)
            except BaseException:
                connection.rollback()
                raise
            else:
                try:
                    connection.commit()
                except sqlite3.OperationalError as exc:
                    connection.rollback()
                    raise RepositoryBusyError(
                        "The engagement record is busy; retry the request."
                    ) from exc
            finally:
                connection.close()

    def put(self, campaign: Campaign, snapshot_turn: Optional[int] = None) -> None:
        with self.transaction() as active:
            active.save_campaign(campaign, snapshot_turn=snapshot_turn)

    def get(self, campaign_id: str) -> Optional[Campaign]:
        with self._lock, self._connect() as connection:
            return _load_campaign(connection, campaign_id)

    def list_recent(self, limit: int = 5) -> List[dict]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, name, scenario_id, status, turn_number, max_turns,
                       failure_reason, created_at, updated_at
                FROM campaigns ORDER BY updated_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def pending_turn_presentation(self, campaign_id: str) -> Optional[dict]:
        with self._lock, self._connect() as connection:
            active = RepositoryTransaction(connection)
            return active.pending_turn_presentation(campaign_id)

    def acknowledge_turn_presentation(
        self, campaign_id: str, turn_number: int
    ) -> bool:
        with self.transaction() as active:
            return active.acknowledge_turn_presentation(campaign_id, turn_number)

    def snapshot_json(self, campaign_id: str, turn_number: int) -> Optional[str]:
        """Inspection hook used by persistence regression tests."""
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT snapshot_json FROM turn_snapshots "
                "WHERE campaign_id = ? AND turn_number = ?",
                (campaign_id, turn_number),
            ).fetchone()
        return None if row is None else str(row["snapshot_json"])

    def add_model_run(self, payload: Mapping[str, Any]) -> None:
        data = dict(payload)
        raw = _json_document("model_run", data)
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO model_runs(campaign_id, turn_number, created_at, payload_json) "
                "VALUES (?, ?, ?, ?)",
                (data.get("campaign_id"), data.get("turn_number"), _utc_now(), raw),
            )

    def model_runs_for_campaign(self, campaign_id: str) -> List[dict]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM model_runs "
                "WHERE campaign_id = ? ORDER BY id",
                (campaign_id,),
            ).fetchall()
        return [_read_document(row["payload_json"], "model_run") for row in rows]

    def all_model_runs(self) -> List[dict]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM model_runs ORDER BY id"
            ).fetchall()
        return [_read_document(row["payload_json"], "model_run") for row in rows]

    def clear_model_runs(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM model_runs")

    def clear(self) -> None:
        """Delete all local records. Intended for explicit reset/tests only."""
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM campaigns")
            connection.execute("DELETE FROM model_runs")
