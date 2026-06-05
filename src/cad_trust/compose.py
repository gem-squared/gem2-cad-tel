"""U8: Compose_F + Aggregate_F — per-field EEF + scale-anchor + aggregates.

Contract:
    A: { canonical_image, geometry (U5), ocr (U6), symbols (U7) }
    B: EngineOutput (U2 schema) with per-field epistemic + refusals + aggregates

WP-Level invariants enforced here:
    Measurement_Policy: ¬scale_anchor → all measurement_mm = None + tag = ⊥
    Refusal_Over_Bluff: U7 refusal_candidates promoted to top-level refusals
    Provenance_Visibility: drawing_id flows through from caller

This is THE TPMN heart of the engine.
"""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np

from cad_trust.geometry import GeometryResult, WallCandidate
from cad_trust.ocr import OCRResult
from cad_trust.schema import (
    Aggregate,
    Aggregates,
    EngineOutput,
    EpistemicMark,
    EpistemicTagLiteral,
    Evidence,
    Geometry,
    Object,
    Refusal,
    ScaleAnchor,
)
from cad_trust.symbols import RefusalCandidate, SymbolResult

# Scale anchor tolerance: candidate px_per_mm cluster within ±5%
SCALE_ANCHOR_TOL = 0.05
SCALE_ANCHOR_MIN_AGREEMENTS = 2


def _ev(source: str, signal: str) -> Evidence:
    return Evidence(source=source, signal=signal)


def _mark_grounded(evs: list[Evidence]) -> EpistemicMark:
    return EpistemicMark(tag="⊢", evidence=evs)


def _mark_inferred(evs: list[Evidence]) -> EpistemicMark:
    return EpistemicMark(tag="⊨", evidence=evs)


def _mark_extrapolated(evs: list[Evidence], basis: str) -> EpistemicMark:
    return EpistemicMark(tag="⊬", evidence=evs, basis=basis)


def _mark_unknown(gap: str) -> EpistemicMark:
    return EpistemicMark(tag="⊥", evidence=[], gap=gap)


def _bbox_to_coords(bbox: list[tuple[float, float]]) -> list[list[float]]:
    return [[float(p[0]), float(p[1])] for p in bbox]


# ── scale anchor extraction ─────────────────────────────────────────────────


def _wall_length_px(wall: WallCandidate) -> float:
    pts = wall.polyline
    if len(pts) < 2:
        return 0.0
    total = 0.0
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        total += math.hypot(x2 - x1, y2 - y1)
    return total


def _try_extract_scale_anchor(
    ocr: OCRResult, walls: list[WallCandidate]
) -> tuple[ScaleAnchor, str]:
    """Try to match dimension_text values (mm) against wall lengths (px).

    Strategy: for each (dim, wall) pair compute candidate px_per_mm.
    Look for a cluster of ≥SCALE_ANCHOR_MIN_AGREEMENTS values within
    ±SCALE_ANCHOR_TOL of each other. If found → detected.
    """
    dims_mm: list[float] = []
    for t in ocr.texts:
        if t.classification != "dimension_text":
            continue
        try:
            dims_mm.append(float(t.text))
        except ValueError:
            continue
    if not dims_mm or not walls:
        return (
            ScaleAnchor(detected=False, px_per_mm=None, source=None),
            "no dimension_text + wall_candidate pair available",
        )
    candidates: list[float] = []
    for dim in dims_mm:
        for w in walls:
            L = _wall_length_px(w)
            if dim > 0 and L > 50:
                candidates.append(L / dim)
    if not candidates:
        return (
            ScaleAnchor(detected=False, px_per_mm=None, source=None),
            "no candidate px_per_mm ratios produced",
        )
    candidates.sort()
    for i, c in enumerate(candidates):
        agreements = [
            c2 for c2 in candidates if abs(c2 - c) / c <= SCALE_ANCHOR_TOL
        ]
        if len(agreements) >= SCALE_ANCHOR_MIN_AGREEMENTS:
            mean = sum(agreements) / len(agreements)
            return (
                ScaleAnchor(detected=True, px_per_mm=mean, source="dimension_text_match"),
                f"cluster of {len(agreements)} candidate ratios within ±{SCALE_ANCHOR_TOL:.0%} of {mean:.4f} px/mm",
            )
    return (
        ScaleAnchor(detected=False, px_per_mm=None, source=None),
        f"no cluster of ≥{SCALE_ANCHOR_MIN_AGREEMENTS} agreeing px/mm ratios (sample: {[f'{c:.3f}' for c in candidates[:5]]})",
    )


