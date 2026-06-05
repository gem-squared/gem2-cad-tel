"""Top-level pipeline glue — single entrypoint that wires U4-U8 together."""
from __future__ import annotations

from pathlib import Path

from cad_trust.compose import compose
from cad_trust.geometry import extract_geometry
from cad_trust.ingest import ingest
from cad_trust.ocr import run_ocr
from cad_trust.schema import EngineOutput
from cad_trust.symbols import detect_symbols


def run(drawing_path: Path | str, dpi_target: int = 200) -> EngineOutput:
    """Run the full pipeline on one drawing → typed EngineOutput."""
    path = Path(drawing_path)
    ingest_result = ingest(path, dpi_target=dpi_target)
    canonical = ingest_result.canonical_image
    geom = extract_geometry(canonical)
    ocr = run_ocr(canonical)
    syms = detect_symbols(canonical, geom, ocr)
    return compose(drawing_id=path.stem, canonical_image=canonical, geometry=geom, ocr=ocr, symbols=syms)
