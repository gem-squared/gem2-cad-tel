# Hybrid Floor-Plan Vision — Design Specification

**Status:** Human-approved design

**Approved:** 2026-08-25

**Project:** `gem2-cad-tel` / CAD Trust Engine Lite

**Planning boundary:** Design only; implementation is divided into three subsequent work plans.

## 1. Objective

Improve the engine from a rule-based demonstration into a benchmark-driven hybrid vision pipeline that detects the core quantity-takeoff objects in rasterized architectural floor plans:

- walls;
- doors;
- windows;
- room or space regions; and
- dimension text, dimension lines, and scale anchors.

The objective is measurable improvement over the current v0.1 pipeline on a frozen, labeled evaluation set. It is not a claim that the engine can recognize every possible floor plan universally. Generalization claims remain bounded by the evaluated drawing styles and sources.

The existing trust posture remains constitutive: the engine must preserve per-claim evidence, EEF marks, explicit refusal, Measurement Policy, auditability, and Human authority over final acceptance.

## 2. Scope

### 2.1 Included inputs

- PNG, JPG/JPEG, and rasterized PDF pages.
- Architectural floor plans across multiple drawing styles, languages, resolutions, scan qualities, rotations, and symbol conventions.
- A single, explicitly selected floor-plan page per pipeline invocation.

### 2.2 Excluded inputs

- elevations;
- sections;
- schedules and tables;
- detail sheets;
- MEP-only sheets;
- photographs of buildings;
- native DWG/DXF interpretation;
- multi-page document orchestration; and
- mixed sheets containing floor plans alongside elevations, sections, schedules, or details.

Mixed sheets are refused with a specific page-type reason in this iteration. Region isolation requires a separate future contract.

### 2.3 Included object semantics

The detector commits only to geometry that its evidence supports. A generic `wall` type must be available so that an unclassified wall is not mislabeled as `wall_structural`. Wet, dry, structural, fire-rated, or material subtypes remain unknown unless separately evidenced.

Room identity and room geometry remain separate claims: a space polygon may be valid even when its OCR label is unknown, and a text label does not by itself prove the enclosing polygon is a room.

## 3. Architectural design

```text
Rasterized drawing
        |
        v
Input validation and normalization
        |
        v
FloorPlanGuard ---------------------> full-page refusal when unsupported
        |
        v
+-------------------------------+
| Wall/Space Segmenter          |
| Door/Window Detector          |
| Dimension OCR + Line Detector |
+-------------------------------+
        |
        v
Spatial association and geometry reconciliation
        |
        v
Cross-check, confidence calibration, and refusal policy
        |
        v
EEF claim composition
        |
        v
EngineOutput + Audit DB + Review UI
```

The class-specific experts do not directly produce accepted `Object` records. They produce typed candidate claims. A separate fusion layer owns reconciliation, calibration, EEF assignment, and refusal routing.

### 3.1 Input validation and normalization

This component:

- validates file type and decoded image shape;
- enforces pixel-count, page-count, memory, and inference-time limits;
- normalizes color, contrast, orientation, and resolution without changing the source artifact;
- records every transformation and its parameters; and
- preserves coordinates required to map normalized detections back to source pixels.

### 3.2 FloorPlanGuard

`FloorPlanGuard` distinguishes supported floor-plan pages from elevations, sections, schedules, details, photographs, and unsupported mixed sheets.

- Supported page: inference continues.
- Unsupported, mixed, or ambiguous page: the engine returns no object commitments, a full-page refusal, a false scale anchor, and an auditable guard decision.

### 3.3 Wall/Space Segmenter

This expert produces wall masks or polygons and room/space masks or polygons. It is responsible for regional geometry, not semantic wall subtype or room name.

Post-processing may derive wall centerlines and connected components, but the source mask or polygon remains available as evidence. Topology repair is permitted only through deterministic, recorded operations.

### 3.4 Door/Window Detector

This expert detects discrete door and window instances and their spans. Candidate geometry is reconciled against wall geometry:

- intersection or attachment to a wall supports the candidate;
- disagreement downgrades or refuses the claim;
- proximity alone is not sufficient to auto-accept a semantic type; and
- window versus balcony-sash ambiguity remains explicit unless supported by additional evidence.

### 3.5 Dimension OCR and spatial association

OCR identifies dimension text. A separate line/arrow/extension-line detector identifies dimension geometry. The association layer links text to a specific dimension line and measured object or span.

Scale-anchor extraction must use these spatially associated pairs. The current Cartesian comparison of every dimension value against every wall length is prohibited. Two or more independent, spatially valid anchors must agree before global millimetre conversion is allowed. Conflicting anchors produce a refusal and keep measurements unknown.

### 3.6 Candidate and expert contracts

Each expert returns a versioned result containing:

