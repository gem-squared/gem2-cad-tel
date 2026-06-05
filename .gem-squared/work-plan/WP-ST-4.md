# WP-ST-4: v0.1.3 — 'pd' license fix + re-crawl + Streamlit preview pane
**STATUS:** IN_PROGRESS | **STATE:** — | **task_id:** 4dd5c03b
**created_at:** 2026-06-05T15:23:24Z | **project_slug:** gem2-vision
**parent_context:** WP-ST-3 v0.1.2 (34-drawing corpus, 27 license-refused) + WP-ST-2 v0.1.1 (Streamlit UI baseline)

## Objective
Bundle two small targeted improvements: (a) extend the Wikimedia license mapping to handle plain `"pd"` and `"public-domain"` raw codes so the 27 candidates v0.1.2 refused (raw='pd', no prefix) now correctly map to `"public"` and download — `License_Discipline` preserved because public-domain IS commercially safe (this is correct mapping, not bluffing); (b) add a small preview pane right of the Drawing dropdown in the Streamlit Run Engine tab so users can see the selected sample *before* clicking Run Engine — solves the UX gap where complex Wikimedia drawings can take 116 seconds before any visual feedback appears. Both changes preserve `Backward_Compat` (no pipeline contract change) and `Preview_Is_Read_Only` (preview never mutates audit DB or runs pipeline).

## WP-Level Invariants

```
WP_Invariants ≜ [

  ⊢ License_Discipline_Preserved:
      "pd" → "public" is CORRECT mapping (public domain is commercially safe),
      NOT bluffing. No_Source_Bluff still holds — only fully unknown licenses are refused.

  ⊢ Backward_Compat:
      All 130 v0.1.2 tests still pass. EngineOutput shape unchanged.
      pipeline.run signature unchanged.

  ⊢ Preview_Is_Read_Only:
      Preview rendering MUST NOT mutate the audit DB.
      Preview MUST NOT call run_pipeline.
      Preview MUST NOT write provenance.
      Preview is a pure visual surface — selectbox change → image bytes → st.image. Nothing else.

  ⊢ Cached_Preview:
      @st.cache_data wraps the preview-bytes-loader so repeated selections of
      the same drawing don't re-decode. Cache key = file path + mtime.

  ⊢ Crawl_Dedup_Idempotent:
      Re-running scripts/crawl_corpus.py with the fix in place must NOT
      duplicate the 22 existing Wikimedia files (sha256 dedup from WP-ST-3 U2 still works).
]
```

## Unit-Works

### 1. License mapping fix — plain "pd" + "public-domain" prefixes + tests | STATUS: IN_PROGRESS
- A: scripts/crawl_corpus.py _license_mapping_table() with current 9 entries
- B: {
    _license_mapping_table() extended with ("pd", "public") and ("public-domain", "public")
    entries placed AFTER longer-prefix entries (pd-, publicdomain) to preserve match priority,
    map_license("pd") → "public", map_license("public-domain") → "public",
    map_license("PD-old") still → "public" (regression: longer prefix still wins),
    map_license("custom-corporate-eula") still → None (No_Source_Bluff unchanged),
    NEW tests in tests/test_crawl_client.py covering pd/public-domain mapping
  }
- P: scripts/crawl_corpus.py exists from WP-ST-3 U1
- Clarity: 95%
- Unclear: order placement — need to verify "pd-" prefix still matches "pd-old" before plain "pd" catches it (since the table is iterated in order, longer entries must come first)
- Acceptance:
  - tests/test_crawl_client.py: 4 new test cases pass — map_license("pd") == "public", map_license("public-domain") == "public", map_license("PD-old") == "public" (regression — longer match still wins), map_license("custom-corporate-eula") is None (No_Source_Bluff unchanged)
  - All 23 existing test_crawl_client.py tests still pass
  - 2-line patch in scripts/crawl_corpus.py — minimal diff
- Tags: [extending-license-table, fixing-pd-mapping, preserving-no-source-bluff]
- Result:
- State:
- Truth:

### 2. Re-crawl execution — acquire previously-refused public-domain drawings | STATUS: PENDING
- A: { extended license mapping (U1), existing 22 Wikimedia + 12 synthetic drawings, sha256 dedup from data/provenance/ }
- B: {
    `python scripts/crawl_corpus.py --target 25` executed,
    data/samples/ grows by ≥5 new files (lower bound — empirical),
    each new file has matching provenance.json validating ProvenanceRecord,
    new license tags ∈ {public, CC-BY-SA, CC-BY} (no None / no missing),
    .gem-squared/crawl_summary.json reflects the latest run (refused_by_license should be lower vs WP-ST-3 baseline)
  }
- P: U1 complete (license mapping fix in place); network reachability
- Clarity: 70%
- Unclear: exact yield depends on Wikimedia category contents at request time + how many of the previously-refused "pd" candidates are still in the categories; dedup sha256 check prevents collisions; some new candidates may be NEW (not from prior pool) since the API may return slightly different ordering
- Acceptance:
  - data/samples/ count > 34 (previous baseline)
  - All new provenance files validate against ProvenanceRecord
  - crawl_summary.json refused_by_license count < 27 (the v0.1.2 baseline)
  - No license=None in any provenance JSON
  - sha256 collision sanity: tests/test_corpus.py test_no_duplicate_sha256 still passes
