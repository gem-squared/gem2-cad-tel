"""U7: Symbol_F — rule-based door / window / space + EXPLICIT refusal_candidates.

Contract:
    A: { canonical_image, wall_candidates (U5), contours (U5), texts (U6) }
    B: SymbolResult { doors, windows, spaces, refusal_candidates, diagnostic }
    P: U5 + U6 outputs available

Per WP-Level Refusal_Over_Bluff invariant:
    When evidence is INSUFFICIENT (≥1 signal but <2), emit refusal_candidate
    rather than a low-confidence detection. Low coverage is acceptable;
    confident wrong detections are NOT.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np

from cad_trust.geometry import Evidence, GeometryResult, WallCandidate
from cad_trust.ocr import OCRResult, TextDetection

# Tunables
ARC_MIN_RADIUS = 25
ARC_MAX_RADIUS = 90
ARC_DETECT_BLUR_KSIZE = 5
WINDOW_PAIR_GAP_MAX_PX = 14  # walls were 3-18; windows in our generator are ~6
WINDOW_PAIR_GAP_MIN_PX = 3
SPACE_MIN_AREA = 20_000  # px²
DOOR_MIN_EVIDENCE_SIGNALS = 2
WINDOW_MIN_EVIDENCE_SIGNALS = 2


@dataclass
class Detection:
    bbox: list[tuple[float, float]]  # 2-point bbox: [(x0,y0),(x1,y1)]
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class Door(Detection):
    arc_center: tuple[float, float] | None = None
    arc_radius: float | None = None


@dataclass
class Window(Detection):
    span_polyline: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class Space:
    polygon: list[tuple[float, float]]
    enclosed_label: str | None
    area_px: float
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class RefusalCandidate:
    region: list[tuple[float, float]]  # 2-point bbox
    attempted_type: str
    why_refused: str


@dataclass
class SymbolResult:
    doors: list[Door]
    windows: list[Window]
    spaces: list[Space]
    refusal_candidates: list[RefusalCandidate]
    diagnostic: str = ""


# ── helpers ─────────────────────────────────────────────────────────────────


def _point_in_bbox(px: float, py: float, bbox: list[tuple[float, float]]) -> bool:
    (x0, y0), (x1, y1) = bbox
    xmin, xmax = min(x0, x1), max(x0, x1)
    ymin, ymax = min(y0, y1), max(y0, y1)
    return xmin <= px <= xmax and ymin <= py <= ymax


def _bbox_from_polyline(polyline: list[tuple[float, float]], pad: float = 4.0) -> list[tuple[float, float]]:
    xs = [p[0] for p in polyline]
    ys = [p[1] for p in polyline]
    return [(min(xs) - pad, min(ys) - pad), (max(xs) + pad, max(ys) + pad)]


def _polygon_centroid(poly: list[tuple[float, float]]) -> tuple[float, float]:
    if not poly:
        return (0.0, 0.0)
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _wall_contains(wall: WallCandidate, x: float, y: float, slack: float = 6.0) -> bool:
    """Approximate: is the point near any segment of the wall polyline?"""
    pts = wall.polyline
    if len(pts) < 2:
        return False
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        if L2 < 1e-6:
            continue
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
        px = x1 + t * dx
        py = y1 + t * dy
        if math.hypot(x - px, y - py) < slack + wall.thickness_px:
            return True
    return False


# ── door detection via Hough circles + opening check ────────────────────────


def _detect_door_arcs(
    canonical_image: np.ndarray, wall_candidates: list[WallCandidate]
) -> tuple[list[Door], list[RefusalCandidate]]:
    gray = cv2.cvtColor(canonical_image, cv2.COLOR_RGB2GRAY) if canonical_image.ndim == 3 else canonical_image
    gray_blurred = cv2.GaussianBlur(gray, (ARC_DETECT_BLUR_KSIZE, ARC_DETECT_BLUR_KSIZE), 0)
    circles = cv2.HoughCircles(
        gray_blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=40,
        param1=80,
        param2=22,
        minRadius=ARC_MIN_RADIUS,
        maxRadius=ARC_MAX_RADIUS,
    )
    doors: list[Door] = []
    refusals: list[RefusalCandidate] = []
    if circles is None:
        return doors, refusals
    for cx_, cy_, r_ in circles[0]:
        cx, cy, r = float(cx_), float(cy_), float(r_)
        # Signal 1: arc detected
        evidence: list[Evidence] = [
            Evidence(source="opencv_houghCircles", signal=f"arc center=({cx:.0f},{cy:.0f}), r={r:.1f}px"),
        ]
        # Signal 2: arc is near a wall — supports "door opening in wall"
        near_wall = any(_wall_contains(w, cx, cy, slack=r + 8.0) for w in wall_candidates)
        if near_wall:
            evidence.append(
                Evidence(source="wall_proximity", signal=f"arc center within (r + 8px) of a wall_candidate")
            )
        bbox = [(cx - r, cy - r), (cx + r, cy + r)]
        if len(evidence) >= DOOR_MIN_EVIDENCE_SIGNALS:
            doors.append(Door(bbox=bbox, evidence=evidence, arc_center=(cx, cy), arc_radius=r))
        else:
            refusals.append(
                RefusalCandidate(
                    region=bbox,
                    attempted_type="door",
                    why_refused=(
                        f"arc detected at ({cx:.0f},{cy:.0f}) r={r:.1f}px but no wall_proximity "
                        f"signal — single-signal evidence below {DOOR_MIN_EVIDENCE_SIGNALS}-signal threshold; "
                        f"could be a non-door arc (logo, chair, decorative)"
                    ),
                )
            )
    return doors, refusals


# ── window detection: short parallel-pairs inside wall spans ────────────────


def _detect_windows(
    canonical_image: np.ndarray, wall_candidates: list[WallCandidate]
) -> tuple[list[Window], list[RefusalCandidate]]:
    """Window = two close parallel thin lines inside a wall span.

    Strategy: run a TIGHT Hough pass for short thin lines, then find pairs
    whose gap is in the window-gap range AND whose midpoint sits on a wall.
    """
    gray = cv2.cvtColor(canonical_image, cv2.COLOR_RGB2GRAY) if canonical_image.ndim == 3 else canonical_image
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    raw = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=math.pi / 180,
        threshold=40,
        minLineLength=40,
        maxLineGap=4,
    )
    windows: list[Window] = []
    refusals: list[RefusalCandidate] = []
    if raw is None:
        return windows, refusals
    segs = [tuple(float(v) for v in s[0]) for s in raw]
    # Pair short parallel close lines
    used: set[int] = set()
    for i in range(len(segs)):
        if i in used:
            continue
        x1, y1, x2, y2 = segs[i]
        ang_i = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180.0
        mx_i, my_i = (x1 + x2) / 2, (y1 + y2) / 2
        for j in range(i + 1, len(segs)):
            if j in used:
                continue
            X1, Y1, X2, Y2 = segs[j]
            ang_j = math.degrees(math.atan2(Y2 - Y1, X2 - X1)) % 180.0
            d_ang = min(abs(ang_i - ang_j), 180.0 - abs(ang_i - ang_j))
            if d_ang > 3.0:
                continue
            mx_j, my_j = (X1 + X2) / 2, (Y1 + Y2) / 2
            # Perpendicular gap
            dx, dy = x2 - x1, y2 - y1
            L = math.hypot(dx, dy)
            if L < 1e-6:
                continue
            nx, ny = -dy / L, dx / L
            gap = abs((mx_j - mx_i) * nx + (my_j - my_i) * ny)
            if gap < WINDOW_PAIR_GAP_MIN_PX or gap > WINDOW_PAIR_GAP_MAX_PX:
                continue
            # Signal 1: parallel close pair
            evidence: list[Evidence] = [
                Evidence(
                    source="opencv_double_line",
                    signal=f"parallel pair (Δang={d_ang:.1f}°, gap={gap:.1f}px)",
                ),
            ]
            # Signal 2: midpoint is on a wall_candidate
            mid_cx = (mx_i + mx_j) / 2
            mid_cy = (my_i + my_j) / 2
            on_wall = any(_wall_contains(w, mid_cx, mid_cy, slack=10.0) for w in wall_candidates)
            if on_wall:
                evidence.append(
                    Evidence(source="wall_proximity", signal="double-line midpoint sits inside a wall_candidate")
                )
            bbox_pts = [(x1, y1), (x2, y2), (X1, Y1), (X2, Y2)]
            bx0 = min(p[0] for p in bbox_pts)
            by0 = min(p[1] for p in bbox_pts)
            bx1 = max(p[0] for p in bbox_pts)
            by1 = max(p[1] for p in bbox_pts)
            bbox = [(bx0, by0), (bx1, by1)]
            if len(evidence) >= WINDOW_MIN_EVIDENCE_SIGNALS:
                windows.append(
                    Window(
                        bbox=bbox,
                        evidence=evidence,
                        span_polyline=[((x1 + X1) / 2, (y1 + Y1) / 2), ((x2 + X2) / 2, (y2 + Y2) / 2)],
                    )
                )
                used.add(i)
                used.add(j)
                break
            else:
                refusals.append(
                    RefusalCandidate(
                        region=bbox,
                        attempted_type="window",
                        why_refused=(
                            f"parallel pair gap={gap:.1f}px but pair midpoint not on a wall_candidate; "
                            f"could be decorative double-line, not a window"
                        ),
                    )
                )
    return windows, refusals


# ── space detection: closed contours + room label tagging ───────────────────


def _detect_spaces(
    geometry: GeometryResult, ocr: OCRResult
) -> list[Space]:
    spaces: list[Space] = []
    room_labels = [t for t in ocr.texts if t.classification == "room_label"]
    for c in geometry.contours:
        if c.area_px < SPACE_MIN_AREA or len(c.points) < 4:
            continue
        # Inside which polygon does any room_label sit?
        enclosed_label: str | None = None
        for label in room_labels:
            if not label.bbox:
                continue
            lx = sum(p[0] for p in label.bbox) / len(label.bbox)
            ly = sum(p[1] for p in label.bbox) / len(label.bbox)
            if _point_in_polygon(lx, ly, c.points):
                enclosed_label = label.text
                break
        evidence: list[Evidence] = [
            Evidence(source="contour_closure", signal=f"closed contour area={c.area_px:.0f}px²"),
        ]
        if enclosed_label:
            evidence.append(
                Evidence(source="ocr_label_inside", signal=f"room_label '{enclosed_label}' enclosed")
            )
        spaces.append(
            Space(
                polygon=c.points,
                enclosed_label=enclosed_label,
                area_px=c.area_px,
                evidence=evidence,
            )
        )
    return spaces


def _point_in_polygon(px: float, py: float, polygon: list[tuple[float, float]]) -> bool:
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-9) + xi):
            inside = not inside
        j = i
    return inside


# ── public entrypoint ───────────────────────────────────────────────────────


def detect_symbols(
    canonical_image: np.ndarray, geometry: GeometryResult, ocr: OCRResult
) -> SymbolResult:
    if canonical_image is None or canonical_image.size == 0:
        return SymbolResult(
            doors=[], windows=[], spaces=[], refusal_candidates=[],
            diagnostic="empty input image"
        )
    doors, door_refusals = _detect_door_arcs(canonical_image, geometry.wall_candidates)
    windows, window_refusals = _detect_windows(canonical_image, geometry.wall_candidates)
    spaces = _detect_spaces(geometry, ocr)
    refusals = door_refusals + window_refusals
    diagnostic = ""
    if not doors and not windows and not spaces and not refusals:
        diagnostic = (
            "no doors, windows, or spaces detected and no refusal_candidates produced — "
            "either drawing is empty or below v0.1 thresholds"
        )
    return SymbolResult(
        doors=doors,
        windows=windows,
        spaces=spaces,
        refusal_candidates=refusals,
        diagnostic=diagnostic,
    )
