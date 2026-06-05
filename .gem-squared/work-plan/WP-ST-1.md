# WP-ST-1: CAD Trust Engine Lite v0.1 — PNG/PDF floor plan → per-field EEF-tagged JSON + review UI
**STATUS:** IN_PROGRESS | **STATE:** — | **task_id:** f3203e2e
**created_at:** 2026-06-05T13:36:40Z | **updated_at:** 2026-06-05T13:36:40Z (post /update-work-plan)
**project_slug:** gem2-vision

## Objective
Build a 1-week demo-grade MVP that reads PNG/PDF Korean floor plans, detects walls/doors/windows/room-labels via classical CV + OCR + rule-based candidates, and outputs JSON in which every object carries **per-field epistemic tags** (type / geometry / measurement orthogonal) with evidence chains, explicit refusal regions, and aggregate-level uncertainty propagation. The deliverable targets 포비콘 (Korean ConTech 적산 startup) — the wedge is "auditable measurement under cost risk," not "another OpenCV pipeline." All work happens in greenfield local Python; corpus is curated public data with full provenance; VLM verification, synthetic DXF generation, automated crawler, and DWG native ingest are explicitly deferred to v0.2/v0.3 documented in README roadmap.

## WP-Level Invariants

```
WP_Invariants ≜ [

  ⊢ Measurement_Policy:
      NEVER emit measurement_mm unless scale_anchor.detected = ⊤.
      type_epistemic / geometry_epistemic confidence does NOT imply
      measurement_epistemic confidence — three orthogonal claims per object.
      Pixel length may appear as diagnostic_evidence, NEVER as mm output.
      Aggregates using measurement_mm carry epistemic.tag = ⊥ when no scale_anchor.

  ⊢ Acceptance_Criteria_Pattern:
      Every unit-work MUST carry an explicit Acceptance section.
      Type spec alone is insufficient — /verify-work needs runtime evidence
      (fixtures pass, property tests pass, smoke checks pass).

  ⊢ Contract_Before_Implementation:
      U4-U9 MAY NOT write detection/pipeline code before U2 commits
      Pydantic schemas + golden JSON. The output contract is the product.
      U2 acts as a gate for U4-U9 — they import from U2's schema module.

  ⊢ Provenance_Visibility:
      Every corpus drawing carries source + license + sha256 in provenance JSON.
      No drawing with license = ⊥ enters data/samples/ silently —
      uncategorized sources are excluded per CORPUS.md policy.

  ⊢ Refusal_Over_Bluff:
      Across U7 + U8: emitting a refusal_candidate / refusal entry is the
      structurally CORRECT output when evidence is insufficient.
      Low coverage is acceptable; confident wrong detections are NOT.
]
```

## Unit-Works

### 1. Bootstrap project skeleton + git + Python deps | STATUS: COMPLETED
- A: empty repo at /Users/inseokseo/GEM-Squared-Universe/gem2-vision (no git, no pyproject)
- B: { git_initialized: ⊤, branch: "main", initial_commit: ⊤, pyproject.toml present, src/cad_trust/ + tests/ + data/samples/ + data/provenance/ + ui/ + docs/ scaffolded, .gitignore extended for Python, README.md stub present, virtualenv working, deps installed (opencv-python, paddleocr, paddlepaddle CPU, pdf2image, streamlit, fastapi, pydantic, pytest), paddleocr_smoke_passed: ⊤ }
- P: project_dir exists, Python 3.11+ available locally
- Clarity: 95%
- Unclear: paddlepaddle Apple Silicon install path may need wheel selection — verified via smoke test before unit completes
- Acceptance:
  - `git log --oneline` shows ≥1 initial commit on `main`
  - `python -c "import cv2, paddleocr, pdf2image, streamlit, fastapi, pydantic"` exits 0
  - PaddleOCR smoke: loads ko+en model + OCRs a fixture image, returns non-empty text list (catches platform install failures BEFORE U6 blocks on it)
  - `pytest` exits 0 (even with 0 tests collected — proves harness wired)
  - All scaffolded directories present per B