- Tags: [re-crawling-wikimedia, expanding-corpus, deduping-existing]
- Result:
- State:
- Truth:

### 3. Streamlit preview pane + helpers + UI tests | STATUS: PENDING
- A: { ui/app.py with existing 2-tab layout from WP-ST-2 U5 }
- B: {
    NEW preview helpers in ui/app.py (or ui/preview.py if cleaner):
      - `load_preview_image(path: Path, max_width: int = 400) -> PIL.Image.Image | None`
        * .png/.jpg/.jpeg → PIL.Image.open + RGB + thumbnail((max_width, max_width*2))
        * .pdf → pdf2image.convert_from_path(dpi=100, first_page=1, last_page=1) → first page
        * .svg / other → return None (signals "preview unavailable")
        * @st.cache_data wrapping (cache key path + mtime via path.stat().st_mtime)
      - `preview_status_message(path: Path) -> str | None`
        * .svg → "Preview unavailable for SVG — ingest will refuse this format"
        * else → None
    ui/app.py Run Engine tab layout REFACTORED:
      - Replace `col_pick, _ = st.columns([1, 3])` with `col_pick, col_preview = st.columns([2, 3])`
      - col_pick: existing dropdown + upload widget unchanged
      - col_preview: subheader "Preview" + st.image(load_preview_image(chosen_path), width=380) or info message
      - No file chosen: neutral st.caption("(select a drawing to preview)")
    NEW tests/test_ui_preview.py covering helpers (no Streamlit runtime needed):
      - load_preview_image returns PIL.Image for PNG corpus sample
      - load_preview_image returns PIL.Image for JPG corpus sample
      - load_preview_image returns PIL.Image for PDF corpus sample (renders page 0)
      - load_preview_image returns None for SVG
      - load_preview_image returns None for nonexistent path
      - preview_status_message returns SVG-specific message for .svg
      - Cached_Preview check: load_preview_image is wrapped with @st.cache_data (attribute check)
    ui/app.py syntactic validity (compile check)
  }
- P: U2 complete (corpus has multiple file types: PNG / JPG / PDF / SVG)
- Clarity: 80%
- Unclear: where to put the helpers — inline in ui/app.py (simpler) vs new ui/preview.py (cleaner). Recommend inline since they're <30 lines total. @st.cache_data may need invalidation testing — verify that changing mtime triggers re-load (acceptable to trust Streamlit's implementation in v0.1.3)
- Acceptance:
  - tests/test_ui_preview.py covers load_preview_image for PNG / JPG / PDF / SVG / nonexistent
  - Streamlit smoke: process still launches + serves HTTP 200 after edit
  - ui/app.py syntactically valid Python (compile check)
  - Run Engine tab layout shows two side-by-side columns (dropdown left, preview right)
  - Preview_Is_Read_Only: no calls to run_pipeline, init_audit_db, or AuditContext from preview path (verified by grep in test)
- Tags: [adding-preview-pane, caching-image-bytes, refactoring-ui-layout]
- Result:
- State:
- Truth:

### 4. Docs + full suite + v0.1.3 git tag | STATUS: PENDING
- A: { U1-U3 complete; new tests + corpus + UI all in place }
- B: {
    docs/CORPUS.md: sources table updated with new wikimedia_commons count (was 22, now >27),
    root README.md: Status section + v0.1.3 line summarizing license fix + preview pane,
    full pytest green (130 baseline + new license tests + UI preview tests),
    git tag v0.1.3 created on main with full WP-ST-4 message
  }
- P: U1-U3 all COMPLETED|SUCCESS
- Clarity: 90%
- Unclear: whether the smoke test from WP-ST-3 U5 needs re-running (it took 10 min last time; if corpus grew by N new drawings the smoke would now take +N×3-30s). Decision: skip in fast suite + document that smoke would need separate re-run on the expanded corpus
- Acceptance:
  - Fast pytest exits 0 — all tests green except 3 smoke tests (which are excluded from fast suite via --ignore)
  - docs/CORPUS.md updated source counts match actual data/samples/ counts
  - README.md v0.1.3 line names: 2 fixes (license mapping + preview pane) + new test counts
  - git tag v0.1.3 created with detailed completion message naming WP-ST-4 + 4 unit-works + 4 invariants
- Tags: [updating-docs, tagging-version, finalizing-release]
- Result:
- State:
- Truth:

---

## References
- Parent: WP-ST-3 v0.1.2 (added the crawler whose license table this WP fixes) — `.gem-squared/work-plan/WP-ST-3.md`
- Parent: WP-ST-2 v0.1.1 (Streamlit baseline + audit subsystem) — `.gem-squared/work-plan/WP-ST-2.md`
- ProvenanceRecord schema: src/cad_trust/provenance.py (UNCHANGED — schema already supports "public" license)
- WP-ST-2 U5 streamlit query patterns: `_resolve_audit_db()` + tab-layout — preview pane refactor stays consistent with existing UI conventions
- Deferred: SVG ingest support (cairosvg/wand dep decision), PDF multi-page preview, in-line per-object overlay drilldown, audit-DB-backed "previously seen" badges
- Architectural source: this turn's Alchy framing — license fix is a 2-line patch unlocking ~15-25 extra public-domain drawings; preview pane is the UX polish that makes browsing a 50+ drawing corpus tolerable
