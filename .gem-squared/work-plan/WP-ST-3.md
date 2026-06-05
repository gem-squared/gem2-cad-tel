# WP-ST-3: Crawl real public-source CAD/floor plan drawings — v0.1.2 corpus expansion
**STATUS:** IN_PROGRESS | **STATE:** — | **task_id:** f6316037
**created_at:** 2026-06-05T14:54:02Z | **project_slug:** gem2-vision
**parent_context:** WP-ST-1 v0.1.0 (synthetic baseline of 12 drawings) + WP-ST-2 v0.1.1 (audit subsystem); 91 tests passing at HEAD

## Objective
Extend the corpus with real public-source architectural CAD/floor plan images crawled from license-explicit sources (primarily Wikimedia Commons; secondarily curated public GitHub repos with OSS licenses). Target: add 15-30 real drawings on top of the 12 synthetic baseline so the engine's rule-based detection (WP-ST-1 U7) gets stress-tested on diverse real-world layouts — varied wall thickness, irregular shapes, dense annotation, stylized symbols. The synthetic samples stay (still useful unit-test fixtures); real drawings supplement them. License discipline is non-negotiable: any uncategorized source is REFUSED (mirrors the engine's own Refusal_Over_Bluff posture, applied to corpus building).

## WP-Level Invariants

```
WP_Invariants ≜ [

  ⊢ License_Discipline:
      NO file with license = None / unverifiable enters data/samples/.
      Uncategorized sources are recorded in an "excluded" log, NEVER silently included.
      "check-required" license tag is acceptable (surfaces for human review),
      "⊥" / missing is not.

  ⊢ Provenance_Visibility:
      Every new drawing has a matching data/provenance/{stem}.json validating against
      ProvenanceRecord (source, license, sha256, fetched_at, original_uri, usage, domain).

  ⊢ Polite_Crawling:
      Identifying user-agent ("gem2-vision/0.1.2 (educational; david@gineers.ai)").
      Sleep ≥ 0.5s between HTTP requests.
      Respect robots.txt where applicable. (Wikimedia API explicitly permits programmatic use.)

  ⊢ No_Source_Bluff:
      If a license cannot be determined from API response, the file is REFUSED.
      License is NEVER optimistically guessed as "public" or "CC-BY" — surface as "check-required" or exclude.

  ⊢ Backward_Compat:
      Existing 91 WP-ST-1 + WP-ST-2 tests MUST still pass after the crawl runs.
      pipeline.run must work on every new drawing (audit DB confirms).

  ⊢ Audit_On_Corpus_Build:
      Crawl script writes a summary log: N candidates / M downloaded / K refused (by license, by 404).
      Meta-auditability: the engine that records its refusals also records the corpus builder's refusals.
]
```

## Unit-Works

### 1. Crawler module + Wikimedia Commons API + license mapping | STATUS: COMPLETED
- A: { wikimedia_base_url: "https://commons.wikimedia.org/w/api.php", license_mapping_table: dict, user_agent: str }
- B: {
    scripts/crawl_corpus.py created with:
      - `class WikimediaClient` exposing `query_category(category: str, limit: int) -> list[Candidate]` and `fetch_imageinfo(filenames: list[str]) -> dict[str, dict]`,
      - rate-limited requests (sleep_sec=0.5),
      - identifying user-agent,
      - `Candidate` dataclass: {filename, url, license_raw, license_mapped, attribution, source_page_url},
      - license routing: Wikimedia license codes → LicenseCategory enum:
        * cc-by-sa-* → "CC-BY-SA",
        * cc-by-* → "CC-BY",
        * cc-by-nc-* → "CC-BY-NC",
        * pd-* / publicdomain → "public",
        * cc-zero → "public",
        * unknown / null → None (REFUSED, not "check-required" — Wikimedia metadata IS the ground truth),
    no actual downloads in this unit — just the client + mapping logic
  }
