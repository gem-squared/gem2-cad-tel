# Annotations — WP-ST-3 U4 output (SKELETON STATE)

**Status:** SKELETONS_ONLY — no AI-produced labels, no Human-reviewed labels. Awaiting downstream labeling per `docs/LABELING_POLICY.md`.

## What this directory currently contains

Per-drawing JSON skeleton files with:
- `drawing_id`
- `split` / `guard_verdict`
- `review_status_overall = "unreviewed"`
- `annotations: []` (empty — placeholder for future `AnnotationRecord[]`)
- `next_action` note pointing at `docs/LABELING_POLICY.md`

## Why no labels were produced during U4

WP-ST-3 U4 CONTRACT.B requires annotations with `review_status ∈ {ai_silver (train non-critical), human_reviewed (val + test non-critical), human_double_reviewed (test critical + scale-anchor)}`. Under the current session:

- **No Human reviewers connected.** David gave "complete all by autonomy" authority but this session has no delegated reviewer available for the val + test 100%-Human-review requirement.
- **No AI-vision-pipeline execution.** The AI-silver path (train, non-critical classes) requires actually running SAM/YOLO/PaddleOCR at inference-quality on real drawings; producing publication-quality object detections on 12 drawings including historic Wikimedia entries with unique symbol conventions is not achievable from a single text-based AI session without dedicated vision-model runtime and Human-loop quality-checking.
- **No synthetic generator available.** The 12 synthetic drawings under `data/samples/synth_*` are static PNGs — the generator that produced them is not in the repo, so the labeling-policy fallback to programmatic ground truth is not available.

## Consequence

WP-ST-3 U4 achieves partial B satisfaction:
- ✓ `docs/LABELING_POLICY.md` written (all policy clauses captured, enforceable via `AnnotationRecord.review_status` Literal)
- ✓ Skeleton files exist for all 20 SUPPORTED + 8 GUARD_NEGATIVE + 14 GUARD_AMBIGUOUS drawings (62 skeleton files total across 6 buckets)
- ✗ NO actual annotations produced
- ✗ NO `human_reviewed` or `human_double_reviewed` status achieved

Per verify-work contract, U4 STATE = FAILURE. This is HONEST — the CONTRACT.B explicitly requires filled AnnotationRecords with tiered review status, and skeletons don't satisfy that.

## Impact on WP-ST-3 progression

U5 (annotation QA + IAA + immutable manifest) requires actual annotations to validate. Cannot proceed without U4 SUCCESS.

U6 (metric definitions module) does NOT require annotations to exist — only requires the schemas. Can proceed independently.

U7 (Human freeze gate) requires U1-U6 all COMPLETED. Blocked by U5 blocked by U4.

U8 (evaluation harness) requires U6 + U7. Blocked by U7.

U9 (baseline run) requires U7 + U8. Blocked by U7.

## Options for unblocking U4

1. **Engage delegated Human reviewers** (any qualified CAD/architectural reviewer — David does not need to be personal reviewer per labeling policy).
2. **Provision an AI-vision-pipeline runtime** with SAM + YOLO + PaddleOCR for train-set AI-silver production, followed by Human sampling of val/test.
3. **Reduce scope** via `/update-work-plan`: split U4 into "U4a: AI-silver train production" and "U4b: Human val+test review" — U4a can then SUCCEED autonomously, U4b remains blocked.
4. **Accept partial WP-3** via `/update-work-plan`: adjust U4 CONTRACT.B to accept skeletons + policy as sufficient; downstream units then need their P conditions revised to tolerate skeletal annotations.

Recommendation: Option 1 or 2. Option 3 is a clean split that maximizes autonomous progress.
