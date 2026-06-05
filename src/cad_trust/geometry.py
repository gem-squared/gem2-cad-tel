"""U5: Geometry_F — OpenCV line + contour extraction + wall_candidates.

Contract:
    A: canonical_image (from U4) — ndarray (H,W,3) uint8
    B: GeometryResult { lines, contours, wall_candidates, diagnostic }
    P: canonical_image is grayscale-convertible

NEVER returns silent None — empty → GeometryResult with empty lists + diagnostic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np

# Tunables (v0.1 defaults; revisit in v0.2 once real corpus arrives)
HOUGH_MIN_LINE_LENGTH_PX = 60
HOUGH_MAX_LINE_GAP_PX = 8
PAIR_ORIENTATION_TOL_DEG = 3.0
PAIR_OVERLAP_RATIO_MIN = 0.55
PAIR_GAP_MIN_PX = 3
PAIR_GAP_MAX_PX = 18  # walls drawn at WALL_THICKNESS=8 → expect gap ~5-15 with HoughP edge effects


@dataclass
class Evidence:
    source: str
    signal: str


@dataclass
class Line:
    p1: tuple[float, float]
    p2: tuple[float, float]
    length_px: float
    thickness_px: float
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class Contour:
    points: list[tuple[float, float]]
    area_px: float
    closed: bool


@dataclass
class WallCandidate:
    polyline: list[tuple[float, float]]
    thickness_px: float
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class GeometryResult:
    lines: list[Line]
    contours: list[Contour]
    wall_candidates: list[WallCandidate]
    diagnostic: str = ""


# ── helpers ─────────────────────────────────────────────────────────────────


def _angle_deg(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180.0


def _line_length(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def _midpoint(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]:
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _perpendicular_distance(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Distance from (px,py) to the infinite line through (x1,y1)-(x2,y2)."""
    num = abs((y2 - y1) * px - (x2 - x1) * py + x2 * y1 - y2 * x1)
    den = math.hypot(y2 - y1, x2 - x1)
    return num / den if den > 1e-6 else 0.0


def _project_overlap_ratio(la: tuple, lb: tuple) -> float:
    """Fraction of the SHORTER line that overlaps the longer line when projected
    along the shared direction."""
    (ax1, ay1, ax2, ay2) = la
    (bx1, by1, bx2, by2) = lb
    # Direction unit vector from the LONGER line
    if _line_length(*la) >= _line_length(*lb):
        x0, y0, x1, y1 = ax1, ay1, ax2, ay2
        sx1, sy1, sx2, sy2 = bx1, by1, bx2, by2
    else:
        x0, y0, x1, y1 = bx1, by1, bx2, by2
        sx1, sy1, sx2, sy2 = ax1, ay1, ax2, ay2
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return 0.0
    ux, uy = dx / L, dy / L
    # Projection of endpoints onto direction
    p0 = 0.0
    p1 = L
    q0 = (sx1 - x0) * ux + (sy1 - y0) * uy
    q1 = (sx2 - x0) * ux + (sy2 - y0) * uy
    qmin, qmax = min(q0, q1), max(q0, q1)
    overlap = max(0.0, min(p1, qmax) - max(p0, qmin))
    short_len = math.hypot(sx2 - sx1, sy2 - sy1)
    if short_len < 1e-6:
        return 0.0
    return overlap / short_len


# ── core ────────────────────────────────────────────────────────────────────


def _detect_lines(gray: np.ndarray) -> list[Line]:
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    raw = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=math.pi / 180,
        threshold=80,
        minLineLength=HOUGH_MIN_LINE_LENGTH_PX,
        maxLineGap=HOUGH_MAX_LINE_GAP_PX,
    )
    out: list[Line] = []
    if raw is None:
        return out
    for entry in raw[:, 0, :]:
        x1, y1, x2, y2 = (float(v) for v in entry)
        length = _line_length(x1, y1, x2, y2)
        out.append(
            Line(
                p1=(x1, y1),
                p2=(x2, y2),
                length_px=length,
                thickness_px=1.0,  # unknown from HoughP alone
                evidence=[Evidence(source="opencv_houghP", signal=f"len={length:.1f}px")],
            )
        )
    return out