- producer and model identifier;
- model artifact digest;
- preprocessing configuration;
- candidate class;
- source-pixel geometry;
- raw and calibrated confidence values;
- direct evidence references;
- diagnostic warnings; and
- explicit unavailable or failed state.

Numeric confidence is a model signal, not an EEF mark and not Human Truth. The fusion layer converts evidence and agreement into bounded EEF claims under explicit policy.

### 3.7 Fusion, EEF, and refusal

The fusion layer may accept a candidate, downgrade it to Human review, or refuse it. It may reconcile overlapping geometry through a deterministic rule, but it may not invent a class or geometry absent from expert output.

Refusal reasons distinguish at least:

- unsupported page type;
- expert unavailable;
- insufficient confidence;
- cross-expert disagreement;
- invalid or disconnected geometry;
- ambiguous semantic subtype;
- missing dimension association; and
- conflicting scale anchors.

The existing `EngineOutput` remains the public result boundary. Schema evolution must be backward-compatible and add generic wall semantics plus reproducibility metadata without silently reinterpreting existing fields.

## 4. Dataset and annotation design

### 4.1 Corpus construction

The project will establish a license-audited corpus representative of the supported floor-plan domain. The corpus must include diversity across:

- source organizations or datasets;
- synthetic versus real drawings;
- drawing and symbol conventions;
- Korean and non-Korean text;
- raster quality and resolution;
- clean exports versus scans; and
- simple versus dense layouts.

The existing corpus may seed this work, but orphan provenance records are reconciled before selection. A drawing without a valid source, license, digest, and usable image cannot enter a split.

### 4.2 Annotation contract

Annotations use class-appropriate geometry:

- walls: masks or polygons, with optional centerlines as derived annotations;
- rooms/spaces: polygons or instance masks;
- doors/windows: instance boxes plus attachment spans where visible;
- dimension text: transcription and quadrilateral;
- dimension geometry: line or polyline, endpoints, and extension lines where visible; and
- dimension association: the specific object or span measured by the dimension.

Ambiguous or illegible instances are marked as such and excluded from ordinary positive/negative scoring rather than forced into a class.

### 4.3 Split discipline

Train, validation, and test splits are separated by source family or drawing family, not by random page alone. Near-duplicates, revisions, adjacent pages from one set, and synthetic variants generated from one template cannot cross splits.

The test split is frozen before model tuning. Test annotations are not used to select thresholds, architectures, augmentations, or checkpoints.

### 4.4 Annotation quality assurance

The annotation process includes:

- written labeling guidance with positive, negative, and ambiguous examples;
- automated schema and geometry validation;
- double review of the frozen test split;
- inter-annotator agreement sampling; and
- immutable dataset manifests with file and annotation digests.

## 5. Evaluation and acceptance

### 5.1 Frozen baseline

The current v0.1 pipeline is executed on the frozen evaluation set before hybrid model work. Its raw output, runtime, failures, refusals, and metrics form the baseline artifact.

The metric definitions, macro-score weighting, critical-class designation, and promotion comparison procedure are frozen and Human-approved in WP 1 before the baseline is calculated. They cannot be changed after examining test results.

### 5.2 Class-specific metrics

- Walls and rooms: mask or polygon IoU, instance recall, boundary quality, and topology/connectivity checks.
- Doors and windows: precision, recall, and mean average precision at documented IoU thresholds.
- Dimension OCR: exact-match rate and character error rate.
- Dimension association: correct text-to-dimension and dimension-to-object association rate.
- Scale anchors: false-anchor rate and relative scale error on drawings with valid ground truth.
- Trust behavior: accuracy among committed claims, refusal rate, coverage, and risk-versus-coverage curves.
- Operations: latency, peak memory, artifact size, and expert failure rate.

### 5.3 Promotion rule

A candidate hybrid release is promotable only when:

1. it improves the declared macro benchmark over the frozen v0.1 baseline;
2. no critical object class regresses without an explicit Human waiver and recorded rationale;
3. false scale-anchor rate does not regress;
4. no Measurement Policy violation occurs;
5. results are reproducible from versioned data, configuration, and model artifacts; and
6. the Human acceptance gate approves the evidence package.

Benchmark improvement is decision support. It does not automatically establish production truth or universal floor-plan coverage.

## 6. Model selection policy

The hybrid architecture fixes component roles but does not prematurely fix one vendor or model family. Within the implementation WP, each learned expert receives a bounded bake-off of no more than two technically and legally acceptable candidates.

Selection uses the frozen validation set and considers:

- class-specific quality;
- calibration and refusal behavior;
- CPU/GPU latency and memory;
- artifact size;
- license compatibility; and
- maintainability in the current Python/Docker deployment.

The test split is used only after candidate and threshold selection. A Human records the final model choice and basis.

## 7. Runtime and failure semantics

