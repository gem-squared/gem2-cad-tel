# Corpus Policy — gem2-vision

**Scope:** what enters `data/samples/` and how it is recorded in `data/provenance/`.

## Source posture

The v0.1 corpus is **curated public data only**. Real production drawings (from 포비콘 or any construction company) are **never** included in this repository. The auditability wedge the engine claims for its detections applies equally to its training data.

## License categories (six accepted)

| License           | Commercial-safe? | Notes                                                |
|-------------------|------------------|------------------------------------------------------|
| `CC-BY`           | Yes              | Attribution required                                 |
| `CC-BY-SA`        | Yes              | Share-alike — derivatives must be CC-BY-SA           |
| `CC-BY-NC`        | **No**           | Non-commercial only — research/portfolio use         |
| `academic`        | **No**           | Research/educational license; e.g., FloorPlanCAD     |
| `public`          | Yes              | Public domain OR self-generated synthetic            |
| `check-required`  | **No (gate)**    | Surface for human review before any commercial use   |

A source whose license is **unclear** is tagged `check-required` and surfaced; it is **never silently promoted** to a commercial-safe category.

A source whose license cannot be determined at all is **excluded** (the `ProvenanceRecord` validator rejects `license=None`).

## Excluded source categories (never enter `data/samples/`)

| Category                                  | Reason                                       |
|-------------------------------------------|----------------------------------------------|
| 분양자료 (Korean apt marketing materials) | Real-estate copyright minefield              |
| Real-estate blog / property listing       | Aggregator copyright + provenance unclear    |
| Pinterest / image-search scrape           | License untraceable                          |
| Construction-company internal PDF         | Confidential by default                      |

These categories appear in `excluded_sources` lists at runtime (e.g., `Drawing_Corpus_Builder.B.excluded_sources` in the v0.2 crawler), not in `data/samples/`.

## Domain tags (three)

| Tag        | Meaning                                                              |
|------------|----------------------------------------------------------------------|
| `global`   | Culturally-neutral floor plan (FloorPlanCAD, generic Roboflow sets)  |
| `kr`       | Korean apartment / 적산 domain (hand-drawn samples + future Korean datasets) |
| `dwg_demo` | Cal Poly DWG rendered to PNG — **for ingest demo only, not training** |

## Provenance schema

Every drawing in `data/samples/{drawing_id}.{png,pdf}` has a matching `data/provenance/{drawing_id}.json` validating against `src/cad_trust/provenance.py:ProvenanceRecord`:

```json
{
  "drawing_id": "...",
  "source": "floorplancad | calpoly_dwg | hand_drawn_kr | ...",
  "license": "CC-BY | CC-BY-SA | CC-BY-NC | academic | public | check-required",
  "sha256": "<64-char hex digest>",
  "fetched_at": "<ISO8601>",
  "original_uri": "<URL or path>",
  "usage": "demo-only",
  "domain": "global | kr | dwg_demo"
}
```

## Refusal posture (mirrors the engine)

The corpus builder's refusal posture mirrors the engine's. Categories the builder will not commit on (no license + no clean provenance) are tracked and surfaced, not silently dropped. **What we exclude is as visible as what we include.**

---

*v0.2 lifts this from a hand-curated convention to an automated `Drawing_Corpus_Builder` F — see WP-ST-1 References.*