- P: Python 3.11+ stdlib (urllib.request, json, time, dataclasses)
- Clarity: 80%
- Unclear: exact Wikimedia API response shape for license metadata — handled by inspecting first response live; fallback to filename-from-URL when image metadata is sparse; rate-limit may need tuning if Wikimedia returns 429s
- Acceptance:
  - `from cad_trust_corpus.crawl import WikimediaClient` succeeds (package importable; can live under scripts/ since not a library export)
  - `WikimediaClient.query_category("Floor plans", limit=5)` returns ≥1 Candidate when network is up
  - Each Candidate has license_raw + license_mapped fields populated (license_mapped may be None when no mapping)
  - User-agent header is sent on every request (verified via dry-run test patching urllib)
  - `pytest tests/test_crawl_client.py` covers license mapping table + mock-response parsing
- Tags: [building-crawler, mapping-licenses, querying-wikimedia, refusing-unknown-licenses]
- Result: scripts/crawl_corpus.py (stdlib-only, 350+ LOC) implements WikimediaClient + license-mapping table + safe_stem + infer_extension + download_and_record (U2 territory; see U2 Result for its tests). WikimediaClient.query_category uses generator=categorymembers + prop=imageinfo single-roundtrip with extmetadata License/LicenseShortName/Artist + url/mime/size. map_license uses ordered-prefix matching (longer first to avoid 'cc-by-nc' false-matching 'cc-by-'); No_Source_Bluff enforced — unknown codes → None → caller refuses. safe_stem strips "File:" prefix, lowercases, replaces non-alnum, caps at 80 chars. Polite_Crawling: USER_AGENT='gem2-vision/0.1.2 (educational; david@gineers.ai)', REQUEST_SLEEP_SEC=0.5, handles HTTP 429 / URLError gracefully. pytest tests/test_crawl_client.py 23/23 PASSED in 0.06s: 14 license-mapping cases (cc-by-sa-4.0 → CC-BY-SA, pd-old → public, unknown → None, CC0 plain → None), safe_stem strips & lowercases, infer_extension prefers content-type, query_category mock returns parsed candidates with attribution + correct license mapping + REFUSES candidate with empty extmetadata, query_category sends User-Agent header (Polite_Crawling check), query_category returns [] on HTTP 429 and on bad JSON.
- State: SUCCESS
- Truth:

### 2. Download + sha256 + provenance.json generation + refusal log | STATUS: IN_PROGRESS
- A: { candidates: list[Candidate] (from U1), out_samples_dir: Path, out_provenance_dir: Path, audit_log_path: Path }
- B: {
    `download_and_record(candidates, ...)` function appended to scripts/crawl_corpus.py:
      - for each candidate: if license_mapped is None → REFUSE, log + skip,
      - HTTP GET the image bytes; if non-200 → REFUSE_404, log + skip,
      - compute sha256 of bytes,
      - write data/samples/{safe_stem}.{ext} (deduplicate by sha256 — skip if already present),
      - write data/provenance/{safe_stem}.json validating against ProvenanceRecord schema,
      - append to crawl summary: {downloaded, refused_by_license, refused_by_404, by_source: dict, refused_details: list},
    returns the summary dict,
    crawl summary written to audit_log_path (JSON)
  }
- P: U1 complete; ProvenanceRecord schema available from cad_trust.provenance
- Clarity: 85%
- Unclear: filename safety (Wikimedia titles contain spaces, parens, non-ASCII) — sanitize to [a-z0-9_-]+; file extension inference from Content-Type or URL suffix
- Acceptance:
  - When given a candidate with license_mapped=None → summary.refused_by_license += 1, no file written
  - When given a candidate with HTTP 404 → summary.refused_by_404 += 1, no file written
  - When given a valid CC-BY candidate → file written + provenance JSON validates against ProvenanceRecord
  - sha256 deduplication: re-running on same candidate is idempotent (no duplicate)
  - Summary JSON written to audit_log_path, validates as dict with required keys
  - `pytest tests/test_crawl_download.py` covers all 4 paths with monkeypatched urllib
- Tags: [downloading-images, recording-provenance, refusing-uncategorized]
- Result:
- State:
- Truth:

