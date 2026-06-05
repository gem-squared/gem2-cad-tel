"""U3 corpus builder — generates synthetic floor plans + writes provenance.

Synthetic drawings are license = 'public' (we own the generator).
They are clearly labeled as synthetic in the source field — no pretending these
are FloorPlanCAD. Per the Refusal_Over_Bluff invariant, honest provenance is
non-negotiable.
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR = ROOT / "data" / "samples"
PROVENANCE_DIR = ROOT / "data" / "provenance"

CANVAS = (1024, 768)
WALL_THICKNESS = 8
DEFAULT_FONT_PATHS = (
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
)


def _font(size: int) -> ImageFont.ImageFont:
    for p in DEFAULT_FONT_PATHS:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _draw_wall_segment(d: ImageDraw.ImageDraw, p1: tuple[int, int], p2: tuple[int, int]) -> None:
    """Wall = thick black line (parallel-pair would be ideal but a single thick line
    is detectable by OpenCV LSD + thickness inference)."""
    d.line([p1, p2], fill="black", width=WALL_THICKNESS)


def _draw_door(d: ImageDraw.ImageDraw, center: tuple[int, int], radius: int = 38) -> None:
    """Door = arc symbol — quarter-circle in the opening + small rectangle indicating leaf."""
    cx, cy = center
    box = [cx - radius, cy - radius, cx + radius, cy + radius]
    d.arc(box, start=0, end=90, fill="black", width=2)
    d.line([(cx, cy), (cx + radius, cy)], fill="black", width=2)


def _draw_window(d: ImageDraw.ImageDraw, p1: tuple[int, int], p2: tuple[int, int]) -> None:
    """Window = double parallel line in wall span."""
    d.line([p1, p2], fill="white", width=WALL_THICKNESS - 2)  # clear the wall first
    # Two parallel lines representing the window
    if p1[1] == p2[1]:  # horizontal
        y = p1[1]
        d.line([(p1[0], y - 3), (p2[0], y - 3)], fill="black", width=1)
        d.line([(p1[0], y + 3), (p2[0], y + 3)], fill="black", width=1)
    else:  # vertical
        x = p1[0]
        d.line([(x - 3, p1[1]), (x - 3, p2[1])], fill="black", width=1)
        d.line([(x + 3, p1[1]), (x + 3, p2[1])], fill="black", width=1)


def _draw_room_label(d: ImageDraw.ImageDraw, center: tuple[int, int], text: str, size: int = 26) -> None:
    font = _font(size)
    bbox = d.textbbox(center, text, font=font, anchor="mm")
    pad = 4
    d.rectangle([bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad], fill="white")
    d.text(center, text, fill="black", font=font, anchor="mm")


def _draw_dimension_text(d: ImageDraw.ImageDraw, anchor: tuple[int, int], text: str, size: int = 18) -> None:
    font = _font(size)
    d.text(anchor, text, fill="black", font=font)


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ── Floor plan generators ───────────────────────────────────────────────────

def _generate_apt_simple(seed: int) -> Image.Image:
    rng = random.Random(seed)
    img = Image.new("RGB", CANVAS, "white")
    d = ImageDraw.Draw(img)
    # Outer walls — simple rectangle
    x0, y0, x1, y1 = 100, 100, 924, 668
    _draw_wall_segment(d, (x0, y0), (x1, y0))  # top
    _draw_wall_segment(d, (x0, y1), (x1, y1))  # bottom
    _draw_wall_segment(d, (x0, y0), (x0, y1))  # left
    _draw_wall_segment(d, (x1, y0), (x1, y1))  # right
    # Interior wall — divides into 거실 + 침실
    mid_x = (x0 + x1) // 2 + rng.randint(-40, 40)
    _draw_wall_segment(d, (mid_x, y0), (mid_x, y1))
    # Door in interior wall
    door_y = (y0 + y1) // 2 + rng.randint(-60, 60)
    _draw_door(d, (mid_x + 10, door_y))
    # Window on outer wall
    _draw_window(d, (x0 + 200, y0), (x0 + 320, y0))
    _draw_window(d, (x1, y0 + 200), (x1, y0 + 320))
    # Room labels
    _draw_room_label(d, ((x0 + mid_x) // 2, (y0 + y1) // 2), "거실")
    _draw_room_label(d, ((mid_x + x1) // 2, (y0 + y1) // 2), "침실")
    # Dimension texts — no scale anchor (intentional: U8 should produce ⊥ measurement)
    _draw_dimension_text(d, (x0 + 20, y0 - 28), f"{x1 - x0}")  # px value as label
    return img


def _generate_apt_three_room(seed: int) -> Image.Image:
    rng = random.Random(seed)
    img = Image.new("RGB", CANVAS, "white")
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 80, 80, 944, 688
    # Outer walls
    _draw_wall_segment(d, (x0, y0), (x1, y0))
    _draw_wall_segment(d, (x0, y1), (x1, y1))
    _draw_wall_segment(d, (x0, y0), (x0, y1))
    _draw_wall_segment(d, (x1, y0), (x1, y1))
    # Two interior walls — 3 rooms in a row
    w_third = (x1 - x0) // 3
    a = x0 + w_third + rng.randint(-30, 30)
    b = x0 + 2 * w_third + rng.randint(-30, 30)
    _draw_wall_segment(d, (a, y0), (a, y1))
    _draw_wall_segment(d, (b, y0), (b, y1))
    # Doors in interior walls
    _draw_door(d, (a + 12, y0 + 180))
    _draw_door(d, (b + 12, y0 + 380))
    # Windows
    _draw_window(d, (x0 + 100, y0), (x0 + 220, y0))
    _draw_window(d, (a + 60, y1), (a + 180, y1))
    _draw_window(d, (b + 60, y0), (b + 180, y0))
    # Labels
    _draw_room_label(d, ((x0 + a) // 2, (y0 + y1) // 2), "거실")
    _draw_room_label(d, ((a + b) // 2, (y0 + y1) // 2), "주방")
    _draw_room_label(d, ((b + x1) // 2, (y0 + y1) // 2), "침실")
    _draw_dimension_text(d, (x0 + 20, y0 - 30), "4200")
    _draw_dimension_text(d, (b + 60, y1 + 6), "2800")
    return img


def _generate_office_open(seed: int) -> Image.Image:
    rng = random.Random(seed)
    img = Image.new("RGB", CANVAS, "white")
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 60, 60, 964, 708
    _draw_wall_segment(d, (x0, y0), (x1, y0))
    _draw_wall_segment(d, (x0, y1), (x1, y1))
    _draw_wall_segment(d, (x0, y0), (x0, y1))
    _draw_wall_segment(d, (x1, y0), (x1, y1))
    # Meeting room — partition size varies
    px0 = x1 - (260 + rng.randint(-30, 40))
    py1 = y0 + (200 + rng.randint(-20, 40))
    _draw_wall_segment(d, (px0, y0), (px0, py1))
    _draw_wall_segment(d, (px0, py1), (x1, py1))
    _draw_door(d, (px0 + 12, py1 - rng.randint(30, 60)))
    # Windows — varied positions
    wx_start = x0 + rng.randint(120, 180)
    _draw_window(d, (wx_start, y0), (wx_start + 140, y0))
    _draw_window(d, (wx_start + 250, y0), (wx_start + 390, y0))
    _draw_window(d, (x0, y0 + rng.randint(170, 230)), (x0, y0 + rng.randint(310, 370)))
    _draw_room_label(d, ((x0 + px0) // 2, (y0 + y1) // 2), "Office")
    _draw_room_label(d, ((px0 + x1) // 2, (y0 + py1) // 2), "Meeting")
    _draw_dimension_text(d, (x0 + 20, y0 - 30), str(rng.choice([7500, 8000, 8400, 9000])))
    return img


def _generate_apt_kr_balcony(seed: int) -> Image.Image:
    """Korean apt layout with balcony — the 적산 scenario."""
    rng = random.Random(seed)
    img = Image.new("RGB", CANVAS, "white")
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 100, 120, 924, 648
    _draw_wall_segment(d, (x0, y0), (x1, y0))
    _draw_wall_segment(d, (x0, y1), (x1, y1))
    _draw_wall_segment(d, (x0, y0), (x0, y1))
    _draw_wall_segment(d, (x1, y0), (x1, y1))
    by = y1 - (80 + rng.randint(-10, 30))
    _draw_wall_segment(d, (x0, by), (x1, by))
    _draw_window(d, (x0 + 60, y1), (x1 - 60, y1))
    mid_x = (x0 + x1) // 2 + rng.randint(-40, 40)
    _draw_wall_segment(d, (mid_x, y0), (mid_x, by))
    _draw_door(d, (mid_x + 12, y0 + rng.randint(150, 220)))
    w1_off = rng.randint(150, 240)
    _draw_window(d, (x0 + w1_off, y0), (x0 + w1_off + 120, y0))
    w2_off = rng.randint(150, 240)
    _draw_window(d, (mid_x + w2_off, y0), (mid_x + w2_off + 120, y0))
    _draw_room_label(d, ((x0 + mid_x) // 2, (y0 + by) // 2), "거실")
    _draw_room_label(d, ((mid_x + x1) // 2, (y0 + by) // 2), "안방")
    _draw_room_label(d, ((x0 + x1) // 2, (by + y1) // 2 - 4), "발코니")
    _draw_dimension_text(d, (x0 + 20, y0 - 30), str(rng.choice([5200, 5400, 5800, 6000])))
    return img


GENERATORS = {
    "apt_simple": _generate_apt_simple,
    "apt_three_room": _generate_apt_three_room,
    "office_open": _generate_office_open,
    "apt_kr_balcony": _generate_apt_kr_balcony,
}


def main() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    PROVENANCE_DIR.mkdir(parents=True, exist_ok=True)

    plan: list[tuple[str, str, str, str]] = []
    counter = 0
    # 3 samples per generator → 12 total
    for kind, gen in GENERATORS.items():
        for variant in range(3):
            counter += 1
            seed = 1000 + counter
            drawing_id = f"synth_{kind}_{variant + 1:02d}"
            domain = "kr" if kind.startswith("apt") else "global"
            plan.append((drawing_id, kind, str(seed), domain))

    for drawing_id, kind, seed_str, domain in plan:
        out_png = SAMPLES_DIR / f"{drawing_id}.png"
        out_prov = PROVENANCE_DIR / f"{drawing_id}.json"
        if not out_png.exists():
            img = GENERATORS[kind](int(seed_str))
            img.save(out_png)
        sha = _sha256(out_png)
        rec = {
            "drawing_id": drawing_id,
            "source": "synthetic_self_generated",
            "license": "public",
            "sha256": sha,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "original_uri": f"file://{out_png.resolve()}",
            "usage": "demo-only",
            "domain": domain,
        }
        out_prov.write_text(json.dumps(rec, indent=2, ensure_ascii=False))
        print(f"  + {drawing_id}  domain={domain}  sha256={sha[:12]}…")

    print(f"\nWrote {counter} synthetic drawings to {SAMPLES_DIR}")
    print(f"Wrote {counter} provenance JSONs to {PROVENANCE_DIR}")


if __name__ == "__main__":
    main()