- Input decode, normalization, or FloorPlanGuard infrastructure failure: pipeline `FAILURE`.
- Valid non-floor-plan or unsupported mixed sheet: valid refused result, not a crash.
- One expert unavailable or timed out: other experts may continue; affected classes receive explicit refusals and the audit run is `DEGRADED`.
- OCR present but dimension association absent: object detection may continue, while scale and physical measurements remain unknown.
- Conflicting anchors: scale is refused even when individual OCR values are confident.
- Corrupt or digest-mismatched model artifact: affected expert does not run.
- No candidate produced: diagnostic evidence distinguishes a valid empty result from unavailable inference.

Fallback to the legacy detector is permitted only when explicitly configured and visibly recorded. Legacy output cannot be presented as hybrid output.

## 8. Review UI and audit integration

The existing UI will expose:

- source image and normalized image;
- per-expert overlays;
- fused output overlay;
- candidate confidence and calibration state;
- model and dataset version metadata;
- evidence and disagreement details;
- refusal regions and reasons; and
- benchmark comparison summaries.

This iteration does not build a complete annotation editor or automated learning-from-review loop. Human review remains an acceptance and diagnostic surface; any future correction workflow requires its own contract.

Audit records must connect each run to source digest, preprocessing configuration, expert versions, model digests, thresholds, fusion policy version, output schema version, runtime statistics, refusals, and final exit state.

## 9. Testing strategy

### 9.1 Contract tests

- Candidate and expert result validation.
- Backward-compatible `EngineOutput` parsing.
- Generic wall semantics without forced structural classification.
- Measurement Policy and scale-anchor association invariants.
- Audit metadata completeness.

### 9.2 Component tests

- Normalization and coordinate round trips.
- FloorPlanGuard positive, negative, and ambiguous fixtures.
- Wall/space post-processing and topology.
- Door/window attachment reconciliation.
- OCR parsing and spatial association.
- Confidence calibration and refusal routing.

### 9.3 Failure tests

- malformed and oversized inputs;
- model load and digest failures;
- expert timeout or out-of-memory simulation;
- partial expert availability;
- conflicting scale anchors; and
- valid unsupported page refusal.

### 9.4 Benchmark and regression tests

Fast CI uses unit, contract, and small fixture tests. The frozen benchmark runs in a separate reproducible evaluation job because model inference is materially heavier. Benchmark artifacts include configuration, environment, metrics, per-drawing results, and failures.

### 9.5 End-to-end tests

- Input through hybrid pipeline to valid output.
- Audit replay and metadata traceability.
- UI overlay and evidence rendering.
- Docker artifact load and health checks.
- Legacy-path behavior when explicitly enabled.

## 10. Security and operational constraints

- Enforce decoded pixel and upload-size limits before inference.
- Use collision-resistant temporary paths rather than user filenames.
- Apply per-expert timeout and memory budgets.
- Treat model artifacts and dataset manifests as versioned supply-chain inputs with digests.
- Do not store BYO API keys; VLM remains outside the primary detection path.
- Do not log uploaded image content or sensitive OCR text unless the deployment policy explicitly allows it.

## 11. Work-plan decomposition

### WP 1 — Benchmark and annotation foundation

Establish the dataset contract, source and license inventory, annotation schema, split discipline, QA process, evaluation harness, and frozen v0.1 baseline. This WP produces evidence but no trained production candidate.

### WP 2 — Hybrid vision experts and cross-checking

Implement input normalization, FloorPlanGuard, wall/space segmentation, door/window detection, dimension geometry and OCR association, typed expert adapters, fusion, calibration, refusal policy, and versioned model packaging. Candidate selection occurs through the bounded validation-set bake-off.

### WP 3 — Trust integration, regression evaluation, and review UI

Integrate the hybrid pipeline with `EngineOutput`, audit storage, failure states, Streamlit evidence views, Docker runtime, regression tests, and the frozen benchmark. Produce the final evidence package for Human promotion or rejection.

The three WPs are sequential: WP 2 requires the accepted benchmark contract and baseline from WP 1; WP 3 requires versioned candidate artifacts from WP 2.

## 12. Explicit non-goals

- Universal recognition of all architectural documents.
- Elevation, section, schedule, detail, MEP, or photograph detection.
- Native DWG/DXF parsing.
- Multi-page document orchestration or mixed-sheet region isolation.
- Material, structural, fire-rating, or wet/dry wall classification without direct evidence.
- Automated cost estimation.
- VLM as primary detector.
- Automatic production promotion from benchmark scores.
- A full annotation or Human-correction product.
- Continuous online learning from reviewer actions.

## 13. Authority and evidence boundary

The system produces candidate detections, evidence, calibrated metrics, refusals, and audit records. Those artifacts may support a Human decision. They do not own final Truth/False judgment, production acceptance, or quantity-takeoff liability.
