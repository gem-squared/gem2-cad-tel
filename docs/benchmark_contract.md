---
{
  "macro_weights": {
    "wall": 0.20,
    "door": 0.10,
    "window": 0.10,
    "room": 0.10,
    "ocr": 0.10,
    "dimension_assoc": 0.10,
    "scale": 0.15,
    "trust": 0.10,
    "ops": 0.05
  },
  "critical_classes": ["wall", "door", "window", "room", "scale_anchor"],
  "measurement_policy_zero_tolerance": true,
  "false_anchor_regression_tolerance": 0.0,
  "canonical_bundle_sha256": ""
}
---

# Benchmark Contract — Hybrid Floor-Plan Vision

**Version:** 1.0.0-DRAFT-AI-PROPOSED | **Status:** AWAITING_HUMAN_RATIFICATION | **WP:** WP-ST-3 U6
**Approver required:** David Seo of GEM².AI (per spec §5.1 — must be Human-approved BEFORE baseline is calculated)

## Macro-score weights (AI-proposed defaults)

The weights above (JSON front-matter) sum to 1.00. Rationale:

| Class weight | Value | Rationale |
|--------------|-------|-----------|
| `wall` (0.20) | Highest | Wall detection is the foundation — errors propagate to rooms, doors, dimensions. |
| `scale` (0.15) | Second-highest | Scale-anchor correctness gates all mm measurements (Measurement Policy). False anchors are the highest-consequence failure. |
| `door` / `window` / `room` / `ocr` / `dimension_assoc` (0.10 each) | Moderate | Standard object-detection weight; equal weight prevents any single class from dominating. |
| `trust` (0.10) | Moderate | Refusal calibration + risk-vs-coverage. |
| `ops` (0.05) | Lowest | Latency + memory matter but do not dominate quality. |

## Critical classes (regression forbidden without waiver)

`wall`, `door`, `window`, `room`, `scale_anchor` — these are the classes a QTO cost estimator absolutely needs. Any regression on these triggers `WAIVER_REQUIRED` state per promotion predicate.

## Promotion predicate — three-state machine

Implemented in `src/cad_trust/eval/promotion.py::evaluate_promotion`. Returns `PromotionVerdict` with `overall ∈ {PASS, WAIVER_REQUIRED, FAIL}`:

- **PASS**: All 5 clauses PASS (macro-improvement + no critical regression + no false-anchor regression + zero Measurement Policy violations + reproducibility verified) AND no waivers required.
- **WAIVER_REQUIRED**: Otherwise PASS-shaped BUT at least one critical-class regression exists. Requires explicit Human waiver via `Waiver` YAML with approver + rationale + evidence_refs.
- **FAIL**: Any of {macro non-improvement, false-anchor regression, Measurement Policy violation, reproducibility broken}.

Clause 6 (Human acceptance) is NOT machine-evaluated here — it lives in WP-ST-5 U9 as a separate Human-decision unit.

## Reproducibility check requirements

The hybrid summary passed to `evaluate_promotion` must declare:
- `canonical_bundle_sha256` matching the frozen WP-ST-3 U7 digest
- `config_digest`, `env_digest`, `model_digests`

Missing or mismatched fields → `reproducibility: FAIL`.

## Machine-checkable script

```bash
python scripts/check_promotion_predicate.py \
  --baseline .gem-squared/evidences/benchmarks/wp-st-3-baseline/*/baseline_result.json \
  --hybrid .gem-squared/evidences/benchmarks/wp-st-5-hybrid/*/hybrid_result.json \
  --contract docs/benchmark_contract.md \
  --waivers data/waivers/*.yaml
```

Exit codes: 0=PASS, 2=WAIVER_REQUIRED, 3=FAIL, 4=reproducibility-broken.

## Human ratification section (currently empty)

| Field | Value |
|-------|-------|
| Ratified by | (empty — AWAITING) |
| Ratified at | (empty) |
| Weight amendments made | (empty) |
| Critical-class amendments made | (empty) |
| Signature (detached) | See `data/freeze/APPROVAL_RECORD.md` after U7 |

**When ratified, the JSON front-matter above is hashed and included in U7 canonical_bundle.txt.**

## Non-negotiable invariants

- Test set never used for macro-weight selection or critical-class selection (spec §5.1).
- Machine PASS does NOT auto-approve promotion (WP-ST-5 U9 Human decision retained per spec §12/§13).
- Machine FAIL does NOT block Human from recording APPROVED_WITH_WAIVER if they take responsibility with structured evidence.
