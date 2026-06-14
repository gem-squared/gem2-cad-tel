# WP-ST-8: v0.1.6 — ash_pits default demo + visible BYO LLM prompt + live deploy
**STATUS:** IN_PROGRESS | **STATE:** — | **task_id:** fb9115d5
**created_at:** 2026-06-14T04:21:00Z | **project_slug:** gem2-vision

## Objective
Land v0.1.6 as the live portfolio demo at `cad-tel.gemsquared.ai`. Three concrete shifts: (1) the Streamlit dropdown defaults to the `wm_00104_bm--cross_section_of_ash_pits--wabash_railroad--decatur_il_50f7feda-0ce0-4.jpg` Wikimedia cross-section — a high-signal real-world drawing that exercises Refusal Over Bluff so a cold portfolio visitor sees the wedge immediately, not a clean synthetic; (2) the BYO LLM-key affordance becomes visibly prompted from the main panel (banner above the Run Engine pane + contextual post-run callout when refusals are present) rather than buried in the sidebar; (3) commit + push to `origin/main` with tag `v0.1.6` + deploy to the Vultr VPS, with SSH-based ground-truth verification because the existing `deploy.sh` smoke check has a documented body-grep false-negative.

**Locked decisions:**
- ⊢ Default sample: `DEFAULT_SAMPLE_NAME` constant + index-resolution helper (fallback to index 1 if file removed from corpus).
- ⊢ BYO prompt: two `st.info(...)` callouts — top-of-Run-Engine-tab banner + contextual post-run prompt gated on `output.refusals` non-empty AND empty `st.session_state['vlm_api_key']`.
- ⊢ Version bump: v0.1.5 → v0.1.6 across `pyproject.toml`, `ui/app.py:443`, both READMEs, `alarm.md`.
- ⊢ Git: single commit per CLAUDE.md convention; `git push origin main && git push --tags`. NEVER force-push.
- ⊢ Deploy: `./deploy/deploy.sh root@173.199.92.236 --domain cad-tel.gemsquared.ai`. Accept the documented `deploy.sh` body-grep false-negative — recovery via direct SSH verification (mirror of WP-ST-6 precedent).
- ⊢ Live verify: SSH-grep the deployed `ui/app.py` for the v0.1.6 footer; SSH-grep for `DEFAULT_SAMPLE_NAME`; `curl https://cad-tel.gemsquared.ai/_stcore/health` HTTP 200.

## Unit-Works

### 1. ui/app.py — ash_pits default + visible BYO prompts | STATUS: COMPLETED
- A: `ui/app.py:209` currently sets `index=1 if samples else 0` — the selected default is whatever sorts first in the wm_* group. No top-of-tab BYO banner; the BYO sidebar block (WP-ST-7 U2, lines 194-216) exists but is invisible until the visitor opens the sidebar drawer. No post-run BYO callout. `data/samples/wm_00104_bm--cross_section_of_ash_pits--wabash_railroad--decatur_il_50f7feda-0ce0-4.jpg` exists ⊢ (verified). 145/2 pytest baseline.
- B: `ui/app.py` edits:
  - **Constant** `DEFAULT_SAMPLE_NAME = "wm_00104_bm--cross_section_of_ash_pits--wabash_railroad--decatur_il_50f7feda-0ce0-4.jpg"` defined near `SAMPLES_DIR` (top-of-module constants block).
  - **Helper** `_default_sample_index(sample_options: list[str]) -> int` returns the position of `DEFAULT_SAMPLE_NAME` in `sample_options` if present, else `1` if any sample exists, else `0`. Pure function, testable.
  - **Selectbox** at the dropdown call site updated to `index=_default_sample_index(sample_options)`.
  - **Top-of-tab banner**: inside `with tab_run:` and before `col_pick, col_preview = st.columns(...)`, render `st.info("🔑 Optional: paste your own LLM API key in the sidebar to enable VLM_Verify (v0.2 preview). No key required for the v0.1 trust pipeline below.")` — single static call, not gated; visible on first render.
  - **Post-run BYO callout**: after `st.success("Pipeline complete...")` and BEFORE the columns render, add a conditional `if output.refusals and not st.session_state.get("vlm_api_key"): st.info(f"💡 VLM_Verify could re-check these {len(output.refusals)} refused regions. Paste your API key in the sidebar to enable (v0.2 preview).")`.
  - **One new unit test** in `tests/test_ui_app_default_sample.py` (new file) covering `_default_sample_index`: (a) when `DEFAULT_SAMPLE_NAME` present in options → returns its index, (b) when absent + ≥1 sample → returns 1, (c) when only `(upload your own)` option → returns 0.
