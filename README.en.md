[한국어](README.md) · **English**

---

# CAD Trust Engine Lite

**Auditable Floor-Plan Intelligence for Quantity Takeoff (적산)**

*Designed and implemented by David Seo of GEM².AI*

## 🟢 Live Demo

**[https://cad-tel.gemsquared.ai](https://cad-tel.gemsquared.ai)** — one-click browser access. Upload a PNG / JPG / PDF drawing and inspect the result in the review UI. The first OCR invocation may take 1–2 minutes as models load.

---

## 1. The Problem

Floor-plan recognition results flow directly into **material quantity and cost decisions**. Misreading a single wall or miscomputing a dimension propagates straight into material ordering and cost estimates. Most such errors do not surface until construction is already underway.

Chasing the "detect more, detect more accurately" objective favored by generic computer-vision benchmarks does not address this risk. In the construction domain, **a confidently-wrong number is a bigger liability than an unrecognized drawing**. An honest-but-empty result can be revisited by a reviewer; a confidently-wrong result flows through procurement before anyone notices.

This engine exists to expose, alongside every detection, the **evidence, uncertainty, and review path** behind each judgment — a trust surface shaped by the construction domain rather than by generic CV metrics. It does not replace, and does not attempt to replace, a professional quantity surveyor's judgment. Its job is to surface results honestly enough that a surveyor can audit and review them with confidence.

## 2. How It Solves the Problem

Four norms are enforced at schema level. Each of them is visible to a reviewer in the live demo. The internal rules that implement them are not disclosed.

- **Separated epistemic claims** — every object records its judgment about *what it is* (type), *its shape* (geometry), and *its physical measurement* **independently**. Confidence on one does not automatically transfer to the others. The review UI visually distinguishes the three judgments per object.
- **No forced judgment** — regions where evidence is insufficient are not pushed out as low-confidence detections; they are surfaced as **explicit refusal regions**. In the review UI these appear as overlays on the source drawing, giving the reviewer an immediate signal of "this needs a human eye."
- **Measurement safety gate** — no physical-unit (mm) value is emitted for a drawing without a reliable scale reference. Pixel values may remain as diagnostic evidence, but the output contract itself refuses to convert them to millimeters without a supporting scale commitment.
- **Auditability** — run results, refusals, and policy events all persist in an audit store. A reviewer can inspect not only a single drawing's result but error and refusal patterns across many runs over time.

The end-to-end flow is one line:

> Floor-plan input → trust-aware analysis → reviewable result + structured output + audit trail

## 3. Design Principles

Five principles shape how this engine behaves. The internal algorithms, thresholds, and model choices are not disclosed, but the principles are — a reviewer or collaborator should be able to understand *why* the system behaves the way it does.

- **Refusal is a first-class output** — refusal is neither silence nor a placeholder; it is a legitimate output. Low coverage is acceptable; confident-wrong detections are not allowed into the review pipeline.
- **Evidence granularity is per-claim** — a single object carries three independent judgments (identity, geometry, measurement). Collapsing them into one confidence score would destroy the trust surface.
- **Physical units gate on scale evidence** — no mm value is produced until a scale reference is independently established. This is not a convention — the schema enforces it.
- **Every uncertain claim is annotated** — a judgment that lacks direct evidence carries the shape of that missing evidence (either an explicit basis for the extrapolation or an explicit knowledge gap). Bare uncertainty is rejected at the schema layer.
- **Provenance is enforced, not implied** — evaluation assets are used only when their source and license are verified. License-uncertain sources are excluded explicitly rather than absorbed silently.

## 4. Current Result

**Stable version (v0.1.6)**

- Classical CV / OCR vertical slice is shipped and running as the live demo
- Public output contract (`EngineOutput`) enforced by Pydantic
- Review UI + audit CLI
- Supported input: PNG / JPG / JPEG / rasterized PDF (floor plans). Elevations, sections, detail sheets, MEP-only sheets, and photographs are not supported
- No physical-unit (mm) value is produced without a reliable scale reference
- Repository snapshot (as of 2026-08-28)
  - 42 sample images
  - 50 provenance records (of which 8 are orphan records preserved non-destructively — no matching sample file)
  - 19 test files · 137 test functions

**Release timeline (domain milestones)**

| Release | Date | Milestone |
|---------|------|-----------|
| v0.1.0 | 2026-06-05 | End-to-end analysis + review-UI vertical slice |
| v0.1.1 | 2026-06-05 | Audit subsystem introduced — run and refusal history persisted |
| v0.1.2 | 2026-06-05 | Real-drawing corpus adopted (beyond synthetic fixtures) |
| v0.1.3 | 2026-06-06 | Provenance and license coverage broadened |
| v0.1.4 | 2026-06-06 | Hosted demo shipped on containerized runtime |
| v0.1.5 | 2026-06-14 | Deployment discipline + BYO-key visitor pattern |
| v0.1.6 | 2026-06-14 | Default-demo tuning + review-UI polish (current stable) |

**v0.2 improvement program (in progress)**

- A benchmark-driven improvement foundation and stronger data governance are under development
- Because Human-reviewed ground truth and a frozen benchmark are not yet in place, **no improved recognition accuracy is claimed**
- Internal pipeline decomposition, candidate models, model-selection criteria, and evaluation weights are not disclosed

## 5. Technology Stack (Category-Level)

- **Language**: Python 3.11+
- **Computer vision / OCR**: proven open-source CV + multilingual OCR (Korean + Latin scripts)
- **Schema / typed contract**: Pydantic v2
- **Review UI**: Streamlit
- **Audit store**: SQLite (standard library)
- **PDF handling**: page-level rasterization
- **Delivery**: Docker-based container

Specific algorithm combinations, thresholds, post-processing rules, model-selection criteria, and scale-judgment methods are not disclosed.

## 6. Minimal Local Installation (for technical verification)

The hosted demo is the primary path. To reproduce locally:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
streamlit run ui/app.py
```

- Open `http://localhost:8501` in a browser and upload a drawing
- The first run downloads OCR models — expect a delay
- Deployment scripts, container topology, and reverse-proxy configuration are not included in the public repository

## 7. License / IP

- **Source code license**: `Proprietary` (per `pyproject.toml`)
- Corpus assets carry per-item public licenses (CC-BY, CC-BY-SA, public, etc.); the source-code license and the corpus licenses are distinct
- The repository follows a **capability-public / recipe-protected** strategy: capability is verifiable via the demo and the public output contract, while internal recipes, thresholds, and routing rules are not published

---

*CAD Trust Engine Lite · v0.1.6 (stable) · v0.2 benchmark-driven upgrade in progress · David Seo of GEM².AI*
