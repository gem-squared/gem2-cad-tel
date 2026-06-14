# Corpus Policy — gem2-vision

**Scope:** what enters `data/samples/` and how it is recorded in `data/provenance/`.

## Source posture

The v0.1 corpus is **curated public data only**. Real production drawings (from any construction company) are **never** included in this repository. The auditability wedge the engine claims for its detections applies equally to its training data.

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

## Crawl strategy (v0.1.2)

WP-ST-3 (v0.1.2) added a real-source crawler that supplements the synthetic baseline:

```bash
python scripts/crawl_corpus.py --target 25
# Output: 22 real architectural drawings from Wikimedia Commons,
# 27 refused by No_Source_Bluff (no mappable license),
# 1 refused by too-small.
```

**Primary source: Wikimedia Commons** (`https://commons.wikimedia.org/w/api.php`)

- Categories queried: `Floor plans`, `Architectural drawings`, `House plans`
- License metadata via `prop=imageinfo&iiprop=url|extmetadata`
- License mapping: `cc-by-sa-*` → `CC-BY-SA`, `cc-by-*` → `CC-BY`, `pd-*` → `public`, `cc-zero` → `public`; unknown → REFUSED
- Polite crawler: identifying `User-Agent`, 0.5s sleep between requests
- Per-file: `sha256` + `provenance.json` validating against `ProvenanceRecord`
- All Wikimedia drawings tagged `domain=global` + `source=wikimedia_commons`
- `License_Discipline` invariant: any candidate whose license cannot be confidently mapped is REFUSED — never optimistically guessed as "public"

**Sources used (v0.1.3):**

| Source              | Count | License classes               | Domain  |
|---------------------|-------|-------------------------------|---------|
| synthetic_self_generated | 12 | public                       | 9 kr + 3 global |
| wikimedia_commons   | 38    | CC-BY-SA + CC-BY + public    | global  |
| **Total**           | **50** |                            |         |

The v0.1.2 → v0.1.3 jump (+16 drawings) came from extending the license
mapping table to handle plain `pd` and `public-domain` raw codes, which
Wikimedia uses heavily for historical building plans, watercolours, and
architectural sketches. License discipline preserved: 11 candidates still
refused in v0.1.3 (down from 27 in v0.1.2) because their raw values remain
unmappable (GFDL-only, fair-use claims, etc.).

**Refusal log** at `.gem-squared/crawl_summary.json` records:
- `downloaded` / `refused_by_license` / `refused_by_404` / `refused_by_too_small` counts
- Per-source breakdown
- Every refusal carries a specific `reason` + `stage` field (never `"unknown"`)

**Format support after v0.1.2:** Ingest_F accepts `.png`, `.jpg`/`.jpeg`, and `.pdf`. SVG and other formats raise typed `IngestError` (not silently skipped).

---

## Empirical coverage on real drawings (WP-ST-3 U5)

The pipeline ran end-to-end on every ingestable drawing (32 = 12 synthetic + 20 real PNG/JPG/PDF):

- **100% success** (no crashes, all produce valid `EngineOutput`)
- Synthetic baseline: 15-24 objects, **0 refusals**, scale anchor detected, ~3s each
- Real Wikimedia: 11-20,267 objects, **2-931 refusals each**, mixed scale anchor, 1-116s

The huge variance in refusal counts on real data is the point: `Refusal_Over_Bluff` produces vastly more refusals on complex drawings, all auditably queryable via the v0.1.1 audit subsystem.

---

*v0.2 lifts the crawler into a full `Drawing_Corpus_Builder` F — see WP-ST-1 References. v0.2 will also support FloorPlanCAD / ArchCAD-400K (registration-gated) and DWG native ingest.*
