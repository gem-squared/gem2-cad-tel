"""Metric definitions per spec §5.2.

Pure functions — no I/O, no dataset assumptions. Callers pass paired
(prediction, ground_truth) items and receive numeric scores. Metrics use
plain Python + math where possible; numpy fallback where matrix work is
unavoidable but the shapes are small.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence


# ── Geometry primitives ─────────────────────────────────────────────────────
# Kept intentionally simple; heavy CV work stays in WP-ST-4 vision layer.

def _polygon_area(vertices: Sequence[Sequence[float]]) -> float:
    """Shoelace-formula polygon area. Vertices in CW or CCW order."""
    n = len(vertices)
    if n < 3:
        return 0.0
    a = 0.0
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def _bbox_iou(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> float:
    """IoU over axis-aligned bboxes [[x0,y0],[x1,y1]]."""
    (ax0, ay0), (ax1, ay1) = a
    (bx0, by0), (bx1, by1) = b
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix0 >= ix1 or iy0 >= iy1:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    aa = (ax1 - ax0) * (ay1 - ay0)
    ba = (bx1 - bx0) * (by1 - by0)
    union = aa + ba - inter
    return inter / union if union > 0 else 0.0


def mask_polygon_iou(
    pred: dict, gt: dict, kind: str = "polygon"
) -> float:
    """Intersection-over-Union for polygon or mask.

    For polygon (list of vertices): uses shoelace areas + intersection via
    Shapely-fallback approximation (bounding-box + rasterization not required
    at this abstraction; delegated to WP-ST-4 vision layer for real masks).
    For simple shapes (rects), uses _bbox_iou.
    """
    if kind == "bbox":
        return _bbox_iou(pred["bbox"], gt["bbox"])
    # For polygon: approximate via bbox-of-hull. Real mask IoU delegated to CV lib.
    pv = pred.get("vertices") or []
    gv = gt.get("vertices") or []
    if not pv or not gv:
        return 0.0
    def _bbox_of(v):
        xs = [p[0] for p in v]
        ys = [p[1] for p in v]
        return [[min(xs), min(ys)], [max(xs), max(ys)]]
    return _bbox_iou(_bbox_of(pv), _bbox_of(gv))


def instance_recall(
    predictions: Sequence[dict],
    ground_truth: Sequence[dict],
    iou_threshold: float = 0.5,
    kind: str = "polygon",
) -> float:
    """Instance recall = |matched GT| / |GT|."""
    if not ground_truth:
        return 1.0 if not predictions else 0.0
    matched = set()
    for i, gt in enumerate(ground_truth):
        for p in predictions:
            if mask_polygon_iou(p, gt, kind=kind) >= iou_threshold:
                matched.add(i)
                break
    return len(matched) / len(ground_truth)


def boundary_quality(
    predictions: Sequence[dict], ground_truth: Sequence[dict]
) -> float:
    """Boundary F-measure approximation.

    Uses vertex-count and perimeter-length agreement as a boundary-quality
    proxy. Full boundary-F needs mask rasterization + boundary distance
    transform — deferred to WP-ST-4 vision layer.
    """
    if not predictions or not ground_truth:
        return 0.0
    def _perim(v):
        return sum(
            math.hypot(v[i + 1][0] - v[i][0], v[i + 1][1] - v[i][1])
            for i in range(len(v) - 1)
        )
    diffs = []
    for p, g in zip(predictions[: len(ground_truth)], ground_truth):
        pv = p.get("vertices") or []
        gv = g.get("vertices") or []
        if not pv or not gv:
            continue
        pp, gp = _perim(pv), _perim(gv)
        if gp > 0:
            diffs.append(min(pp / gp, gp / pp))
    return sum(diffs) / len(diffs) if diffs else 0.0


def topology_connectivity(
    prediction_walls: Sequence[dict], ground_truth_walls: Sequence[dict]
) -> float:
    """Topology-connectivity proxy: connected-component count agreement.

    Delegates connected-component analysis to WP-ST-4 vision layer for
    mask-level accuracy; here we use wall-count as a scaffold that vision
    layer will refine.
    """
    if not ground_truth_walls:
        return 1.0 if not prediction_walls else 0.0
    ratio = len(prediction_walls) / len(ground_truth_walls)
    return max(0.0, 1.0 - abs(1.0 - ratio))


# ── Detection metrics (doors/windows) ──────────────────────────────────────

def _precision_recall(
    predictions: Sequence[dict],
    ground_truth: Sequence[dict],
    iou_threshold: float,
    kind: str = "bbox",
) -> tuple[float, float]:
    if not predictions and not ground_truth:
        return 1.0, 1.0
    if not predictions:
        return 0.0, 0.0
    if not ground_truth:
        return 0.0, 1.0
    tp = 0
    matched_gt = set()
    for p in sorted(predictions, key=lambda x: -x.get("calibrated_conf", x.get("raw_conf", 0))):
        for i, g in enumerate(ground_truth):
            if i in matched_gt:
                continue
            if mask_polygon_iou(p, g, kind=kind) >= iou_threshold:
                tp += 1
                matched_gt.add(i)
                break
    fp = len(predictions) - tp
    fn = len(ground_truth) - tp
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return precision, recall


def map_at_ious(
    predictions: Sequence[dict],
    ground_truth: Sequence[dict],
    iou_thresholds: Sequence[float] = (0.5,),
    kind: str = "bbox",
) -> dict[float, float]:
    """AP at each IoU threshold. Returns {iou: AP}.

    Simplified AP = area-under-PR = precision at recall points.
    Full COCO-style AP delegated to WP-ST-4 vision layer.
    """
    result = {}
    for iou in iou_thresholds:
        p, r = _precision_recall(predictions, ground_truth, iou, kind=kind)
        # AP proxy = harmonic mean of P and R (avoids overweighting either)
        if p + r > 0:
            result[iou] = 2 * p * r / (p + r)
        else:
            result[iou] = 0.0
    return result


# ── OCR metrics (dimension_text) ───────────────────────────────────────────

def character_error_rate(prediction: str, ground_truth: str) -> float:
    """Levenshtein / len(ground_truth). Standard OCR CER."""
    if not ground_truth:
        return 0.0 if not prediction else 1.0
    m, n = len(prediction), len(ground_truth)
    if m == 0:
        return 1.0
    # Wagner-Fischer edit distance
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        curr = [i] + [0] * n
        for j in range(1, n + 1):
            cost = 0 if prediction[i - 1] == ground_truth[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[n] / len(ground_truth)


# ── Dimension association ──────────────────────────────────────────────────

def dimension_association_accuracy(
    predicted_associations: Sequence[dict],
    ground_truth_associations: Sequence[dict],
) -> float:
    """Association = (text_ref, line_ref, measured_object_ref) triple.

    Accuracy = fraction of predicted triples that exactly match a GT triple.
    """
    if not ground_truth_associations:
        return 1.0 if not predicted_associations else 0.0
    gt_set = {
        (a["text_ref"], a["line_ref"], a["measured_object_or_span_ref"])
        for a in ground_truth_associations
    }
    matches = sum(
        1
        for a in predicted_associations
        if (a["text_ref"], a["line_ref"], a["measured_object_or_span_ref"]) in gt_set
    )
    return matches / len(ground_truth_associations)


# ── Scale-anchor metrics ───────────────────────────────────────────────────

def false_anchor_rate(
    predicted_anchors: Sequence[dict],
    ground_truth_anchors: Sequence[dict],
) -> float:
    """Fraction of predicted anchors that don't match any GT anchor within tolerance."""
    if not predicted_anchors:
        return 0.0
    gt_ratios = [a["implied_ratio_mm_per_px"] for a in ground_truth_anchors]
    if not gt_ratios:
        return 1.0  # any prediction is false when no GT
    false_count = 0
    for p in predicted_anchors:
        pr = p["implied_ratio_mm_per_px"]
        # tolerance: within 3% of any GT anchor
        if not any(abs(pr - gr) / max(abs(gr), 1e-9) <= 0.03 for gr in gt_ratios):
            false_count += 1
    return false_count / len(predicted_anchors)


