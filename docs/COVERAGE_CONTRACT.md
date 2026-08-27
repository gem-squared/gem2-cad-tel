# Coverage Contract — Hybrid Floor-Plan Vision Corpus

**Version:** 1.0.0-DRAFT-AI-PROPOSED | **Status:** AWAITING_HUMAN_RATIFICATION | **WP:** WP-ST-3 Unit 1
**Approver required:** David Seo of GEM².AI (per WP-ST-3 U4 labeling policy)

## Purpose

Declare the Human-approved minimum coverage the WP-ST-3 corpus must meet, per axis, before dataset freeze (WP-ST-3 U7). Per CD Mission Directive: **if any minimum is unmet, controlled sourcing (per `data/reconciliation/supplementation_contract.md`) is a BLOCKING prerequisite before U7 freeze.**

## Axes and minimum coverage (AI-proposed defaults)

The rows below are AI-proposed conservative minimums. **They are NOT active until Human ratifies.** Human may amend any row.

### Per class (SUPPORTED_FLOOR_PLAN pool must contain ≥ N drawings with a valid annotation for each class)

| Class | AI-proposed min instances | Rationale |
|-------|---------------------------|-----------|
| `wall` (generic) | ≥ 100 | Instance-level metric needs enough samples for stable IoU/instance-recall statistics |
| `door` | ≥ 40 | mAP@0.5 has meaningful variance below ~30 samples |
| `window` | ≥ 40 | Same as door |
| `room_label` | ≥ 30 | OCR + room-identity claim rare enough that 30 is a floor |
| `space_polygon` | ≥ 40 | Room-geometry claim |
| `dimension_text` | ≥ 60 | OCR CER + exact-match need denser sampling |
| `dimension_line` | ≥ 60 | Association metric needs paired text+line |
| Valid scale-anchor pair (≥2 agreeing anchors) | ≥ 15 drawings | Scale-anchor promotion rule needs at least 15 drawings for stable false-anchor-rate |

### Per source family

| Source family | AI-proposed min drawings in SUPPORTED pool |
|---------------|--------------------------------------------|
| synthetic (kr apt) | ≥ 12 (current: 12 ✓) |
| synthetic (office) | ≥ 3 (current: 3 ✓) |
| wikimedia_commons (historic global) | ≥ 8 (current: 8 ✓) |
| Additional public dataset (e.g., FloorPlanCAD, Roboflow) | ≥ 20 (current: 0 ✗ — blocking) |
| Korean domain (non-synthetic) | ≥ 10 (current: 0 ✗ — blocking) |

### Per language

| Language content | AI-proposed min drawings | Current |
|------------------|--------------------------|---------|
| Korean (KR text visible) | ≥ 15 | 9 (synthetic only) — near-blocking |
| Non-Korean | ≥ 15 | 11 — near-met |
| No text | ≥ 5 | 0 — soft-gap |

### Per raster quality

| Raster quality | AI-proposed min | Current |
|----------------|-----------------|---------|
| clean_export (vector-rendered PNG/PDF) | ≥ 15 | 12 |
| paper_scan (real scanner) | ≥ 10 | 0 ✗ — blocking |
| photograph_of_paper | ≥ 5 | 0 — soft-gap |

### Per guard verdict

| Guard verdict | AI-proposed min | Current |
|---------------|-----------------|---------|
| SUPPORTED (positive-guard set) | ≥ 30 for guard training | 20 (SUPPORTED_FLOOR_PLAN) — near-met if AMBIGUOUS review resolves some as SUPPORTED |
| UNSUPPORTED (negative-guard set) | ≥ 20 across all 8 unsupported subtypes | 8 GUARD_NEGATIVE + up to 14 AMBIGUOUS could add — near-blocking |
| AMBIGUOUS (for calibration) | ≥ 10 | 14 currently — met, but shrinks after Human review reassigns to SUPPORTED/NEGATIVE |

## Promotion predicate reference

These minimums combine with WP-ST-3 U6 metric thresholds. If any axis marked ✗ or "near-blocking" above remains unmet after Human review of the current pool AND after any controlled supplementation, the U7 freeze gate cannot legitimately proceed.

## Human ratification (currently empty)

| Field | Value |
|-------|-------|
| Ratified by | (empty — AWAITING) |
| Ratified at | (empty) |
| Amendments made | (empty) |
| Waivers on any minimum | (empty) |
| Signature | (empty) |

**When ratified, this file will be hashed and included in WP-ST-3 U7 canonical_bundle.txt so approval is bound to the exact numeric minimums.**

## SPT check

- ⊨ (inferred) minimums based on standard ML-benchmark sample-size heuristics + spec §4.1 diversity language. NOT ⊢ (grounded) — Human may revise based on domain judgment.
- No S→T claim: current pool insufficiency is a state-of-2026-08-25, not a permanent trait.
- No L→G claim: minimums bound to gem2-cad-tel scope, not floor-plan-vision generally.
