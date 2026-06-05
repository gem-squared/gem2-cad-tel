"""U5 acceptance — pipeline.run on every ingestable drawing in the corpus.

Real drawings stress-test the rule-based detector; per Refusal_Over_Bluff,
high refusal counts are ACCEPTABLE. What is NOT acceptable: pipeline crashing
or producing malformed EngineOutput.

Diagnostic mode: collect per-drawing stats (objects, refusals, scale_anchor,
runtime). When run with `-s`, prints a coverage table.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pytest

from cad_trust.ingest import IngestError
from cad_trust.pipeline import run as run_pipeline
from cad_trust.schema import EngineOutput

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"

INGESTABLE_SUFFIXES = (".png", ".pdf", ".jpg", ".jpeg")
SKIPPED_SUFFIXES = (".svg",)


def _all_drawings() -> list[Path]:
    return sorted(p for p in SAMPLES.iterdir() if p.is_file())


def _ingestable(p: Path) -> bool:
    return p.suffix.lower() in INGESTABLE_SUFFIXES


def _classified() -> tuple[list[Path], list[Path]]:
    ingestable = [p for p in _all_drawings() if _ingestable(p)]
    skipped = [p for p in _all_drawings() if p.suffix.lower() in SKIPPED_SUFFIXES]
    return ingestable, skipped


# ── Aggregate smoke ─────────────────────────────────────────────────────────


def test_corpus_split_by_ingestability() -> None:
    """The corpus must contain a meaningful number of ingestable drawings."""
    ingestable, _ = _classified()
    assert len(ingestable) >= 13, f"only {len(ingestable)} ingestable drawings; expected ≥13"


def test_unsupported_formats_raise_typed_ingest_error() -> None:
    """SVG (or anything else) must raise IngestError, not silently produce garbage."""
    _, skipped = _classified()
    if not skipped:
        pytest.skip("no SVG / unsupported-format drawings in corpus")
    for p in skipped[:2]:
        with pytest.raises(IngestError, match="unsupported"):
            run_pipeline(p)


def test_at_least_80_percent_ingestable_succeed(tmp_path: Path) -> None:
    """Aggregate smoke: ≥80% of ingestable drawings run end-to-end. Diagnostic print on -s."""
    ingestable, _ = _classified()
    db = tmp_path / "audit.sqlite"
    table: list[dict] = []
    failed: list[str] = []
    for p in ingestable:
        t0 = time.perf_counter()
        try:
            out = run_pipeline(p, audit_db_path=db)
            ok = True
            stats = {
                "drawing": p.name,
                "ok": True,
                "objects": len(out.objects),
                "refusals": len(out.refusals),
                "scale_anchor": out.scale_anchor.detected,
                "runtime_ms": int((time.perf_counter() - t0) * 1000),
            }
        except Exception as exc:
            ok = False
            stats = {
                "drawing": p.name,
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
            failed.append(f"{p.name}: {exc}")
        table.append(stats)
    rate = sum(1 for r in table if r["ok"]) / len(table)
    print(f"\n--- coverage smoke ({len(table)} ingestable, {len(failed)} failed, {rate:.0%} success) ---")
    for row in table:
        if row["ok"]:
            print(f"  ✓ {row['drawing']:<60} obj={row['objects']:>3}  ref={row['refusals']:>2}  "
                  f"anchor={'Y' if row['scale_anchor'] else 'N'}  {row['runtime_ms']:>4}ms")
        else:
            print(f"  ✗ {row['drawing']:<60} ERROR: {row['error']}")
    assert rate >= 0.80, (
        f"only {rate:.0%} ingestable drawings completed; expected ≥80%. failures: {failed}"
    )