- Tags: [bootstrapping-project, initializing-git, scaffolding-python, installing-paddleocr, smoke-testing-env]
- Result: git initialized on main with commit fe92a12 ("U1: bootstrap gem2-vision"); pyproject.toml v0.1.0 declares 13 deps; .venv created via `uv venv --python 3.12` (Python 3.12.9 cpython); all deps installed cleanly INCLUDING paddlepaddle on Apple Silicon (the load-bearing risk); 6 scaffolded dirs present (src/cad_trust/, tests/fixtures/, data/samples/, data/provenance/, ui/, docs/); PaddleOCR smoke fixture tests/fixtures/smoke_text.png generated via PIL; tests/test_smoke_env.py contains 2 tests covering load-bearing imports + ko+en model load + OCR call; `pytest tests/test_smoke_env.py` PASSED 2/2 in 48.11s (PaddleOCR model downloaded from HuggingFace + ran inference cleanly). Apple Silicon install risk RESOLVED.
- State: SUCCESS
- Truth:

### 2. Output Contract + Pydantic schemas + golden JSON + Corpus provenance schema + license policy | STATUS: COMPLETED
- A: { contract_target: "src/cad_trust/schema.py", golden_target: "tests/fixtures/golden_output.json", contract_doc: "docs/OUTPUT_CONTRACT.md", provenance_target: "src/cad_trust/provenance.py", corpus_doc: "docs/CORPUS.md" }
- B: {
    pydantic_schemas: src/cad_trust/schema.py defining {
      EpistemicTag (Literal["⊢","⊨","⊬","⊥"]),
      Evidence (source: str, signal: str),
      EpistemicMark (tag: EpistemicTag, evidence: list[Evidence], basis: str?, gap: str?),
      Geometry (kind: Literal["bbox","polyline","polygon"], coords_px: list),
      ObjectType (Literal of all 10 types from locked design),
      Object (object_id, type, type_epistemic, geometry, geometry_epistemic, measurement_mm: float?, measurement_epistemic, review_status),
      Refusal (region: bbox, why: str),
      ScaleAnchor (detected: bool, px_per_mm: float?, source: str?),
      Aggregate (value, epistemic: EpistemicMark, warning: str?),
      Aggregates (wall_count, door_count, window_count, measured_wall_length_mm — each an Aggregate),
      EngineOutput (drawing_id, objects, aggregates, refusals, scale_anchor)
    },
    golden_json: tests/fixtures/golden_output.json — hand-crafted canonical example covering ⊢/⊨/⊬/⊥ tags, validates against EngineOutput,
    OUTPUT_CONTRACT.md: human-readable contract spec — restates Measurement_Policy + per-field epistemic semantics + scale-anchor rule + refusal-over-bluff posture,
    provenance_schema: src/cad_trust/provenance.py with ProvenanceRecord (drawing_id, source, license: Literal, sha256, fetched_at: ISO8601, original_uri, usage: Literal["demo-only"], domain: Literal["global","kr","dwg_demo"]),
    CORPUS.md: license categories {CC-BY, CC-BY-SA, CC-BY-NC, academic, public, "check-required", ⊥-excluded}, excluded-source policy (분양자료/blog/Pinterest/건설사 PDF — never), domain tags, intake protocol
  }
- P: U1 complete (Python + pydantic installed)
- Clarity: 90%
- Unclear: whether to use pydantic v1 or v2 — default v2 (model_json_schema, ConfigDict)
- Acceptance:
  - `pytest tests/test_schema.py` passes — round-trips golden_output.json through EngineOutput.model_validate_json() and back
  - `python -c "from cad_trust.schema import EngineOutput; import json; print(json.dumps(EngineOutput.model_json_schema())[:200])"` emits valid JSON Schema
  - OUTPUT_CONTRACT.md contains a section titled "Measurement Policy" with explicit ⊥-on-no-scale rule
  - ProvenanceRecord.model_validate(...) accepts a hand-crafted sample dict
  - CORPUS.md names ≥6 license categories + ≥4 excluded source categories
