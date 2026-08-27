# Corpus Supplementation Contract

**WP:** WP-ST-3 Unit 1 | **Authority:** CD Mission Directive 2026-08-25 | **Status:** Contract-only; no fetching executed during U1

## Scope

Rules for how the WP-ST-3 corpus may be supplemented with additional drawings **if and only if** `docs/COVERAGE_CONTRACT.md` minimums are unmet after Human review of the current pool. Supplementation is a **separate controlled step** — it does NOT execute during U1 and requires explicit Human authorization per addition (or per batch).

## Prohibitions (hard invariants)

- **NO** silent addition. Every new drawing goes through this contract.
- **NO** license-uncertain drawings. `check-required` disposition per `docs/CORPUS.md` triage first; only after license clarification does eligibility follow.
- **NO** photographs of real construction sites, marketing materials (분양자료), aggregator scrapes (Pinterest, real-estate blog), or construction-company internal PDFs — excluded categories per `docs/CORPUS.md`.
- **NO** silent overwrite of any existing sample or provenance file.

## Required per new drawing

1. **Source-URI fetch** with recorded HTTP response headers + timestamp.
2. **License verification** — license text visible on source page at fetch time; store license link + attribution string.
3. **Floor-plan-relevance check** — visual inspection classifying to WP-ST-3 U1 taxonomy {SUPPORTED_FLOOR_PLAN, GUARD_NEGATIVE, GUARD_AMBIGUOUS, UNUSABLE}.
4. **SHA-256** of the fetched bytes recorded fresh.
5. **ProvenanceRecord** written under `data/provenance/` conforming to `src/cad_trust/provenance.py` schema.
6. **Human sign-off** — reviewer records approval per addition (or per batch) before drawing enters any split.

## Reconsideration of the 8 quarantined orphans

The 8 `ORPHAN_EXCLUDED` records may be **individually** reconsidered under this contract. Each requires:

1. Fresh HTTP GET of `original_uri` (retained in provenance record).
2. License still visible on source page.
3. Fresh SHA-256 (may differ from the frozen `sha256` field — that field is historic; new fetch gets new digest).
4. Floor-plan-relevance classification.
5. Human sign-off.

If any check fails, the orphan stays quarantined. If all pass, a NEW provenance record is written (the original historic record is preserved for audit); the drawing enters the pool via normal U1 classification.

## Allowed sources for controlled supplementation

Per `docs/CORPUS.md` and spec §4.1:

- **FloorPlanCAD** — academic license, dry storage restricted per license; use only for `academic` domain evaluation, not commercial.
- **Roboflow public floor-plan datasets** — license-per-set; must verify each.
- **Wikimedia Commons** — CC-BY, CC-BY-SA, public domain — already the primary real source; may fetch additional entries.
- **Cal Poly DWG demo set** — `dwg_demo` domain only; for ingest demo, not object-recognition training/scoring.
- **Self-generated synthetic** — permitted for supplementing simple/dense/scan diversity axes; requires programmatic-ground-truth path per WP-ST-3 U4 labeling policy.

## Batch process

If a batch of N new drawings is proposed:
1. Draft a batch manifest under `data/reconciliation/supplementation_batches/{YYYY-MM-DD}-batch-{n}.md` listing each drawing + intended source + license + rationale.
2. Human reviews the batch manifest.
3. On approval, fetch + verify each drawing per the per-drawing checklist above.
4. Update `eligibility_classification.json` with each new drawing.
5. Re-run `coverage_analysis.md` and check coverage-minimum status.

## Non-execution note

**No fetching occurs during WP-ST-3 U1 execution.** U1's B contract is limited to writing this contract file + the classification + the coverage analysis. Actual supplementation is a downstream activity gated on Human review of current pool + explicit authorization.
