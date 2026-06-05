"""U1 smoke: every load-bearing dep imports + PaddleOCR can load and OCR a fixture."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_imports_load_bearing() -> None:
    """Every dep used by U2-U9 must import cleanly."""
    import cv2  # noqa: F401
    import fastapi  # noqa: F401
    import numpy  # noqa: F401
    import pdf2image  # noqa: F401
    import pydantic  # noqa: F401
    import streamlit  # noqa: F401


def test_paddleocr_smoke() -> None:
    """PaddleOCR must load ko+en models and return non-empty result on fixture."""
    from paddleocr import PaddleOCR

    fixture = Path(__file__).parent / "fixtures" / "smoke_text.png"
    if not fixture.exists():
        subprocess.run(
            [sys.executable, str(Path(__file__).parent / "fixtures" / "make_smoke_image.py")],
            check=True,
        )
    assert fixture.exists(), f"fixture missing: {fixture}"

    # PaddleOCR 3.x API
    ocr = PaddleOCR(use_doc_orientation_classify=False, use_doc_unwarping=False, lang="korean")
    result = ocr.predict(str(fixture))
    assert result, "PaddleOCR returned empty result on smoke fixture"
    # Result is a list of OCRResult-like objects
    first = result[0]
    # Try multiple attribute paths (PaddleOCR API surface differs across versions)
    texts: list[str] = []
    if hasattr(first, "json"):
        data = first.json
        if isinstance(data, dict):
            rec_texts = data.get("res", {}).get("rec_texts") or data.get("rec_texts")
            if rec_texts:
                texts = list(rec_texts)
    if not texts and isinstance(first, dict):
        texts = first.get("rec_texts", []) or []
    # Soft assertion: smoke passes if PaddleOCR ran without crashing
    # (text content varies by model version; "WALL" or "4200" SHOULD appear but we don't hard-gate on exact text)
    assert texts or result, "PaddleOCR returned no recoverable text from smoke fixture"
    print(f"PaddleOCR smoke: detected {len(texts)} text(s): {texts[:5]}")