# ── compose objects ─────────────────────────────────────────────────────────


def _compose_walls(walls: list[WallCandidate], scale: ScaleAnchor, start_id: int) -> tuple[list[Object], int]:
    objects: list[Object] = []
    nid = start_id
    for w in walls:
        evs = [_ev(e.source, e.signal) for e in w.evidence]
        type_mark = _mark_grounded(evs)  # parallel-pair pattern is direct evidence
        geom_evs = [_ev("opencv_line_pair", "polyline endpoints from paired Hough lines")]
        geom = Geometry(kind="polyline", coords_px=[[p[0], p[1]] for p in w.polyline])
        geom_mark = _mark_inferred(geom_evs)
        measurement_mm: float | None = None
        if scale.detected and scale.px_per_mm:
            L_px = _wall_length_px(w)
            measurement_mm = L_px / scale.px_per_mm
            meas_mark = _mark_inferred(
                [_ev("scale_anchor", f"px_per_mm={scale.px_per_mm:.4f}, length_px={L_px:.1f}")]
            )
        else:
            meas_mark = _mark_unknown("no scale_anchor; mm conversion refused per Measurement_Policy")
        review = "auto_accepted" if type_mark.tag in ("⊢", "⊨") and geom_mark.tag in ("⊢", "⊨") else "needs_human"
        nid += 1
        objects.append(
            Object(
                object_id=f"obj_{nid:04d}",
                type="wall_structural",  # v0.1 doesn't distinguish wet/dry/structural
                type_epistemic=type_mark,
                geometry=geom,
                geometry_epistemic=geom_mark,
                measurement_mm=measurement_mm,
                measurement_epistemic=meas_mark,
                review_status=review,
            )
        )
    return objects, nid


def _compose_doors(doors: list, scale: ScaleAnchor, start_id: int) -> tuple[list[Object], int]:
    objects: list[Object] = []
    nid = start_id
    for d in doors:
        evs = [_ev(e.source, e.signal) for e in d.evidence]
        type_mark = _mark_inferred(evs)  # arc + wall_proximity = inferred door
        geom = Geometry(kind="bbox", coords_px=_bbox_to_coords(d.bbox))
        geom_mark = _mark_inferred([_ev("opencv_arc", "bbox encloses arc + opening")])
        meas_mark = _mark_unknown("no scale_anchor") if not scale.detected else _mark_inferred(
            [_ev("scale_anchor", f"px_per_mm={scale.px_per_mm:.4f}")]
        )
        measurement_mm: float | None = None
        if scale.detected and scale.px_per_mm and d.arc_radius:
            measurement_mm = (2 * d.arc_radius) / scale.px_per_mm  # door width ≈ 2r
        review = "auto_accepted" if type_mark.tag in ("⊢", "⊨") else "needs_human"
        nid += 1
        objects.append(
            Object(
                object_id=f"obj_{nid:04d}",
                type="door",
                type_epistemic=type_mark,
                geometry=geom,
                geometry_epistemic=geom_mark,
                measurement_mm=measurement_mm,
                measurement_epistemic=meas_mark,
                review_status=review,
            )
        )
    return objects, nid


def _compose_windows(windows: list, scale: ScaleAnchor, start_id: int) -> tuple[list[Object], int]:
    objects: list[Object] = []
    nid = start_id
    for w in windows:
        evs = [_ev(e.source, e.signal) for e in w.evidence]
        # Window detection in v0.1 is double-line + wall_proximity. Calling it "window"
        # specifically (vs "balcony_sash") is an extrapolation — name the basis.
        type_mark = _mark_extrapolated(
            evs,
            basis=(
                "double parallel line in wall span is consistent with both 'window' and "
                "'balcony_sash'; v0.1 has no semantic verifier — VLM_Verify lands in v0.2"
            ),
        )
        geom = Geometry(kind="bbox", coords_px=_bbox_to_coords(w.bbox))
        geom_mark = _mark_inferred([_ev("opencv_double_line", "bbox encloses paired line span")])
        meas_mark = _mark_unknown("no scale_anchor") if not scale.detected else _mark_inferred(
            [_ev("scale_anchor", f"px_per_mm={scale.px_per_mm:.4f}")]
        )
        measurement_mm: float | None = None
        if scale.detected and scale.px_per_mm and w.span_polyline:
            (x1, y1), (x2, y2) = w.span_polyline
            measurement_mm = math.hypot(x2 - x1, y2 - y1) / scale.px_per_mm
        # ⊬ type → needs_human always
        review = "needs_human"
        nid += 1
        objects.append(
            Object(
                object_id=f"obj_{nid:04d}",
                type="window",
                type_epistemic=type_mark,
                geometry=geom,
                geometry_epistemic=geom_mark,
                measurement_mm=measurement_mm,
                measurement_epistemic=meas_mark,
                review_status=review,
            )
        )
    return objects, nid


