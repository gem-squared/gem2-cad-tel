# Annotation Guide — Hybrid Floor-Plan Vision

**WP:** WP-ST-3 U2 | **Schema source of truth:** `src/cad_trust/annotation/schema.py` | **Interchange:** LabelMe (see `labelme_adapter.py`)

## Cardinal rules

1. **Ambiguous instances stay ambiguous.** Never force an unclear thing into a positive class. Set `ambiguity_flag ∈ {ambiguous, illegible, out_of_scope}` and move on.
2. **Room identity ⟂ room geometry.** A `space_polygon` annotation (the enclosing region) is a separate claim from a `room_label` (the OCR text). One can be annotated without the other.
3. **Generic `wall` is a first-class class.** If you cannot tell whether a wall is `wall_structural`, `wall_wet`, `wall_dry`, or a subtype — annotate as `wall`. Do NOT default to `wall_structural`.
4. **`scale_anchor_evidence` requires a triple.** Dimension text + dimension line + the specific measured object. Annotate all three separately, then create the `scale_anchor_evidence` record with `association_ref` pointing at the measured object's `annotation_id`.
5. **Every annotation records producer + tool + review status.** No anonymous labels.

## Class taxonomy

| Class | Geometry kind | Positive example | Negative example | Ambiguous case |
|-------|---------------|------------------|------------------|----------------|
| `wall` (generic) | mask or polygon | Interior partition in a floor plan whose subtype cannot be determined from the drawing | Elevation wall (this is on a wall-view sheet, not a plan-view) | Wall drawn with a hatch pattern you don't recognize — mark `ambiguous` |
| `wall_wet` | mask or polygon | Explicitly labeled 습식 / wet / kitchen partition | Any wall without wet-vs-dry indication | Hatched wall where hatch semantics unclear |
| `wall_dry` | mask or polygon | Explicitly labeled 건식 / dry partition | Any wall without wet-vs-dry indication | Same as wet |
| `wall_structural` | mask or polygon | Explicitly labeled 내력벽 / structural / bearing wall, OR thick+hatched in structural drawing | A thin drawn line without structural indication | Wall in a decorative-only representation |
| `door` | bbox + attachment_span_ref | Door swing arc + threshold at wall opening | Any hinged opening in an elevation view (excluded — not a plan) | Balcony sliding sash — use `ambiguous_window_or_balcony_sash` OR set flag |
| `window` | bbox + attachment_span_ref | Window opening in wall with parallel-line frame notation | Window shown in elevation | Balcony sliding sash — see above |
| `balcony_sash` | bbox + attachment_span_ref | Explicit 발코니 창호 / balcony sliding-glass panel | An interior room window | Very small sliding panel where balcony-vs-window unclear |
| `inspection_hatch` | bbox | Ceiling access hatch square in plan | Manhole cover shown in exterior site plan | Very small ambiguous square |
| `dimension_text` | quad + transcription | Numeric string near dimension line: "5400", "2,700 mm" | Any label text (room names, drawing titles) | Cropped or degraded OCR — mark `illegible` |
| `dimension_line` | polyline + extension_lines | Line with terminators (arrows/ticks) spanning a measured distance | A wall centerline (that's geometry, not dimension) | Line without terminators — could be reference line |
| `scale_anchor_evidence` | polyline (line ref) + `association_ref` (measured obj) + peer `dimension_text` | dimension_text="5400" ↔ dimension_line ↔ wall polygon whose pixel length matches | Two dimensions on the same wall (only one becomes anchor evidence per triple) | Dimension whose association is unclear — do NOT create scale_anchor_evidence; leave as text+line separately |
| `room_label` | quad + transcription | OCR of "거실" / "Living Room" placed inside a room | Any non-room text (title block, dimension) | Small ambiguous text inside a room polygon |
| `space_polygon` | polygon | Enclosing polygon of a room's interior area, walls-excluded | The whole floor's exterior boundary (that's outside the taxonomy) | Enclosed area that could be a room or a hallway — mark `ambiguous` and add note |

## Ambiguity flag semantics

| Flag | When to use |
|------|-------------|
| `clear` (default) | Instance is unambiguously the labeled class |
| `ambiguous` | Class or geometry has legitimate multiple readings — reviewer explanation attached |
| `illegible` | Text OCR failed, or geometry too degraded to trace confidently |
| `out_of_scope` | Instance belongs to an excluded input type (elevation, section, MEP-only, photo, 3D view) that leaked into a supposed floor plan |

Ambiguous/illegible/out_of_scope instances are **excluded from ordinary positive/negative scoring** (spec §4.2, WP-3 U4 policy). They still appear in the annotation record for provenance.

## Review status ladder

| Status | Meaning | Allowed to enter split |
|--------|---------|------------------------|
| `unreviewed` | AI or Human produced but not yet reviewed | ⚠ NEVER — cannot enter train / val / test |
| `ai_silver` | AI-produced; pre-review triage complete | ⚠ Train only. NEVER val, NEVER test. |
| `human_reviewed` | One qualified Human reviewer signed off | ✓ Train + val. NOT frozen test critical classes. |
| `human_double_reviewed` | Two independent Human reviewers agreed | ✓ Any split, including frozen test critical classes + scale anchors. |

Critical classes for frozen test: `wall`, `door`, `window`, `space_polygon`, `scale_anchor_evidence`. These require `human_double_reviewed` on the test split.

## Producer + tool provenance

Every annotation records:
- `label_producer` ∈ {`human`, `ai_claude`, `ai_codex`, `ai_approved_vision_pipeline`, `programmatic_synthetic`}
- `tool` (e.g., "labelme", "cvat", "codex_vision")
- `tool_version`
- `reviewer_identity_or_role` (e.g., "David Seo of GEM².AI", "contracted CAD reviewer #42", "AI")
- `annotation_digest` (SHA-256 over the canonical payload minus itself)

## Interchange format

The canonical format for annotation exchange is LabelMe JSON per drawing. See `src/cad_trust/annotation/labelme_adapter.py` for round-trip conversion between LabelMe shapes and `AnnotationRecord`.

Round-trip is lossless for the shape+label+ambiguity+transcription tuple. Fields not representable in LabelMe (attachment_span_ref, association_ref, review_status detail) are managed via a sidecar `{drawing_id}.annotations.json` conforming to `AnnotationRecord` schema (see `annotation_schema.json`).

## Do-not clauses (hard rules)

- Do **not** force an ambiguous instance into a class.
- Do **not** default `wall` to `wall_structural`.
- Do **not** annotate a `space_polygon` without visible wall-enclosure evidence.
- Do **not** produce `scale_anchor_evidence` without the full triple (text + line + object).
- Do **not** promote AI-produced labels to `human_reviewed` without an actual Human reviewer signing off.
- Do **not** modify frozen test annotations to match model output (see WP-3 U4 policy invariant: candidate-model outputs must NOT silently rewrite test ground truth).

## Files

| Path | Purpose |
|------|---------|
| `src/cad_trust/annotation/schema.py` | Pydantic AnnotationRecord source-of-truth |
| `src/cad_trust/annotation/labelme_adapter.py` | LabelMe ↔ AnnotationRecord round-trip |
| `src/cad_trust/annotation/annotation_schema.json` | Machine-readable JSON schema (Pydantic-exported) |
| `docs/ANNOTATION_GUIDE.md` | This document — human guide for reviewers |