### 3. Execute the crawl — populate data/samples/ with real drawings | STATUS: PENDING
- A: { target_count: 20, categories_to_query: ["Floor plans", "Architectural drawings", "House plans"], out_samples_dir: data/samples/, out_provenance_dir: data/provenance/, audit_log_path: .gem-squared/crawl_summary.json }
- B: {
    scripts/crawl_corpus.py invoked as `__main__` (CLI) — runs the crawl,
    actual files appear in data/samples/ (target: +15 to +30 PNG/JPG),
    actual provenance JSONs appear in data/provenance/ (one per new drawing),
    .gem-squared/crawl_summary.json records the run (counts + per-source breakdown),
    crawl is REAL — not mocked — uses live Wikimedia Commons API
  }
- P: U1 + U2 complete; network reachability to commons.wikimedia.org
- Clarity: 70%
- Unclear: actual download success rate (depends on category contents, license metadata completeness); target_count is a goal but actual count may be lower if discipline excludes many; some Wikimedia category members may be tagged/non-floor-plan diagrams that still pass; pipeline-suitability of downloaded images (resolution, format) — addressed in U5 smoke
- Acceptance:
  - data/samples/ count grows by ≥ 5 new files (lower bound — license discipline may exclude many)
  - Each new file has matching provenance.json
  - .gem-squared/crawl_summary.json exists and lists downloaded + refused totals
  - All license_mapped values in provenance are ∈ {CC-BY, CC-BY-SA, CC-BY-NC, public, academic, check-required} (no None / no missing)
  - sha256 in each provenance JSON matches the actual file's hash (smoke-checked on ≥3 files)
- Tags: [executing-crawl, populating-corpus, recording-summary]
- Result:
- State:
- Truth:

### 4. Corpus validation tests (extended) + license whitelist enforcement | STATUS: PENDING
- A: { existing tests/test_corpus.py + new data/samples/ contents (synthetic + real) + crawl_summary.json }
- B: {
    tests/test_corpus.py acceptance criteria already cover: count in [10, ≤many], provenance per sample, sha256 match, license != None, domain coverage — these MUST continue passing on the expanded corpus,
    tests/test_corpus_crawl.py NEW with:
      - every provenance.license ∈ LicenseCategory whitelist (no extension drift),
      - synthetic_self_generated and crawled sources both represented,
      - crawl_summary.json validates as expected schema (downloaded + refused_by_license + refused_by_404 keys present),
      - excluded sources (when present) have non-empty reason fields,
    fix tests/test_corpus.py count upper bound if needed (currently 30 — may need to raise to 100)
  }
- P: U3 complete (corpus populated)
- Clarity: 90%
- Unclear: whether test_corpus.py count assertion `10 ≤ N ≤ 30` will break if crawl adds many — need to relax upper bound to a more reasonable ceiling like 200 (per WP-ST-1 U3 original spec said 10-30 but that was v0.1, this is v0.1.2)
- Acceptance:
  - existing tests/test_corpus.py: all 7 tests still pass on expanded corpus (after upper-bound relax)
  - tests/test_corpus_crawl.py: NEW tests cover license whitelist + source diversity + crawl_summary schema
  - `pytest tests/test_corpus.py tests/test_corpus_crawl.py` exits 0
- Tags: [validating-corpus, enforcing-license-whitelist, testing-summary-schema]
- Result:
- State:
- Truth:

### 5. Integration smoke — pipeline.run on every new drawing + audit confirmation | STATUS: PENDING
- A: { audit_db_path: .gem-squared/audit_smoke_v012.sqlite, all drawings in data/samples/ }
- B: {
    tests/test_corpus_pipeline_smoke.py NEW: iterates every drawing in data/samples/, runs pipeline.run with audit on, asserts:
      - pipeline.run produces a valid EngineOutput (Pydantic round-trip),
      - audit DB has a runs row per drawing with exit_state SUCCESS,
      - failed drawings (if any — real-world JPGs may be too small / wrong shape / etc.) are SURFACED in the test report with their failure reason (skip if unsupported format, fail otherwise),
    coverage observation: tally per-drawing (objects count, refusal count, scale_anchor detected?) — print as informational diagnostic via -s flag,
    no shape assertion beyond "valid EngineOutput" — engine MAY produce many refusals on complex drawings; that's TPMN-correct, not a failure
  }
