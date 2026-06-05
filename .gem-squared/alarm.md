# ALARM — gem2-vision
## Last checked: 2026-06-06T00:35:00Z

## Current Status
**Branch:** main  |  **Tags:** v0.1.0, v0.1.1, v0.1.2, v0.1.3

PENDING: 0 | IN_PROGRESS: 0 | COMPLETED: 4 | DECOMPOSED: 0 | ABORTED: 0 | DEFERRED: 0

> **WP-ST-4 COMPLETED|SUCCESS 2026-06-06** — License fix + preview pane v0.1.3.
> 4 unit-works delivered autonomously. 145 fast tests + 3 smoke = 148 total
> green. Corpus 34 → 50 drawings (license fix unlocked 16 previously-refused
> public-domain candidates). Streamlit preview pane right of Drawing dropdown.
> v0.1.3 git tag. All four WPs awaiting `/archive-work`.

### Active (IN_PROGRESS) — units remaining
(none)

### Awaiting /archive-work (COMPLETED|SUCCESS, work-plan/ → archive/ pending)

| WP | Title | task_id | Units | Notes |
|----|-------|---------|-------|-------|
| WP-ST-1 | CAD Trust Engine Lite v0.1 — 포비콘 application MVP | f3203e2e | 9 | v0.1.0; 53/53 tests; 1 retry; 9 commits |
| WP-ST-2 | CAD Trust Engine Audit Subsystem v0.1.1 — SQLite audit/logging | 09750a81 | 6 | v0.1.1; 91/91 tests; 0 retries; 6 commits |
| WP-ST-3 | Crawl real public-source CAD/floor plan drawings — v0.1.2 corpus expansion | f6316037 | 6 | v0.1.2; 130 tests; 1 retry; 6 commits; corpus 12→34 |
| WP-ST-4 | v0.1.3 — 'pd' license fix + re-crawl + Streamlit preview pane | 4dd5c03b | 4 | v0.1.3; 148 tests; 1 retry (AST invariant refactor); 4 commits; corpus 34→50; preview pane added |

### PENDING (not started)
(none)

### DEFERRED
(none)

### DECOMPOSED
(none)

### ABORTED
(none)

---

## Recently COMPLETED (last 10)

| WP | Date | Summary | STATE |
|----|------|---------|-------|
| WP-ST-4 | 2026-06-06 | v0.1.3 license fix + preview pane — 4 units: U1 exact-vs-prefix license matcher (prevents pd→pdf false-match) + plain pd/cc0/public-domain mappings, U2 re-crawl +16 drawings (corpus 34→50), U3 Streamlit preview pane right of dropdown with PIL.Image + @st.cache_data + Preview_Is_Read_Only AST invariant, U4 docs/CORPUS.md + README + tag. 145 fast tests + 3 smoke. | SUCCESS |
| WP-ST-3 | 2026-06-05 | Real-source corpus crawl v0.1.2 — 6 units; +22 Wikimedia drawings; pipeline 100% success on 32 ingestable. | SUCCESS |
| WP-ST-2 | 2026-06-05 | Audit Subsystem v0.1.1 — 6 units; SQLite + AuditContext + Streamlit Past Runs tab. | SUCCESS |
| WP-ST-1 | 2026-06-05 | CAD Trust Engine Lite v0.1.0 — 9 units; per-field EEF + Measurement_Policy + refusal_candidates + Streamlit. | SUCCESS |

---

## Archive Summary
**Archived:** 0
**Awaiting /archive-work:** 4 (WP-ST-1 + WP-ST-2 + WP-ST-3 + WP-ST-4)
**Remaining in work-plan/:** 4 files

---

## Pending Decisions
- v0.2 scope sequencing — VLM_Verify especially attractive now that we see 50-drawing corpus produces 0-931 refusals per drawing on real data
- Whether to `/archive-work` all four WPs at once or sequentially
- Whether to fix the 2 SVG drawings (remove or extend with cairosvg dep)
- Whether to re-run the 10-min smoke test on the expanded 50-drawing corpus

---

## Known Issues
- ⊥ 2 SVG drawings cannot be ingested (SVG support needs cairosvg/wand new dep)
- ⊥ Some real drawings produce 20,000+ objects (mostly noise on non-CAD content like watercolours/cross-sections); high refusal counts make them demo-positive but slow (~116s)
- ⊬ Audit DB grows unbounded — retention/rotation deferred to v0.3
- ⊬ 11 Wikimedia candidates still refused by license (GFDL-only, fair-use, etc.) — these are correct refusals per No_Source_Bluff
- ⊥ Visual Streamlit UI verification still deferred — process auto-reloaded with new preview pane; interactive flow not browser-tested in autonomous session

---

*Initialized: 2026-06-05T13:01:56Z via /init-session*
*Updated: 2026-06-05T14:18:00Z — WP-ST-1 COMPLETED|SUCCESS, v0.1.0, 53 tests*
*Updated: 2026-06-05T14:46:00Z — WP-ST-2 COMPLETED|SUCCESS, v0.1.1, 91 tests*
*Updated: 2026-06-06T00:18:00Z — WP-ST-3 COMPLETED|SUCCESS, v0.1.2, 130 tests (corpus 12→34)*
*Updated: 2026-06-06T00:35:00Z — WP-ST-4 COMPLETED|SUCCESS, v0.1.3, 148 tests (corpus 34→50, license fix unlocks +16, preview pane added). Counters: PENDING 1→0, COMPLETED 3→4.*
