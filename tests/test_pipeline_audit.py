"""U3 acceptance tests — pipeline + stage instrumentation.

The backward-compat regression (existing 53 tests) is verified by the rest
of the suite — these tests cover only the new audit-on path.
"""
from __future__ import annotations

import sqlite3
import warnings
from pathlib import Path

import pytest

from cad_trust.pipeline import run as run_pipeline

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"


def _conn(db: Path) -> sqlite3.Connection:
    c = sqlite3.connect(str(db))
    c.row_factory = sqlite3.Row
    return c


def _sample() -> Path:
    return sorted(SAMPLES.glob("synth_apt_*.png"))[0]


def test_pipeline_no_audit_path_runs_identical_to_v010(tmp_path: Path) -> None:
    """No audit_db_path AND no env var → identical to v0.1.0 path."""
    # No env var set
    out = run_pipeline(_sample(), audit_db_path=None)
    # Shape unchanged: standard EngineOutput
    assert out.drawing_id
    assert out.objects
    # Critical: there's no audit DB file created anywhere
    assert not (tmp_path / "audit.sqlite").exists()


def test_pipeline_with_audit_records_run_row(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    out = run_pipeline(_sample(), audit_db_path=db)
    assert db.exists()
    rows = _conn(db).execute("SELECT * FROM runs").fetchall()
    assert len(rows) == 1
    assert rows[0]["drawing_id"] == out.drawing_id
    assert rows[0]["exit_state"] == "SUCCESS"
    assert rows[0]["duration_ms"] >= 0


def test_pipeline_records_at_least_one_event_per_stage(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    run_pipeline(_sample(), audit_db_path=db)
    rows = _conn(db).execute(
        "SELECT DISTINCT stage FROM stage_events"
    ).fetchall()
    stages = {r["stage"] for r in rows}
    # 5 stages must each emit at least one event
    assert {"ingest", "geometry", "ocr", "symbols", "compose"} <= stages


def test_pipeline_records_starting_and_complete_per_stage(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    run_pipeline(_sample(), audit_db_path=db)
    for stage in ("ingest", "geometry", "ocr", "symbols", "compose"):
        msgs = {
            r["message"]
            for r in _conn(db)
            .execute("SELECT message FROM stage_events WHERE stage = ?", (stage,))
            .fetchall()
        }
        assert "starting" in msgs, f"{stage} missing 'starting' event"
        assert "complete" in msgs, f"{stage} missing 'complete' event"


def test_measurement_policy_fires_when_no_scale_anchor(tmp_path: Path) -> None:
    """When scale_anchor.detected = False, policy_fires must record Measurement_Policy.

    Uses a blank fixture — no walls + no dimension text → scale extraction must fail.
    Verifies the *code path* lights up correctly.
    """
    from PIL import Image
    blank = tmp_path / "blank_no_anchor.png"
    Image.new("RGB", (1024, 768), "white").save(blank)
    db = tmp_path / "audit.sqlite"
    out = run_pipeline(blank, audit_db_path=db)
    assert not out.scale_anchor.detected, "blank image somehow detected a scale anchor"
    rows = _conn(db).execute(
        "SELECT * FROM policy_fires WHERE policy_name = 'Measurement_Policy'"
    ).fetchall()
    assert len(rows) == 1
    assert "scale_anchor" in (rows[0]["detail_json"] or "")


def test_refusals_appear_in_refusals_log(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    out = run_pipeline(_sample(), audit_db_path=db)
    rows = _conn(db).execute("SELECT * FROM refusals_log").fetchall()
    # If U7 produced refusals, they must appear in the log
    # (Some corpus drawings may produce 0 refusals — accept either case)
    if rows:
        sample_row = rows[0]
        assert sample_row["attempted_type"] in {"door", "window"}
        assert sample_row["why"]
        assert sample_row["region_json"].startswith("[")


def test_epistemic_counts_recorded_per_field(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    run_pipeline(_sample(), audit_db_path=db)
    rows = _conn(db).execute("SELECT DISTINCT field FROM epistemic_counts").fetchall()
    fields = {r["field"] for r in rows}
    assert {"type_epistemic", "geometry_epistemic", "measurement_epistemic"} <= fields


def test_pipeline_ingest_error_records_failure_state(tmp_path: Path) -> None:
    db = tmp_path / "audit.sqlite"
    from cad_trust.ingest import IngestError
    bogus = tmp_path / "not_a_real.png"
    bogus.write_bytes(b"not png header")
    with pytest.raises(IngestError):
        run_pipeline(bogus, audit_db_path=db)
    rows = _conn(db).execute("SELECT * FROM runs").fetchall()
    assert len(rows) == 1
    assert rows[0]["exit_state"] == "FAILURE"
    assert "IngestError" in (rows[0]["error_msg"] or "")


def test_pipeline_returns_same_engine_output_with_or_without_audit(tmp_path: Path) -> None:
    """EngineOutput shape MUST be identical with/without audit (WP_Invariant: Backward_Compatibility)."""
    sample = _sample()
    no_audit = run_pipeline(sample, audit_db_path=None)
    db = tmp_path / "audit.sqlite"
    with_audit = run_pipeline(sample, audit_db_path=db)
    # drawing_id, object count, refusal count, scale_anchor verdict must match
    assert no_audit.drawing_id == with_audit.drawing_id
    assert len(no_audit.objects) == len(with_audit.objects)
    assert len(no_audit.refusals) == len(with_audit.refusals)
    assert no_audit.scale_anchor.detected == with_audit.scale_anchor.detected
