# WP-ST-6: Drawing dropdown reorder — wm_* before synth_* + ship live
**STATUS:** IN_PROGRESS | **STATE:** — | **task_id:** d88cc110
**created_at:** 2026-06-08T00:13:52Z | **project_slug:** gem2-vision

## Objective
Reorder the Streamlit Drawing dropdown so Wikimedia-sourced samples (`wm_*`) appear
before procedural fixtures (`synth_*`) — cleaner first impression on the public demo
at https://cad-tel.gemsquared.ai. Scope: minimal sort-key change in `ui/app.py:190-198`,
one ordering test in `tests/`, full fast-suite regression, commit + push to `main`,
and ship via `deploy/deploy.sh` to the existing Vultr VPS (`root@173.199.92.236`,
domain `cad-tel.gemsquared.ai`). No file removal — `synth_*` remain in `data/samples/`.

## Unit-Works

### 1. Implement prefix-priority sort in ui/app.py | STATUS: COMPLETED
- A: `ui/app.py` lines 190-198 build `samples` via alphabetical glob across
     `*.png|*.pdf|*.jpg|*.jpeg|*.svg`. Result: `synth_*` precedes `wm_*` in dropdown.
- B: `samples` ordered such that all `wm_*` entries appear before all `synth_*`
     entries; within each group, alphabetical order is preserved; non-wm/non-synth
     files (if any future addition) sort last alphabetically.
- P: `ui/app.py` readable; SAMPLES_DIR resolves; no other call sites depend on the
     prior alphabetical contract (verified by grep before edit).
- Clarity: 95%
- Unclear: whether to use one-line sort-key (`key=lambda s: (rank, s.name)`) or
  concat-with-filter (`wm + synth`); pick the sort-key form for one-edit minimality.
- Tags: [reordering-dropdown, sorting-samples, fixing-ui, extracting-helper]
- Result: Added pure helper `_sort_samples_for_dropdown(paths) -> list[Path]` at
  `ui/app.py:55-64` that ranks `wm_*` → 0, `synth_*` → 1, else → 2, secondary
  sort alphabetical by filename. Replaced the 5x `sorted(glob(...))` concat at
  `ui/app.py:190-198` with a single `_sort_samples_for_dropdown(list(...) + ...)`
  call across the same 5 extensions. `ast.parse` syntax OK. Isolated helper test:
  `[synth_apt_01, wm_zebra, wm_alpha, synth_apt_02, other] → [wm_alpha, wm_zebra,
  synth_apt_01, synth_apt_02, other]` — ordering correct.
- State: SUCCESS
- Truth:

### 2. Add ordering test in tests/ | STATUS: COMPLETED
- A: `tests/test_ui_preview.py` exists; no test asserts dropdown order.
- B: A pytest case (in `tests/test_ui_preview.py` or a new `tests/test_ui_ordering.py`)
     that calls the new sort helper or replays the listing logic against a fixture
     directory containing both `wm_*` and `synth_*` files, asserting all wm indices
     precede all synth indices.
- P: pytest available in `.venv`; fixture pattern from `tests/fixtures/` reusable.
- Clarity: 90%
- Unclear: whether to factor the sort into a pure helper in `ui/app.py` for direct
  testability (preferred) vs. testing via Streamlit's app harness (heavier).
- Tags: [testing-ordering, asserting-sort, regressing-ui, reusing-fixture]
- Result: Added two tests to `tests/test_ui_preview.py` (appended after the
  existing `test_preview_is_read_only_invariant`):
    1. `test_sort_samples_wm_before_synth` — deterministic fixture test:
       inputs `[synth_03, wm_zebra, wm_alpha, synth_01, other]` →
       expects `[wm_alpha, wm_zebra, synth_01, synth_03, other]`.
    2. `test_sort_samples_real_corpus_wm_indices_precede_synth` — live-corpus
       check across `data/samples/`: asserts `max(wm_idx) < min(synth_idx)`
       in the sorted output; skips gracefully if either group is empty.
  Both reuse the existing `helpers` fixture (importlib-based load of `ui/app.py`).
  `pytest -k sort_samples` → 2 passed in 1.16s.
- State: SUCCESS
- Truth:

### 3. Run fast test suite (regression gate) | STATUS: PENDING
- A: Baseline from WP-ST-5: 145/145 fast tests passing.
- B: `pytest -q -m "not slow"` returns 0 with at least 146 passed (new ordering test
     included); no previously-passing test regresses.
- P: `.venv` activatable; `pytest` invocable; no env vars missing.
- Clarity: 95%
- Unclear: none.
- Tags: [running-tests, gating-regression]
- Result:
- State:
- Truth:

### 4. Commit + push to main | STATUS: PENDING
- A: Working tree contains only the 2 intended edits (`ui/app.py` + test file);
     tests green from U3.
- B: One commit on `main` (per project convention: detailed body + Date + Author);
     `origin/main` updated.
- P: `git status` clean of unrelated changes; `git remote` configured.
- Clarity: 95%
- Unclear: none.
- Tags: [committing-changes, pushing-main]
- Result:
- State:
- Truth:

### 5. Deploy to VPS + verify live order | STATUS: PENDING
- A: `origin/main` carries the reorder commit; VPS at `root@173.199.92.236` is
     reachable; SSH key at `~/.ssh/id_ed25519_aio_deploy` valid.
- B: `./deploy/deploy.sh root@173.199.92.236 --domain cad-tel.gemsquared.ai`
     succeeds; smoke check passes; live `https://cad-tel.gemsquared.ai` Drawing
     dropdown lists `wm_*` entries before any `synth_*` entries (verified via
     curl + grep on the page source, or a brief headless check if Streamlit
     renders the options server-side).
- P: deploy.sh exists + executable; rsync available locally; VPS Docker healthy.
- Clarity: 85%
- Unclear: Streamlit renders selectbox options inside a hydration payload — the
  exact selector to grep for in the rendered HTML is uncertain; fallback is to
  verify by reading the rsync'd `ui/app.py` on the VPS + a container restart log.
- Tags: [deploying-vps, verifying-live, shipping-change]
- Result:
- State:
- Truth:

## References
- WP-ST-5 (`f3203e2e` deploy pattern + VPS host + Caddy reverse proxy)
- `ui/app.py:190-198` (existing glob)
- `tests/test_ui_preview.py` (existing UI test pattern)
- `deploy/deploy.sh` (rsync + compose + smoke)
- CLAUDE.md (commit convention)
