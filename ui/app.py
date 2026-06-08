"""CAD Trust Engine Lite — Streamlit review UI with Audit (Past Runs) tab.

Run with: streamlit run ui/app.py
"""
from __future__ import annotations

import io
import json
import os
import sqlite3
import sys
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw

# Allow running from anywhere
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from cad_trust.audit_schema import init_audit_db  # noqa: E402
from cad_trust.ingest import IngestError, ingest  # noqa: E402
from cad_trust.pipeline import run as run_pipeline  # noqa: E402
from cad_trust.schema import EngineOutput, Object  # noqa: E402

SAMPLES_DIR = ROOT / "data" / "samples"
DEFAULT_AUDIT_DB = ROOT / ".gem-squared" / "audit.sqlite"

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


def _resolve_audit_db() -> Path:
    env = os.environ.get("GEM2_VISION_AUDIT_DB")
    return Path(env) if env else DEFAULT_AUDIT_DB


def _sort_samples_for_dropdown(paths: list[Path]) -> list[Path]:
    """Order: wm_* first, synth_* second, others last; alphabetical within each group."""
    def rank(p: Path) -> tuple[int, str]:
        name = p.name
        if name.startswith("wm_"):
            return (0, name)
        if name.startswith("synth_"):
            return (1, name)
        return (2, name)
    return sorted(paths, key=rank)


# ── Preview helpers (WP-ST-4 U3) ────────────────────────────────────────────


PREVIEW_MAX_WIDTH = 400
PREVIEW_SUPPORTED = (".png", ".jpg", ".jpeg", ".pdf")
PREVIEW_KNOWN_UNSUPPORTED = (".svg",)


def _load_preview_image_impl(path_str: str, mtime: float, max_width: int) -> Image.Image | None:
    """Pure-function preview loader.

    Returns a PIL.Image (RGB, thumbnail-sized) or None when the format is
    unsupported / file unreadable. NEVER raises on bad input — None signals
    "preview unavailable", which the UI surfaces as a caption.

    `mtime` is here purely as a cache-key contributor (st.cache_data hashes args).
    """
    path = Path(path_str)
    if not path.exists():
        return None
    suffix = path.suffix.lower()
    try:
        if suffix in (".png", ".jpg", ".jpeg"):
            with Image.open(path) as img:
                rgb = img.convert("RGB")
                rgb.thumbnail((max_width, max_width * 2), Image.LANCZOS)
                # Force eager decode so the with-block can close
                rgb.load()
                return rgb
        if suffix == ".pdf":
            from pdf2image import convert_from_path
            pages = convert_from_path(str(path), dpi=72, first_page=1, last_page=1)
            if not pages:
                return None
            rgb = pages[0].convert("RGB")
            rgb.thumbnail((max_width, max_width * 2), Image.LANCZOS)
            return rgb
    except Exception:
        return None
    return None


def load_preview_image(path: Path, max_width: int = PREVIEW_MAX_WIDTH) -> Image.Image | None:
    """Streamlit-wrapped preview loader. Caches per (path, mtime) so reselects are instant.

    Per `Preview_Is_Read_Only` invariant: this function MUST NOT call run_pipeline,
    open the audit DB, or write provenance. It is a pure visual surface.
    """
    if not path.exists():
        return None
    return _load_preview_image_cached(str(path), path.stat().st_mtime, max_width)


@st.cache_data(show_spinner=False)
def _load_preview_image_cached(path_str: str, mtime: float, max_width: int) -> Image.Image | None:
    return _load_preview_image_impl(path_str, mtime, max_width)


def preview_status_message(path: Path) -> str | None:
    """Returns a status string when the file format is known-unsupported, else None."""
    if not path.exists():
        return "(file not found)"
    suffix = path.suffix.lower()
    if suffix in PREVIEW_KNOWN_UNSUPPORTED:
        return (
            f"Preview unavailable for {suffix.upper()} — pipeline will refuse "
            f"this format at ingest ({suffix} not in supported {PREVIEW_SUPPORTED})."
        )
    if suffix not in PREVIEW_SUPPORTED:
        return f"Preview unavailable for {suffix or '(no extension)'}."
    return None


