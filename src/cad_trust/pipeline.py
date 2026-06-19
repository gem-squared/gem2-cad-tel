"""Top-level pipeline glue — single entrypoint that wires U4-U8 together.

`audit_db_path` is optional: None → identical to v0.1.0 behavior. When set
(or when the env var GEM2_VISION_AUDIT_DB is exported), an AuditContext
opens for the run and all stage events / refusals / policy fires /
epistemic counts are recorded into the SQLite DB.
"""
from __future__ import annotations

import os
from pathlib import Path

from cad_trust.compose import compose
from cad_trust.geometry import extract_geometry
from cad_trust.ingest import ingest
from cad_trust.ocr import run_ocr
from cad_trust.schema import EngineOutput
from cad_trust.symbols import detect_symbols


def _resolve_audit_db_path(audit_db_path: Path | str | None) -> Path | str | None:
    """If caller didn't provide a path, fall back to env var (opt-in for power users)."""
    if audit_db_path is not None:
        return audit_db_path
    env = os.environ.get("GEM2_VISION_AUDIT_DB")
    return env if env else None


def run(
    drawing_path: Path | str,
    dpi_target: int = 200,
    audit_db_path: Path | str | None = None,
) -> EngineOutput:
    """Run the full pipeline on one drawing → typed EngineOutput.

    When audit_db_path is None and GEM2_VISION_AUDIT_DB is unset → no audit overhead.
    When either is set → wraps the run in an AuditContext recording all critical paths.
    """
    path = Path(drawing_path)
    resolved = _resolve_audit_db_path(audit_db_path)

    if resolved is None:
        # Backward-compatible v0.1.0 path — no audit overhead at all
        ingest_result = ingest(path, dpi_target=dpi_target)
        canonical = ingest_result.canonical_image
        geom = extract_geometry(canonical)
        ocr = run_ocr(canonical)
        syms = detect_symbols(canonical, geom, ocr)
        return compose(
            drawing_id=path.stem, canonical_image=canonical, geometry=geom, ocr=ocr, symbols=syms
        )

    # Audit path — opt-in
    from cad_trust.audit import AuditContext  # local import to avoid cycles

    with AuditContext(resolved, drawing_id=path.stem) as ctx:
        ingest_result = ingest(path, dpi_target=dpi_target, audit=ctx)
        canonical = ingest_result.canonical_image
        geom = extract_geometry(canonical, audit=ctx)
        ocr = run_ocr(canonical, audit=ctx)
        syms = detect_symbols(canonical, geom, ocr, audit=ctx)
        return compose(
            drawing_id=path.stem,
            canonical_image=canonical,
            geometry=geom,
            ocr=ocr,
            symbols=syms,
            audit=ctx,
        )
