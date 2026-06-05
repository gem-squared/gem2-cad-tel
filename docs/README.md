# CAD Trust Engine Lite — Engineering Thesis

**Version:** 0.1.0 | **Project:** gem2-vision | **Target audience:** 포비콘 (Korean ConTech, automated 적산)

---

## Thesis

CAD drawing recognition for construction is **not an object-detection problem**. It is an **auditable measurement problem under cost risk**. A misrecognized wall means a wrong material order — millions of KRW. So the engine's primary deliverable is not "detections" but **a per-claim trust surface**: every output carries an evidence chain, a per-field epistemic tag, and the explicit refusal regions that mark what the engine *will not commit on*.

This is the structural difference from a generic OpenCV+OCR pipeline:

> A detector gives answers. A trust engine gives **answers, evidence, uncertainty, refusal, and review path**.

---

## TPMN Posture (the wedge)

Every detected object carries **three orthogonal epistemic claims**:

| Mark                    | Question it answers                  |
|-------------------------|--------------------------------------|
| `type_epistemic`        | Is this really a wall / door / ... ? |
| `geometry_epistemic`    | Is this the right shape / extent ?   |
| `measurement_epistemic` | Is the mm measurement reliable ?     |

The engine may be *confident this is a wall* (⊨), *confident of its pixel shape* (⊢), and *yet refuse to claim it is 4,200 mm* (⊥). Conflating these collapses the trust surface — and that collapse is what makes black-box detectors unsafe for 적산 systems.

### EEF taxonomy

| Tag | Name         | When                                              |
|-----|--------------|---------------------------------------------------|
| ⊢   | GROUNDED     | Direct evidence (OCR hit, exact geometry match)   |
| ⊨   | INFERRED     | Derived from ⊢ with visible chain                 |
| ⊬   | EXTRAPOLATED | Beyond evidence — `basis` MUST name the leap      |
| ⊥   | UNKNOWN      | Knowledge gap — `gap` MUST name what's missing    |

`⊬` and `⊥` are **structurally enforced** by the Pydantic validator at the schema layer. The contract refuses to accept an extrapolation without a stated basis.

### Measurement Policy (load-bearing invariant)

> **Never emit `measurement_mm` unless `scale_anchor.detected = True`.**

A pixel length is not a millimeter measurement. Without a scale anchor (extracted by matching dimension-text values against wall span lengths within ±5%), the engine refuses mm conversion across all objects AND the mm aggregate. The Pydantic `model_validator` enforces this at the schema boundary — it is impossible to construct an `EngineOutput` that violates the policy.

### Refusal Over Bluff

When evidence is insufficient (fewer than 2 supporting signals), the engine emits a `refusal_candidate` rather than a low-confidence detection. These promote to top-level `EngineOutput.refusals` with `attempted_type` and human-readable `why_refused`. Low coverage is acceptable; confident-wrong detections are not.

---

## Architecture

```
PNG/PDF input
   │
   ▼ U4 Ingest_F          → IngestResult (canonical ndarray + metadata)
   │
   ▼ U5 Geometry_F        → GeometryResult (lines + contours + wall_candidates)
   │
   ▼ U6 OCR_F             → OCRResult (texts + dim/label classification)
   │
   ▼ U7 Symbol_F          → SymbolResult (doors + windows + spaces + refusal_candidates)
   │
   ▼ U8 Compose_F+Agg_F   → EngineOutput
                              ↳ objects (per-field EEF)
                              ↳ aggregates (with taint warnings)
                              ↳ refusals (first-class)
                              ↳ scale_anchor (gates mm)
   │
   ▼ U9 Streamlit Review UI
```

The output contract (U2) was committed **before** detection code (U4-U9) — per the `Contract_Before_Implementation` invariant, the schema gates the implementation, not the other way around.

---

## Scope (v0.1)

| ✅ In v0.1                              | ❌ Deferred to v0.2 / v0.3                |
|-----------------------------------------|-------------------------------------------|
| PNG + PDF ingest                        | DWG native ingest (ODA/LibreDWG) → v0.3   |
| OpenCV line / contour / wall extraction | YOLO / RT-DETR finetuning → v0.2          |
| PaddleOCR (ko + en) + dim/label classify| VLM_Verify (Qwen-VL re-checker) → v0.2    |
| Rule-based door/window/space            | Synthetic KR apartment generator → v0.2   |
| Per-field EEF + refusals                | Automated dataset crawler + ledger → v0.2 |
| Scale-anchor extraction (px↔mm)         | Full cost-aggregate ⊬ taint math → v0.3   |
| Streamlit review UI                     | Multi-page PDF → v0.2                     |
| Curated mini-corpus + provenance        |                                           |

---

## Limitations (named honestly)

- **Corpus is 100% synthetic** in v0.1 (12 self-generated floor plans, license=`public`). Real public-source drawings (FloorPlanCAD, Cal Poly DWG) deferred to v0.2's automated crawler.
- **Detection is rule-based.** No fine-tuned model. Korean stylized symbols may fall below v0.1 thresholds → flow to `refusals`. This is *acceptable per the Refusal_Over_Bluff invariant*, not a failure.
- **No DWG support yet.** The ingest contract is shaped for `.dwg` but v0.1 ingests `.png` and `.pdf` only.
- **Single-page PDF only.** Multi-page PDFs are warned + ingest page 0 (rolling to v0.2).
- **No VLM semantic verification.** A `⊬`-tagged window could be a balcony sash; the `basis` field names this honestly. VLM re-check lands in v0.2.

---

## Reproducing the demo

```bash
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
.venv/bin/python scripts/build_corpus.py    # regenerates 12 synthetic drawings
pytest                                       # full suite
streamlit run ui/app.py                      # localhost demo
```

---

## Roadmap

**v0.2 (next):** VLM_Verify (Qwen-VL re-checker on ⊬ regions), Synthetic KR DXF generator with real Korean apt patterns, automated dataset crawler + license ledger pipeline, YOLO finetune on assembled corpus, multi-page PDF.

**v0.3:** DWG native ingest via ODA/LibreDWG, full cost-aggregate ⊬ taint propagation through quantity-takeoff calculations, web API for 산출내역서 integration.

---

*See also: `docs/OUTPUT_CONTRACT.md` (the formal contract), `docs/CORPUS.md` (corpus policy), `docs/DEMO_SCENARIOS.md` (5 walkthroughs), `docs/POBICON_PITCH.ko.md` (Korean application pitch).*