def _compose_spaces(spaces: list, scale: ScaleAnchor, start_id: int) -> tuple[list[Object], int]:
    objects: list[Object] = []
    nid = start_id
    for s in spaces:
        evs = [_ev(e.source, e.signal) for e in s.evidence]
        # Space with enclosed label = ⊢ grounded (label confirms identity)
        if s.enclosed_label:
            type_mark = _mark_grounded(evs)
        else:
            type_mark = _mark_extrapolated(
                evs,
                basis="closed contour without enclosing room_label — could be furniture outline",
            )
        geom = Geometry(kind="polygon", coords_px=[[p[0], p[1]] for p in s.polygon])
        geom_mark = _mark_inferred([_ev("contour_closure", f"polygon area={s.area_px:.0f}px²")])
        # Area measurement requires scale anchor
        measurement_mm: float | None = None
        if scale.detected and scale.px_per_mm:
            area_mm2 = s.area_px / (scale.px_per_mm ** 2)
            measurement_mm = area_mm2
            meas_mark = _mark_inferred(
                [_ev("scale_anchor", f"area_mm² via (px_per_mm)²={scale.px_per_mm**2:.6f}")]
            )
        else:
            meas_mark = _mark_unknown("no scale_anchor; area mm² refused per Measurement_Policy")
        review = "auto_accepted" if type_mark.tag in ("⊢", "⊨") else "needs_human"
        nid += 1
        objects.append(
            Object(
                object_id=f"obj_{nid:04d}",
                type="space_polygon",
                type_epistemic=type_mark,
                geometry=geom,
                geometry_epistemic=geom_mark,
                measurement_mm=measurement_mm,
                measurement_epistemic=meas_mark,
                review_status=review,
            )
        )
    return objects, nid


def _compose_dimension_texts(ocr: OCRResult, start_id: int) -> tuple[list[Object], int]:
    """Dimension texts become objects too — type ⊢ from OCR, measurement always ⊥
    (the text VALUE is not its own measurement; it's a SOURCE for scale anchor)."""
    objects: list[Object] = []
    nid = start_id
    for t in ocr.texts:
        if t.classification != "dimension_text":
            continue
        evs = [_ev("paddleocr", f"text='{t.text}' char_conf={t.char_conf:.2f}, regex=dim")]
        type_mark = _mark_grounded(evs)
        # bbox from PaddleOCR is a 4-point quad; reduce to 2-point bbox
        if t.bbox:
            xs = [p[0] for p in t.bbox]
            ys = [p[1] for p in t.bbox]
            bbox = [[min(xs), min(ys)], [max(xs), max(ys)]]
        else:
            bbox = [[0.0, 0.0], [0.0, 0.0]]
        geom = Geometry(kind="bbox", coords_px=bbox)
        geom_mark = _mark_grounded([_ev("paddleocr", "bbox from PaddleOCR rec_polys")])
        meas_mark = _mark_unknown(
            "dimension text VALUE is not its own measurement_mm; "
            "v0.1 dimension texts feed scale_anchor extraction, not their own mm field"
        )
        nid += 1
        objects.append(
            Object(
                object_id=f"obj_{nid:04d}",
                type="dimension_text",
                type_epistemic=type_mark,
                geometry=geom,
                geometry_epistemic=geom_mark,
                measurement_mm=None,
                measurement_epistemic=meas_mark,
                review_status="auto_accepted",
            )
        )
    return objects, nid


# ── aggregates ──────────────────────────────────────────────────────────────