def _detect_contours(gray: np.ndarray) -> list[Contour]:
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out: list[Contour] = []
    for c in contours:
        if cv2.contourArea(c) < 200:
            continue
        epsilon = 0.01 * cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, epsilon, True)
        pts = [(float(p[0][0]), float(p[0][1])) for p in approx]
        out.append(Contour(points=pts, area_px=float(cv2.contourArea(c)), closed=True))
    return out


def _pair_lines_into_walls(lines: list[Line]) -> list[WallCandidate]:
    """Pair parallel close lines into wall candidates.

    Two HoughP lines form a wall when:
      - angles within ±PAIR_ORIENTATION_TOL_DEG,
      - perpendicular distance ∈ [PAIR_GAP_MIN_PX, PAIR_GAP_MAX_PX],
      - projected overlap ≥ PAIR_OVERLAP_RATIO_MIN of the shorter line.
    """
    if len(lines) < 2:
        return []
    used: set[int] = set()
    walls: list[WallCandidate] = []
    by_length = sorted(range(len(lines)), key=lambda i: -lines[i].length_px)
    for i in by_length:
        if i in used:
            continue
        la = lines[i]
        ang_a = _angle_deg(la.p1[0], la.p1[1], la.p2[0], la.p2[1])
        mx_a, my_a = _midpoint(la.p1[0], la.p1[1], la.p2[0], la.p2[1])
        best_j = -1
        best_gap = float("inf")
        for j in by_length:
            if j == i or j in used:
                continue
            lb = lines[j]
            ang_b = _angle_deg(lb.p1[0], lb.p1[1], lb.p2[0], lb.p2[1])
            dang = min(abs(ang_a - ang_b), 180.0 - abs(ang_a - ang_b))
            if dang > PAIR_ORIENTATION_TOL_DEG:
                continue
            mx_b, my_b = _midpoint(lb.p1[0], lb.p1[1], lb.p2[0], lb.p2[1])
            gap = _perpendicular_distance(mx_b, my_b, la.p1[0], la.p1[1], la.p2[0], la.p2[1])
            if gap < PAIR_GAP_MIN_PX or gap > PAIR_GAP_MAX_PX:
                continue
            overlap = _project_overlap_ratio(
                (la.p1[0], la.p1[1], la.p2[0], la.p2[1]),
                (lb.p1[0], lb.p1[1], lb.p2[0], lb.p2[1]),
            )
            if overlap < PAIR_OVERLAP_RATIO_MIN:
                continue
            if gap < best_gap:
                best_gap = gap
                best_j = j
        if best_j >= 0:
            lb = lines[best_j]
            used.add(i)
            used.add(best_j)
            # Centerline: average of endpoint midpoints
            cx1, cy1 = _midpoint(la.p1[0], lb.p1[0], la.p1[1], lb.p1[1])
            cx2, cy2 = _midpoint(la.p2[0], lb.p2[0], la.p2[1], lb.p2[1])
            walls.append(
                WallCandidate(
                    polyline=[(la.p1[0], la.p1[1]), (la.p2[0], la.p2[1])],
                    thickness_px=best_gap,
                    evidence=[
                        Evidence(
                            source="opencv_line_pair",
                            signal=(
                                f"parallel pair, Δangle≈{dang:.1f}°, gap={best_gap:.1f}px, "
                                f"overlap≥{PAIR_OVERLAP_RATIO_MIN:.0%}"
                            ),
                        ),
                    ],
                )
            )
    return walls


def extract_geometry(canonical_image: np.ndarray) -> GeometryResult:
    if canonical_image is None or canonical_image.size == 0:
        return GeometryResult(
            lines=[],
            contours=[],
            wall_candidates=[],
            diagnostic="empty input image",
        )
    if canonical_image.ndim == 3:
        gray = cv2.cvtColor(canonical_image, cv2.COLOR_RGB2GRAY)
    else:
        gray = canonical_image
    lines = _detect_lines(gray)
    contours = _detect_contours(gray)
    walls = _pair_lines_into_walls(lines)
    diag_parts: list[str] = []
    if not lines:
        diag_parts.append("HoughLinesP returned no lines")
    if not walls:
        diag_parts.append(
            "no wall_candidates produced — either no parallel pairs survived gap/overlap thresholds, "
            "or walls are drawn too thin for v0.1 thresholds"
        )
    return GeometryResult(
        lines=lines,
        contours=contours,
        wall_candidates=walls,
        diagnostic=" | ".join(diag_parts),
    )
