# Verification Log: WP-ST-6
**WP:** Drawing dropdown reorder — wm_* before synth_* + ship live
**task_id:** d88cc110 | **project_slug:** gem2-vision

---

## Unit 1: Implement prefix-priority sort in ui/app.py — SUCCESS (verified 2026-06-08T00:16:56Z)

### CONTRACT.B (expected)
`samples` ordered such that all `wm_*` entries appear before all `synth_*`
entries; within each group, alphabetical order is preserved; non-wm/non-synth
files (if any future addition) sort last alphabetically.

### Result (actual)
Added pure helper `_sort_samples_for_dropdown(paths) -> list[Path]` at
`ui/app.py:55-64` that ranks `wm_*` → 0, `synth_*` → 1, else → 2, secondary
sort alphabetical by filename. Replaced the 5× `sorted(glob(...))` concat at
`ui/app.py:190-198` with a single `_sort_samples_for_dropdown(list(...) + ...)`
call across the same 5 extensions. `ast.parse` syntax OK. Isolated helper test:
`[synth_apt_01, wm_zebra, wm_alpha, synth_apt_02, other] →
 [wm_alpha, wm_zebra, synth_apt_01, synth_apt_02, other]` — ordering correct.

### Judgment
- **Field coverage**: every CONTRACT.B field has corresponding behavior in Result.
  - B.1 "wm_* before synth_*" ⟺ rank(wm_*)=0 < rank(synth_*)=1 — ✓
  - B.2 "alphabetical within group" ⟺ secondary key `name` — ✓ (test: wm_alpha < wm_zebra)
  - B.3 "non-wm/non-synth last" ⟺ rank 2 for others — ✓ (test: 'other.png' at tail)
- **Type conformance**: helper signature `list[Path] → list[Path]` matches expected `samples: list[Path]`.
- **P satisfaction**:
  - `ui/app.py` readable — confirmed (edits applied successfully).
  - `SAMPLES_DIR resolves` — line 27 unchanged.
  - "no other call sites depend on prior alphabetical contract" — grep confirms
    `samples` referenced only at line 202 (definition), 209 (`sample_options`),
    210 (`st.selectbox(... index=1 if samples else 0)`). No code asserts a
    specific ordering of `samples`; the selectbox merely uses it as a list.
- **Verdict**: SUCCESS — all three CONTRACT.B clauses satisfied, P holds, no
  side effects beyond the two edits.

---

## Unit 2: Add ordering test in tests/ — SUCCESS (verified 2026-06-08T00:19:06Z)

### CONTRACT.B (expected)
A pytest case (in `tests/test_ui_preview.py` or a new `tests/test_ui_ordering.py`)
that calls the new sort helper or replays the listing logic against a fixture
directory containing both `wm_*` and `synth_*` files, asserting all wm indices
precede all synth indices.

### Result (actual)
Two tests appended to `tests/test_ui_preview.py`:
1. `test_sort_samples_wm_before_synth` — fixture inputs
   `[synth_03, wm_zebra, wm_alpha, synth_01, other]` → expected
   `[wm_alpha, wm_zebra, synth_01, synth_03, other]`.
2. `test_sort_samples_real_corpus_wm_indices_precede_synth` — across
   `data/samples/` real corpus, asserts `max(wm_idx) < min(synth_idx)`.
Both reuse the existing `helpers` fixture. `pytest -k sort_samples` → 2 passed.

### Judgment
- **Field coverage**: B specifies (1) pytest case (2) calls helper (3) asserts
  wm precedes synth — Result delivers all three (×2 cases for coverage).
- **Type conformance**: pytest functions, fixture-driven; matches existing
  module pattern.
- **P satisfaction**: pytest in `.venv` confirmed by 2-passed observation;
  `helpers` fixture reused (no new fixture infrastructure needed).
- **Verdict**: SUCCESS — both deterministic-fixture and live-corpus assertions
  pass; ordering invariant codified in suite.

---

