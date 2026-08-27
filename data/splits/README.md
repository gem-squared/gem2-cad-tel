# Splits — WP-ST-3 U3

**Generated:** 2026-08-25T13:20:00+0900 | **Basis:** `data/reconciliation/eligibility_classification.json` (AI-provisional, awaiting Human review)

## Two separate manifests (per CD Mission Directive)

- `object_recognition/{train,val,test}.json` — SUPPORTED_FLOOR_PLAN pool only, for WP-ST-4 U3-U5 experts and WP-ST-5 U7 regression
- `guard/{positive,negative,ambiguous}.json` — by GUARD verdict, for WP-ST-4 U2 FloorPlanGuard classifier

## Hard invariant: family_id never crosses object-recognition splits

Verified by `scripts/verify_split_isolation.py` (exit 0 on isolation, exit 1 on violation).

## Family derivation rule

- **Synthetic drawings** (`source = synthetic_self_generated`): family_id = prefix-before-numeric-suffix → all `synth_apt_kr_balcony_{01,02,03}` share one family.
- **Wikimedia Commons drawings**: family_id = drawing_id (each wm entry is its own family — independent sources, no template lineage).

## Split algorithm

Per source-group:
1. Sort families by SHA-256(family_id) ascending (deterministic).
2. 1st family → `test`, 2nd family → `val`, remainder → `train`.

Rationale: on a very small corpus (12 families), a pure hash-bucket algorithm can collapse to a single split. Per-source proportional allocation guarantees non-empty val + test even when there are only a handful of families per source.

## Current allocation (frozen state — regenerate ONLY when eligibility classification changes)

| Split | Drawings | Families | Family list |
|-------|----------|----------|-------------|
| train | 12 | 8 | synth_apt_kr_balcony, synth_apt_simple, 6 wikimedia families |
| val | 4 | 2 | synth_apt_three_room, 1 wikimedia family |
| test | 4 | 2 | synth_office_open, 1 wikimedia family |

## Guard splits (by verdict — not train/val/test)

| Verdict | Drawings |
|---------|----------|
| positive | 20 (SUPPORTED_FLOOR_PLAN) |
| negative | 8 (GUARD_NEGATIVE) |
| ambiguous | 14 (GUARD_AMBIGUOUS — resolves after Human review) |

**WP-ST-4 U2** further partitions guard sets into train/val/test for the FloorPlanGuard classifier bake-off. That partition is downstream and NOT frozen here.

## Freeze anchors (SHA-256)

See `FREEZE_HASHES.txt`. Any modification to any split JSON changes its digest → the freeze is broken and re-freeze (via U7) is required.

## Known limitations (documented, not workarounds)

- **Test = 4 drawings.** Statistically small. Documented in `docs/COVERAGE_CONTRACT.md` as blocking-if-supplementation-doesn't-close-gaps.
- **Test = 1 wm-family + 1 synth-family (3 drawings from same template).** The synth_office_open family shares a template — 3 drawings are variants. This is a WEAKNESS surfaced by the small pool; controlled supplementation should add ≥2 additional distinct source-families to test before U7 freeze.
- **AI-provisional eligibility.** Splits inherit AI-provisional classifications. When Human review updates `eligibility_classification.json`, re-run `scripts/build_splits.py` — the deterministic algorithm gives stable placement for unchanged families.

## Regenerate

```bash
python scripts/build_splits.py            # rebuild all splits
python scripts/verify_split_isolation.py  # confirm no family_id leakage
```

## Test-split use invariant

Per spec §5.1 and WP-ST-4 CONTRACT: the frozen test split MUST NOT be used for model, threshold, augmentation, calibration, or checkpoint selection. WP-ST-3 U8 harness enforces this — attempting a `purpose=selection` call on `split=test` raises `ValueError`.