def _overlay(canonical: np.ndarray, output: EngineOutput) -> Image.Image:
    img = Image.fromarray(canonical).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay, "RGBA")
    for r in output.refusals:
        (x0, y0), (x1, y1) = r.region[0], r.region[1]
        d.rectangle([x0, y0, x1, y1], fill=(255, 80, 80, 70), outline=(200, 0, 0, 220), width=2)
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


def _ensure_audit_db_exists() -> Path:
    db = _resolve_audit_db()
    init_audit_db(db)
    return db


# ── App ─────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="CAD Trust Engine Lite", layout="wide")
st.title("CAD Trust Engine Lite")
st.caption(
    "PNG/PDF floor plan → per-field EEF-tagged JSON + refusal regions. "
    "**Refusal Over Bluff**: the engine names what it doesn't know — *and remembers it*."
)

audit_db_path = _resolve_audit_db()
st.sidebar.markdown("### Audit")
st.sidebar.code(f"DB: {audit_db_path}", language="text")
st.sidebar.caption("Set `GEM2_VISION_AUDIT_DB` env var to override.")

tab_run, tab_past = st.tabs(["Run Engine", "Past Runs (Audit)"])


# ── Tab 1: Run Engine ───────────────────────────────────────────────────────

with tab_run:
    col_pick, col_preview = st.columns([2, 3])
    with col_pick:
        samples = _sort_samples_for_dropdown(
            list(SAMPLES_DIR.glob("*.png"))
            + list(SAMPLES_DIR.glob("*.pdf"))
            + list(SAMPLES_DIR.glob("*.jpg"))
            + list(SAMPLES_DIR.glob("*.jpeg"))
            + list(SAMPLES_DIR.glob("*.svg"))
        )
        sample_options = ["(upload your own)"] + [s.name for s in samples]
        choice = st.selectbox("Drawing", sample_options, index=1 if samples else 0)
        uploaded = None
        if choice == "(upload your own)":
            uploaded = st.file_uploader("Upload PNG / JPG / PDF", type=["png", "jpg", "jpeg", "pdf"])

    if choice != "(upload your own)":
        chosen_path = SAMPLES_DIR / choice
    elif uploaded is not None:
        chosen_path = Path("/tmp") / uploaded.name
        chosen_path.write_bytes(uploaded.getvalue())
    else:
        chosen_path = None

    # Preview pane (WP-ST-4 U3) — right of dropdown, BEFORE pipeline runs
    with col_preview:
        st.markdown("**Preview**")
        if chosen_path is None:
            st.caption("(select a drawing to preview)")
        else:
            status = preview_status_message(chosen_path)
            if status:
                st.info(status)
            else:
                preview_img = load_preview_image(chosen_path)
                if preview_img is None:
                    st.warning(f"Could not load preview for {chosen_path.name}")
                else:
                    st.image(preview_img, caption=chosen_path.name, width=PREVIEW_MAX_WIDTH)

    if chosen_path and st.button("Run Engine", type="primary"):
        try:
            with st.spinner("Running ingest → geometry → OCR → symbols → compose ..."):
                _ensure_audit_db_exists()
                output = run_pipeline(chosen_path, audit_db_path=audit_db_path)
                canonical = ingest(chosen_path).canonical_image
            st.success("Pipeline complete. Run logged to audit DB.")

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
                        "벽체 후보는 검출되었지만, 신뢰 가능한 치수 기준점이 없어 mm 단위 산출에는 "
                        "포함하지 않았습니다. 검수자 확인이 필요합니다."
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


# ── Tab 2: Past Runs (Audit) ────────────────────────────────────────────────


def _conn_ro(db: Path) -> sqlite3.Connection | None:
    if not db.exists():
        return None
    c = sqlite3.connect(str(db))
    c.row_factory = sqlite3.Row
    return c