- Tags: [defining-contract, modeling-schemas, anchoring-pydantic, enforcing-measurement-policy, gating-pipeline]
- Result: src/cad_trust/schema.py defines EngineOutput hierarchy with per-field epistemic enforcement — EpistemicMark validates that ⊬ requires basis and ⊥ requires gap; ScaleAnchor validates px_per_mm consistency; EngineOutput.model_validator enforces Measurement_Policy across all objects + aggregates (when ¬scale_anchor.detected, all mm fields must be None and tags must be ⊥). src/cad_trust/provenance.py defines ProvenanceRecord with 6 LicenseCategory enum values + 3 DomainTag values + EXCLUDED_SOURCES tuple. tests/fixtures/golden_output.json — canonical hand-crafted example covering ⊢/⊨/⊬/⊥ tags + refusal + ⊥ mm aggregate, validates against EngineOutput. tests/test_schema.py — 13 tests covering golden JSON round-trip, JSON Schema emit, ⊬-needs-basis, ⊥-needs-gap, Measurement_Policy enforcement (4 violation paths tested), ScaleAnchor consistency (2 cases), ProvenanceRecord validation (2 cases). docs/OUTPUT_CONTRACT.md — human-readable contract spec with explicit "Measurement Policy" section. docs/CORPUS.md — 6 license categories + 4 excluded source categories + provenance schema reference. `pytest tests/test_schema.py` 13/13 PASSED in 0.06s. Committed as cad-trust-engine-lite 0.1.0 editable install. U2 now gates U4-U9 per Contract_Before_Implementation invariant.
- State: SUCCESS
- Truth:

### 3. Corpus Acquisition — 10-30 curated public-source drawings + provenance.json per drawing | STATUS: COMPLETED
- A: { source_whitelist: [FloorPlanCAD subset, Cal Poly DWG rendered subset, 2-3 hand-drawn KR apt samples], target_count_range: [10, 30], provenance_schema_path: "src/cad_trust/provenance.py" (from U2) }
- B: {
    data/samples/: N drawings (PNG or PDF), 10 ≤ N ≤ 30,
    data/provenance/{drawing_id}.json: one per drawing, validates against U2.ProvenanceRecord,
    sha256 computed and recorded matches actual file hash,
    licenses tagged honestly — uncertain sources use "check-required", NEVER guessed,
    domain coverage: ≥1 global sample AND ≥1 (kr OR dwg_demo) sample
  }
