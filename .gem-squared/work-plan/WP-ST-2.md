# WP-ST-2: CAD Trust Engine Audit Subsystem v0.1.1 — SQLite-backed audit/logging for all critical pipeline paths
**STATUS:** IN_PROGRESS | **STATE:** — | **task_id:** 09750a81
**created_at:** 2026-06-05T14:22:56Z | **project_slug:** gem2-vision
**parent_context:** WP-ST-1 v0.1.0 COMPLETED|SUCCESS at HEAD (53 tests passing) — this WP extends the engine WITHOUT modifying its EngineOutput contract

## Objective
Add a dedicated SQLite-backed audit subsystem to the CAD Trust Engine so every critical pass — pipeline runs, stage entry/exit, scale-anchor verdicts, refusals emitted, Measurement_Policy fires, epistemic-tag distributions, errors — is traceable, debuggable, and historically queryable. The audit DB extends WP-ST-1's per-run Refusal_Over_Bluff invariant ACROSS TIME: refusal patterns become queryable across the corpus, not just visible per drawing. This is the auditability story we promised 포비콘. All work happens via stdlib `sqlite3` (no new external dep) under a strict backward-compatibility invariant — the existing 53 WP-ST-1 tests MUST still pass after instrumentation; audit is opt-in via an optional parameter on `pipeline.run()`.

## WP-Level Invariants

```
WP_Invariants ≜ [

  ⊢ Backward_Compatibility:
      Existing 53 WP-ST-1 tests MUST still pass after every unit in this WP.
      Audit is opt-in via an OPTIONAL parameter (audit_db_path=None default).
      EngineOutput contract from WP-ST-1 / U2 schema is UNCHANGED.

  ⊢ No_Silent_Audit_Failures:
      If an audit insert raises, log the error visibly (stderr or warnings),
      DO NOT swallow it, but ALSO do not abort the pipeline — engine output
      delivery is independent of audit success.

  ⊢ Refusal_Over_Bluff_Across_Time:
      refusals_log table is THE first-class extension of WP-ST-1's refusals
      contract. Every refusal_candidate from U7 + every promoted Refusal
      from U8 must be recorded with run_id linkage so cross-corpus queries
      work ("which attempted_types refuse most on kr-domain drawings?").

  ⊢ Schema_Versioned:
      PRAGMA user_version = 1 in v0.1. Migration runner is idempotent —
      applying twice is a no-op. Future schemas check user_version + migrate.

  ⊢ ISO8601_UTC_Datetimes:
      Every datetime column stored as ISO8601 UTC text — sqlite-friendly,
      timezone-explicit, human-readable in CLI dumps.

  ⊢ Stdlib_Only:
      sqlite3 + argparse + json + datetime — no new external dependency.
      Pydantic (already a dep) used for row-type validation.
]
```

## Unit-Works

### 1. Audit DB schema + idempotent migration runner | STATUS: COMPLETED
- A: { db_path: Path, schema_version_target: 1 }
- B: { sqlite_file_created_or_present: ⊤, schema_meta_table_present: ⊤, PRAGMA_user_version=1, tables_created: [runs, stage_events, epistemic_counts, refusals_log, policy_fires, schema_meta], indices_created: [idx_stage_events_run_id, idx_refusals_run_id, idx_policy_fires_run_id, idx_runs_drawing_id], migration_idempotent: ⊤ }
- P: Python 3.11+; project_dir writable
- Clarity: 95%
- Unclear: whether to put schema as inline SQL constants in audit.py or external `schema.sql` (recommend inline — single-file module, no path resolution issues)
- Acceptance:
  - First call to `init_audit_db(path)` creates file + applies schema + sets PRAGMA user_version = 1
  - Second call to `init_audit_db(path)` is a no-op (idempotent migration)
  - All 6 tables present after init (verified via `SELECT name FROM sqlite_master`)
  - `PRAGMA user_version` returns 1
  - All datetime columns declared TEXT (not INTEGER/REAL)
  - `pytest tests/test_audit_schema.py` covers fresh-create, re-open, table presence, version check
- Tags: [defining-schema, migrating-sqlite, anchoring-version, indexing-fks]
- Result: src/cad_trust/audit_schema.py defines schema v1 via stdlib sqlite3. 6 tables (runs / stage_events / epistemic_counts / refusals_log / policy_fires / schema_meta) + 5 indices (idx_stage_events_run_id, idx_refusals_run_id, idx_policy_fires_run_id, idx_runs_drawing_id, idx_refusals_attempted_type). PRAGMA user_version = 1 gates migrations. init_audit_db(path) is idempotent: returns immediately when user_version == SCHEMA_VERSION; refuses downgrade when user_version > SCHEMA_VERSION; auto-creates parent dirs; supports `:memory:` path. All datetime columns declared TEXT (ISO8601 UTC). schema_meta table records 'schema_version' → '1'. pytest tests/test_audit_schema.py 8/8 PASSED in 0.04s.
- State: SUCCESS
- Truth:

