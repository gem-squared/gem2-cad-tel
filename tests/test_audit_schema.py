"""U1 acceptance tests — schema + migration runner."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cad_trust.audit_schema import (
    SCHEMA_VERSION,
    TABLE_NAMES,
    get_schema_version,
    init_audit_db,
    list_tables,
)


def test_init_creates_file_and_tables(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    assert not db.exists()
    init_audit_db(db)
    assert db.exists()
    tables = set(list_tables(db))
    assert set(TABLE_NAMES) <= tables


def test_pragma_user_version_set(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    init_audit_db(db)
    assert get_schema_version(db) == SCHEMA_VERSION


def test_migration_idempotent_second_call_is_noop(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    init_audit_db(db)
    init_audit_db(db)  # second call must not raise
    init_audit_db(db)  # third either
    assert get_schema_version(db) == SCHEMA_VERSION
    # Tables still all present, no duplicates
    tables = list_tables(db)
    assert sorted(tables) == sorted(set(tables)), "duplicate tables on re-init"


def test_init_creates_parent_dirs(tmp_path: Path) -> None:
    db = tmp_path / "deep" / "nested" / "audit.sqlite"
    init_audit_db(db)
    assert db.exists()


def test_schema_meta_records_version(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    init_audit_db(db)
    conn = sqlite3.connect(str(db))
    try:
        row = conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        ).fetchone()
        assert row is not None
        assert row[0] == str(SCHEMA_VERSION)
    finally:
        conn.close()


def test_datetime_columns_declared_text(tmp_path: Path) -> None:
    """All datetime fields stored as TEXT, not INTEGER/REAL — sqlite-friendly + human-readable."""
    db = tmp_path / "audit.sqlite"
    init_audit_db(db)
    conn = sqlite3.connect(str(db))
    try:
        for table, cols in (
            ("runs", {"started_at", "completed_at"}),
            ("stage_events", {"timestamp"}),
            ("refusals_log", {"recorded_at"}),
            ("policy_fires", {"timestamp"}),
        ):
            schema = {
                row[1]: row[2]
                for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            for col in cols:
                assert schema[col].upper() == "TEXT", (
                    f"{table}.{col} declared {schema[col]} — expected TEXT for ISO8601 UTC"
                )
    finally:
        conn.close()


def test_downgrade_refused(tmp_path: Path) -> None:
    """If somehow user_version > target, init must refuse."""
    db = tmp_path / "audit.sqlite"
    init_audit_db(db)
    conn = sqlite3.connect(str(db))
    try:
        conn.execute("PRAGMA user_version = 999")
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RuntimeError, match="refusing to downgrade"):
        init_audit_db(db)


def test_memory_db_works() -> None:
    """`:memory:` is a valid path for tests — exercised by U3 backward-compat suite."""
    init_audit_db(":memory:")  # smoke: must not raise
