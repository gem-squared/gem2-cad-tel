"""U5 Geometry_F acceptance tests."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cad_trust.geometry import GeometryResult, extract_geometry
from cad_trust.ingest import ingest

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"


def _all_samples() -> list[Path]:
    return sorted(SAMPLES.glob("*.png"))


def test_extract_geometry_returns_typed_result_on_blank() -> None:
    """Empty input never returns silent None."""
    blank = np.full((100, 100, 3), 255, dtype=np.uint8)
    result = extract_geometry(blank)
    assert isinstance(result, GeometryResult)
    assert result.lines == []
    assert result.wall_candidates == []
    assert result.diagnostic  # non-empty diagnostic when nothing found


def test_extract_geometry_returns_typed_result_on_none() -> None:
    """Defensive: None / empty array still returns typed object."""
    result = extract_geometry(np.zeros((0, 0), dtype=np.uint8))
    assert isinstance(result, GeometryResult)
    assert result.diagnostic == "empty input image"


def test_known_good_fixture_has_lines_and_walls() -> None:
    """A corpus sample produces lines AND wall_candidates."""
    samples = _all_samples()
    assert samples, "U3 corpus must exist"
    canonical = ingest(samples[0]).canonical_image
    result = extract_geometry(canonical)
    assert len(result.lines) > 0, "Hough should detect lines on a CAD floor plan"
    assert len(result.wall_candidates) > 0, "parallel-pair pairing should find at least 1 wall"


def test_every_wall_candidate_has_evidence() -> None:
    """Per U7 acceptance pattern — no detection without evidence."""
    samples = _all_samples()
    canonical = ingest(samples[0]).canonical_image
    result = extract_geometry(canonical)
    for wc in result.wall_candidates:
        assert wc.evidence, "wall_candidate emitted without evidence"
        for ev in wc.evidence:
            assert ev.source and ev.signal


def test_corpus_calibration_smoke() -> None:
    """≥80% of corpus samples produce ≥1 wall_candidate (baseline calibration)."""
    samples = _all_samples()
    n = len(samples)
    assert n >= 10
    hits = 0
    for p in samples:
        canonical = ingest(p).canonical_image
        result = extract_geometry(canonical)
        if result.wall_candidates:
            hits += 1
    rate = hits / n
    assert rate >= 0.80, f"only {hits}/{n} = {rate:.0%} of corpus produced wall_candidates (<80%)"