### 2. AuditContext API + connection management | STATUS: COMPLETED
- A: { db_path: Path, drawing_id: 𝕊 }
- B: AuditContext context manager that:
  - on `__enter__`: opens connection, inserts row in `runs` with run_id (uuid4) + drawing_id + started_at + exit_state="in_progress", returns self,
  - exposes methods: emit_stage_event(stage, level, message, payload), record_policy_fire(policy_name, detail), record_refusal(region, attempted_type, why), record_epistemic_count(stage, tag, field, count), record_error(error_msg),
  - on `__exit__`: updates the runs row with completed_at + duration_ms + exit_state (SUCCESS if no exception; FAILURE if exception; records error_msg from exc),
  - on any insert error: emits warnings.warn(...) + continues (No_Silent_Audit_Failures invariant),
  - exposes run_id property for downstream linkage
- P: U1 complete (schema + migration available)
- Clarity: 90%
- Unclear: whether to use sqlite3.Connection.row_factory=Row by default (recommend ⊤ — makes CLI/Streamlit queries cleaner)
- Acceptance:
  - `with audit_run(db_path, "test_drawing") as ctx:` creates a runs row visible via SELECT
  - After context exits successfully → runs row has completed_at + duration_ms > 0 + exit_state="SUCCESS"
  - After context exits via exception → exit_state="FAILURE" + error_msg populated + exception re-raised
  - emit_stage_event records a stage_events row matching input args
  - record_refusal records a refusals_log row with region serialized as JSON
  - record_policy_fire records a policy_fires row with detail serialized as JSON
  - record_epistemic_count UPSERTs (run_id, stage, tag, field) composite key
  - When sqlite3 raises mid-method, warnings.warn fires and method returns without re-raising
  - `pytest tests/test_audit_context.py` covers all 6 cases above
- Tags: [contextmanaging-audit, emitting-events, recording-trust-trail, failure-softing-warnings]
- Result: src/cad_trust/audit.py defines AuditContext class + audit_run() factory. Lifecycle: __enter__ calls init_audit_db (idempotent) + opens connection with row_factory=Row + inserts runs row with exit_state='in_progress'. __exit__ updates the row with completed_at + duration_ms (perf_counter-based) + exit_state ('SUCCESS' iff exc_type is None else 'FAILURE') + error_msg ('{ExcName}: {message}' on failure). Five emission methods all share the failure-soft pattern — sqlite3.Error → warnings.warn + continue, NEVER abort. record_epistemic_count does UPSERT via ON CONFLICT DO UPDATE on (run_id, stage, tag, field) composite key. _now_iso() produces ISO8601 UTC text. _json_dumps falls back to repr() if json.dumps raises. main() is a U4 stub. pytest tests/test_audit_context.py 9/9 PASSED in 0.06s: runs row lifecycle (insert + clean exit + exception exit + reraise), all 4 emission methods (stage_event / refusal / policy_fire / epistemic_count UPSERT), emit-after-exit warns, forced-closed connection mid-context warns (failure-soft proof).
- State: SUCCESS
- Truth:

### 3. Pipeline + stage instrumentation (backward-compatible) | STATUS: COMPLETED
- A: { existing pipeline.py + ingest/geometry/ocr/symbols/compose modules from WP-ST-1, AuditContext from U2 }
- B: {
    pipeline.run signature changed to `run(drawing_path, dpi_target=200, audit_db_path=None)` — backward compatible,
    when audit_db_path is None → pipeline runs identically to v0.1.0 (no audit overhead, no schema change),
    when audit_db_path is set → AuditContext opened, each stage emits stage_event (entry "starting" level=INFO + exit "complete" level=INFO with count payload),
    compose stage additionally:
      - records every U7 refusal_candidate via record_refusal,
      - records every promoted top-level Refusal via record_refusal,
      - records Measurement_Policy fire when scale_anchor.detected = False (record_policy_fire),
      - records epistemic_count rollups per stage and per field (record_epistemic_count),
    IngestError caught → record_error, exit_state=FAILURE, re-raised,
    EngineOutput shape UNCHANGED (no new fields)
  }
