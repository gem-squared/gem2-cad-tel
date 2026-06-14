# Verification Log: WP-ST-8
**WP:** v0.1.6 — ash_pits default demo + visible BYO LLM prompt + live deploy
**task_id:** fb9115d5 | **project_slug:** gem2-vision

---

## Unit 1: ui/app.py — ash_pits default + visible BYO prompts — SUCCESS (verified 2026-06-14T04:35:51Z)

### CONTRACT.B (expected)
- `DEFAULT_SAMPLE_NAME` constant defined at module top.
- `_default_sample_index(sample_options)` helper — returns index of DEFAULT_SAMPLE_NAME if present; falls back to 1 if any sample exists; returns 0 otherwise.
- Selectbox uses computed default index instead of `index=1 if samples else 0`.
- Top-of-Run-Engine-tab `st.info` banner pointing to BYO sidebar.
- Post-run conditional `st.info` callout: fires when `output.refusals` non-empty AND `st.session_state['vlm_api_key']` empty.
- New `tests/test_ui_app_default_sample.py` with unit tests covering the helper.

### Result (actual)
- `ui/app.py:29` — `DEFAULT_SAMPLE_NAME = "wm_00104_bm--cross_section_of_ash_pits--wabash_railroad--decatur_il_50f7feda-0ce0-4.jpg"` ⊢.
- `ui/app.py:68` — `def _default_sample_index(sample_options: list[str]) -> int:` with `DEFAULT_SAMPLE_NAME in sample_options → return its index`; `len(sample_options) > 1 → return 1`; else `return 0` ⊢.
- `ui/app.py:252` — `choice = st.selectbox("Drawing", sample_options, index=_default_sample_index(sample_options))` ⊢.
- `ui/app.py:238-241` — Top-of-tab `st.info("🔑 Optional — paste your own LLM API key in the **sidebar** to enable VLM_Verify (v0.2 preview). No key required for the v0.1 trust pipeline below.")` ⊢.
- `ui/app.py:289-293` — Post-run conditional: `if output.refusals and not st.session_state.get("vlm_api_key"): st.info(f"💡 VLM_Verify could re-check these {len(output.refusals)} refused region(s). Paste your LLM API key in the sidebar to enable (v0.2 preview).")` ⊢.
- `tests/test_ui_app_default_sample.py` (2336 bytes) — 5 tests: (a) `DEFAULT_SAMPLE_NAME` is ash_pits cross-section; (b) helper returns index when present; (c) falls back to 1 when absent + samples exist; (d) returns 0 when only upload placeholder; (e) named default file actually exists on disk in `data/samples/`. **5 passed in 0.82s** ⊢.
- Full fast suite: `pytest --ignore=tests/test_corpus_pipeline_smoke.py` → **150 passed, 2 skipped, 3 warnings in 104.93s** — baseline 145 → 150 with the 5 new tests, no regression ⊢.

### Judgment
- **Field coverage**: every CONTRACT.B clause has a corresponding artifact in the actual codebase, located at named lines.
- **Type conformance**: helper returns `int`; constants are `str`; `st.info(...)` calls are documented Streamlit widgets; conditional uses `output.refusals` (list, truthy when non-empty) and `st.session_state.get` (None-safe). All types align with B.
- **Constraint satisfaction (P)**: baseline 145/2 preserved as 150/2 (5 new tests integrated cleanly, no breakage in adjacent test files). Working tree was clean of unrelated edits at start. `py_compile` confirmed syntax.
- **STATE = SUCCESS** — CONTRACT.B fulfilled, P holds, no regression.
