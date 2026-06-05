# Audit Subsystem — gem2-vision v0.1.1

> **Refusal Over Bluff, remembered.**
> WP-ST-1 made refusals first-class outputs *per run*. WP-ST-2 makes them
> first-class *across time* via a dedicated SQLite audit trail.

---

## Posture

The CAD Trust Engine's wedge is auditability under cost risk. Every detection
already carries an evidence chain and a per-field epistemic tag. The audit DB
extends that posture in time: every pipeline run, every stage transition, every
refusal, every Measurement_Policy fire, and every epistemic-tag distribution
accumulates into a queryable trail.

Why this matters for 적산: when a reviewer asks "we used the engine for
30 drawings last week — which attempted detections did it refuse most often?",
the answer should be a SQL query, not a guess from memory.

---

## Schema (v1)

```
runs              one row per pipeline invocation
  run_id PK | drawing_id | started_at | completed_at | duration_ms
  exit_state ('in_progress' | 'SUCCESS' | 'FAILURE') | error_msg

stage_events      per-stage entry / exit / arbitrary
  event_id PK | run_id FK | stage | level | message | payload_json | timestamp

epistemic_counts  tag distribution rollups
  (run_id, stage, tag, field) composite key | count

refusals_log      every refusal_candidate + promoted refusal
  row_id PK | run_id FK | region_json | attempted_type | why | recorded_at

policy_fires      Measurement_Policy + future invariant fires
  row_id PK | run_id FK | policy_name | detail_json | timestamp

schema_meta       generic key/value
  key PK | value
```

All datetime columns store ISO8601 UTC text (e.g. `2026-06-05T14:00:00Z`) —
sqlite-friendly, timezone-explicit, human-readable in CLI dumps.

`PRAGMA user_version = 1` gates migrations. `init_audit_db(path)` is idempotent:
calling it twice on an already-initialized DB is a no-op.

---

## Using the audit subsystem

### From Python

```python
from cad_trust.pipeline import run

# Backward-compatible: no audit
output = run("data/samples/synth_apt_simple_01.png")

# With audit
output = run("data/samples/synth_apt_simple_01.png",
             audit_db_path=".gem-squared/audit.sqlite")
```

### Via env var

Export `GEM2_VISION_AUDIT_DB` and the pipeline + Streamlit UI will use that
path automatically:

```bash
export GEM2_VISION_AUDIT_DB="/path/to/my/audit.sqlite"
```

### Streamlit UI

`streamlit run ui/app.py` opens two tabs:

- **Run Engine** — runs the pipeline with audit-on by default; logs to the
  resolved DB path (shown in the sidebar).
- **Past Runs (Audit)** — 4 metric cards + aggregate refusal pattern bar
  chart + recent runs selectbox; drill into any run for events / refusals /
  policy fires / epistemic distribution.

---

## CLI

```bash
# List 20 most recent runs
python -m cad_trust.audit list-runs

# Filter by drawing
python -m cad_trust.audit list-runs --drawing-id synth_apt_simple_01 --limit 5

# Full detail for one run
python -m cad_trust.audit show-run <run_id>

# Aggregate refusal pattern
python -m cad_trust.audit refusals
python -m cad_trust.audit refusals --attempted-type door

# Overall stats (epistemic distribution rollup + top refusal targets)
python -m cad_trust.audit stats
```

`--db <path>` overrides DB resolution if needed; otherwise the same env var
→ default path chain applies.

---

## Example queries

The audit DB is just SQLite — you can query it directly.

```sql
-- Which drawings most frequently fire Measurement_Policy?
SELECT runs.drawing_id, COUNT(*) AS policy_fires
FROM policy_fires p JOIN runs ON p.run_id = runs.run_id
WHERE p.policy_name = 'Measurement_Policy'
GROUP BY runs.drawing_id
ORDER BY policy_fires DESC;

-- What's the engine's overall confidence distribution across all type_epistemic claims?
SELECT tag, SUM(count) AS total
FROM epistemic_counts
WHERE field = 'type_epistemic'
GROUP BY tag
ORDER BY tag;

-- All refusals on a specific drawing
SELECT r.attempted_type, r.why, r.recorded_at
FROM refusals_log r JOIN runs ON r.run_id = runs.run_id
WHERE runs.drawing_id = 'synth_apt_kr_balcony_01';

-- Slowest pipeline runs
SELECT drawing_id, duration_ms, exit_state
FROM runs
ORDER BY duration_ms DESC NULLS LAST
LIMIT 10;
```

---

## Invariants

| Invariant                          | Meaning                                                              |
|------------------------------------|----------------------------------------------------------------------|
| Backward_Compatibility             | Existing 53 WP-ST-1 tests still pass; audit is opt-in via param      |
| No_Silent_Audit_Failures           | sqlite errors → `warnings.warn` + continue; never abort the pipeline |
| Refusal_Over_Bluff_Across_Time     | `refusals_log` is the historical extension of WP-ST-1's refusals     |
| Schema_Versioned                   | `PRAGMA user_version = 1`; init is idempotent                        |
| ISO8601_UTC_Datetimes              | All timestamp columns are TEXT, ISO8601 UTC                          |
| Stdlib_Only                        | sqlite3 + argparse + json + datetime — no new external dep           |

---

## Limitations + roadmap

| Postponed                          | Lands in |
|------------------------------------|----------|
| Real-time streaming dashboard      | v0.2     |
| Prometheus / external metric export | v0.2    |
| Multi-tenant DB separation         | v0.2     |
| Retention / rotation policies      | v0.3     |
| Replay tool (re-run pipeline from audit trail) | v0.3 |

---

*See also: `docs/README.md` (engineering thesis), `docs/OUTPUT_CONTRACT.md`
(per-run schema), `docs/DEMO_SCENARIOS.md` (5 walkthroughs).*
