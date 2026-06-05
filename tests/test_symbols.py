"""U7 Symbol_F acceptance tests."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cad_trust.geometry import extract_geometry
from cad_trust.ingest import ingest
from cad_trust.ocr import run_ocr
from cad_trust.symbols import SymbolResult, detect_symbols

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"


def _kr_sample() -> Path:
    return sorted(SAMPLES.glob("synth_apt_*.png"))[0]


def test_empty_input_returns_typed_result() -> None:
    from cad_trust.geometry import GeometryResult
    from cad_trust.ocr import OCRResult

    result = detect_symbols(
        np.zeros((0, 0, 3), dtype=np.uint8),
        GeometryResult(lines=[], contours=[], wall_candidates=[]),
        OCRResult(texts=[]),
    )
    assert isinstance(result, SymbolResult)
    assert result.diagnostic


def test_every_detection_has_evidence() -> None:
    """No detection emitted without evidence."""
    sample = _kr_sample()
    canonical = ingest(sample).canonical_image
    geom = extract_geometry(canonical)
    ocr = run_ocr(canonical)
    result = detect_symbols(canonical, geom, ocr)
    for d in result.doors:
        assert d.evidence, "door without evidence"
    for w in result.windows:
        assert w.evidence, "window without evidence"
    for s in result.spaces:
        assert s.evidence, "space without evidence"


def test_no_detection_has_fewer_than_two_signals() -> None:
    """Per Refusal_Over_Bluff invariant: low-evidence candidates flow to refusal_candidates."""
    sample = _kr_sample()
    canonical = ingest(sample).canonical_image
    geom = extract_geometry(canonical)
    ocr = run_ocr(canonical)
    result = detect_symbols(canonical, geom, ocr)
    for d in result.doors:
        assert len(d.evidence) >= 2, f"door has {len(d.evidence)} signals; <2 should flow to refusals"
    for w in result.windows:
        assert len(w.evidence) >= 2, f"window has {len(w.evidence)} signals; <2 should flow to refusals"


def test_refusal_candidates_have_specific_why() -> None:
    """every refusal_candidate.why_refused is human-readable specific text (not 'unknown')."""
    sample = _kr_sample()
    canonical = ingest(sample).canonical_image
    geom = extract_geometry(canonical)
    ocr = run_ocr(canonical)
    result = detect_symbols(canonical, geom, ocr)
    for r in result.refusal_candidates:
        assert r.why_refused
        assert r.why_refused.lower() not in {"unknown", "error", ""}
        assert len(r.why_refused) > 10  # not a one-word stub


def test_pipeline_never_silently_empty() -> None:
    """On a real sample: |doors| + |windows| + |spaces| + |refusal_candidates| ≥ 1."""
    sample = _kr_sample()
    canonical = ingest(sample).canonical_image
    geom = extract_geometry(canonical)
    ocr = run_ocr(canonical)
    result = detect_symbols(canonical, geom, ocr)
    total = len(result.doors) + len(result.windows) + len(result.spaces) + len(result.refusal_candidates)
    assert total >= 1, f"pipeline silently empty on {sample.name} (diagnostic: {result.diagnostic})"
