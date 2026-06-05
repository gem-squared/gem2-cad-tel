# CAD Trust Engine Lite — gem2-vision

**v0.1.0 — MVP for 포비콘 application**

PNG/PDF Korean floor plan → per-field EEF-tagged JSON + Streamlit review UI.

## Wedge

Not "another OpenCV pipeline." A **trust engine** — every detection carries
per-field epistemic tags (type / geometry / measurement orthogonal),
evidence chains, and explicit refusal regions for uncommittable areas.

## Status

Under construction (WP-ST-1, autonomous build 2026-06-05). Full engineering
thesis README lands in U9.

## Quickstart (after U1 completes)

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
pytest
```
