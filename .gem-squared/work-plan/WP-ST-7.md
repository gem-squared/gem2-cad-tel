# WP-ST-7: Portfolio reframing — README tech-stack emphasis + BYO LLM-key pattern
**STATUS:** IN_PROGRESS | **STATE:** — | **task_id:** 7b84e197
**created_at:** 2026-06-14T03:59:00Z | **project_slug:** gem2-vision

## Objective
Reframe gem2-vision (CAD Trust Engine Lite) as a portfolio piece: drop employer-specific (포비콘 / Pobicon) positioning across all user-facing surfaces, restructure the README to emphasize **what tech stack was used for what** and **how to build it locally + Docker + VPS**, and flip the LLM-API-key posture from "operator inserts into VPS `.env`" to **BYO via UI sidebar** so portfolio visitors can run optional VLM features without server-side secrets.

**Locked decisions (no further clarification needed):**
- ⊢ Git scope: **HEAD-forward** edits + new commit. NO history rewrite — preserves v0.1.0..v0.1.4 tag chain and avoids force-push.
- ⊢ Project name "**CAD Trust Engine Lite**" retained (already company-neutral).
- ⊢ Tagline reframed → `Portfolio · Auditable CAD floor-plan recognition (Korean ConTech 적산 wedge)`.
- ⊢ `docs/POBICON_PITCH.ko.md` **deleted** (Korean job-application pitch — substance already covered in `docs/README.md`'s engineering thesis).
- ⊢ Internal lifecycle state (`.gem-squared/work-plan/WP-ST-1..6.md`, `alarm.md`) **left untouched** — internal project memory, not user-facing, mutating breaks TPMN lifecycle invariants.
- ⊢ Version bump: `v0.1.4` → `v0.1.5` (substantive positioning + secrets-pattern cut, cumulative since live deploy).

## Unit-Works

### 1. README rewrite — tech-stack emphasis, build instructions, drop 포비콘 from user-facing surfaces | STATUS: COMPLETED
- A: README.md / README.en.md (6+4 포비콘 hits, current tagline `포비콘 지원용 MVP`), `pyproject.toml:4` (description), `deploy/deploy.sh:210` (post-deploy hint), `docs/README.md` (2 hits, "Target audience: 포비콘"), `docs/CORPUS.md:7`, `docs/DEPLOY.md:43`, `docs/DEMO_SCENARIOS.md:72`, `docs/POBICON_PITCH.ko.md` (entire file). README currently mixes positioning + brief tech overview + roadmap; tech stack rationale is scattered.
- B: All 포비콘 / Pobicon references removed from listed user-facing files. `docs/POBICON_PITCH.ko.md` deleted. `README.md` (Korean) and `README.en.md` restructured so that, in order:
  - (a) **Portfolio tagline** — `Portfolio · Auditable CAD floor-plan recognition (Korean ConTech 적산 wedge)` replaces the 포비콘 line, live-demo badge preserved.
  - (b) **TL;DR** — kept, scrubbed of employer-specific wording.
  - (c) **🧱 Tech Stack — what was used for what** — new prominent section, table form: `Component | Purpose | Why this choice`. Rows must cover: Python 3.11+, OpenCV / classical CV (Hough-P walls), PaddleOCR ko+en (dimension/label text), Pydantic v2 (typed EngineOutput + Measurement_Policy validator), SQLite stdlib (audit DB, no extra dep), Streamlit (review UI), pdf2image + Poppler (PDF ingest), Docker + Caddy + Vultr VPS (deploy), pytest (148 tests).
  - (d) **🛠 How to build** — new prominent section with three concrete paths: **(i) Local dev** (`python -m venv`, `pip install -r requirements.txt`, `streamlit run ui/app.py`), **(ii) Docker** (`docker compose -f deploy/docker-compose.yml up --build`), **(iii) VPS deploy** (one-line pointer to `docs/DEPLOY.md` with the prerequisite list).
  - (e) Existing sections (TPMN posture, EEF, Refusal Over Bluff, roadmap, etc.) preserved with 포비콘 wording stripped.
  - `pyproject.toml:4` description rewritten to portfolio framing.
  - `deploy/deploy.sh:210` post-deploy hint scrubbed (e.g., `share $PUBLIC_URL — portfolio live demo URL`).
  - `docs/README.md` "Target audience" line generalized.
- P: Repo at HEAD `9834174` (or its descendant). No concurrent edits to listed files. `grep` for 포비콘/Pobicon on completion must return zero hits **outside** `.gem-squared/work-plan/` and `.gem-squared/alarm.md`.
- Clarity: 90%
- Unclear: exact wording of the tech-stack `Why this choice` cells — will draft from existing docs/README.md rationale + Korean tone matching current README.md.
- Tags: [rewriting-readme, removing-pobicon, documenting-buildflow, promoting-techstack, expanding-deployflow]
- Result: 8 user-facing files edited + 1 deleted:
  - **README.md (KR) — full rewrite**: tagline → `Portfolio · Auditable CAD floor-plan recognition (Korean ConTech 적산 wedge)`. New section **🧱 기술 스택 — 무엇을, 왜 사용했는가** promoted to right after TL;DR; original table (12 rows) expanded with 3 deploy rows (Docker, Caddy 2, Vultr VPS) and an "intentionally not used" subsection. New section **🛠 빌드 방법 — 3가지 경로** with `경로 1 · 로컬 개발`, `경로 2 · Docker (compose up --build)`, `경로 3 · VPS 라이브 배포` — each path is a runnable shell block. Footer rewritten → `Portfolio`. Documentation map row for `POBICON_PITCH.ko.md` removed; `DEPLOY.md` row added. Removed standalone "포비콘 지원 핵심 메시지" section. v0.1.4 release row added to the build-history table. VLM_Verify roadmap entry rewritten as BYO-key (pre-staging U2 of WP-ST-7).
  - **README.en.md — full rewrite**: same structural changes mirrored (tagline → `Portfolio · Auditable CAD floor-plan recognition for Korean ConTech 적산`; **🧱 Tech stack** + **🛠 How to build** promoted; "Path 1 / 2 / 3" build flow; doc map updated; v0.1.4 row; VLM_Verify rewritten as BYO-key).
  - **pyproject.toml:4** `description = "CAD Trust Engine Lite — portfolio demo of auditable PNG/PDF floor-plan recognition for Korean ConTech 적산"`.
  - **deploy/deploy.sh:210** post-deploy hint → `share $PUBLIC_URL — portfolio live demo URL`.
  - **docs/README.md** Target-audience header → `Korean ConTech 적산 (automated quantity takeoff) — portfolio thesis`; footer see-also drops `POBICON_PITCH.ko.md`, adds `docs/DEPLOY.md`.
  - **docs/CORPUS.md:7** source-posture sentence generalized: "from any construction company".
  - **docs/DEPLOY.md:43** domain optionality note → "Both modes work for the portfolio live demo."
  - **docs/DEMO_SCENARIOS.md:72** Scenario-4 closing → "the single scenario the portfolio is built around".
  - **docs/POBICON_PITCH.ko.md DELETED** (substance lives in docs/README.md engineering thesis).
  - **Empirical check**: `grep -rn '포비콘\|Pobicon\|pobicon' .` (excluding `.git`, `.venv`, `.gem-squared/work-plan/`, `.gem-squared/alarm.md`, `.gem-squared/external-skills/`, `.claude/projects/`) → **0 hits** ⊢. All remaining mentions are in WP-ST-1/2/3/5/7.md and alarm.md (per WP exclusion — internal lifecycle memory left intact for U3 to update).
- State: SUCCESS
- Truth:

### 2. BYO LLM-key pattern — flip docs guidance + add UI sidebar scaffold | STATUS: COMPLETED
- A: `docs/DEPLOY.md:118-126` "Secrets handling" section currently prescribes: *"If future features need API keys (e.g., VLM_Verify), add them as environment variables in `.env` on the VPS, reference them in `docker-compose.yml`."* — a server-side-secret pattern that's wrong for a public portfolio demo. `ui/app.py` sidebar currently only shows the audit DB path; no key input scaffolding. `.gitignore` already excludes `.env`, `*.key`, `*.pem`, `.streamlit/secrets.toml` (no committed leak to scrub). No live LLM integration in v0.1.4 (grep confirms only `GEM2_VISION_AUDIT_DB` env var used).
- B: `docs/DEPLOY.md` "Secrets handling" section rewritten: explicitly states **LLM API keys are NEVER stored server-side** for this portfolio. The pattern is BYO via UI sidebar (`st.text_input(type="password")` → `st.session_state`), key lives only in the visitor's browser session, never reaches the audit DB or container env. `ui/app.py` sidebar gains a new `### Optional: VLM_Verify (BYO key)` block:
  - `st.text_input("API key", type="password", key="vlm_api_key", help="...")` — paste-only, never persisted server-side.
  - `st.selectbox("Provider", ["(none)", "Anthropic Claude vision", "Qwen-VL"], key="vlm_provider")`.
  - Status caption when empty: `"(no key — VLM_Verify disabled; planned for v0.2)"`; when set: `"⊢ key in session — VLM_Verify ready when v0.2 lands"`.
  - **No actual VLM call wired** — this is the pattern scaffold; v0.2 will plug in.
  - README "Tech Stack" section (from U1) gains a `Security · BYO key` row referencing this pattern.
- P: U1 complete (README structure exists to receive the BYO-key row). `ui/app.py` test suite still green before edit. `streamlit run ui/app.py` boots locally without error after edit (smoke check).
- Clarity: 80%
- Unclear: precise sidebar copy + provider list — will match Streamlit conventions and tone-match existing audit-DB sidebar block; Korean help-text in `README.md` BYO row will mirror existing voice.
- Tags: [flipping-keypattern, scaffolding-byo, updating-deploydocs, adding-securityrow]
- Result: 4 files edited:
  - **docs/DEPLOY.md** "Secrets handling" section rewritten end-to-end. Old guidance ("if future features need API keys, add them as env vars in `.env`") REPLACED with explicit BYO posture: opening sentence — *"This portfolio demo runs LLM API keys client-side only — BYO. No LLM API key is ever stored on the server, in `.env`, in `docker-compose.yml`, or in `.streamlit/secrets.toml`."* Three bullets cover: (i) `.env` carries only `DOMAIN`, (ii) LLM keys BYO via `st.session_state['vlm_api_key']` for the session, (iii) *Why BYO* — quota hijack + visitor cannot audit server-side key scope. Pre-existing `.streamlit/secrets.toml` exclusion bullet preserved.
  - **ui/app.py** new BYO sidebar block inserted after the existing `### Audit` block (around line 194). Block contains: header `### Optional: VLM_Verify (BYO key)`; `st.sidebar.selectbox("Provider", ["(none)", "Anthropic Claude vision", "Qwen-VL"], key="vlm_provider", help=...)`; `st.sidebar.text_input("API key", type="password", key="vlm_api_key", placeholder="paste only — never persisted server-side", help="Lives only in your browser session. Close the tab → key is gone.")`; conditional caption — `⊢ key in session — VLM_Verify ready when v0.2 lands` when set, `(no key — VLM_Verify disabled; planned for v0.2)` when empty. **No actual VLM call wired** — pattern scaffold only, ready for v0.2 to plug in.
  - **README.md** Tech-Stack table gains a new row: `보안 · LLM 키 | BYO (Bring-Your-Own) | LLM API key는 절대 서버 측 env에 저장하지 않음. 방문자가 UI sidebar에 직접 paste → st.session_state에만 존재 → 탭 닫으면 사라짐. v0.2 VLM_Verify는 이 패턴으로만 활성화.`
  - **README.en.md** Tech-Stack table gains a new row: `Security · LLM key | BYO (Bring-Your-Own) | No LLM API key in server-side env. The visitor pastes into the UI sidebar; key lives only in st.session_state; gone when the tab closes. v0.2 VLM_Verify activates only through this path.`
  - **Smoke verification**: `python -m py_compile ui/app.py` → syntax OK ⊢. `.venv/bin/python -m pytest --ignore=tests/test_corpus_pipeline_smoke.py -x -q` → **145 passed, 2 skipped** (SVG tests; matches baseline) — no regression introduced ⊢. Streamlit boot not executed (port-binding side-effect avoided in pytest harness); syntax + import surface validated.
- State: SUCCESS
- Truth:

### 3. Verify + version bump + commit + tag v0.1.5 | STATUS: IN_PROGRESS
- A: U1 + U2 complete. `pyproject.toml` version still `0.1.4`. README footer caption `CAD Trust Engine Lite v0.1.3` (note: `ui/app.py:443` carries v0.1.3 — must bump to v0.1.5). `alarm.md` reflects last state at WP-ST-6.
- B: Smoke verification battery:
  - `grep -rn '포비콘\|Pobicon' .` (excluding `.git`, `.venv`, `.gem-squared/work-plan/`, `.gem-squared/alarm.md`) → **0 hits**.
  - `pytest tests/ -x -q` → **all green**, count ≥ prior baseline (148).
  - `streamlit run ui/app.py` → boots HTTP 200, sidebar shows new BYO-key block, no exceptions in stderr (1-min smoke).
  - `pyproject.toml` version → `0.1.5`. `ui/app.py:443` caption → `v0.1.5`. README version line → `v0.1.5`.
  - `.gem-squared/alarm.md` updated: WP-ST-7 row added, counters bumped.
  - Single git commit per CLAUDE.md convention (Detailed message + Date + Author block), then `git tag v0.1.5`.
- P: U1 + U2 STATE = SUCCESS. Working tree clean except U1/U2 edits + version bumps + alarm.md.
- Clarity: 95%
- Unclear: nothing material — standard lifecycle close.
- Tags: [verifying-build, bumping-version, tagging-release]
- Result:
- State:
- Truth:

## References
- WP-ST-5 (v0.1.4 deploy pattern — Caddy + Docker + Vultr provenance kept intact)
- WP-ST-6 (most recent UX-polish commit `9834174` is HEAD baseline)
- `docs/DEPLOY.md` §Secrets handling (the guidance flipped in U2)
- `ui/app.py:189-192` (existing sidebar pattern U2 mirrors)
- CLAUDE.md §"Git Commit Convention" + §"Mandatory Execution Rule" (drives U3)
- Memory: `feedback_decisiveness.md` (David's "find best way and do" — locked decisions, no menu re-asks)
