# Labeling Policy — Hybrid Floor-Plan Vision Corpus

**WP:** WP-ST-3 U4 | **Authority:** CD Mission Directive 2026-08-25 | **Approver required for changes:** David Seo of GEM².AI

## Purpose

Declare the risk-tiered labeling process for the WP-ST-3 corpus. This policy governs WHO may produce annotations and WHICH annotations may enter WHICH split. The invariant: **AI-only annotations CANNOT become frozen benchmark truth.**

## Allowed label producers

| Producer | Value in `AnnotationRecord.label_producer` |
|----------|---------------------------------------------|
| Qualified Human CAD/architectural reviewer | `human` |
| Claude (any version) via approved workflow | `ai_claude` |
| Codex vision via approved workflow | `ai_codex` |
| Other approved vision pipeline (e.g., self-hosted SAM/YOLO/PaddleOCR) | `ai_approved_vision_pipeline` |
| Synthetic drawing generator (deterministic ground truth) | `programmatic_synthetic` |

## Tiered gates per split

| Split | Gate | Minimum `review_status` per annotation |
|-------|------|----------------------------------------|
| train | AI-silver allowed for non-critical classes; risk-based Human sampling required | `ai_silver` OR higher (with sampling audit) |
| train (critical classes: `wall`, `door`, `window`, `space_polygon`, `scale_anchor_evidence`) | 100% Human review even in train | `human_reviewed` |
| val | 100% Human review before any use | `human_reviewed` |
| test (non-critical classes) | Human review | `human_reviewed` |
| test (critical classes + all scale-anchor associations) | Independent Human verification + double review | `human_double_reviewed` |

## Reviewer qualification

- The reviewer may be any qualified CAD or architectural reviewer — David does NOT need to be the reviewer personally.
- David retains approval of: labeling contract (this document), ambiguity policy (`docs/ANNOTATION_GUIDE.md`), QA thresholds (see `docs/COVERAGE_CONTRACT.md`), dataset freeze (WP-ST-3 U7), and unresolved adjudications.
- Delegated reviewers must be recorded per annotation via `AnnotationRecord.reviewer_identity_or_role`.

## Hard invariants (structural, non-waivable)

1. **AI-only annotations cannot enter frozen benchmark truth.** Any annotation with `review_status ∈ {unreviewed, ai_silver}` must not appear in val or test splits as authoritative.
2. **Ambiguous instances stay ambiguous.** `ambiguity_flag ∈ {ambiguous, illegible, out_of_scope}` — never force into a class.
3. **Test-annotation immutability under model drift.** Candidate-model outputs and frozen-test benchmark results must NOT silently rewrite test ground truth. Any test-annotation relabel goes through an explicit U7-style adjudication with a fresh digest change and a Human-signed rationale.
4. **Synthetic drawings prefer programmatic ground truth.** When the synthesizer that produced the image is available, use its deterministic output; do not re-derive via AI classification if programmatic labels exist.
5. **Every annotation records producer + tool + version + review_status + reviewer.** No anonymous labels.
6. **Ambiguous eligibility ≠ ambiguous annotation.** Corpus-level eligibility (`GUARD_AMBIGUOUS` in `eligibility_classification.json`) is a separate axis from per-instance annotation ambiguity.

## AI-silver process (train-split only, non-critical classes)

If AI-silver labels are used for train:
1. Producer runs vision pipeline → outputs `AnnotationRecord` with `review_status = "ai_silver"`.
2. Risk-based sampling: select N% of AI-silver labels for Human review (higher-risk classes = higher N). Recommended default:
   - `door` / `window` on train: 20% sample review
   - `wall` on train: 10% sample review
   - `dimension_text` on train: 15% sample review (OCR quality)
   - `dimension_line` + `scale_anchor_evidence`: 100% Human review even in train (critical)
3. Sampled labels' review_status upgrades to `human_reviewed` after reviewer sign-off. Non-sampled labels stay `ai_silver`.
4. IAA sample per class computed on the sampled subset (see U5).
5. If sampled subset shows disagreement rate above threshold (default: any class with >20% AI/Human disagreement), the whole class's AI-silver batch is rejected and re-labeled — either by another AI pipeline or by full Human labeling.

## Test-annotation double-review process

For test critical classes + all scale-anchor associations:
1. Reviewer A independently annotates → `review_status = "human_reviewed"` + `reviewer_identity_or_role = "Reviewer A [role]"`.
2. Reviewer B independently annotates the same drawings → separate `human_reviewed`.
3. Adjudication script (WP-ST-3 U5) compares A vs B; disagreements above IoU threshold surface for a third-party adjudicator (default: David).
4. Only after all disagreements resolved → both records' `review_status` becomes `human_double_reviewed`.
5. Frozen test bundle (WP-ST-3 U7) verifies critical classes on test all show `human_double_reviewed`.

## Adjudication for unresolved cases

When two reviewers cannot converge:
- Case escalated to David for final adjudication.
- David's decision recorded per-annotation with rationale.
- Decision stored in `data/adjudications/{drawing_id}_{annotation_id}.json` linking to reviewers A and B.

## Non-execution of this policy during U4 automated run

Under the current session (David all-authority autonomy, but no Human reviewers connected), U4 execution can produce ONLY:
- This policy document (grounds the invariants).
- Annotation-file skeletons per SUPPORTED drawing (empty shapes, `review_status = "unreviewed"`, ready for Human/AI labeling downstream).

It CANNOT produce val/test annotations with `human_reviewed` or `human_double_reviewed` status — those require actual Human reviewers. This limitation is explicit and blocks U5-U9 progression until reviewers are engaged.

## Reference

- `src/cad_trust/annotation/schema.py` (`ReviewStatus` Literal enforces the ladder)
- `docs/ANNOTATION_GUIDE.md` (per-class rules for reviewers)
- `docs/COVERAGE_CONTRACT.md` (minimum coverage per axis)
- `data/reconciliation/eligibility_classification.json` (which drawings are annotatable at all)
