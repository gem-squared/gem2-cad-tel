"""U2 acceptance tests — AuditContext lifecycle + emission API + failure-soft."""
from __future__ import annotations

import sqlite3
import warnings
from pathlib import Path

import pytest

from cad_trust.audit import AuditContext, audit_run


def _conn(db: Path) -> sqlite3.Connection:
    c = sqlite3.connect(str(db))
    c.row_factory = sqlite3.Row
    return c


def test_enter_inserts_runs_row(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    with audit_run(db, "test_drawing_01") as ctx:
        rows = _conn(db).execute(
            "SELECT * FROM runs WHERE run_id = ?", (ctx.run_id,)
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["drawing_id"] == "test_drawing_01"
        assert rows[0]["exit_state"] == "in_progress"
        assert rows[0]["started_at"]
        assert rows[0]["completed_at"] is None


def test_exit_clean_updates_runs_to_success(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    with audit_run(db, "drawing_x") as ctx:
        run_id = ctx.run_id
    row = _conn(db).execute(
        "SELECT * FROM runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    assert row["exit_state"] == "SUCCESS"
    assert row["completed_at"]
    assert row["duration_ms"] is not None and row["duration_ms"] >= 0
    assert row["error_msg"] is None


def test_exit_on_exception_records_failure_and_reraises(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    captured_run_id: str | None = None
    with pytest.raises(ValueError, match="boom"):
        with audit_run(db, "drawing_x") as ctx:
            captured_run_id = ctx.run_id
            raise ValueError("boom")
    assert captured_run_id is not None
    row = _conn(db).execute(
        "SELECT * FROM runs WHERE run_id = ?", (captured_run_id,)
    ).fetchone()
    assert row["exit_state"] == "FAILURE"
    assert row["error_msg"]
    assert "ValueError" in row["error_msg"]
    assert "boom" in row["error_msg"]


def test_emit_stage_event_records_row(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    with audit_run(db, "draw") as ctx:
        ctx.emit_stage_event("ingest", "INFO", "starting", {"path": "/tmp/x.png"})
    rows = _conn(db).execute("SELECT * FROM stage_events").fetchall()
    assert len(rows) == 1
    assert rows[0]["stage"] == "ingest"
    assert rows[0]["level"] == "INFO"
    assert rows[0]["message"] == "starting"
    assert "/tmp/x.png" in (rows[0]["payload_json"] or "")


def test_record_refusal_serializes_region_as_json(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    with audit_run(db, "draw") as ctx:
        ctx.record_refusal(
            region=[[10.0, 20.0], [50.0, 80.0]],
            attempted_type="door",
            why="single-signal arc without wall_proximity",
        )
    rows = _conn(db).execute("SELECT * FROM refusals_log").fetchall()
    assert len(rows) == 1
    assert rows[0]["attempted_type"] == "door"
    assert "wall_proximity" in rows[0]["why"]
    assert "[10.0, 20.0]" in rows[0]["region_json"]


def test_record_policy_fire_serializes_detail(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    with audit_run(db, "draw") as ctx:
        ctx.record_policy_fire(
            "Measurement_Policy",
            detail={"reason": "no scale_anchor", "objects_affected": 7},
        )
    rows = _conn(db).execute("SELECT * FROM policy_fires").fetchall()
    assert len(rows) == 1
    assert rows[0]["policy_name"] == "Measurement_Policy"
    assert "no scale_anchor" in rows[0]["detail_json"]


def test_record_epistemic_count_upserts(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    with audit_run(db, "draw") as ctx:
        ctx.record_epistemic_count("compose", "⊢", "type_epistemic", 3)
        ctx.record_epistemic_count("compose", "⊢", "type_epistemic", 5)  # update
        ctx.record_epistemic_count("compose", "⊥", "measurement_epistemic", 7)
    rows = _conn(db).execute(
        "SELECT * FROM epistemic_counts ORDER BY tag"
    ).fetchall()
    assert len(rows) == 2
    by_tag = {r["tag"]: r for r in rows}
    assert by_tag["⊢"]["count"] == 5  # updated to 5
    assert by_tag["⊥"]["count"] == 7


def test_emit_outside_context_warns(tmp_path: Path) -> None:
    """Calling methods after __exit__ → warnings.warn, not exception."""
    db = tmp_path / "audit.sqlite"
    with audit_run(db, "draw") as ctx:
        held = ctx
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        held.emit_stage_event("ingest", "INFO", "after-exit")
        held.record_refusal([[0, 0], [1, 1]], "door", "test")
    assert any("outside of context" in str(x.message) for x in w)


def test_audit_failure_soft_does_not_abort_pipeline(tmp_path: Path) -> None:
    """If sqlite raises mid-emit, we warn + continue, never propagate the sqlite error."""
    db = tmp_path / "audit.sqlite"
    with audit_run(db, "draw") as ctx:
        # Force the connection closed under the context's feet
        if ctx._conn is not None:
            ctx._conn.close()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ctx.emit_stage_event("ingest", "INFO", "starting", {"k": "v"})
            ctx.record_refusal([[0, 0], [1, 1]], "door", "test")
            ctx.record_policy_fire("Measurement_Policy", {"x": 1})
            ctx.record_epistemic_count("compose", "⊢", "type", 1)
        # At least one warning surfaced — no exception escaped
        assert any("failed" in str(x.message) for x in w)
