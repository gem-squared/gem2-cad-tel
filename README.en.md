[한국어](README.md) · **English**

---

# CAD Trust Engine Lite

**v0.1.3** · MVP for [포비콘](https://www.pobicon.com) application · Python 3.11+ · MIT-equivalent (proprietary source, public-licensed corpus)

> A detector gives answers.
> A **CAD Trust Engine** gives **answers, evidence, uncertainty, refusal, and review path** — and remembers them.

PNG/PDF/JPG architectural floor plan → **per-field EEF-tagged JSON** + Streamlit review UI + SQLite audit trail.

---

## TL;DR

This is not "another OpenCV pipeline." It's a small, working **trust engine** for CAD drawing recognition under cost risk. The wedge is not detection accuracy — it's **auditable measurement that knows what it doesn't know**.

Built end-to-end in 4 autonomous WP cycles (26 commits, 4 tagged releases, 148 tests, 50-drawing corpus). Every detection carries three orthogonal epistemic claims (type / geometry / measurement), explicit refusal regions for uncommittable areas, and a full audit trail of every run / refusal / policy fire / epistemic distribution.

---

## Why this approach is different for 적산 (quantity takeoff)

CAD drawing recognition for construction is **not an object-detection problem**. It is an **auditable measurement problem under cost risk**.

A misrecognized wall means a wrong material order — millions of KRW. The cost system cannot detect a confidently-wrong measurement until the construction phase. So the engine's primary deliverable is not "detections" — it is a **per-claim trust surface** that lets a reviewer query:

- *what* was detected,
- *why* the engine thinks so (evidence chain),
- *how confident* it is per field (type / geometry / measurement separately),
- *what it refused to commit on* (with the reason),
- and the *historical pattern* of those refusals across the whole corpus.

That is the auditability story 포비콘 needs to plug recognition results into a 산출내역서 system.

For a Korean application pitch, see [`docs/POBICON_PITCH.ko.md`](docs/POBICON_PITCH.ko.md).

---

## EEF — Epistemic Evaluation Framework

Every important claim the engine makes carries one of four tags. The tags are not confidence scores — they are **kinds of knowledge**.

| Tag | Name | When to use | Mandatory field |
|:---:|------|-------------|-----------------|
| ⊢ | **GROUNDED** | direct evidence (OCR hit, exact geometry match) | `evidence` |
| ⊨ | **INFERRED** | derived from ⊢ claims with a visible chain | `evidence`, `derivation_chain` (optional) |
| ⊬ | **EXTRAPOLATED** | beyond evidence — could be wrong | `evidence` + **`basis`** (REQUIRED) |
| ⊥ | **UNKNOWN** | knowledge gap, stops the inference chain | **`gap`** (REQUIRED) |

`⊬` and `⊥` are **structurally enforced** by the Pydantic schema validator. The contract refuses to accept an extrapolation without a stated `basis`, and refuses to accept an unknown without a stated `gap`. You cannot bluff at the schema layer.

### Per-field epistemic — three orthogonal claims per object

Every detected object carries **three independent epistemic marks**:

| Mark | Question it answers |
|------|---------------------|
| `type_epistemic` | Is this *really* a wall / door / window / ...? |
| `geometry_epistemic` | Is this the right *shape and extent*? |
| `measurement_epistemic` | Is the mm *measurement* reliable? |

The engine may be *confident this is a wall* (⊨), *confident of its pixel shape* (⊢), and *yet refuse to claim it is 4,200 mm long* (⊥). Conflating these collapses the trust surface — and that collapse is what makes black-box detectors unsafe for 적산 systems.

**Real example** from the audit DB:

```json
{
  "object_id": "obj_0042",
  "type": "wall_structural",
  "type_epistemic":        { "tag": "⊨", "evidence": [{"source":"opencv_line_pair","signal":"parallel pair gap=12px"}] },
  "geometry_epistemic":    { "tag": "⊨", "evidence": [{"source":"opencv_line_pair","signal":"endpoints from paired Hough"}] },
  "measurement_mm":        null,
  "measurement_epistemic": { "tag": "⊥", "gap": "no scale_anchor; mm refused per Measurement_Policy" },
  "review_status":         "needs_human"
}
```

---

## Load-bearing invariants

The engine refuses to violate these — they are validator-enforced at the schema layer.

### Measurement_Policy

> **Never emit `measurement_mm` unless `scale_anchor.detected = True`.**

When the engine cannot extract a reliable px-to-mm conversion factor (by matching detected dimension text against wall lengths), it refuses mm conversion across **all** objects AND aggregates. The `EngineOutput.model_validator` enforces this — it is impossible to construct an `EngineOutput` that violates the policy. A pixel length may appear in `evidence` as a diagnostic, but **never** as mm output.

### Refusal_Over_Bluff

When evidence is insufficient (fewer than 2 supporting signals), the engine emits a `refusal_candidate` rather than a low-confidence detection. These promote to top-level `refusals` in `EngineOutput`. Low coverage is acceptable; **confident-wrong detections are not**. Real corpus example: on the most complex Wikimedia drawing, the engine produced **20,267 objects + 140 explicit refusals + 747 windows-or-doors flagged** for review.

### Refusal_Over_Bluff_Across_Time (v0.1.1 audit)

The audit DB extends this invariant in time. Every refusal accumulates into a SQLite ledger with `run_id` linkage so a reviewer can query *patterns* of refusals across the entire corpus — not just per-drawing snapshots.

### License_Discipline (v0.1.2/3 corpus)

Same posture applied to corpus building. Every sample carries a `ProvenanceRecord` with `sha256` + explicit license tag. **No source with unmappable license enters `data/samples/`** — uncategorized sources surface in an `excluded` log, never silently included. The v0.1.3 license fix (`pd` + `cc0` + `public-domain` exact-match) unlocked +16 public-domain drawings while preserving the discipline (still 11 candidates refused for unmappable licenses).

---

## What's built (v0.1.3 — 4 tagged releases)

| Release | Lands | Highlights |
|--------:|------:|------------|
| **v0.1.0** | 2026-06-05 | 9-unit pipeline: Ingest → Geometry → OCR → Symbols → Compose+Aggregate + Streamlit review UI + 12-drawing synthetic corpus + 53 tests |
| **v0.1.1** | 2026-06-05 | Audit subsystem: SQLite schema + AuditContext + 5-stage instrumentation + CLI (`list-runs`/`show-run`/`refusals`/`stats`) + Streamlit "Past Runs" tab + 91 tests |
| **v0.1.2** | 2026-06-05 | Wikimedia Commons crawl: +22 real drawings (License_Discipline refused 27 unmappable) + JPG ingest support + 130 tests + 100% pipeline success on 32 ingestable real-world drawings |
| **v0.1.3** | 2026-06-06 | License mapping fix (exact-vs-prefix matcher) unlocked +16 PD drawings → 50 total + Streamlit preview pane right of the Drawing dropdown + 148 tests |

### Concrete numbers

- **5-stage pipeline**: Ingest → Geometry → OCR → Symbol → Compose+Aggregate
- **148 tests** across 9 modules (145 fast + 3 corpus-wide smoke)
- **50-drawing corpus** (12 synthetic + 38 Wikimedia, all with provenance + sha256)
- **27 git commits** on `main`, **4 tagged releases**
- **6 WP-level invariants** enforced across the codebase
- **100% pipeline success** on 32 ingestable real drawings; object counts 11–20,267; refusal counts 0–931 per drawing

---

## Architecture

```
PNG/JPG/PDF drawing
       │
       ▼  Ingest_F          → IngestResult (canonical RGB ndarray + metadata)
       │
       ▼  Geometry_F        → lines / contours / wall_candidates  (OpenCV Canny + HoughLinesP + parallel-pair fusion)
       │
       ▼  OCR_F             → texts + dim/label classification    (PaddleOCR ko + en + regex classifier)
       │
       ▼  Symbol_F          → doors / windows / spaces + refusal_candidates  (HoughCircles + double-line + wall_proximity)
       │
       ▼  Compose_F+Agg_F   → EngineOutput (full schema)
       │                         ↳ objects (per-field EEF: type / geometry / measurement)
       │                         ↳ aggregates (with ⊬/⊥ taint warnings)
       │                         ↳ refusals  (first-class output)
       │                         ↳ scale_anchor (gates all mm output)
       │
       ▼
   Streamlit Review UI   +   SQLite Audit DB   +   CLI queries
   (preview + overlay         (runs, stage_events,    (list-runs /
    + evidence panel +         refusals_log,          show-run /
    Past Runs tab)             policy_fires,          refusals /
                               epistemic_counts)      stats)
```

The output contract ([`src/cad_trust/schema.py`](src/cad_trust/schema.py), [`docs/OUTPUT_CONTRACT.md`](docs/OUTPUT_CONTRACT.md)) was committed **before** detection code per the `Contract_Before_Implementation` invariant — the schema gates the implementation, not the other way around.

---

## Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language | Python 3.11+ | Mature ecosystem, simplest path to combined CV + OCR + UI |
| Schema | Pydantic v2 | `model_validator` enforces Measurement_Policy at the contract boundary |
| Classical CV | OpenCV (`opencv-python`) | Canny + HoughLinesP + HoughCircles + contour analysis cover the rule-based detection in v0.1.x |
| OCR | PaddleOCR (ko + en) | Reliable on both Korean room labels and Latin dimension text |
| PDF | `pdf2image` + Poppler | Stable page rasterization |
| Image I/O | Pillow | Already a PaddleOCR dep; covers PNG/JPG/PDF preview |
| UI | Streamlit 1.58 | Fast iteration; tabs for Run Engine + Past Runs; native caching |
| Audit DB | `sqlite3` (stdlib) | Zero new deps; PRAGMA user_version gates migrations |
| CLI | `argparse` (stdlib) | `python -m cad_trust.audit list-runs / show-run / refusals / stats` |
| Tests | `pytest` | 148 tests; fixtures + parametrize; AST-based invariant checks |
| Corpus crawl | `urllib.request` (stdlib) | Polite user-agent, 0.5s rate-limit, sha256 dedup, license-mapping refusal |
| Type hints | PEP 585 + 604 | `list[T]` / `T | None` throughout; no `typing.List` legacy |

**Deliberately not used** (and the reasoning is in `docs/README.md`):
- **No YOLO/RT-DETR fine-tune** in v0.1.x — would require a labeled corpus we don't have yet (v0.3 territory)
- **No VLM** in v0.1.x — would handle 20,000+ raw HoughP candidates per drawing inefficiently; expert CV cross-checking + page-type guard come first (planned WP-ST-5)
- **No DWG native ingest** in v0.1.x — needs ODA/LibreDWG, separate dep decision (v0.3 territory)
- **No new external deps for audit** — stdlib `sqlite3` keeps the audit subsystem zero-cost to install

---

## Engineering posture (the skills we exercised)

Concrete engineering practices visible in the commit history and tests:

- **Contract-before-implementation** — Pydantic schemas + golden JSON committed in WP-ST-1 U2 *before* any detection code; subsequent units imported from that schema rather than inventing their own
- **Backward-compatibility as an invariant** — every release passes the previous release's full test suite (53 → 91 → 130 → 148, never going backwards)
- **Refusal as a first-class output type** — at every layer: pipeline refuses uncommittable regions, corpus builder refuses uncategorized licenses, audit DB records the refusal trail in time
- **Audit-first observability** — the audit subsystem (WP-ST-2) does not change pipeline contracts; it is purely additive and opt-in via an optional parameter, but it makes the trust surface historically queryable
- **Schema-enforced invariants** — Measurement_Policy is enforced by `model_validator` at the data layer, not by convention or comment. The schema **refuses to construct** invalid outputs.
- **TPMN unit-work discipline** — every change cycle runs the full plan → proceed → verify → archive loop documented in `.gem-squared/work-plan/` with per-unit `Acceptance` criteria
- **Honest refusal of work I can't do** — `data/samples/` is 100% public-source-with-provenance because I deliberately did not scrape unlicensed material; documented in [`docs/CORPUS.md`](docs/CORPUS.md)

---

## Quickstart

```bash
# Clone + venv
git clone https://github.com/gem-squared/gem2-cad-tel.git gem2-vision
cd gem2-vision
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Generate the synthetic corpus baseline (12 drawings)
.venv/bin/python scripts/build_corpus.py

# (Optional) extend the corpus from Wikimedia Commons (~22 more PNGs/JPGs/PDFs)
.venv/bin/python scripts/crawl_corpus.py --target 25

# Full fast test suite (~97s; 145 tests; skips the 10-min corpus-wide smoke)
.venv/bin/python -m pytest --ignore=tests/test_corpus_pipeline_smoke.py

# Launch the demo UI (http://localhost:8501)
.venv/bin/python -m streamlit run ui/app.py
```

Once the Streamlit UI is running:

- **Run Engine tab** — pick a drawing → see preview immediately → click Run Engine → see overlay + per-field epistemic badges + JSON download
- **Past Runs (Audit) tab** — drill into recorded runs, view aggregate refusal patterns by `attempted_type` across the corpus

For CLI audit queries:

```bash
.venv/bin/python -m cad_trust.audit list-runs
.venv/bin/python -m cad_trust.audit show-run <run_id>
.venv/bin/python -m cad_trust.audit refusals --attempted-type door
.venv/bin/python -m cad_trust.audit stats
```

---

## Documentation map

| File | Purpose |
|------|---------|
| [`docs/README.md`](docs/README.md) | Engineering thesis — start here for the full TPMN argument |
| [`docs/OUTPUT_CONTRACT.md`](docs/OUTPUT_CONTRACT.md) | Formal contract spec + Measurement Policy reference |
| [`docs/CORPUS.md`](docs/CORPUS.md) | Corpus license posture, sources used, exclusion policy |
| [`docs/AUDIT.md`](docs/AUDIT.md) | Audit subsystem: schema, CLI usage, example SQL queries |
| [`docs/DEMO_SCENARIOS.md`](docs/DEMO_SCENARIOS.md) | 5 walkthrough scenarios incl. the Korean apt 적산 refusal demo |
| [`docs/POBICON_PITCH.ko.md`](docs/POBICON_PITCH.ko.md) | 포비콘 application pitch (Korean) |
| `.gem-squared/work-plan/WP-ST-1.md` … `WP-ST-4.md` | The 4 TPMN work plans — A → B \| P contracts per unit, with results |

---

## Roadmap

**MVP 0.2 — planned**

- **WP-ST-5: Expert CV cross-check + Page Type guard** — refactor the single rule-based detector into expert modules (WallExpert / DoorExpert / WindowExpert / SpaceExpert / TextSuppressor / PageTypeExpert) emitting `claim` records, fused by `CrossCheck_F` into final EEF tags. UI gains per-expert vote panels. Reduces over-detection on mixed-sheet drawings (the audit DB shows 747 refusals on one drawing — the expert layer would explain *why* each refused and probably reduce many of them to clean rejects).
- **WP-ST-6: public Streamlit deployment** — cloud-deploy current demo as a shareable URL; cheap and high-impact for proposal optics.
- **WP-ST-7: VLM_Verify on ⊬ crops only** — Qwen-VL / Claude vision as a *re-checker* for extrapolated claims, never as a primary detector. VLM may confirm / reject / abstain. Never overrides scale_anchor policy.

**MVP 0.3 — beyond**

- Synthetic Korean apartment generator (preps labeled training data)
- YOLO/RT-DETR finetuning on assembled labeled corpus
- DWG native ingest via ODA / LibreDWG
- Full cost-aggregate ⊬-taint propagation through 산출내역서 calculations
- Audit-DB retention / rotation policies

---

## Status

- **v0.1.0** — 2026-06-05 · 9 units · 53 tests · `Refusal Over Bluff` introduced
- **v0.1.1** — 2026-06-05 · 6 units · 91 tests · Audit subsystem (SQLite + CLI + Streamlit tab)
- **v0.1.2** — 2026-06-05 · 6 units · 130 tests · Wikimedia corpus (12 → 34 drawings) + JPG ingest
- **v0.1.3** — 2026-06-06 · 4 units · 148 tests · License fix (34 → 50) + preview pane

All four work plans (`WP-ST-1` through `WP-ST-4`) are `COMPLETED|SUCCESS` and awaiting `/archive-work`.

---

*CAD Trust Engine Lite · gem-squared/gem2-cad-tel · 2026-06-06*
