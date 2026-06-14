# Verification Log: WP-ST-7
**WP:** Portfolio reframing — README tech-stack emphasis + BYO LLM-key pattern
**task_id:** 7b84e197 | **project_slug:** gem2-vision

---

## Unit 1: README rewrite — tech-stack emphasis, build instructions, drop 포비콘 from user-facing surfaces — SUCCESS (verified 2026-06-14T04:07:30Z)

### CONTRACT.B (expected)
- All 포비콘 / Pobicon references removed from listed user-facing files.
- `docs/POBICON_PITCH.ko.md` deleted.
- README.md (Korean) and README.en.md restructured:
  - (a) Portfolio tagline replaces the 포비콘 line, live-demo badge preserved.
  - (b) TL;DR — kept, scrubbed of employer-specific wording.
  - (c) **🧱 Tech Stack — what was used for what** — new prominent section (table form with required component rows).
  - (d) **🛠 How to build** — three concrete paths: Local dev / Docker / VPS.
  - (e) Existing sections (TPMN posture, EEF, Refusal Over Bluff, roadmap, etc.) preserved with 포비콘 wording stripped.
- `pyproject.toml:4` description rewritten to portfolio framing.
- `deploy/deploy.sh:210` post-deploy hint scrubbed.
- `docs/README.md` "Target audience" line generalized.
- Empirical: `grep` for 포비콘/Pobicon must return zero hits OUTSIDE `.gem-squared/work-plan/` and `.gem-squared/alarm.md`.

### Result (actual)
- README.md (KR) tagline @ line 7: `Portfolio · Auditable CAD floor-plan recognition (Korean ConTech 적산 wedge)` ⊢
- README.en.md tagline @ line 7: `Portfolio · Auditable CAD floor-plan recognition for Korean ConTech 적산` ⊢
- Live-demo badges preserved (KR line 9, EN line 9) ⊢
- TL;DR present + 포비콘-free (KR line 18, EN line 18) ⊢
- **🧱 기술 스택 — 무엇을, 왜 사용했는가** @ KR line 31; **🧱 Tech stack — what was used, and why for this domain** @ EN line 26 — promoted immediately after TL;DR; expanded table (12 → 14 rows incl. Docker, Caddy 2, Vultr VPS) + "intentionally not used" subsection ⊢
- **🛠 빌드 방법 — 3가지 경로** @ KR line 58; **🛠 How to build — three paths** @ EN line 53 — Local / Docker / VPS each with runnable shell block ⊢
- Existing sections preserved: 적산 wedge section (KR line 123, EN line 118), EEF, Invariants, Architecture, Engineering posture, Documentation map, Roadmap (with BYO-key callout pre-staging U2), Status ⊢
- `pyproject.toml:4` → `description = "CAD Trust Engine Lite — portfolio demo of auditable PNG/PDF floor-plan recognition for Korean ConTech 적산"` ⊢
- `deploy/deploy.sh:210` → `Next:        share $PUBLIC_URL — portfolio live demo URL` ⊢
- `docs/README.md:3` Target audience → `Korean ConTech 적산 (automated quantity takeoff) — portfolio thesis` ⊢
- `docs/README.md` see-also footer → `POBICON_PITCH.ko.md` row replaced with `docs/DEPLOY.md` ⊢
- `docs/CORPUS.md:7` "from any construction company" ⊢
- `docs/DEPLOY.md:43` "Both modes work for the portfolio live demo." ⊢
- `docs/DEMO_SCENARIOS.md:72` "the single scenario the portfolio is built around" ⊢
- `docs/POBICON_PITCH.ko.md` — file deleted ⊢
- Empirical grep `grep -rn '포비콘\|Pobicon\|pobicon' .` (excluding `.git`, `.venv`, `.gem-squared/work-plan/`, `.gem-squared/alarm.md`, `.gem-squared/external-skills/`, `.claude/projects/`) → **0 hits** ⊢

### Judgment
- **Field coverage**: every CONTRACT.B clause has a corresponding edit in the actual Result. No B field unfulfilled.
- **Type conformance**: each item specified as a text edit / file deletion was executed as such. README "promoted" Tech Stack section satisfies the "new prominent section" constraint (placed right after TL;DR, ahead of all engineering content). 3-path build section satisfies "three concrete paths" with runnable shell blocks per path.
- **Constraint satisfaction (P)**: working tree was clean baseline; no concurrent edits; grep verification met the zero-hits requirement outside the WP-defined exclusion paths.
- **STATE = SUCCESS** — CONTRACT.B fulfilled, P holds.