- P: U1 starts on a clean working tree (modulo WP-ST-7 lifecycle residues that will be folded into U2's commit). `pytest --ignore=tests/test_corpus_pipeline_smoke.py -x -q` baseline 145/2.
- Clarity: 85%
- Unclear: exact placement of the post-run callout relative to the column layout (above col_img/col_data vs inside col_data) — will choose above-columns for visibility. Banner copy may want a 한국어 mirror — defer until David asks.
- Tags: [defaulting-sample, prompting-byokey, scaffolding-callout, testing-helper]
- Result: 2 files edited + 1 new test file:
  - **ui/app.py**:
    - Constant `DEFAULT_SAMPLE_NAME = "wm_00104_bm--cross_section_of_ash_pits--wabash_railroad--decatur_il_50f7feda-0ce0-4.jpg"` added after `DEFAULT_AUDIT_DB` (top-of-module constants block) ⊢.
    - Helper `_default_sample_index(sample_options: list[str]) -> int` added after `_sort_samples_for_dropdown` — pure function, returns index of DEFAULT_SAMPLE_NAME if present; falls back to 1 if any sample exists; returns 0 if only "(upload your own)" remains ⊢.
    - Selectbox call site: `index=1 if samples else 0` → `index=_default_sample_index(sample_options)` ⊢.
    - **Top-of-Run-Engine-tab BYO banner** (inside `with tab_run:` before the columns): `st.info("🔑 Optional — paste your own LLM API key in the **sidebar** to enable VLM_Verify (v0.2 preview). No key required for the v0.1 trust pipeline below.")` ⊢.
    - **Post-run BYO callout** (after `st.success("Pipeline complete...")` and before `col_img, col_data = st.columns(...)`): conditional `if output.refusals and not st.session_state.get("vlm_api_key"): st.info(f"💡 VLM_Verify could re-check these {len(output.refusals)} refused region(s). Paste your LLM API key in the sidebar to enable (v0.2 preview).")` ⊢.
  - **tests/test_ui_app_default_sample.py** (new): 5 tests covering: (a) `DEFAULT_SAMPLE_NAME` constant is the ash_pits cross-section; (b) `_default_sample_index` returns correct index when present; (c) falls back to 1 when absent + samples exist; (d) returns 0 when only upload placeholder; (e) the actual default file exists on disk in `data/samples/`. Mirror of the `importlib.util.spec_from_file_location` import pattern used by tests/test_ui_preview.py (loads module-level Streamlit calls as no-ops in test runtime).
  - **Smoke**: `py_compile ui/app.py` → syntax OK ⊢. New 5 tests: `pytest tests/test_ui_app_default_sample.py -x -v` → **5 passed in 0.82s** ⊢. Full fast suite: `pytest --ignore=tests/test_corpus_pipeline_smoke.py` → **150 passed, 2 skipped, 3 warnings in 104.93s** (baseline 145 → 150 with the 5 new tests; no regression) ⊢.
- State: SUCCESS
- Truth:

### 2. Version bump v0.1.6 + commit + push | STATUS: IN_PROGRESS
- A: U1 complete with passing tests. `pyproject.toml` at `0.1.5`. `ui/app.py:443` caption at `v0.1.5`. `README.md` line 7 + `README.en.md` line 7 + their 빌드 현황/What's-built tables at v0.1.5. `alarm.md` reflects last state at WP-ST-7. Working tree carries U1 edits + WP-ST-7 lifecycle residues (`WP-ST-7.md` + `verify-work-logs/WP-ST-7.md`).
- B:
  - `pyproject.toml` `version = "0.1.5"` → `version = "0.1.6"`.
  - `ui/app.py:443` `v0.1.5` → `v0.1.6`.
  - `README.md` line 7 + `빌드 현황` header (5 → 6 → 6 tagged releases since v0.1.5 was just landed... actually 5→6→7 tags) + new v0.1.6 row + 진행 상황 section v0.1.6 line.
  - `README.en.md` mirrors.
  - `alarm.md` updated: Last-checked timestamp; Tags list `+ v0.1.6`; COMPLETED counter 7 → 8 (after this WP completes); WP-ST-8 row added to both Awaiting-archive + Recently-COMPLETED tables; Archive Summary `7 → 8 awaiting`; footer Updated-line appended.
  - WP-ST-8.md + verify-work-logs/WP-ST-8.md (created by /proceed-work and /verify-work for U1) included in this commit's staging.
  - **Single git commit** per CLAUDE.md convention: title `WP-ST-8: v0.1.6 — ash_pits default demo + visible BYO LLM prompt`; body covers U1 edits + version bumps + WP-ST-7 lifecycle-residue closeout; `Date:` + `Author: David Seo of GEM².AI`.
  - **Tag**: `git tag -a v0.1.6 -m "v0.1.6 — ash_pits default demo + visible BYO LLM prompt"`.
  - **Push**: `git push origin main` (commit) + `git push origin v0.1.5 v0.1.6` (or `git push --tags` for all). NEVER force-push.
  - Post-state: `git log origin/main` shows the new commit; `git ls-remote --tags origin` shows v0.1.6.
- P: U1 STATE = SUCCESS; `origin` remote configured (verified by prior commits e.g. `9834174` pushed in WP-ST-6); SSH key for GitHub valid (David has push permissions to gem-squared/gem2-cad-tel).
- Clarity: 95%
- Unclear: nothing material — mechanical mirror of WP-ST-7 U3 plus a push step.
- Tags: [bumping-version, committing-changes, pushing-remote]
- Result:
- State:
- Truth:

### 3. Deploy v0.1.6 to VPS + SSH-verify live | STATUS: PENDING
- A: U2 complete; `origin/main` carries the v0.1.6 commit + tag. VPS reachable at `root@173.199.92.236`; SSH key `~/.ssh/id_ed25519_aio_deploy` valid (WP-ST-5/6 precedent). Host Caddy + Docker compose stack live. The pre-existing live site at `https://cad-tel.gemsquared.ai` serves v0.1.4 container (v0.1.5 never deployed; WP-ST-7 did not touch the live site).
- B: `./deploy/deploy.sh root@173.199.92.236 --domain cad-tel.gemsquared.ai` executed. Expected sequence per `docs/DEPLOY.md`: rsync → compose up --build → healthcheck → smoke. The documented `deploy.sh` body-grep false-negative on Streamlit JS-rendered title MAY cause an exit-1 — accepted, not blocking. Live verification via direct SSH ground-truth (mirror of WP-ST-6):
  - `ssh root@173.199.92.236 'docker ps --format "{{.Names}}\t{{.Status}}"'` → both `cad-trust-streamlit` and `cad-trust-caddy` Up.
  - `ssh root@173.199.92.236 'grep "v0.1.6" /opt/cad-tel/ui/app.py'` → matches the bumped footer caption (deployed code reflects v0.1.6) ⊢.
  - `ssh root@173.199.92.236 'grep DEFAULT_SAMPLE_NAME /opt/cad-tel/ui/app.py'` → matches the new constant (default-sample logic deployed) ⊢.
  - `ssh root@173.199.92.236 'docker logs cad-trust-streamlit --tail 30'` → no Python exceptions in startup; "Uvicorn server started" present.
  - `curl -s -o /dev/null -w '%{http_code}' https://cad-tel.gemsquared.ai/_stcore/health` → `200`.
  - `curl -s -o /dev/null -w '%{http_code}' https://cad-tel.gemsquared.ai/` → `200`.
- P: U2 STATE = SUCCESS; SSH connectivity to 173.199.92.236; host Docker stack healthy at task start (pre-flight `ssh ... 'docker ps'` confirms before triggering deploy.sh).
- Clarity: 80%
- Unclear: whether deploy.sh smoke fails on v0.1.6 the same way it did in WP-ST-6 (it should — body-grep behavior unchanged); whether the cad-trust-streamlit container restart inherits cached PaddleOCR models (it should — named volume persists). Both risks have well-documented recovery: direct SSH ground-truth + post-restart `docker logs` tail.
- Tags: [deploying-vps, verifying-live, ssh-grounding]
- Result:
- State:
- Truth:

## References
- WP-ST-5 (`docs/DEPLOY.md` + `deploy/deploy.sh` source — deploy mechanics)
- WP-ST-6 (default-sample-sort precedent + deploy.sh body-grep false-negative recovery via SSH)
- WP-ST-7 (BYO sidebar block at ui/app.py:194-216 — pattern this WP makes more visible; version-bump mechanical pattern)
- `data/samples/wm_00104_bm--cross_section_of_ash_pits--wabash_railroad--decatur_il_50f7feda-0ce0-4.jpg` (target default sample, verified present)
- CLAUDE.md §"Git Commit Convention" + §"Mandatory Execution Rule"
- Memory: `feedback_decisiveness.md` (locked plan; no menu re-asks during execution)