- P: U1 + U2 complete (schema + AuditContext available); existing 53 tests are the baseline that must remain green
- Clarity: 75%
- Unclear: cleanest API for stage instrumentation — option A: each stage accepts optional `audit: AuditContext | None` param + checks inside; option B: pipeline wraps each stage call with try/audit emit. Recommend A (each stage explicit about what it emits, evidence chain stays grouped per stage)
- Acceptance:
  - `pipeline.run(path)` (no audit_db_path) produces identical EngineOutput as WP-ST-1 (regression: full existing 53 tests still pass)
  - `pipeline.run(path, audit_db_path=":memory:")` produces same EngineOutput + records run row + ≥5 stage_events (one per stage entry, one per stage exit at minimum)
  - When compose detects scale_anchor=False → policy_fires row recorded with policy_name="Measurement_Policy"
  - When compose emits any refusal → refusals_log row recorded per refusal
  - When pipeline raises IngestError on a bad file → exit_state="FAILURE" + error_msg populated, original exception re-raised
  - Audit emission failure (simulated by injecting a closed connection) emits warnings.warn but does NOT abort pipeline
  - `pytest tests/test_pipeline_audit.py` covers all 6 cases
  - **Critical**: full `pytest` suite (53 WP-ST-1 + new audit tests) all green
