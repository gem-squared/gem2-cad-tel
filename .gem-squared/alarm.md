# ALARM — gem2-vision
## Last checked: 2026-06-14T04:12:16Z

## Current Status
**Branch:** main  |  **Tags:** v0.1.0, v0.1.1, v0.1.2, v0.1.3, v0.1.4, v0.1.5
**Live demo:** https://cad-tel.gemsquared.ai

PENDING: 0 | IN_PROGRESS: 0 | COMPLETED: 7 | DECOMPOSED: 0 | ABORTED: 0 | DEFERRED: 0

> **WP-ST-7 COMPLETED|SUCCESS 2026-06-14** — Portfolio reframing + BYO LLM-key pattern (v0.1.5).
> 3 unit-works: (U1) README tech-stack/build emphasis + 포비콘 wording stripped from all user-facing
> surfaces + `docs/POBICON_PITCH.ko.md` deleted; (U2) BYO LLM-key sidebar scaffold in `ui/app.py`
> + `docs/DEPLOY.md` secrets-section rewritten ("no LLM API key in server-side env"); (U3) version
> bump v0.1.4 → v0.1.5, single commit, `v0.1.5` tag. 145/145 fast tests still green.

### Active (IN_PROGRESS) — units remaining
(none)

### Awaiting /archive-work (COMPLETED|SUCCESS, work-plan/ → archive/ pending)

| WP | Title | task_id | Units | Notes |
|----|-------|---------|-------|-------|
| WP-ST-1 | CAD Trust Engine Lite v0.1 — 포비콘 application MVP | f3203e2e | 9 | v0.1.0; 53 tests; 1 retry; 9 commits |
| WP-ST-2 | Audit Subsystem v0.1.1 — SQLite audit/logging | 09750a81 | 6 | v0.1.1; 91 tests; 0 retries; 6 commits |
| WP-ST-3 | Crawl public-source CAD drawings — v0.1.2 corpus expansion | f6316037 | 6 | v0.1.2; 130 tests; 1 retry; 6 commits; corpus 12→34 |
| WP-ST-4 | v0.1.3 — pd license fix + re-crawl + Streamlit preview pane | 4dd5c03b | 4 | v0.1.3; 148 tests; 1 retry; 4 commits; corpus 34→50 |
| WP-ST-5 | v0.1.4 — Vultr VPS deployment (containerized Streamlit + Caddy reverse proxy) | 00d8cde5 | 6 | v0.1.4; 145 tests; 2 mid-flight fixes; 5 commits; **live at https://cad-tel.gemsquared.ai** |
| WP-ST-7 | v0.1.5 — Portfolio reframing + BYO LLM-key pattern | 7b84e197 | 3 | v0.1.5; 145 tests; 0 retries; 1 commit; 포비콘 wording removed, `docs/POBICON_PITCH.ko.md` deleted, BYO sidebar scaffold landed |

### PENDING (not started)
(none — WP-ST-6 shipped live 2026-06-08T00:51:54Z)

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
| WP-ST-7 | 2026-06-14 | v0.1.5 Portfolio reframing — 3 units: (U1) README tech-stack/build emphasis + 포비콘 wording stripped from all user-facing surfaces + `docs/POBICON_PITCH.ko.md` deleted; (U2) BYO LLM-key sidebar scaffold in `ui/app.py` + `docs/DEPLOY.md` secrets-section rewritten with explicit "no LLM API key in server-side env" posture; (U3) version bump v0.1.4 → v0.1.5, single commit + `v0.1.5` tag. | SUCCESS |
| WP-ST-5 | 2026-06-06 | Vultr VPS deployment v0.1.4 — 6 units: container artifacts (Dockerfile + compose + Caddyfile + .dockerignore), bootstrap.sh (Docker + ufw + 2GB swap, idempotent), deploy.sh (rsync + compose up + healthcheck + honest smoke), docs/DEPLOY.md, **live SSH deploy on Vultr 173.199.92.236** (Ubuntu 24.04; integrated with pre-existing host Caddy via vhost append), README badge + tag. Live URL: https://cad-tel.gemsquared.ai. | SUCCESS |
| WP-ST-4 | 2026-06-06 | v0.1.3 license fix + preview pane — 4 units. | SUCCESS |
| WP-ST-3 | 2026-06-05 | Real-source corpus crawl v0.1.2 — 6 units; +22 Wikimedia drawings. | SUCCESS |
| WP-ST-2 | 2026-06-05 | Audit Subsystem v0.1.1 — 6 units. | SUCCESS |
| WP-ST-1 | 2026-06-05 | CAD Trust Engine Lite v0.1.0 — 9 units. | SUCCESS |

---

## Archive Summary
**Archived:** 0
**Awaiting /archive-work:** 7 (WP-ST-1 + WP-ST-2 + WP-ST-3 + WP-ST-4 + WP-ST-5 + WP-ST-6 + WP-ST-7)
**Remaining in work-plan/:** 7 files

---

## Pending Decisions
- Whether to `/archive-work` all five WPs at once or sequentially
- v0.2 scope sequencing — WP-ST-6 Expert CV CrossCheck + Page Type guard is the recommended next move
- Whether to harden VPS deploy (disable root password auth on 173.199.92.236, add fail2ban, etc.)
- Whether to add a CI/CD GitHub Actions workflow that auto-deploys on push to main

---

## Known Issues
- ⊥ 2 SVG drawings cannot be ingested (SVG support would require cairosvg/wand new dep)
- ⊬ Some real drawings produce 20,000+ "objects" — high refusal counts make them safe but slow (~116s)
- ⊬ Audit DB grows unbounded — retention/rotation deferred to v0.3
- ⊬ deploy.sh smoke check still looks for "CAD Trust Engine" in HTML body but Streamlit renders title via JS → false-positive failure path. Worth tightening to check Streamlit health endpoint instead. Minor.
- ⊥ VPS root password was shared in conversation; David should rotate at convenience
- ⊥ Visual demo verification by David still pending — process is healthy + serves HTTP 200, interactive flow not browser-tested

---

*Initialized: 2026-06-05T13:01:56Z via /init-session*
*Updated: 2026-06-05T14:18:00Z — WP-ST-1 COMPLETED|SUCCESS, v0.1.0, 53 tests*
*Updated: 2026-06-05T14:46:00Z — WP-ST-2 COMPLETED|SUCCESS, v0.1.1, 91 tests*
*Updated: 2026-06-06T00:18:00Z — WP-ST-3 COMPLETED|SUCCESS, v0.1.2, 130 tests*
*Updated: 2026-06-06T00:35:00Z — WP-ST-4 COMPLETED|SUCCESS, v0.1.3, 148 tests (corpus 34→50)*
*Updated: 2026-06-06T01:50:00Z — WP-ST-5 COMPLETED|SUCCESS, v0.1.4, live at cad-tel.gemsquared.ai (Vultr VPS via host Caddy + Docker single-service compose). Counters: PENDING 1→0, COMPLETED 4→5.*
*Updated: 2026-06-14T04:12:16Z — WP-ST-7 COMPLETED|SUCCESS, v0.1.5, Portfolio reframing + BYO LLM-key pattern. 포비콘 wording stripped from user-facing surfaces, `docs/POBICON_PITCH.ko.md` deleted, BYO sidebar scaffold landed. Counters: COMPLETED 6→7. Tags: + v0.1.5.*