def relative_scale_error(
    predicted_mm_per_px: float | None,
    ground_truth_mm_per_px: float | None,
) -> float:
    """|pred - gt| / gt. Returns inf if pred exists but gt doesn't (false-anchor case)."""
    if ground_truth_mm_per_px is None:
        return math.inf if predicted_mm_per_px is not None else 0.0
    if predicted_mm_per_px is None:
        return 1.0  # refusal counted as 100% error at scoring time
    return abs(predicted_mm_per_px - ground_truth_mm_per_px) / abs(ground_truth_mm_per_px)


# ── Trust metrics ──────────────────────────────────────────────────────────

@dataclass
class RiskCoveragePoint:
    coverage: float
    accuracy: float
    threshold: float


def risk_coverage_curve(
    predictions: Sequence[dict],
    ground_truth: Sequence[dict],
    is_correct: Callable[[dict, Sequence[dict]], bool],
    thresholds: Sequence[float] = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9),
) -> list[RiskCoveragePoint]:
    """For each confidence threshold, compute (coverage, accuracy among committed)."""
    points = []
    for t in thresholds:
        committed = [p for p in predictions if p.get("calibrated_conf", 0) >= t]
        if not committed:
            points.append(RiskCoveragePoint(coverage=0.0, accuracy=1.0, threshold=t))
            continue
        correct = sum(1 for p in committed if is_correct(p, ground_truth))
        coverage = len(committed) / max(len(predictions), 1)
        accuracy = correct / len(committed)
        points.append(RiskCoveragePoint(coverage=coverage, accuracy=accuracy, threshold=t))
    return points
