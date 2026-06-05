# ALARM — gem2-vision
## Last checked: 2026-06-06T00:18:00Z

## Current Status
**Branch:** main  |  **Tags:** v0.1.0, v0.1.1, v0.1.2

PENDING: 1 | IN_PROGRESS: 0 | COMPLETED: 3 | DECOMPOSED: 0 | ABORTED: 0 | DEFERRED: 0

> **WP-ST-3 COMPLETED|SUCCESS 2026-06-05** — Real-source corpus crawl v0.1.2.
> 6 unit-works delivered autonomously. 127 fast tests + 3 smoke tests
> = 130 total green. Corpus 12 → 34 drawings (synthetic + Wikimedia).
> 100% pipeline success on all 32 ingestable drawings. v0.1.2 git tag.
> All three WPs awaiting `/archive-work`.

### Active (IN_PROGRESS) — units remaining
(none)

### Awaiting /archive-work (COMPLETED|SUCCESS, work-plan/ → archive/ pending)

| WP | Title | task_id | Units | Notes |
|----|-------|---------|-------|-------|
| WP-ST-1 | CAD Trust Engine Lite v0.1 — 포비콘 application MVP | f3203e2e | 9 | tag v0.1.0; 53/53 tests; 1 retry (U6 empty-text filter); 9 commits |
| WP-ST-2 | CAD Trust Engine Audit Subsystem v0.1.1 — SQLite audit/logging | 09750a81 | 6 | tag v0.1.1; 91/91 tests (53 backward-compat + 38 audit); 0 retries; 6 commits |
| WP-ST-3 | Crawl real public-source CAD/floor plan drawings — v0.1.2 corpus expansion | f6316037 | 6 | tag v0.1.2; 130 tests (127 fast + 3 smoke); 1 retry (U2 relative_to fallback); 6 commits; corpus 12→34 drawings; 100% pipeline success on 32 real+synthetic |

### PENDING (not started)

| WP | Title | task_id | Units | Avg Clarity |
|----|-------|---------|-------|-------------|
| WP-ST-4 | v0.1.3 — 'pd' license fix + re-crawl + Streamlit preview pane | 4dd5c03b | 4 | 84% |

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
| WP-ST-3 | 2026-06-05 | Real-source corpus crawl v0.1.2 — 6 units: U1 Wikimedia API client + license mapping (No_Source_Bluff), U2 download + sha256 + provenance refusal log, U3 live crawl (22 real drawings + 27 license-refused), U4 corpus validation tests + license whitelist, U5 pipeline smoke (32/32 = 100% success, refusal counts 0-931), U6 docs + tag. Corpus 12 → 34. JPG ingest added. | SUCCESS |
| WP-ST-2 | 2026-06-05 | Audit Subsystem v0.1.1 — 6 units: SQLite schema (PRAGMA user_version=1) + AuditContext + 5-stage instrumentation (backward-compat) + CLI + Streamlit Past Runs tab + docs/AUDIT.md. 91/91 tests. | SUCCESS |
| WP-ST-1 | 2026-06-05 | CAD Trust Engine Lite v0.1 — 9 units autonomous build: bootstrap → output contract → corpus → ingest → geometry → ocr → symbols → compose+aggregate → UI+docs+pitch. 53/53 tests. v0.1.0 tag. | SUCCESS |

---

## Archive Summary
**Archived:** 0
**Awaiting /archive-work:** 3 (WP-ST-1 + WP-ST-2 + WP-ST-3)
**Remaining in work-plan/:** 3 files

---

## Pending Decisions
- v0.2 scope sequencing — David picks priority among: VLM_Verify (Qwen-VL re-checker, especially valuable now that we see high refusal counts on real drawings) / Synthetic KR generator enrichment / FloorPlanCAD or ArchCAD-400K (registration-gated) / DWG ingest / Real-time audit streaming / Multi-tenant DB
- Whether to `/archive-work` all three WPs at once or sequentially

---

## Known Issues
- ⊥ 2 SVG drawings (wm_2689-atlantic-print.svg, wm_ah_r_k_k_plan.svg) cannot be ingested — SVG support would require cairosvg/wand (new dep); v0.1.2 documents as unsupported
- ⊥ Some real drawings produce 20,000+ "objects" (mostly noise lines in non-CAD content like watercolours) — high coverage refusal rate makes them safe demo-wise but they slow the pipeline substantially (one drawing took 116s)
- ⊬ "pd" raw license tag in Wikimedia metadata didn't match my "pd-" prefix → 27 candidates refused. License mapping table could be extended to handle plain "pd" in a future patch (would lift many public-domain candidates)
- ⊥ Visual Streamlit UI verification still deferred — process running on 8501 but interactive Past Runs tab drill-down not browser-tested in autonomous session
- ⊬ Audit DB grows unbounded — no retention/rotation policy in v0.1.x; deferred to v0.3

---

*Initialized: 2026-06-05T13:01:56Z via /init-session*
*Updated: 2026-06-05T14:18:00Z — WP-ST-1 COMPLETED|SUCCESS, v0.1.0, 53 tests*
*Updated: 2026-06-05T14:46:00Z — WP-ST-2 COMPLETED|SUCCESS, v0.1.1, 91 tests*
*Updated: 2026-06-06T00:18:00Z — WP-ST-3 COMPLETED|SUCCESS, v0.1.2, 130 tests (127 fast + 3 smoke). Corpus grew from 12 synthetic to 34 (12 synthetic + 22 real Wikimedia). 100% pipeline success on all 32 ingestable drawings. Counters: PENDING 1→0, COMPLETED 2→3.*