- Tags: [instrumenting-pipeline, threading-audit, preserving-backward-compat, recording-policy-fires, rolling-up-epistemic]
- Result: pipeline.run signature extended to `run(drawing_path, dpi_target=200, audit_db_path=None)`. When audit_db_path is None AND env var GEM2_VISION_AUDIT_DB unset → identical to v0.1.0 code path (zero overhead). When set → AuditContext opens, threads `audit=ctx` through ingest/geometry/ocr/symbols/compose. Each stage gained an optional `audit: AuditContext | None = None` param (TYPE_CHECKING import to avoid runtime cycle). Each stage emits "starting" event on entry + "complete" event on exit with counts payload (lines/contours/wall_candidates for geometry; doors/windows/spaces/refusal_candidates for symbols; etc.). compose stage emits scale_anchor verdict event, calls record_policy_fire("Measurement_Policy", ...) when scale_anchor.detected=False (with mm_fields_refused count), record_refusal per U7 refusal_candidate (region/attempted_type/why), and 4-tag × 3-field epistemic_count rollup. ingest catches IngestError → emits ERROR event → re-raises (audit observes, doesn't gate). **Backward_Compatibility invariant HELD**: full pytest 79/79 PASSED in 68.73s = 53 WP-ST-1 (regression GREEN) + 8 schema + 9 context + 9 audit-pipeline tests. 9 audit-pipeline tests cover: no-audit identical to v0.1.0, runs row recorded, per-stage starting+complete events, Measurement_Policy fires on no-scale (blank fixture exercises path), refusals_log promotion, epistemic_counts per field, IngestError → FAILURE exit_state + error_msg, shape-equal with/without audit.
- State: SUCCESS
- Truth:

### 4. CLI subcommands — list-runs / show-run / refusals / stats | STATUS: IN_PROGRESS
- A: { db_path resolution: env var GEM2_VISION_AUDIT_DB or default ".gem-squared/audit.sqlite" }
- B: {
    `python -m cad_trust.audit list-runs [--limit N] [--drawing-id X]` prints recent runs as table (run_id, drawing_id, started_at, duration_ms, exit_state),
    `python -m cad_trust.audit show-run <run_id>` prints all stage_events + refusals + policy_fires + epistemic_counts for that run,
    `python -m cad_trust.audit refusals [--drawing-id X] [--attempted-type Y]` prints refusal pattern across runs,
    `python -m cad_trust.audit stats` prints epistemic distribution roll-up: total runs, total objects, % by tag, top attempted_types for refusals,
    exit code 0 on success, 1 on error (db not found / bad SQL),
    `__main__.py` (or equivalent) routes argparse to dispatch
  }
- P: U1 + U2 complete (schema + queryable runs/events tables)
- Clarity: 90%
- Unclear: output format — JSON vs rich table vs tab-separated (recommend simple text tables via stdlib + JSON via --format flag in future v0.1.2)
- Acceptance:
  - `python -m cad_trust.audit list-runs` exits 0 with at least header line printed even on empty DB
  - `python -m cad_trust.audit list-runs --limit 5` returns at most 5 rows
  - `python -m cad_trust.audit show-run <valid_run_id>` prints stage_events + refusals + policy_fires sections
  - `python -m cad_trust.audit show-run <bad_id>` exits 1 with informative stderr
  - `python -m cad_trust.audit refusals` aggregates refusal counts by attempted_type
  - `python -m cad_trust.audit stats` shows tag distribution percentages
  - `pytest tests/test_audit_cli.py` covers all subcommands via subprocess invocation
- Tags: [building-cli, querying-audit, dispatching-argparse]
- Result:
- State:
- Truth:

### 5. Streamlit "Past Runs" tab | STATUS: PENDING
- A: { existing ui/app.py + audit DB possibly populated from prior runs }
- B: {
    ui/app.py refactored to use `st.tabs(["Run Engine", "Past Runs"])`,
    Past Runs tab:
      - List of recent runs (sortable: drawing_id, started_at, duration_ms, exit_state),
      - Selecting a run shows: stage_events timeline + refusals list + policy_fires + epistemic distribution chart,
      - Aggregate section at top: refusal pattern across corpus (bar chart of count by attempted_type via st.bar_chart) + overall tag distribution,
    Run Engine tab now also writes to audit DB by default (audit_db_path resolved from env or default .gem-squared/audit.sqlite),
    handles empty-DB case gracefully (info message, no crash)
  }
- P: U1 + U2 + U3 complete (audit data exists or DB is empty-but-valid)
- Clarity: 80%
- Unclear: chart library choice (Streamlit native st.bar_chart vs altair — recommend native for zero extra dep); whether to paginate runs list (recommend simple LIMIT 50 with refresh button)
- Acceptance:
  - `streamlit run ui/app.py` launches with 2 tabs visible (Run Engine + Past Runs)
  - Past Runs tab on empty DB shows "no runs yet" info message, no exception
  - After running a drawing through Run Engine tab, a row appears in Past Runs
  - Selecting a run displays its stage_events + refusals
  - Streamlit smoke (process launches + HTTP 200) still passes
  - Aggregate refusal chart renders without error when ≥1 refusal exists
- Tags: [building-ui-tab, querying-past-runs, visualizing-refusal-patterns]
- Result:
- State:
- Truth:

### 6. Tests + docs + v0.1.1 git tag | STATUS: PENDING
- A: { U1-U5 complete; all new code committed; baseline 53 WP-ST-1 tests + new audit tests in tests/ }
- B: {
    final `pytest` run: ALL tests green (WP-ST-1's 53 + WP-ST-2's new audit tests),
    docs/AUDIT.md describing: audit posture (Refusal_Over_Bluff across time), schema overview, CLI usage examples, Streamlit Past Runs walkthrough, integration with existing pipeline.run,
    root README.md updated with audit subsystem mention + link to docs/AUDIT.md,
    .gitignore updated to exclude `.gem-squared/audit.sqlite*` (mutable runtime state, not tracked),
    git tag v0.1.1 created with WP-ST-2 completion message
  }
- P: U1-U5 all COMPLETED|SUCCESS
- Clarity: 90%
- Unclear: whether docs/AUDIT.md should include example SELECT queries readers can paste (recommend ⊤ — concrete > abstract)
- Acceptance:
  - `pytest` exit 0 with sum of (53 + new audit tests) all PASSED, 0 FAILED
  - docs/AUDIT.md exists with sections: Posture, Schema, CLI, Streamlit, Example Queries
  - root README.md mentions audit subsystem + links docs/AUDIT.md
  - `.gem-squared/audit.sqlite` matches a `.gitignore` pattern (verify via `git check-ignore`)
  - `git tag v0.1.1` exists on main with completion message naming WP-ST-2 + unit count
  - `git log --oneline -1` shows the WP-finalization commit at HEAD
- Tags: [verifying-suite, writing-audit-docs, tagging-release]
- Result:
- State:
- Truth:

---

## References
- Parent: WP-ST-1 v0.1.0 (engine being instrumented) — `.gem-squared/work-plan/WP-ST-1.md`
- TPMN invariants preserved from WP-ST-1: per-field epistemic tags / refusals first-class / provenance visible / no silent measurement aggregation
- NEW invariants added in this WP: Backward_Compatibility / No_Silent_Audit_Failures / Refusal_Over_Bluff_Across_Time / Schema_Versioned / ISO8601_UTC_Datetimes / Stdlib_Only
- Deferred to v0.1.2+: real-time streaming dashboard, Prometheus/external metric export, multi-tenant DB separation, audit log retention/rotation, replay tool (re-run pipeline from audit trail)
- Architectural source: 3-way alignment session (this autonomous chain) — audit as the temporal extension of WP-ST-1's per-run refusal trail
