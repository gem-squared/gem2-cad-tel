"""U4 acceptance — license whitelist + source diversity + crawl_summary schema."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cad_trust.provenance import ProvenanceRecord

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"
PROVENANCE = ROOT / "data" / "provenance"
SUMMARY = ROOT / ".gem-squared" / "crawl_summary.json"

LICENSE_WHITELIST = {"CC-BY", "CC-BY-SA", "CC-BY-NC", "academic", "public", "check-required"}


def _all_provenance() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(PROVENANCE.glob("*.json"))]


def test_every_provenance_license_in_whitelist() -> None:
    """No license outside the CORPUS.md whitelist."""
    drift = []
    for prov in _all_provenance():
        lic = prov["license"]
        if lic not in LICENSE_WHITELIST:
            drift.append((prov["drawing_id"], lic))
    assert not drift, f"licenses outside whitelist: {drift}"


def test_both_synthetic_and_crawled_sources_present() -> None:
    """After WP-ST-3, the corpus must have ≥1 synthetic AND ≥1 crawled drawing."""
    sources = {prov["source"] for prov in _all_provenance()}
    assert "synthetic_self_generated" in sources, "synthetic baseline missing"
    assert any(s != "synthetic_self_generated" for s in sources), (
        "no crawled source represented — WP-ST-3 should have added at least 1"
    )


def test_wikimedia_provenance_is_global_domain() -> None:
    """Per WP-ST-3 spec, Wikimedia downloads default to domain=global."""
    wm = [p for p in _all_provenance() if p["source"] == "wikimedia_commons"]
    if not wm:
        pytest.skip("no wikimedia_commons drawings in corpus")
    for prov in wm:
        assert prov["domain"] == "global"


def test_wikimedia_provenance_validates_as_provenance_record() -> None:
    wm = [p for p in _all_provenance() if p["source"] == "wikimedia_commons"]
    if not wm:
        pytest.skip("no wikimedia_commons drawings in corpus")
    for prov in wm:
        rec = ProvenanceRecord.model_validate(prov)
        assert rec.usage == "demo-only"


def test_crawl_summary_has_required_keys() -> None:
    """The audit log from the crawl run must be present and structured."""
    if not SUMMARY.exists():
        pytest.skip(f"crawl summary not present at {SUMMARY} — U3 must have run")
    data = json.loads(SUMMARY.read_text())
    for key in (
        "started_at", "completed_at", "downloaded",
        "refused_by_license", "refused_by_404", "refused_by_too_small",
        "by_source", "refused_details", "downloaded_files",
    ):
        assert key in data, f"crawl_summary missing key: {key}"


def test_crawl_summary_refused_details_have_reasons() -> None:
    """No refusal in the audit log has a blank/'unknown' reason."""
    if not SUMMARY.exists():
        pytest.skip("no crawl_summary.json")
    data = json.loads(SUMMARY.read_text())
    for entry in data["refused_details"]:
        reason = entry.get("reason", "")
        assert reason, f"refused entry without reason: {entry}"
        assert reason.lower() not in {"unknown", "error", ""}
        stage = entry.get("stage", "")
        assert stage in {"license_check", "url_check", "download", "size_check", "dedup"}, (
            f"unexpected refusal stage: {stage}"
        )


def test_corpus_has_more_than_synthetic_baseline() -> None:
    """After WP-ST-3 the corpus must have grown beyond the 12 synthetic baseline."""
    n = len(list(PROVENANCE.glob("*.json")))
    assert n >= 13, f"corpus has {n} drawings; expected ≥13 (12 synthetic + ≥1 crawled)"
