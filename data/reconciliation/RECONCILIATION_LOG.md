# Corpus Reconciliation Log — 2026-08-25

**WP:** WP-ST-3 Unit 1 | **Executor:** AI (Claude Opus 4.7 [1M] as ARCHITECT) | **Authority:** CD Mission Directive 2026-08-25 (Strategy C — non-destructive)

## Invariants held

- **NO provenance records deleted.** All 50 records under `data/provenance/` remain unchanged.
- **NO sample files deleted, moved, or refetched.** All 42 files under `data/samples/` remain unchanged.
- SHA-256 audit: **42/42 samples match their declared provenance digest** (verified 2026-08-25).

## Orphan provenance records (8) — preserved per Strategy C

These 8 provenance records have no accompanying sample file at reconciliation time. Per CD directive Strategy C: preserved unchanged, recorded as `ORPHAN_EXCLUDED` in `eligibility_classification.json`, `original_uri` retained for possible future controlled supplementation, excluded from train/val/test manifests.

| # | drawing_id | source | license | domain | original_uri (preserved) |
|---|------------|--------|---------|--------|-----|
| 1 | `wm_1_photo_-_16` | wikimedia_commons | CC-BY-SA | global | `https://commons.wikimedia.org/w/index.php?curid=84658172` |
| 2 | `wm_2-cilindri` | (see json) | (see json) | (see json) | (see json) |
| 3 | `wm_20342-5_bl-east_orange_nj--east_orange_improvements--15th_street_subway_df8215e8` | wikimedia_commons | (see json) | (see json) | (see json) |
| 4 | `wm_2689-atlantic-print` | (see json) | (see json) | (see json) | (see json) |
| 5 | `wm_ah_r_k_k_plan` | (see json) | (see json) | (see json) | (see json) |
| 6 | `wm_akademia_wsb_w_d_browie_g_rniczej_-_003` | (see json) | (see json) | (see json) | (see json) |
| 7 | `wm_architectural_drawing_of_a_garden_met_eg14_108` | (see json) | (see json) | (see json) | (see json) |
| 8 | `wm_peak_ground_velocity_o_grande_paesaggio` | (see json) | (see json) | (see json) | (see json) |

**Exclusion reason (all 8):** "Provenance record exists but no matching sample file at reconciliation time 2026-08-25. Preserved per Strategy C. Original URI retained. May be reconsidered under future controlled corpus supplementation contract with fresh floor-plan-relevance + license verification."

**Future disposition:** Each may be individually reconsidered under `supplementation_contract.md` — requires (a) fresh HTTP GET of `original_uri`, (b) license still visible on source page, (c) floor-plan-relevance verification per FloorPlanGuard schema, (d) fresh SHA-256, (e) Human sign-off before entering any split.

## Eligibility classification summary (50 total)

Full per-drawing detail in `data/reconciliation/eligibility_classification.json` — this table is the roll-up.

| Category | Count | Meaning |
|----------|-------|---------|
| **SUPPORTED_FLOOR_PLAN** | 20 | Target for WP-ST-3 U3(a) object-recognition benchmark |
| **GUARD_NEGATIVE** | 8 | Confirmed non-floor-plan (elevation/section/photo/3D/schedule) — feeds WP-ST-3 U3(b) FloorPlanGuard negative set |
| **GUARD_AMBIGUOUS** | 14 | Cannot be classified from filename+provenance alone — needs Human visual review before entering any benchmark |
| **ORPHAN_EXCLUDED** | 8 | Provenance-without-sample — see above |
| **UNUSABLE_EXCLUDED_FROM_SCORING** | 0 | (none — all 42 sample files have valid provenance) |

## SPT discipline (per CLAUDE.md watchlist)

- **⊬ (Extrapolated) items:** 14 GUARD_AMBIGUOUS classifications are AI-inferred from filename + provenance domain hints. They MUST NOT be treated as ⊢ (grounded) without Human visual review. WP-ST-3 U4 labeling policy applies — AI-provisional classification cannot enter frozen benchmark truth.
- **State-as-Trait avoidance:** "This file is in `data/samples/`" is a state, not the trait "This is a target floor plan." The 8 GUARD_NEGATIVE + 14 GUARD_AMBIGUOUS classifications explicitly reject that S→T slip.
- **Local-as-Global avoidance:** Classification confidence is bounded to filename + declared provenance metadata. No claim beyond that. Visual inspection performed only on 2 sample cases (`wm_1_2-3d_model.pdf` — confirmed 3D perspective sketch; `synth_apt_kr_balcony_01.png` — confirmed floor plan). Other classifications are ⊨ (inferred) or ⊬ (extrapolated) with per-row EEF tags in the JSON.

## Human review requirement (per WP-ST-3 U4 labeling policy)

This classification is AI-produced provisional work. Before U3 splits are frozen (U7 gate), the 14 GUARD_AMBIGUOUS entries must be Human-visually-reviewed and reassigned to SUPPORTED_FLOOR_PLAN / GUARD_NEGATIVE / UNUSABLE. Reviewer should also spot-check the ⊨-tagged classifications and flag any misclassification.

Suggested workflow:
1. Human opens each of the 14 ambiguous images in the review UI.
2. Reassigns category per WP-ST-3 U1 taxonomy.
3. Signs off on the reassigned classification (updates `review_status` field per `eligibility_classification.json` entry).
4. Re-run summary rollup, update this log's category counts.
5. Then proceed to U3 split construction.

## Files produced by this reconciliation

- `data/reconciliation/RECONCILIATION_LOG.md` (this file)
- `data/reconciliation/eligibility_classification.json` (per-drawing classification with EEF tags)
- `data/reconciliation/coverage_analysis.md` (diversity gap analysis, next section)
- `data/reconciliation/supplementation_contract.md` (rules for future controlled sourcing)
- `docs/COVERAGE_CONTRACT.md` (Human-approvable minimum coverage per axis)

No corpus file created, modified, or deleted by this reconciliation.
