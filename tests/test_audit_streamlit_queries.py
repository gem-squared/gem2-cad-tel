"""U5 acceptance — the SQL queries the Streamlit Past Runs tab uses.

Streamlit itself can't be unit-tested headlessly without browser automation,
but its data-fetch code is plain SQL. We exercise that here so a future
schema change can't silently break the tab.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cad_trust.audit_schema import init_audit_db
from cad_trust.pipeline import run as run_pipeline

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"


def _populate(db: Path) -> None:
    for s in sorted(SAMPLES.glob("*.png"))[:2]:
        run_pipeline(s, audit_db_path=db)


@pytest.fixture
def empty_db(tmp_path: Path) -> Path:
    db = tmp_path / "empty.sqlite"
    init_audit_db(db)
    return db


@pytest.fixture
def populated_db(tmp_path: Path) -> Path:
    db = tmp_path / "pop.sqlite"
    _populate(db)
    return db


def _conn(db: Path) -> sqlite3.Connection:
    c = sqlite3.connect(str(db))
    c.row_factory = sqlite3.Row
    return c


# Each query below is a verbatim copy of what ui/app.py executes in the Past Runs tab.
# If schema changes, these break, the Streamlit tab would too — we catch it here.


def test_overview_metric_queries_run_on_empty(empty_db: Path) -> None:
    c = _conn(empty_db)
    try:
        assert c.execute("SELECT COUNT(*) AS c FROM runs").fetchone()["c"] == 0
        assert c.execute("SELECT COUNT(*) AS c FROM runs WHERE exit_state='SUCCESS'").fetchone()["c"] == 0
        assert c.execute("SELECT COUNT(*) AS c FROM runs WHERE exit_state='FAILURE'").fetchone()["c"] == 0
        assert c.execute("SELECT COUNT(*) AS c FROM refusals_log").fetchone()["c"] == 0
        assert c.execute("SELECT COUNT(*) AS c FROM policy_fires").fetchone()["c"] == 0
    finally:
        c.close()


def test_recent_runs_query_on_populated(populated_db: Path) -> None:
    c = _conn(populated_db)
    try:
        rows = c.execute(
            "SELECT run_id, drawing_id, started_at, duration_ms, exit_state "
            "FROM runs ORDER BY started_at DESC LIMIT 50"
        ).fetchall()
        assert len(rows) >= 1
        assert all(r["run_id"] for r in rows)
    finally:
        c.close()


def test_refusal_aggregation_query(populated_db: Path) -> None:
    c = _conn(populated_db)
    try:
        rows = c.execute(
            "SELECT attempted_type, COUNT(*) AS cnt FROM refusals_log "
            "GROUP BY attempted_type ORDER BY cnt DESC"
        ).fetchall()
        # Either some rows or none — both valid; query must not raise
        for r in rows:
            assert r["attempted_type"]
            assert r["cnt"] >= 1
    finally:
        c.close()


def test_drill_into_run_queries(populated_db: Path) -> None:
    c = _conn(populated_db)
    try:
        run = c.execute("SELECT run_id FROM runs LIMIT 1").fetchone()
        assert run is not None
        rid = run["run_id"]

        events = c.execute(
            "SELECT timestamp, stage, level, message, payload_json "
            "FROM stage_events WHERE run_id = ? ORDER BY event_id",
            (rid,),
        ).fetchall()
        assert events  # populated by U3 instrumentation

        refs = c.execute(
            "SELECT attempted_type, why, region_json FROM refusals_log WHERE run_id = ?", (rid,)
        ).fetchall()
        # ≥0 allowed; just must not raise

        pols = c.execute(
            "SELECT policy_name, detail_json, timestamp FROM policy_fires WHERE run_id = ?",
            (rid,),
        ).fetchall()
        # ≥0 allowed

        eps = c.execute(
            "SELECT stage, field, tag, count FROM epistemic_counts WHERE run_id = ? "
            "ORDER BY field, tag",
            (rid,),
        ).fetchall()
        # If compose ran, eps should be populated
        if events:
            assert eps, "compose stage events present but epistemic_counts empty"
    finally:
        c.close()


def test_ui_module_imports_cleanly() -> None:
    """Smoke: ui.app imports without exceptions (catches Streamlit syntax errors)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ui_app_smoke", ROOT / "ui" / "app.py")
    assert spec and spec.loader
    # We can't fully execute (Streamlit runtime context required) but we can
    # at least verify the file is syntactically valid Python.
    src = (ROOT / "ui" / "app.py").read_text()
    compile(src, "ui/app.py", "exec")
