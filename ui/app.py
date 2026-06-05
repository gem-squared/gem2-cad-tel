"""CAD Trust Engine Lite — Streamlit review UI.

Run with: streamlit run ui/app.py
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw

# Allow running from anywhere
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from cad_trust.ingest import IngestError, ingest  # noqa: E402
from cad_trust.pipeline import run as run_pipeline  # noqa: E402
from cad_trust.schema import EngineOutput, Object  # noqa: E402

SAMPLES_DIR = ROOT / "data" / "samples"

TYPE_COLORS = {
    "wall_structural": (40, 40, 200),
    "wall_wet": (40, 120, 200),
    "wall_dry": (80, 80, 220),
    "door": (220, 60, 60),
    "window": (60, 180, 60),
    "balcony_sash": (90, 200, 60),
    "inspection_hatch": (180, 120, 50),
    "dimension_text": (160, 60, 200),
    "room_label": (60, 160, 200),
    "space_polygon": (200, 200, 80),
}
TAG_BADGES = {
    "⊢": "🟢 ⊢ grounded",
    "⊨": "🔵 ⊨ inferred",
    "⊬": "🟡 ⊬ extrapolated",
    "⊥": "🔴 ⊥ unknown",
}


def _overlay(canonical: np.ndarray, output: EngineOutput) -> Image.Image:
    img = Image.fromarray(canonical).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay, "RGBA")
    # Refusal heatmap layer
    for r in output.refusals:
        (x0, y0), (x1, y1) = r.region[0], r.region[1]
        d.rectangle([x0, y0, x1, y1], fill=(255, 80, 80, 70), outline=(200, 0, 0, 220), width=2)
    # Objects by type
    for o in output.objects:
        color = TYPE_COLORS.get(o.type, (100, 100, 100))
        rgba = color + (200,)
        coords = o.geometry.coords_px
        if o.geometry.kind == "bbox" and len(coords) >= 2:
            x0, y0 = coords[0]
            x1, y1 = coords[1]
            d.rectangle([x0, y0, x1, y1], outline=rgba, width=2)
        elif o.geometry.kind == "polyline" and len(coords) >= 2:
            d.line([tuple(p) for p in coords], fill=rgba, width=3)
        elif o.geometry.kind == "polygon" and len(coords) >= 3:
            d.polygon([tuple(p) for p in coords], outline=rgba)
    return Image.alpha_composite(img, overlay).convert("RGB")


def _object_row(o: Object) -> dict:
    return {
        "id": o.object_id,
        "type": o.type,
        "type_tag": TAG_BADGES.get(o.type_epistemic.tag, o.type_epistemic.tag),
        "geometry_tag": TAG_BADGES.get(o.geometry_epistemic.tag, o.geometry_epistemic.tag),
        "measurement_tag": TAG_BADGES.get(o.measurement_epistemic.tag, o.measurement_epistemic.tag),
        "measurement_mm": o.measurement_mm if o.measurement_mm is not None else "—",
        "review": o.review_status,
    }


# ── UI ──────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="CAD Trust Engine Lite", layout="wide")
st.title("CAD Trust Engine Lite")
st.caption(
    "PNG/PDF floor plan → per-field EEF-tagged JSON + refusal regions. "
    "**Refusal Over Bluff**: the engine names what it doesn't know."
)

col_pick, _ = st.columns([1, 3])
with col_pick:
    samples = sorted(SAMPLES_DIR.glob("*.png")) + sorted(SAMPLES_DIR.glob("*.pdf"))
    sample_options = ["(upload your own)"] + [s.name for s in samples]
    choice = st.selectbox("Drawing", sample_options, index=1 if samples else 0)
    uploaded = None
    if choice == "(upload your own)":
        uploaded = st.file_uploader("Upload PNG or PDF", type=["png", "pdf"])

if choice != "(upload your own)":
    chosen_path = SAMPLES_DIR / choice
elif uploaded is not None:
    chosen_path = Path("/tmp") / uploaded.name
    chosen_path.write_bytes(uploaded.getvalue())
else:
    chosen_path = None

if chosen_path and st.button("Run Engine", type="primary"):
    try:
        with st.spinner("Running ingest → geometry → OCR → symbols → compose ..."):
            output = run_pipeline(chosen_path)
            canonical = ingest(chosen_path).canonical_image
        st.success("Pipeline complete.")

        col_img, col_data = st.columns([3, 2])
        with col_img:
            st.subheader("Overlay")
            st.image(_overlay(canonical, output), use_container_width=True)

        with col_data:
            st.subheader("Scale Anchor")
            sa = output.scale_anchor
            if sa.detected:
                st.success(f"⊢ detected — px_per_mm = {sa.px_per_mm:.4f} (source: {sa.source})")
            else:
                st.error(
                    "⊥ NOT DETECTED — mm conversion **refused per Measurement_Policy**. "
                    "벽체 후보는 검출되었지만, 신뢰 가능한 치수 기준점이 없어 mm 단위 산출에는 포함하지 않았습니다. "
                    "검수자 확인이 필요합니다."
                )

            st.subheader("Aggregates")
            st.json({
                "wall_count": output.aggregates.wall_count.model_dump(),
                "door_count": output.aggregates.door_count.model_dump(),
                "window_count": output.aggregates.window_count.model_dump(),
                "measured_wall_length_mm": output.aggregates.measured_wall_length_mm.model_dump(),
            })

            st.subheader("Refusals")
            if output.refusals:
                for r in output.refusals:
                    st.warning(r.why)
            else:
                st.write("(no refusal regions)")

        st.subheader("Objects")
        st.dataframe([_object_row(o) for o in output.objects], use_container_width=True)

        with st.expander("Evidence Panel — drill into per-object claims"):
            for o in output.objects:
                with st.expander(f"{o.object_id} | {o.type} | review: {o.review_status}", expanded=False):
                    st.markdown(f"**type_epistemic**: {TAG_BADGES.get(o.type_epistemic.tag)}")
                    for ev in o.type_epistemic.evidence:
                        st.markdown(f"- `{ev.source}` — {ev.signal}")
                    if o.type_epistemic.basis:
                        st.markdown(f"_basis_: {o.type_epistemic.basis}")
                    if o.type_epistemic.gap:
                        st.markdown(f"_gap_: {o.type_epistemic.gap}")

                    st.markdown(f"**geometry_epistemic**: {TAG_BADGES.get(o.geometry_epistemic.tag)}")
                    for ev in o.geometry_epistemic.evidence:
                        st.markdown(f"- `{ev.source}` — {ev.signal}")

                    st.markdown(f"**measurement_epistemic**: {TAG_BADGES.get(o.measurement_epistemic.tag)}")
                    for ev in o.measurement_epistemic.evidence:
                        st.markdown(f"- `{ev.source}` — {ev.signal}")
                    if o.measurement_epistemic.gap:
                        st.markdown(f"_gap_: {o.measurement_epistemic.gap}")

        st.subheader("JSON")
        json_blob = output.model_dump_json(indent=2)
        st.download_button(
            "Download EngineOutput JSON", data=json_blob, file_name=f"{output.drawing_id}.json",
            mime="application/json",
        )
        st.code(json_blob[:3000] + ("\n..." if len(json_blob) > 3000 else ""), language="json")

    except IngestError as exc:
        st.error(f"Ingest failed: {exc}")
    except Exception as exc:
        st.error(f"Pipeline error: {exc}")
        raise

st.divider()
st.caption("CAD Trust Engine Lite v0.1.0 — gem2-vision — Refusal Over Bluff.")