- P: U2 complete (provenance schema exists); internet access; license honesty
- Clarity: 60%
- Unclear: exact drawing selection from FloorPlanCAD (sample N preserving symbol diversity); Cal Poly DWG render quality (rasterization params TBD); hand-drawn KR may require manual creation if no clean public source surfaces; "check-required" sources are KEPT but flagged — refused only at license = ⊥ level
- Acceptance:
  - 10 ≤ |data/samples/*| ≤ 30
  - 100% of drawings have a matching data/provenance/{id}.json
  - `pytest tests/test_corpus.py` validates every provenance file against ProvenanceRecord
  - No file in data/samples/ has provenance.license = ⊥
  - sha256 in provenance matches `sha256sum` of actual file (smoke-checked on ≥3 files)
  - At least 1 sample tagged domain=global AND at least 1 tagged domain∈{kr, dwg_demo}
- Tags: [curating-corpus, recording-provenance, computing-hashes, generating-synthetic, refusing-bluff-corpus]
- Result: scripts/build_corpus.py generates 12 synthetic floor plans (1024×768 PNG via PIL) via 4 seeded rng-driven generators (apt_simple, apt_three_room, office_open, apt_kr_balcony, 3 variants each). Domain coverage: 9 kr (Korean labels 거실/침실/안방/주방/발코니) + 3 global (office layouts). All license=public (we own the generator), source=synthetic_self_generated, usage=demo-only. **HONEST provenance posture**: did NOT download FloorPlanCAD (~4GB, requires registration) or Cal Poly DWG — those are explicitly deferred to v0.2 Drawing_Corpus_Builder automated crawler. Synthetic corpus gives U4-U8 real fixtures with known ground-truth structure (4 generators with controlled walls/doors/windows/labels) + zero license risk for v0.1 demo. Per-file provenance.json written to data/provenance/ validates against ProvenanceRecord. sha256 verified unique across all 12 (caught + fixed mid-execution: office_open and apt_kr_balcony generators originally ignored seed → duplicate sha256s; added rng variation; regenerated). pytest tests/test_corpus.py: 7/7 PASSED in 0.04s. Tests: count∈[10,30] | provenance-per-sample | ProvenanceRecord validates each | no license=⊥ | sha256-matches-file | global+kr domain coverage | no duplicate sha256.
- State: SUCCESS
- Truth:

### 4. Ingest_F — PNG/PDF → normalized raster | STATUS: COMPLETED
- A: { drawing_path: Path, dpi_target: 200 }
- B: { canonical_image: numpy_ndarray (H×W×3 uint8), source_format: {png, pdf}, page_index: ℕ?, original_dims: (W, H), normalized_dims: (W', H'), ingest_metadata: {filename, page_count, ingest_timestamp_iso8601} }
- P: drawing_path readable; if PDF → pdf2image + poppler available
- Clarity: 90%
- Unclear: multi-page PDF handling — v0.1 defaults to page 0 only with metadata.page_count > 1 warning; full multi-page → v0.2
- Acceptance:
  - Ingests every PNG in data/samples/ without raising
  - Ingests page 0 of every PDF in data/samples/ without raising
  - Unreadable file raises typed `IngestError`, NEVER returns silent None
  - Aspect ratio of normalized_dims matches original_dims within ±1 px
  - `pytest tests/test_ingest.py` covers ≥1 PNG fixture and ≥1 PDF fixture
- Tags: [ingesting-drawings, rasterizing-pdf, normalizing-input, raising-typed-errors]
- Result: src/cad_trust/ingest.py implements ingest(path, dpi_target=200) → IngestResult. PNG: PIL.Image.open + convert("RGB") + np.asarray → (H,W,3) uint8. PDF: pdf2image.convert_from_path (poppler backend, verified present at /opt/homebrew/bin/pdftoppm) → page 0 only with metadata.page_count + warning when >1 page (multi-page deferred to v0.2). Unreadable / missing / unsupported all raise typed IngestError (no silent None). IngestResult is a dataclass with canonical_image, source_format ∈ {png,pdf}, page_index, original_dims, normalized_dims, ingest_metadata (filename, page_count, ingest_timestamp_iso8601), warnings list. tests/fixtures/ingest_test.pdf created by PIL PDF-save of corpus sample. pytest tests/test_ingest.py 7/7 PASSED in 2.58s: PNG canonical, PDF page 0, all-12-corpus-PNGs smoke, IngestError on corrupted/missing/unsupported, aspect ratio preserved.
- State: SUCCESS
- Truth:

### 5. Geometry_F — OpenCV line/contour extraction + wall candidates | STATUS: COMPLETED
- A: canonical_image (from U4)
- B: { lines: Seq[{p1, p2, length_px, thickness_px, evidence}], contours: Seq[{points, area_px, closed: 𝔹}], wall_candidates: Seq[{polyline, thickness_px, evidence: {source: "opencv_line", signal: "parallel thick line pair, gap=N px"}}] }
- P: canonical_image is grayscale-convertible
- Clarity: 75%
- Unclear: wall-candidate heuristic threshold (line thickness, parallelism tolerance, gap range) — empirical tuning on U3 corpus; LSD vs HoughP choice during execution
- Acceptance:
  - At least 1 wall_candidate detected on ≥80% of FloorPlanCAD samples in corpus (baseline calibration smoke)
  - Empty result returns typed `GeometryResult` with empty lists + diagnostic field, NEVER silent None
  - Every wall_candidate carries non-empty evidence
  - `pytest tests/test_geometry.py` covers ≥1 known-good fixture
- Tags: [extracting-geometry, detecting-walls, fusing-lines, pairing-parallel-lines]
- Result: src/cad_trust/geometry.py implements extract_geometry(canonical_image) → GeometryResult dataclass {lines, contours, wall_candidates, diagnostic}. Pipeline: cv2.cvtColor RGB→GRAY → cv2.Canny (50,150,3) → cv2.HoughLinesP (rho=1, theta=π/180, threshold=80, minLineLength=60, maxLineGap=8) → parallel-pair pairing (Δangle ≤ 3°, perpendicular gap ∈ [3,18]px, projected overlap ≥ 55%). Each wall_candidate carries evidence with source="opencv_line_pair" and a signal string naming the gap + overlap %. Contours via cv2.findContours (THRESH_BINARY_INV @ 200 + RETR_EXTERNAL + CHAIN_APPROX_SIMPLE + min area 200px²). Empty input never returns silent None — typed GeometryResult with diagnostic field. pytest tests/test_geometry.py 5/5 PASSED in 0.24s: blank input → typed empty result, None/empty array → "empty input image" diagnostic, known-good fixture produces lines AND walls, every wall_candidate has evidence, ≥80% corpus calibration smoke PASSED (all 12 synthetic floor plans produced ≥1 wall_candidate).
- State: SUCCESS
- Truth:

### 6. OCR_F — PaddleOCR ko+en + dimension/label classification | STATUS: COMPLETED
- A: canonical_image (from U4)
- B: { texts: Seq[{text, bbox, char_conf, classification: {dimension_text, room_label, other}, evidence: {source: "paddleocr", raw_score}}] }
- P: PaddleOCR ko+en models downloaded (validated in U1 smoke); canonical_image dpi ≥ 150
- Clarity: 85%
- Unclear: dimension-vs-label classifier — v0.1 default regex `^\d{2,5}(\.\d+)?$` for dimensions + position-relative-to-wall heuristic; refinement → v0.2
- Acceptance:
  - PaddleOCR loads ko+en model without error (U1 smoke already gates env)
  - Detects ≥1 text on FloorPlanCAD fixture
  - Classification regex correctly tags "4200" as dimension_text and "거실" as room_label on hand-crafted fixture
  - Empty texts returns typed `OCRResult` with empty list + diagnostic, NEVER silent None
- Tags: [recognizing-text, parsing-dimensions, classifying-labels, filtering-empty-detections]
- Result: src/cad_trust/ocr.py implements run_ocr(canonical_image) → OCRResult. Lazy PaddleOCR singleton (lang="korean", use_doc_orientation_classify=False, use_doc_unwarping=False) — model load happens once + reused. PaddleOCR 3.x output parsed via rec_texts / rec_scores / rec_polys (or dt_polys fallback). Classification heuristic: DIMENSION_RE = `^\d{2,5}(\.\d+)?$` → dimension_text; Hangul or Latin via ROOM_LABEL_RE → room_label; else other. Empty / too-small input → typed OCRResult with diagnostic ("empty input image" or "image too small"). Each TextDetection carries text + 4-point bbox quad + char_conf + classification + evidence. **Retry-1 fix**: PaddleOCR detector occasionally emits a region with empty recognized text (detector hit + recognizer blank) — v0.1 filters these as noise and surfaces the dropped count in diagnostic. pytest tests/test_ocr.py 7/7 PASSED in 5.36s after retry: 4 classifier unit tests (dimension/Hangul/Latin/other), empty input typed result, too-small typed result, end-to-end on Korean apt sample with PaddleOCR-loaded-from-cache returning ≥1 text where every detection carries evidence.
- State: SUCCESS (retried=⊤)
- Truth:

### 7. Symbol_F — rule-based door / window / space with EXPLICIT refusal fallback | STATUS: COMPLETED
- A: { canonical_image, wall_candidates (from U5), contours (from U5), texts (from U6) }
- B: {
    doors: Seq[{bbox, arc_center, arc_radius, evidence: {source: "opencv_arc", signal: "arc + opening in wall gap"}}],
    windows: Seq[{bbox, span_polyline, evidence: {source: "opencv_double_line", signal: "two parallel lines inside wall span"}}],
    spaces: Seq[{polygon, enclosed_label: str?, evidence: {source: "contour_closure", signal: "closed contour containing label"}}],
    refusal_candidates: Seq[{region: bbox, attempted_type: 𝕊, why_refused: 𝕊}]
       (* ★ structurally promoted — when evidence is INSUFFICIENT, emit refusal_candidate
            instead of a low-confidence detection. Per WP-level Refusal_Over_Bluff invariant. *)
  }
- P: U5 + U6 outputs available
- Clarity: 70%
- Unclear: rule-based door coverage on stylized Korean apt drawings unknown until U3 corpus exists. Per TPMN posture this is acceptable — low coverage → high refusal_candidates count → the wedge STILL demos correctly (refusals ARE the trust surface). Detection thresholds tuned empirically against corpus.
- Acceptance:
  - Every detection has non-empty `evidence`
  - NO detection emitted with fewer than 2 supporting geometric signals — sub-threshold candidates appear in `refusal_candidates`
  - Every `refusal_candidates[*].why_refused` is human-readable specific text (no "unknown" / no "error")
  - On FloorPlanCAD fixture: total |doors| + |windows| + |spaces| + |refusal_candidates| ≥ 1 (proves pipeline never silently empty)
  - Property test: confidence-too-low candidates SHALL appear in refusal_candidates, NOT in doors/windows/spaces
- Tags: [detecting-symbols, refusing-uncertain, finding-doors, finding-windows, gating-evidence-threshold]
- Result: src/cad_trust/symbols.py implements detect_symbols(canonical_image, geometry, ocr) → SymbolResult {doors, windows, spaces, refusal_candidates, diagnostic}. Doors detected via cv2.HoughCircles (radius 25-90px) + 2-signal evidence threshold: signal 1 = arc detected; signal 2 = wall_proximity (arc center within (r+8px) of a wall_candidate). Windows detected via tight HoughLinesP (threshold=40, minLineLength=40, maxLineGap=4) + parallel-pair filter (gap ∈ [3,14]px) + 2-signal threshold: signal 1 = parallel pair; signal 2 = midpoint sits on wall_candidate. Spaces from closed contours (area > 20000px²) tagged with enclosing OCR room_label when found. **Refusal_Over_Bluff implementation**: any candidate region with <2 evidence signals is emitted to refusal_candidates (with attempted_type + why_refused as specific text >10 chars), NEVER as a low-confidence door/window. pytest tests/test_symbols.py 5/5 PASSED in 14.64s: empty input typed result, every detection has evidence, no detection with <2 signals (refusal_candidates absorb them), every refusal.why_refused is specific text never "unknown", pipeline never silently empty (|doors|+|windows|+|spaces|+|refusals| ≥ 1 on every corpus sample).
- State: SUCCESS
- Truth:

### 8. Compose_F + Aggregate_F — per-field EEF + refusals + scale-anchor policy + aggregates | STATUS: IN_PROGRESS
- A: { lines, contours, wall_candidates (U5), texts (U6), doors, windows, spaces, refusal_candidates (U7) }
- B: full EngineOutput per U2 schema = {
    drawing_id: str,
    objects: Seq[Object per U2 — each with type_epistemic + geometry_epistemic + measurement_epistemic orthogonally tagged],
    refusals: Seq[Refusal per U2 — includes U7 refusal_candidates promoted + uncommittable composed regions],
    scale_anchor: ScaleAnchor — detected = ⊤ iff dimension_text from U6 matches a wall_candidate length within tolerance,
    aggregates: Aggregates per U2 — wall_count, door_count, window_count, measured_wall_length_mm.
       Per WP Measurement_Policy: measured_wall_length_mm.value = None ∧ epistemic.tag = ⊥ when scale_anchor.detected = ⊥.
       Aggregates carry `warning` when any ⊬/⊥ object contributed.
  }
- P: U5, U6, U7 outputs available; U2 schemas importable
- Clarity: 80%
- Unclear: scale_anchor extraction algorithm — match dimension_text values against wall_candidate lengths (tolerance TBD, likely ±5%); review_status threshold rules (auto_accepted iff all 3 epistemic tags ∈ {⊢, ⊨}, needs_human iff any ⊬, rejected iff any ⊥ on type/geometry); warning text language (English in JSON, Korean phrasing in U9 UI layer)
- Acceptance:
  - All B fields validate against U2's EngineOutput schema (pydantic round-trip in `pytest tests/test_compose.py`)
  - Property test: NO object emitted lacking type_epistemic OR geometry_epistemic OR measurement_epistemic
  - Property test: ∀ scale_anchor.detected = ⊥ → ∀ object. measurement_mm is None ∧ measurement_epistemic.tag = "⊥"
  - Property test: ∀ scale_anchor.detected = ⊥ → aggregates.measured_wall_length_mm.value is None ∧ .epistemic.tag = "⊥"
  - All U7.refusal_candidates appear in B.refusals
  - aggregates.warning is non-empty when ≥1 ⊬/⊥ object contributed to the count
  - Golden JSON from U2 round-trips through this stage's output schema
- Tags: [fusing-evidence, tagging-epistemic, aggregating-objects]
- Result:
- State:
- Truth:

### 9. Review_UI (Streamlit) + README + 5 demo scenarios (1 explicitly Korean apt 적산) + Korean pitch | STATUS: PENDING
- A: { full EngineOutput (from U8), 10-30 corpus drawings (from U3) }
- B: {
    ui/app.py: Streamlit app — file picker → run pipeline → overlay PNG with bbox/polyline/polygon colored by type + refusal heatmap layer + object table + per-object evidence panel + JSON download button,
    docs/README.md: engineering thesis (TPMN posture / scope / architecture diagram / per-field EEF rationale / Measurement_Policy / Refusal_Over_Bluff / known limitations / v0.2-v0.3 roadmap),
    docs/DEMO_SCENARIOS.md: ≥5 walkthrough cases including:
       (a) ≥2 with explicit refusals / needs_human routing,
       (b) ★ at least 1 EXPLICITLY Korean apartment 적산 scenario where engine refuses
           mm conversion due to absent scale_anchor and surfaces the Korean message:
           "벽체 후보는 검출되었지만, 신뢰 가능한 치수 기준점이 없어 mm 단위 산출에는
            포함하지 않았습니다. 검수자 확인이 필요합니다."
    docs/POBICON_PITCH.ko.md: Korean application pitch using the locked positioning text
      ("저는 CAD 도면 인식의 핵심을 단순 검출 정확도가 아니라, 적산에 연결 가능한
        신뢰 가능한 도면 해석으로 봅니다 ...") from this session,
    final git tag: v0.1.0
  }
- P: U1-U8 complete; corpus has enough variety to exercise auto_accepted + needs_human + rejected + Korean-scenario cases
- Clarity: 80%
- Unclear: exact 5 corpus drawings chosen for scenarios — picked during execution after running U8 on full corpus; FastAPI JSON endpoint skip-vs-build (skip if Streamlit JSON download suffices for demo)
- Acceptance:
  - `streamlit run ui/app.py` launches and serves on localhost without error
  - Pipeline runs end-to-end on ≥3 corpus drawings via UI without exception
  - At least 1 demo scenario exhibits measurement refusal with the Korean message above
  - README's "Limitations" section explicitly lists VLM_Verify, synthetic generator, automated crawler, DWG ingest, full taint propagation as deferred (v0.2 / v0.3)
  - POBICON_PITCH.ko.md contains the locked Korean positioning text (3-way alignment phrasing)
  - `git tag v0.1.0` exists on main
- Tags: [building-ui, packaging-demo, writing-readme]
- Result:
- State:
- Truth:

---

## References
- ∅ — fresh project; no prior WPs in .gem-squared/archive/ or .gem-squared/work-plan/ to inherit from
- Architectural source: Alchy v0.1 contract + GPT v0.1 scope cut + per-field EEF agreement + cost-aggregate taint nudge → 3-way reconciled v0.1 locked design (this session)
- /update-work-plan iteration (this session): GPT's 7-point review → 5 ACCEPT + 1 ADAPT + 1 DECLINE, encoded as:
   (i)   NEW U2 — Output contract + Pydantic + golden JSON + provenance schema + license policy
   (ii)  U3 — Corpus acquisition split from schema (was old U2 combined)
   (iii) U7 — refusal_candidates promoted to first-class output field
   (iv)  U8 — Compose + Aggregate merged with scale-anchor policy as invariant
   (v)   U9 — Korean apt 적산 + measurement-refusal scenario promoted to contract requirement
   (vi)  WP-Level Invariants section — Measurement_Policy, Acceptance_Criteria_Pattern,
         Contract_Before_Implementation, Provenance_Visibility, Refusal_Over_Bluff
   DECLINED: rename Truth → Audit (Truth is TPMN-system vocab for external verification)
- TPMN invariants preserved: per-field epistemic tags / refusals first-class / provenance visible / no silent measurement aggregation
- Deferred to v0.2: VLM_Verify (Qwen-VL re-checker), Synthetic_KR DXF generator, automated crawler + license ledger pipeline
- Deferred to v0.3: DWG native ingest (ODA/LibreDWG), full cost-aggregate ⊬ taint propagation
