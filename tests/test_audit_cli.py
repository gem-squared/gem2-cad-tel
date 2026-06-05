"""U4 acceptance tests — CLI subcommands list-runs / show-run / refusals / stats.

Uses subprocess to invoke `python -m cad_trust.audit ...` so the test exercises
the actual entry point (not just the in-process functions).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from cad_trust.pipeline import run as run_pipeline

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"


@pytest.fixture(scope="module")
def populated_db(tmp_path_factory) -> Path:
    """A real audit DB populated by running the pipeline on a corpus sample."""
    db = tmp_path_factory.mktemp("audit_cli") / "audit.sqlite"
    # Run pipeline twice on different samples to have ≥2 runs in DB
    samples = sorted(SAMPLES.glob("*.png"))[:2]
    for s in samples:
        run_pipeline(s, audit_db_path=db)
    return db


def _cli(*args: str, db: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "cad_trust.audit"]
    if db is not None:
        cmd += ["--db", str(db)]
    cmd += list(args)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))


def test_list_runs_default(populated_db: Path) -> None:
    r = _cli("list-runs", db=populated_db)
    assert r.returncode == 0, r.stderr
    assert "drawing_id" in r.stdout  # header line
    assert "SUCCESS" in r.stdout


def test_list_runs_with_limit(populated_db: Path) -> None:
    r = _cli("list-runs", "--limit", "1", db=populated_db)
    assert r.returncode == 0
    # Output has header + sep + at most 1 data row
    data_rows = [ln for ln in r.stdout.splitlines() if "SUCCESS" in ln]
    assert len(data_rows) <= 1


def test_show_run_for_valid_id(populated_db: Path) -> None:
    list_r = _cli("list-runs", "--limit", "1", db=populated_db)
    # Extract a run_id from the listing — first column of first data row
    lines = list_r.stdout.splitlines()
    data_line = next(ln for ln in lines if "SUCCESS" in ln)
    run_id = data_line.split()[0]
    r = _cli("show-run", run_id, db=populated_db)
    assert r.returncode == 0, r.stderr
    assert "stage_events" in r.stdout
    assert "refusals_log" in r.stdout
    assert "policy_fires" in r.stdout
    assert "epistemic_counts" in r.stdout


def test_show_run_bad_id_exits_1(populated_db: Path) -> None:
    r = _cli("show-run", "definitely_not_a_real_run_id", db=populated_db)
    assert r.returncode == 1
    assert "not found" in r.stderr


def test_refusals_subcommand(populated_db: Path) -> None:
    r = _cli("refusals", db=populated_db)
    assert r.returncode == 0
    # Output is either "(no refusals match)" or contains attempted_type column header
    assert ("(no refusals match)" in r.stdout) or ("attempted_type" in r.stdout)


def test_stats_subcommand(populated_db: Path) -> None:
    r = _cli("stats", db=populated_db)
    assert r.returncode == 0
    assert "runs:" in r.stdout
    assert "refusals:" in r.stdout
    assert "policy_fires:" in r.stdout
    assert "epistemic distribution" in r.stdout


def test_missing_db_returns_1(tmp_path: Path) -> None:
    nonexistent = tmp_path / "ghost.sqlite"
    r = _cli("list-runs", db=nonexistent)
    assert r.returncode == 1
    assert "not found" in r.stderr
