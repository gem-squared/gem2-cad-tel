# Demo Scenarios — CAD Trust Engine Lite v0.1

Five walkthroughs covering the engine's trust surface. The first three are routine; **scenarios 4 + 5 demonstrate the wedge** — refusal as a first-class output, measurement refusal under the cost-risk invariant.

---

## Scenario 1 — Routine apartment floor plan

**Input:** `data/samples/synth_apt_simple_01.png`

**Flow:**
1. Ingest_F loads PNG → canonical ndarray (1024 × 768 × 3).
2. Geometry_F detects parallel-pair walls (outer rectangle + interior divider).
3. OCR_F reads room labels (`거실`, `침실`) + a dimension text (e.g. `820`).
4. Symbol_F finds a door (arc + wall_proximity) + the parallel-pair window.
5. Compose_F attempts scale_anchor extraction.

**Outcome:**
- Walls tagged `type_epistemic = ⊢` (direct parallel-pair evidence).
- Door tagged `type_epistemic = ⊨` (arc + wall_proximity inferred).
- Window tagged `type_epistemic = ⊬` with basis: *"could be balcony_sash without VLM verifier"*.
- Spaces tagged `type_epistemic = ⊢` when room_label is enclosed.
- `scale_anchor.detected = False` → all `measurement_mm = None`, `measurement_epistemic.tag = ⊥`.
- `aggregates.window_count.warning = "1 of 1 window contributors carry ⊬/⊥ type_epistemic; count carries taint"`.

**What this demonstrates:** the engine confidently identifies most objects while *cleanly refusing* to bluff about measurements.

---

## Scenario 2 — Three-room apartment

**Input:** `data/samples/synth_apt_three_room_02.png`

**Flow:** Same pipeline, more complex layout (3 spaces, 2 interior walls, 2 doors).

**Outcome:** More walls + doors → aggregates show `wall_count.value ≈ 5`, `door_count.value = 2`. Spaces with `거실 / 주방 / 침실` labels become `type_epistemic = ⊢`.

**What this demonstrates:** the trust surface scales linearly with object count; aggregates summarize without flattening tags.

---

## Scenario 3 — Open office layout

**Input:** `data/samples/synth_office_open_01.png`

**Outcome:** English labels (`Office`, `Meeting`) classify as `room_label` (Latin path of the classifier). Same trust posture as Scenario 1.

**What this demonstrates:** the pipeline is bilingual (PaddleOCR ko+en); the architecture does not encode Korean-only assumptions.

---

## Scenario 4 — ★ Korean apartment 적산 with **measurement refusal**

**Input:** `data/samples/synth_apt_kr_balcony_01.png` (the load-bearing demo)

**Flow:**
1. Engine detects walls, doors, windows, balcony sash, and spaces.
2. OCR reads dimension text (e.g. `5400`) + Korean labels (`거실 / 안방 / 발코니`).
3. Scale-anchor extraction attempts to match `dimension_text` value `5400` (mm) against the wall span length (in pixels).
4. The cluster check fails — no ≥2 dim-wall pairs agree on a px/mm ratio within ±5%.
5. `scale_anchor.detected = False`.
6. Measurement_Policy fires: `∀ object. measurement_mm = None ∧ measurement_epistemic.tag = ⊥`.
7. `aggregates.measured_wall_length_mm.value = None`, `.epistemic.tag = ⊥`, `.warning = "No reliable scale anchor detected — mm aggregate is null/⊥ by policy"`.
8. UI surfaces the Korean message:

> **"벽체 후보는 검출되었지만, 신뢰 가능한 치수 기준점이 없어 mm 단위 산출에는 포함하지 않았습니다. 검수자 확인이 필요합니다."**

**What this demonstrates — the wedge:**

The engine *successfully* identifies walls, doors, the balcony sash. It *refuses* to convert the wall lengths into millimeters because the scale-anchor signal is insufficient. **A wrong millimeter conversion is worse than no conversion** — the cost system can route a refusal to a human reviewer; it cannot detect a confidently-wrong number until the construction phase.

This is the single scenario that should determine 포비콘's read: *can our auditability posture survive contact with production?*

---

## Scenario 5 — Symbol refusal_candidate

**Input:** any synthetic apartment with at least one arc-like edge that is **not** a door (e.g., where Hough Circles produces a detection but the arc center is far from any wall_candidate).

**Flow:**
1. Symbol_F's door detector finds an arc via `cv2.HoughCircles`.
2. The 2-signal threshold fires:
   - Signal 1: arc detected (`opencv_houghCircles`).
   - Signal 2 ABSENT: arc center is not within `(r + 8px)` of a wall_candidate.
3. The detector emits a `refusal_candidate` with `attempted_type = "door"` and `why_refused = "arc detected at (x,y) r=Npx but no wall_proximity signal — single-signal evidence below 2-signal threshold; could be a non-door arc (logo, chair, decorative)"`.
4. Compose_F promotes this to a top-level `Refusal` with prefix `[door]`.
5. UI shows the refusal heatmap layer over the region.

**What this demonstrates:** the engine **refuses to call something a door** just because an arc is present. The why_refused field is human-readable, specific, and routed to the review surface.

---

## Reading the demo for trust posture

The five scenarios together answer the question:

> "Will the recognition result survive being plugged into a 산출내역서 system?"

| Aspect                      | Answer the demo gives                                          |
|-----------------------------|----------------------------------------------------------------|
| What does the engine know?  | Walls, doors, spaces (when labeled) — `⊢` and `⊨` tags         |
| What does it guess?         | Windows vs balcony_sash — `⊬` with named basis                 |
| What does it refuse?        | Millimeter measurements without scale anchor — `⊥`              |
| What does it abandon?       | Symbol regions below evidence threshold — `refusal_candidates` |
| Where do mistakes go?       | Review queue (review_status = `needs_human`), not the totals   |

The aggregates never silently absorb tainted values — every `⊬` and `⊥` flag propagates with a named warning.

---

*See `docs/README.md` for the engineering thesis, `docs/OUTPUT_CONTRACT.md` for the formal schema.*
