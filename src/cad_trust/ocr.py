"""U6: OCR_F — PaddleOCR (ko+en) + dimension/label classification.

Contract:
    A: canonical_image (from U4) — ndarray (H,W,3) uint8
    B: OCRResult { texts: list[TextDetection], diagnostic }
    P: PaddleOCR ko+en models downloaded (U1 smoke gates this); dpi ≥ 150

Classification heuristic (v0.1 defaults; v0.2 refines):
    dimension_text — matches ^\\d{2,5}(\\.\\d+)?$
    room_label     — non-empty, all chars matching Hangul or Latin letters
    other          — fallback
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

import numpy as np

if TYPE_CHECKING:
    from cad_trust.audit import AuditContext


@dataclass
class Evidence:
    source: str
    signal: str


@dataclass
class TextDetection:
    text: str
    bbox: list[tuple[float, float]]  # 4-point quad in image coords
    char_conf: float
    classification: str  # 'dimension_text' | 'room_label' | 'other'
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class OCRResult:
    texts: list[TextDetection]
    diagnostic: str = ""


DIMENSION_RE = re.compile(r"^\d{2,5}(\.\d+)?$")
HANGUL_RE = re.compile(r"[ㄱ-힝]")
LATIN_RE = re.compile(r"[A-Za-z]")
ROOM_LABEL_RE = re.compile(r"^[A-Za-zㄱ-힝][\wㄱ-힝\s]*$")


def classify_text(text: str) -> str:
    s = text.strip()
    if not s:
        return "other"
    if DIMENSION_RE.match(s):
        return "dimension_text"
    if ROOM_LABEL_RE.match(s) and (HANGUL_RE.search(s) or LATIN_RE.search(s)):
        return "room_label"
    return "other"


class _LazyPaddleOCR:
    """Lazy singleton — PaddleOCR's model load is slow; reuse across calls."""

    _instance: ClassVar["_LazyPaddleOCR | None"] = None

    def __init__(self, lang: str = "korean") -> None:
        from paddleocr import PaddleOCR

        self.ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            lang=lang,
        )

    @classmethod
    def get(cls) -> "_LazyPaddleOCR":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def _extract_from_result(raw: object) -> tuple[list[str], list[list[tuple[float, float]]], list[float]]:
    """PaddleOCR 3.x returns a list of OCRResult-like objects. Try multiple shapes."""
    texts: list[str] = []
    quads: list[list[tuple[float, float]]] = []
    scores: list[float] = []
    if not raw:
        return texts, quads, scores
    first = raw[0] if isinstance(raw, list) else raw
    data = None
    if hasattr(first, "json"):
        j = first.json
        if isinstance(j, dict):
            data = j.get("res", j)
    if data is None and isinstance(first, dict):
        data = first.get("res", first)
    if not isinstance(data, dict):
        return texts, quads, scores
    rec_texts = data.get("rec_texts") or []
    rec_scores = data.get("rec_scores") or []
    rec_polys = data.get("rec_polys") or data.get("dt_polys") or []
    for i, t in enumerate(rec_texts):
        texts.append(str(t))
        try:
            poly = rec_polys[i]
            # poly may be ndarray or list of [x,y] pairs
            quad = [(float(p[0]), float(p[1])) for p in list(poly)]
        except (IndexError, TypeError, ValueError):
            quad = []
        quads.append(quad)
        try:
            scores.append(float(rec_scores[i]))
        except (IndexError, TypeError, ValueError):
            scores.append(0.0)
    return texts, quads, scores


def run_ocr(
    canonical_image: np.ndarray,
    audit: "AuditContext | None" = None,
) -> OCRResult:
    """Run PaddleOCR on a canonical raster + classify each detection."""
    if audit is not None:
        audit.emit_stage_event("ocr", "INFO", "starting")
    if canonical_image is None or canonical_image.size == 0:
        result = OCRResult(texts=[], diagnostic="empty input image")
        if audit is not None:
            audit.emit_stage_event("ocr", "WARN", "empty input", {"diagnostic": result.diagnostic})
        return result
    if canonical_image.ndim != 3 or canonical_image.shape[2] != 3:
        result = OCRResult(texts=[], diagnostic="expected (H,W,3) uint8 image")
        if audit is not None:
            audit.emit_stage_event("ocr", "WARN", "bad shape", {"diagnostic": result.diagnostic})
        return result
    h, _, _ = canonical_image.shape
    if h < 50:
        result = OCRResult(texts=[], diagnostic=f"image too small (h={h}<50)")
        if audit is not None:
            audit.emit_stage_event("ocr", "WARN", "too small", {"diagnostic": result.diagnostic})
        return result
    try:
        ocr = _LazyPaddleOCR.get().ocr
        raw = ocr.predict(canonical_image)
    except Exception as exc:
        result = OCRResult(texts=[], diagnostic=f"PaddleOCR.predict raised: {exc}")
        if audit is not None:
            audit.emit_stage_event("ocr", "ERROR", "predict raised", {"error": str(exc)})
        return result
    texts_raw, quads, scores = _extract_from_result(raw)
    if not texts_raw:
        return OCRResult(texts=[], diagnostic="PaddleOCR returned 0 text detections")
    detections: list[TextDetection] = []
    skipped_empty = 0
    for t, quad, conf in zip(texts_raw, quads, scores):
        if not t or not t.strip():
            # Detector hit, recognizer empty — drop as noise; surface in diagnostic
            skipped_empty += 1
            continue
        cls = classify_text(t)
        detections.append(
            TextDetection(
                text=t,
                bbox=quad,
                char_conf=conf,
                classification=cls,
                evidence=[
                    Evidence(
                        source="paddleocr",
                        signal=f"text='{t}', char_conf={conf:.2f}, classified={cls}",
                    )
                ],
            )
        )
    diag = ""
    if skipped_empty:
        diag = f"dropped {skipped_empty} empty-text detection(s) (recognizer returned blank)"
    result = OCRResult(texts=detections, diagnostic=diag)
    if audit is not None:
        by_class = {"dimension_text": 0, "room_label": 0, "other": 0}
        for d in detections:
            by_class[d.classification] = by_class.get(d.classification, 0) + 1
        audit.emit_stage_event(
            "ocr",
            "INFO",
            "complete",
            {"total": len(detections), "by_class": by_class, "skipped_empty": skipped_empty},
        )
    return result
