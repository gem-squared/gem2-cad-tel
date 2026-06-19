"""U1: Audit DB schema + idempotent migration runner.

Stdlib sqlite3 only. PRAGMA user_version gates migrations.

v1 schema (this release):
    runs              — one row per pipeline invocation
    stage_events      — per-stage entry / exit / arbitrary events
    epistemic_counts  — tag distribution rollups (composite key)
    refusals_log      — every refusal_candidate + promoted refusal
    policy_fires      — Measurement_Policy + future invariant fires
    schema_meta       — generic key/value (created_at, last_migrated, ...)

All datetime columns are TEXT (ISO8601 UTC, e.g. '2026-06-05T14:00:00Z').
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

DDL_V1: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS runs (
        run_id        TEXT PRIMARY KEY,
        drawing_id    TEXT NOT NULL,
        started_at    TEXT NOT NULL,
        completed_at  TEXT,
        duration_ms   INTEGER,
        exit_state    TEXT NOT NULL DEFAULT 'in_progress',
        error_msg     TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS stage_events (
        event_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id        TEXT NOT NULL REFERENCES runs(run_id),
        stage         TEXT NOT NULL,
        level         TEXT NOT NULL,
        message       TEXT NOT NULL,
        payload_json  TEXT,
        timestamp     TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS epistemic_counts (
        run_id        TEXT NOT NULL REFERENCES runs(run_id),
        stage         TEXT NOT NULL,
        tag           TEXT NOT NULL,
        field         TEXT NOT NULL,
        count         INTEGER NOT NULL,
        PRIMARY KEY (run_id, stage, tag, field)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS refusals_log (
        row_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id          TEXT NOT NULL REFERENCES runs(run_id),
        region_json     TEXT NOT NULL,
        attempted_type  TEXT NOT NULL,
        why             TEXT NOT NULL,
        recorded_at     TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS policy_fires (
        row_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id        TEXT NOT NULL REFERENCES runs(run_id),
        policy_name   TEXT NOT NULL,
        detail_json   TEXT,
        timestamp     TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS schema_meta (
        key    TEXT PRIMARY KEY,
        value  TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_stage_events_run_id ON stage_events(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_refusals_run_id ON refusals_log(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_policy_fires_run_id ON policy_fires(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_runs_drawing_id ON runs(drawing_id)",
    "CREATE INDEX IF NOT EXISTS idx_refusals_attempted_type ON refusals_log(attempted_type)",
)

TABLE_NAMES: tuple[str, ...] = (
    "runs",
    "stage_events",
    "epistemic_counts",
    "refusals_log",
    "policy_fires",
    "schema_meta",
)


def _get_user_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def _set_user_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(f"PRAGMA user_version = {version}")


def _apply_v1(conn: sqlite3.Connection) -> None:
    for stmt in DDL_V1:
        conn.execute(stmt)
    conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )


def init_audit_db(db_path: Path | str) -> Path:
    """Idempotent: create file + apply schema + set PRAGMA user_version.

    Re-invocation is a no-op. Returns the resolved Path.
    """
    path = Path(db_path) if db_path != ":memory:" else Path(":memory:")
    if path != Path(":memory:"):
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        current = _get_user_version(conn)
        if current == SCHEMA_VERSION:
            return path  # already at target
        if current == 0:
            _apply_v1(conn)
            _set_user_version(conn, SCHEMA_VERSION)
            conn.commit()
            return path
        if current > SCHEMA_VERSION:
            raise RuntimeError(
                f"audit DB at {path} has PRAGMA user_version={current} > target {SCHEMA_VERSION}; "
                f"refusing to downgrade"
            )
        # current ∈ (0, SCHEMA_VERSION) — would apply intermediate migrations here
        raise RuntimeError(
            f"unexpected user_version {current}; no migration path defined for v{current}→v{SCHEMA_VERSION}"
        )
    finally:
        conn.close()


def list_tables(db_path: Path | str) -> list[str]:
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def get_schema_version(db_path: Path | str) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        return _get_user_version(conn)
    finally:
        conn.close()
