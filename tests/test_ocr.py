"""U6 OCR_F acceptance tests."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cad_trust.ingest import ingest
from cad_trust.ocr import OCRResult, classify_text, run_ocr

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"


def _kr_apt_sample() -> Path:
    candidates = sorted(SAMPLES.glob("synth_apt_*.png"))
    assert candidates, "U3 must provide apt samples"
    return candidates[0]


# ── classifier unit tests ───────────────────────────────────────────────────


def test_classify_dimension_text() -> None:
    assert classify_text("4200") == "dimension_text"
    assert classify_text("12.5") == "dimension_text"
    assert classify_text("99") == "dimension_text"


def test_classify_room_label_hangul() -> None:
    assert classify_text("거실") == "room_label"
    assert classify_text("침실") == "room_label"
    assert classify_text("발코니") == "room_label"


def test_classify_room_label_latin() -> None:
    assert classify_text("Office") == "room_label"
    assert classify_text("Meeting Room") == "room_label"


def test_classify_other() -> None:
    assert classify_text("") == "other"
    assert classify_text("***") == "other"


# ── OCR integration tests ───────────────────────────────────────────────────


def test_ocr_empty_returns_typed_result() -> None:
    result = run_ocr(np.zeros((0, 0, 3), dtype=np.uint8))
    assert isinstance(result, OCRResult)
    assert result.texts == []
    assert result.diagnostic  # diagnostic non-empty


def test_ocr_too_small_returns_typed_result() -> None:
    result = run_ocr(np.full((10, 100, 3), 255, dtype=np.uint8))
    assert isinstance(result, OCRResult)
    assert result.texts == []
    assert "too small" in result.diagnostic


@pytest.mark.slow
def test_ocr_detects_at_least_one_text_on_kr_apt() -> None:
    """End-to-end: PaddleOCR runs and detects ≥1 text on a Korean apt sample."""
    sample = _kr_apt_sample()
    canonical = ingest(sample).canonical_image
    result = run_ocr(canonical)
    assert result.texts, f"PaddleOCR returned no text on {sample.name}: {result.diagnostic}"
    # Each detection has bbox + classification + evidence
    for d in result.texts:
        assert d.text
        assert d.classification in {"dimension_text", "room_label", "other"}
        assert d.evidence, "every detection must carry evidence"
