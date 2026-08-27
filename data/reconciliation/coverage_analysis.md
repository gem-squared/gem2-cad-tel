# Corpus Coverage Analysis — 2026-08-25

**WP:** WP-ST-3 Unit 1 | **Basis:** `eligibility_classification.json` (AI-provisional; awaiting Human review) | **Spec axes:** §4.1 of `docs/superpowers/specs/2026-08-25-hybrid-floor-plan-vision-design.md`

## Diversity snapshot (AI-provisional counts — pre-Human-review)

### SUPPORTED_FLOOR_PLAN pool (n=20)

| Axis | Distribution |
|------|--------------|
| Source | synthetic_self_generated: 12 · wikimedia_commons: 8 |
| License | public: 15 · CC-BY-SA: 3 · CC-BY: 2 |
| Domain | kr: 9 · global: 11 |
| Raster quality (inferred) | clean_export (synthetic 12): 12 · unknown (wm real 8): 8 — needs Human raster-quality tag |
| Language content (inferred) | kr: 9 (synthetic Korean labels) · non-kr: 11 |
| Scan-vs-clean | clean_export: 12 (synthetic) · unknown: 8 (wm — needs visual review) |
| Symbol convention | modern-kr-apt: 9 · varied historic: 8 · needs enumeration |
| Layout density (inferred) | simple: 12 (synthetic) · unknown: 8 |

### GUARD_AMBIGUOUS pool (n=14) — resolvable via Human review

| Axis | Distribution |
|------|--------------|
| Source | wikimedia_commons: 14 |
| License | public: 7 · CC-BY-SA: 7 |
| Domain | global: 14 |
| Note | All ⊬ (extrapolated) — filename+metadata insufficient. Human visual review will move each to SUPPORTED / GUARD_NEGATIVE / UNUSABLE. |

### GUARD_NEGATIVE pool (n=8) — feeds FloorPlanGuard negative benchmark

| Axis | Distribution |
|------|--------------|
| Source | wikimedia_commons: 8 |
| License | public: 4 · CC-BY-SA: 3 · CC-BY: 1 |
| Domain | global: 8 |
| Subtype (inferred from filename) | 3D_view: 2 (`wm_1_2-3d_model` visual-confirmed, `wm_3dpraxisstudio`) · cross_section: 2 · elevation/decorative_plate: 4 |

## Spec §4.1 diversity axes — gap assessment

| Axis (spec §4.1) | Current pool coverage | Gap | Severity |
|------------------|------------------------|-----|----------|
| **Source organizations / datasets** | 2 (synthetic, wikimedia_commons) | No FloorPlanCAD, Roboflow, no Korean-domain public dataset | HIGH — spec calls for multi-source diversity |
| **Synthetic vs real** | 12 synthetic / 8 real (SUPPORTED); ambiguous 0 synth / 14 real | Ratio skewed toward synthetic in the confirmed-positive pool | MEDIUM |
| **Drawing/symbol conventions** | Modern KR apartment style (synth) + varied historic (wm) | No modern-Western apartment/office plans in SUPPORTED confirmed | MEDIUM |
| **Korean vs non-Korean text** | 9 kr / 11 non-kr in SUPPORTED | Non-Korean-text drawings mostly historic Wikimedia; no modern non-KR office/apt drawings | MEDIUM |
| **Raster quality** | 12 clean_export (synthetic) + 8 unknown (wm) | Zero explicit scans (paper→scan) — spec calls for clean-vs-scan diversity | HIGH |
| **Simple vs dense layouts** | 12 simple (synth-generated) + 8 unknown | Zero explicit dense/complex layouts confirmed | HIGH |
| **Clean export vs scan** | See raster-quality row | Same as raster quality | HIGH |

## Blocking-if-insufficient assessment (per WP-ST-3 U1 CONTRACT)

The WP-3 U1 CONTRACT says: **"if any minimum unmet, controlled sourcing is a BLOCKING prerequisite before dataset freeze (U7)."**

**Current AI-provisional pool cannot meet reasonable minimums on:**
- **Scans** — literally 0 samples marked as `raster_quality=scan`. Split (train/val/test) reservation cannot allocate scan samples if none exist.
- **Dense layouts** — 0 explicit dense-layout samples.
- **Modern non-KR floor plans** — historic Wikimedia entries dominate the non-KR half; no modern-office/apartment non-KR plans.
- **Additional source organizations** — 2 sources are below spec's "diversity across source organizations" language.

**Consequence:** Even after Human review of the 14 AMBIGUOUS potentially moves some to SUPPORTED (raising pool to ~25-30), the diversity gaps above will remain structural. Controlled corpus supplementation (per `supplementation_contract.md`) is a probable blocking prerequisite before U7 freeze.

## Human ratification path

The numeric minimums in `docs/COVERAGE_CONTRACT.md` are AI-proposed defaults that need Human ratification. Once the Human ratifies (or amends) the minimums:
1. Re-check current pool + Human-reviewed AMBIGUOUS reassignments.
2. Any axis still unmet → route to `supplementation_contract.md` for controlled fetching.
3. Only after all minimums met AND all classifications Human-reviewed → U3 can produce split manifests.
4. Only after that → U7 freeze gate is meaningful.

## SPT check

- **S→T avoided:** "42 samples exist" ≠ "42 target floor plans exist". Confirmed 20 SUPPORTED (12 grounded synthetic + 8 ⊨-inferred wm; not yet all visually confirmed).
- **Δe→∫de avoided:** Two visual spot-checks (synth_apt_kr_balcony_01 + wm_1_2-3d_model) don't establish "AI classification is reliable" — most classifications remain ⊬ extrapolated pending Human review.
- **L→G avoided:** Coverage-gap conclusions bounded to this specific 50-record pool; not generalized to floor-plan-recognition in general.

## Next actions

1. Human reviews 14 GUARD_AMBIGUOUS entries and updates `eligibility_classification.json`.
2. Human ratifies `docs/COVERAGE_CONTRACT.md` minimums.
3. If minimums unmet, invoke `supplementation_contract.md` for controlled sourcing.
4. Rerun this analysis after each Human touch.