def _count_aggregate(objects: list[Object], obj_type: str) -> Aggregate:
    contributors = [o for o in objects if o.type == obj_type]
    if not contributors:
        return Aggregate(
            value=0,
            epistemic=_mark_grounded([_ev("compose", f"0 {obj_type} objects in output")]),
        )
    tags = [o.type_epistemic.tag for o in contributors]
    extrap_count = sum(1 for t in tags if t == "⊬")
    unk_count = sum(1 for t in tags if t == "⊥")
    warning: str | None = None
    if extrap_count or unk_count:
        warning = (
            f"{extrap_count + unk_count} of {len(contributors)} {obj_type} contributors carry "
            f"⊬/⊥ type_epistemic; count carries taint"
        )
        agg_mark = _mark_extrapolated(
            [_ev("compose", f"count={len(contributors)} with tainted contributors")],
            basis=warning,
        )
    else:
        agg_mark = _mark_inferred(
            [_ev("compose", f"{len(contributors)} {obj_type} objects, all type_epistemic ∈ ⊢/⊨")]
        )
    return Aggregate(value=len(contributors), epistemic=agg_mark, warning=warning)


def _measured_wall_length_aggregate(objects: list[Object], scale: ScaleAnchor) -> Aggregate:
    if not scale.detected:
        return Aggregate(
            value=None,
            epistemic=_mark_unknown(
                "scale_anchor.detected = false; mm aggregate refused per Measurement_Policy"
            ),
            warning="No reliable scale anchor detected — mm aggregate is null/⊥ by policy",
        )
    walls = [o for o in objects if o.type == "wall_structural" and o.measurement_mm is not None]
    if not walls:
        return Aggregate(
            value=0.0,
            epistemic=_mark_grounded([_ev("compose", "no wall objects with mm measurements")]),
        )
    total = sum(o.measurement_mm or 0.0 for o in walls)
    tags = [o.measurement_epistemic.tag for o in walls]
    has_taint = any(t in ("⊬", "⊥") for t in tags)
    if has_taint:
        return Aggregate(
            value=total,
            epistemic=_mark_extrapolated(
                [_ev("compose", f"sum of {len(walls)} wall lengths, some tainted")],
                basis="≥1 wall measurement is ⊬/⊥-tagged",
            ),
            warning=f"{sum(1 for t in tags if t in ('⊬','⊥'))} of {len(walls)} wall mm measurements tainted",
        )
    return Aggregate(
        value=total,
        epistemic=_mark_inferred([_ev("compose", f"sum of {len(walls)} wall mm measurements, all ⊢/⊨")]),
    )


# ── public entrypoint ───────────────────────────────────────────────────────


def compose(
    drawing_id: str,
    canonical_image: np.ndarray,
    geometry: GeometryResult,
    ocr: OCRResult,
    symbols: SymbolResult,
) -> EngineOutput:
    """Fuse all stage outputs into a typed, EEF-tagged EngineOutput."""
    scale, scale_signal = _try_extract_scale_anchor(ocr, geometry.wall_candidates)

    objects: list[Object] = []
    walls, nid = _compose_walls(geometry.wall_candidates, scale, start_id=0)
    objects.extend(walls)
    doors, nid = _compose_doors(symbols.doors, scale, start_id=nid)
    objects.extend(doors)
    windows, nid = _compose_windows(symbols.windows, scale, start_id=nid)
    objects.extend(windows)
    spaces, nid = _compose_spaces(symbols.spaces, scale, start_id=nid)
    objects.extend(spaces)
    dims, nid = _compose_dimension_texts(ocr, start_id=nid)
    objects.extend(dims)

    refusals: list[Refusal] = []
    for rc in symbols.refusal_candidates:
        refusals.append(
            Refusal(
                region=_bbox_to_coords(rc.region),
                why=f"[{rc.attempted_type}] {rc.why_refused}",
            )
        )

    aggregates = Aggregates(
        wall_count=_count_aggregate(objects, "wall_structural"),
        door_count=_count_aggregate(objects, "door"),
        window_count=_count_aggregate(objects, "window"),
        measured_wall_length_mm=_measured_wall_length_aggregate(objects, scale),
    )

    return EngineOutput(
        drawing_id=drawing_id,
        objects=objects,
        aggregates=aggregates,
        refusals=refusals,
        scale_anchor=scale,
    )