with tab_past:
    db = audit_db_path
    conn = _conn_ro(db)
    if conn is None:
        st.info(
            f"No audit DB at {db}. Run a drawing through the **Run Engine** tab first — "
            "every run gets logged automatically."
        )
    else:
        try:
            # Overall stats
            st.subheader("Audit Overview")
            total_runs = conn.execute("SELECT COUNT(*) AS c FROM runs").fetchone()["c"]
            ok_runs = conn.execute("SELECT COUNT(*) AS c FROM runs WHERE exit_state='SUCCESS'").fetchone()["c"]
            fail_runs = conn.execute("SELECT COUNT(*) AS c FROM runs WHERE exit_state='FAILURE'").fetchone()["c"]
            total_ref = conn.execute("SELECT COUNT(*) AS c FROM refusals_log").fetchone()["c"]
            total_pol = conn.execute("SELECT COUNT(*) AS c FROM policy_fires").fetchone()["c"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("runs total", total_runs)
            c2.metric("SUCCESS / FAILURE", f"{ok_runs} / {fail_runs}")
            c3.metric("refusals logged", total_ref)
            c4.metric("policy fires", total_pol)

            # Aggregate refusal pattern across corpus
            if total_ref > 0:
                st.subheader("Refusal pattern across all runs")
                ref_by_type = conn.execute(
                    "SELECT attempted_type, COUNT(*) AS cnt FROM refusals_log "
                    "GROUP BY attempted_type ORDER BY cnt DESC"
                ).fetchall()
                st.bar_chart({"count": {r["attempted_type"]: r["cnt"] for r in ref_by_type}})

            # Recent runs list
            st.subheader("Recent Runs")
            recent = conn.execute(
                "SELECT run_id, drawing_id, started_at, duration_ms, exit_state "
                "FROM runs ORDER BY started_at DESC LIMIT 50"
            ).fetchall()
            run_options = {
                f"{r['drawing_id']}  |  {r['started_at']}  |  {r['exit_state']}  ({r['run_id'][:8]})": r["run_id"]
                for r in recent
            }
            if not run_options:
                st.write("(no runs yet)")
            else:
                picked_label = st.selectbox("Drill into:", list(run_options.keys()))
                picked_run_id = run_options[picked_label]
                run_row = conn.execute(
                    "SELECT * FROM runs WHERE run_id = ?", (picked_run_id,)
                ).fetchone()
                with st.expander("Run row", expanded=False):
                    st.json({k: run_row[k] for k in run_row.keys()})

                # Stage events
                st.markdown("**Stage events (timeline)**")
                events = conn.execute(
                    "SELECT timestamp, stage, level, message, payload_json "
                    "FROM stage_events WHERE run_id = ? ORDER BY event_id",
                    (picked_run_id,),
                ).fetchall()
                st.dataframe(
                    [
                        {
                            "timestamp": e["timestamp"],
                            "stage": e["stage"],
                            "level": e["level"],
                            "message": e["message"],
                            "payload": (e["payload_json"] or "")[:200],
                        }
                        for e in events
                    ],
                    use_container_width=True,
                )

                # Refusals
                st.markdown("**Refusals**")
                refs = conn.execute(
                    "SELECT attempted_type, why, region_json FROM refusals_log WHERE run_id = ?",
                    (picked_run_id,),
                ).fetchall()
                if refs:
                    for r in refs:
                        st.warning(f"[{r['attempted_type']}] {r['why']}")
                else:
                    st.caption("(no refusals)")

                # Policy fires
                st.markdown("**Policy fires**")
                pols = conn.execute(
                    "SELECT policy_name, detail_json, timestamp FROM policy_fires WHERE run_id = ?",
                    (picked_run_id,),
                ).fetchall()
                if pols:
                    for p in pols:
                        st.info(f"{p['timestamp']}  •  {p['policy_name']}  •  {p['detail_json']}")
                else:
                    st.caption("(no policy fires)")

                # Epistemic distribution
                st.markdown("**Epistemic distribution (this run)**")
                eps = conn.execute(
                    "SELECT stage, field, tag, count FROM epistemic_counts WHERE run_id = ? "
                    "ORDER BY field, tag",
                    (picked_run_id,),
                ).fetchall()
                if eps:
                    st.dataframe(
                        [{"stage": e["stage"], "field": e["field"], "tag": e["tag"], "count": e["count"]} for e in eps],
                        use_container_width=True,
                    )
                else:
                    st.caption("(no epistemic counts)")
        finally:
            conn.close()

st.divider()
st.caption("CAD Trust Engine Lite v0.1.3 — gem2-vision — Refusal Over Bluff, **remembered**.")
