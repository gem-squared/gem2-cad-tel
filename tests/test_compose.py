"""U8 Compose_F + Aggregate_F acceptance tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cad_trust.compose import compose
from cad_trust.geometry import extract_geometry
from cad_trust.ingest import ingest
from cad_trust.ocr import run_ocr
from cad_trust.schema import EngineOutput
from cad_trust.symbols import detect_symbols

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"


def _run_pipeline(sample_path: Path) -> EngineOutput:
    canonical = ingest(sample_path).canonical_image
    geom = extract_geometry(canonical)
    ocr = run_ocr(canonical)
    syms = detect_symbols(canonical, geom, ocr)
    return compose(drawing_id=sample_path.stem, canonical_image=canonical, geometry=geom, ocr=ocr, symbols=syms)


def _first_sample() -> Path:
    return sorted(SAMPLES.glob("synth_apt_*.png"))[0]


def test_compose_output_validates_against_schema() -> None:
    out = _run_pipeline(_first_sample())
    # Pydantic returns a valid EngineOutput; round-trip through JSON proves shape.
    raw = out.model_dump_json()
    EngineOutput.model_validate_json(raw)


def test_every_object_has_three_epistemic_marks() -> None:
    out = _run_pipeline(_first_sample())
    assert out.objects, "no objects produced — pipeline silently empty"
    for o in out.objects:
        assert o.type_epistemic
        assert o.geometry_epistemic
        assert o.measurement_epistemic


def test_no_scale_anchor_implies_all_measurement_unknown() -> None:
    """∀ scale_anchor.detected=False → ∀ object. measurement_mm is None ∧ measurement_epistemic.tag=⊥."""
    out = _run_pipeline(_first_sample())
    if not out.scale_anchor.detected:
        for o in out.objects:
            assert o.measurement_mm is None, f"{o.object_id} has mm but no anchor"
            assert o.measurement_epistemic.tag == "⊥", f"{o.object_id} measurement tag != ⊥"


def test_no_scale_anchor_implies_mm_aggregate_unknown() -> None:
    out = _run_pipeline(_first_sample())
    if not out.scale_anchor.detected:
        agg = out.aggregates.measured_wall_length_mm
        assert agg.value is None
        assert agg.epistemic.tag == "⊥"


def test_symbol_refusal_candidates_appear_in_refusals() -> None:
    """U7 refusal_candidates must be present in EngineOutput.refusals."""
    sample = _first_sample()
    canonical = ingest(sample).canonical_image
    geom = extract_geometry(canonical)
    ocr = run_ocr(canonical)
    syms = detect_symbols(canonical, geom, ocr)
    out = compose(
        drawing_id=sample.stem, canonical_image=canonical, geometry=geom, ocr=ocr, symbols=syms
    )
    assert len(out.refusals) >= len(syms.refusal_candidates)


def test_aggregate_warning_fires_when_extrapolated_objects_contribute() -> None:
    """If any window object is ⊬-tagged → window_count.warning is non-empty."""
    out = _run_pipeline(_first_sample())
    extrapolated_windows = [o for o in out.objects if o.type == "window" and o.type_epistemic.tag == "⊬"]
    if extrapolated_windows:
        assert out.aggregates.window_count.warning, (
            f"{len(extrapolated_windows)} window objects ⊬-tagged but aggregate.warning empty"
        )


def test_golden_json_still_round_trips() -> None:
    """Regression check: U2's golden JSON still validates."""
    fixture = ROOT / "tests" / "fixtures" / "golden_output.json"
    EngineOutput.model_validate_json(fixture.read_text())