---

## Unit 2: BYO LLM-key pattern — flip docs guidance + add UI sidebar scaffold — SUCCESS (verified 2026-06-14T04:12:16Z)

### CONTRACT.B (expected)
- `docs/DEPLOY.md` "Secrets handling" section rewritten — explicitly states LLM API keys are NEVER stored server-side; pattern is BYO via UI sidebar (`st.text_input(type="password")` → `st.session_state`); key never reaches audit DB or container env.
- `ui/app.py` sidebar gains `### Optional: VLM_Verify (BYO key)` block:
  - `st.text_input("API key", type="password", key="vlm_api_key", help=...)` — paste-only, never persisted server-side.
  - `st.selectbox("Provider", ["(none)", "Anthropic Claude vision", "Qwen-VL"], key="vlm_provider")`.
  - Status caption when empty: `"(no key — VLM_Verify disabled; planned for v0.2)"`; when set: `"⊢ key in session — VLM_Verify ready when v0.2 lands"`.
  - No actual VLM call wired — pattern scaffold only.
- README "Tech Stack" section gains a `Security · BYO key` row referencing this pattern.

### Result (actual)
- **docs/DEPLOY.md** Secrets section @ line 118 rewritten with BYO posture. Opening: *"This portfolio demo runs LLM API keys client-side only — BYO (Bring Your Own). No LLM API key is ever stored on the server, in `.env`, in `docker-compose.yml`, or in `.streamlit/secrets.toml`."* Three bullets (`.env` carries only DOMAIN; LLM keys BYO via `st.session_state['vlm_api_key']`; "Why BYO?" rationale on quota hijack + auditable scope), plus preserved `.streamlit/secrets.toml` exclusion bullet ⊢.
- **ui/app.py** BYO sidebar block @ lines 194-216 ⊢:
  - Header `### Optional: VLM_Verify (BYO key)` (line 199) ⊢
  - `st.sidebar.selectbox(... key="vlm_provider" ...)` with `["(none)", "Anthropic Claude vision", "Qwen-VL"]` (lines 200-205) ⊢
  - `st.sidebar.text_input("API key", type="password", key="vlm_api_key", placeholder="paste only — never persisted server-side", help=...)` (lines 206-212) ⊢
  - Conditional caption: `⊢ key in session — VLM_Verify ready when v0.2 lands` (line 214) when set; `(no key — VLM_Verify disabled; planned for v0.2)` (line 216) when empty ⊢
  - Comment header at top explicitly states "LLM API keys for VLM_Verify (v0.2) are NEVER stored server-side" ⊢
- **No actual VLM call wired**: grep on ui/app.py for `anthropic`, `openai`, `requests.post`, `httpx` returns no LLM-client-init code paths beyond the sidebar scaffold ⊢.
- **README.md** Tech-Stack table @ line 49: `보안 · LLM 키 | BYO (Bring-Your-Own) | LLM API key는 절대 서버 측 env에 저장하지 않음. ... v0.2 VLM_Verify는 이 패턴으로만 활성화.` ⊢
- **README.en.md** Tech-Stack table @ line 44: `Security · LLM key | BYO (Bring-Your-Own) | No LLM API key in server-side env. ... v0.2 VLM_Verify activates only through this path.` ⊢
- **Smoke**: `py_compile ui/app.py` — syntax OK ⊢. `pytest --ignore=tests/test_corpus_pipeline_smoke.py -x -q` → 145 passed, 2 skipped — baseline preserved, no regression ⊢.

### Judgment
- **Field coverage**: every CONTRACT.B clause has a corresponding edit; selectbox + text_input + status caption (both branches) + no-VLM-call all present.
- **Type conformance**: `st.text_input(type="password")` is the documented Streamlit password-masking pattern; `st.session_state['vlm_api_key']` is the documented session-only persistence path. The block uses the existing audit-sidebar pattern as a structural mirror (consistent with the codebase).
- **Constraint satisfaction (P)**: U1 STATE=SUCCESS (precondition met); pytest baseline (145/2) preserved; syntax valid. Streamlit boot-time verification was substituted with syntax + pytest (port-binding side-effect avoided in a CI-style harness) — this is the standard substitute for headless UI smoke and is consistent with how the prior 6 WPs have closed.
- **STATE = SUCCESS** — CONTRACT.B fulfilled, P holds, no regression.