- P: U3 + U4 complete; pipeline.run + audit subsystem from WP-ST-2 working
- Clarity: 85%
- Unclear: how many real drawings the rule-based detector + PaddleOCR cope with vs refuse — interesting empirical signal but not a hard pass/fail; some real Wikimedia floor plans may have non-Latin scripts (Greek, Russian etc.) which PaddleOCR ko+en doesn't handle (acceptable — surfaces as 0-text OCR)
- Acceptance:
  - Every drawing in data/samples/ either ingests successfully OR is explicitly listed as "skip" with reason (format unsupported / image too small / corrupted)
  - pipeline.run succeeds on ≥ 80% of new crawled drawings (lower bound — TPMN refusal is acceptable but engine MUST not crash on real inputs)
  - audit DB confirms: runs rows for each successful pipeline.run; refusals_log + epistemic_counts populated
  - Test prints a diagnostic table: |drawing | objects | refusals | scale_anchor | runtime_ms| to validate real-data behavior is non-trivial
- Tags: [smoking-pipeline, validating-real-data, diagnosing-coverage]
- Result:
- State:
- Truth:

### 6. Docs + .gitignore + full suite + v0.1.2 git tag | STATUS: PENDING
- A: { U1-U5 complete }
- B: {
    docs/CORPUS.md updated with: crawl strategy (Wikimedia primary), source breakdown (synthetic + crawled), license discipline reiterated, link to scripts/crawl_corpus.py + crawl_summary.json,
    .gitignore extended to exclude .gem-squared/crawl_summary.json (runtime state) and .gem-squared/audit_smoke_*.sqlite (test artifacts),
    root README.md Status section updated: v0.1.2 line added,
    final pytest: ALL tests green (WP-ST-1 53 + WP-ST-2 38 + WP-ST-3 new tests),
    git tag v0.1.2 created on main with WP-ST-3 completion message naming sources + counts
  }
- P: U1-U5 all COMPLETED|SUCCESS
- Clarity: 90%
- Unclear: exact final test count (depends on how many tests U4 + U5 add — estimate ~10 new)
- Acceptance:
  - docs/CORPUS.md updated with new sections: "Crawl Strategy" + "Sources Used"
  - .gitignore matches `.gem-squared/crawl_summary.json` (verify via `git check-ignore`)
  - root README.md mentions v0.1.2 with combined corpus size + crawl note
  - `pytest` exits 0 with all tests green (no regressions)
  - `git tag v0.1.2` exists on main with descriptive message naming WP-ST-3 + source breakdown
- Tags: [updating-docs, finalizing-release, tagging-version]
- Result:
- State:
- Truth:

---

## References
- Parent context: WP-ST-1 v0.1.0 (synthetic baseline + ingest/geometry/ocr/symbols/compose) + WP-ST-2 v0.1.1 (audit subsystem)
- ProvenanceRecord schema: src/cad_trust/provenance.py (UNCHANGED — schema already supports all license categories needed)
- CORPUS.md license whitelist: CC-BY / CC-BY-SA / CC-BY-NC / academic / public / check-required; excluded categories: 분양자료 / blog / Pinterest / construction-company internal PDF
- Wikimedia Commons API: https://commons.wikimedia.org/w/api.php (action=query, generator=categorymembers, prop=imageinfo)
- Deferred to later: FloorPlanCAD / ArchCAD-400K registration-gated downloads, DWG→PNG rendering (v0.3), synthetic KR enrichment (separate WP), VLM-based semantic verification on crawled drawings
- Architectural source: this turn's Alchy framing — "synthetic is too simple; crawl with license discipline; refusal posture extends to corpus building"
