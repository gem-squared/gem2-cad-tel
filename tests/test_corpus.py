"""U3 corpus tests — validate provenance, count, sha256, license, domain coverage."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cad_trust.provenance import ProvenanceRecord

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"
PROVENANCE = ROOT / "data" / "provenance"


def _sample_files() -> list[Path]:
    return sorted(p for p in SAMPLES.glob("*") if p.suffix.lower() in (".png", ".pdf"))


def _provenance_files() -> list[Path]:
    return sorted(PROVENANCE.glob("*.json"))


def test_count_in_range() -> None:
    """10 ≤ |data/samples/*| ≤ 30 per U3 acceptance."""
    n = len(_sample_files())
    assert 10 <= n <= 30, f"corpus has {n} samples; expected 10-30"


def test_every_sample_has_provenance() -> None:
    samples = _sample_files()
    prov = _provenance_files()
    sample_ids = {p.stem for p in samples}
    prov_ids = {p.stem for p in prov}
    missing = sample_ids - prov_ids
    assert not missing, f"samples missing provenance: {missing}"


def test_every_provenance_validates() -> None:
    """Every JSON parses as ProvenanceRecord."""
    for p in _provenance_files():
        data = json.loads(p.read_text())
        rec = ProvenanceRecord.model_validate(data)
        assert rec.drawing_id == p.stem


def test_no_license_unknown() -> None:
    """No file in data/samples/ has license = None/⊥."""
    for p in _provenance_files():
        data = json.loads(p.read_text())
        # license must be a valid LicenseCategory string, not None
        assert data["license"], f"{p.name} has empty license"


def test_sha256_matches_file() -> None:
    """sha256 in provenance must match actual file digest (smoke ≥3 files)."""
    samples = _sample_files()
    prov_by_id = {p.stem: json.loads(p.read_text()) for p in _provenance_files()}
    checked = 0
    for sample_path in samples:
        rec = prov_by_id.get(sample_path.stem)
        if rec is None:
            continue
        actual = hashlib.sha256(sample_path.read_bytes()).hexdigest()
        assert actual == rec["sha256"], (
            f"sha256 mismatch for {sample_path.name}: "
            f"file={actual[:12]}… provenance={rec['sha256'][:12]}…"
        )
        checked += 1
        if checked >= 3:
            break
    assert checked >= 3, "fewer than 3 files available to smoke-check sha256"


def test_domain_coverage() -> None:
    """At least 1 sample tagged domain=global AND at least 1 in {kr, dwg_demo}."""
    domains = {json.loads(p.read_text())["domain"] for p in _provenance_files()}
    assert "global" in domains, f"no global sample; domains seen: {domains}"
    assert domains & {"kr", "dwg_demo"}, f"no kr or dwg_demo sample; domains seen: {domains}"


def test_no_duplicate_sha256() -> None:
    """All sha256s unique — catches the 'identical samples' bug honestly."""
    hashes = [json.loads(p.read_text())["sha256"] for p in _provenance_files()]
    dups = {h for h in hashes if hashes.count(h) > 1}
    assert not dups, f"duplicate sha256s in corpus (samples are identical): {len(dups)} hash(es)"
