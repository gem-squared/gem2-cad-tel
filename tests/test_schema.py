"""U2 acceptance tests: schema round-trip, Measurement_Policy enforcement, provenance validation."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from cad_trust.provenance import ProvenanceRecord
from cad_trust.schema import (
    Aggregate,
    Aggregates,
    EngineOutput,
    EpistemicMark,
    Evidence,
    Geometry,
    Object,
    Refusal,
    ScaleAnchor,
)

FIXTURE = Path(__file__).parent / "fixtures" / "golden_output.json"


# ── Round-trip + json-schema ────────────────────────────────────────────────


def test_golden_json_round_trips() -> None:
    """Golden JSON validates against EngineOutput and survives a round-trip."""
    raw = FIXTURE.read_text()
    obj = EngineOutput.model_validate_json(raw)
    redumped = obj.model_dump_json(indent=2)
    obj2 = EngineOutput.model_validate_json(redumped)
    assert obj == obj2


def test_engine_output_schema_emits_valid_json_schema() -> None:
    schema = EngineOutput.model_json_schema()
    # JSON Schema mandates $defs and properties at top
    assert isinstance(schema, dict)
    assert "properties" in schema
    assert "objects" in schema["properties"]
    # Round-trip through json
    json.dumps(schema)


# ── Per-field epistemic invariants ──────────────────────────────────────────


def test_extrapolated_tag_requires_basis() -> None:
    with pytest.raises(ValidationError, match="basis"):
        EpistemicMark(tag="⊬", evidence=[], basis=None, gap=None)


def test_unknown_tag_requires_gap() -> None:
    with pytest.raises(ValidationError, match="gap"):
        EpistemicMark(tag="⊥", evidence=[], basis=None, gap=None)


def test_grounded_tag_allows_no_basis_or_gap() -> None:
    mark = EpistemicMark(
        tag="⊢",
        evidence=[Evidence(source="opencv_line", signal="parallel thick lines")],
    )
    assert mark.tag == "⊢"


# ── Measurement_Policy enforcement ──────────────────────────────────────────


def _make_object_with_mm(mm: float | None, m_tag: str) -> Object:
    return Object(
        object_id="obj_test",
        type="wall_structural",
        type_epistemic=EpistemicMark(tag="⊢", evidence=[Evidence(source="x", signal="y")]),
        geometry=Geometry(kind="polyline", coords_px=[[0.0, 0.0], [10.0, 0.0]]),
        geometry_epistemic=EpistemicMark(tag="⊢", evidence=[Evidence(source="x", signal="y")]),
        measurement_mm=mm,
        measurement_epistemic=(
            EpistemicMark(tag=m_tag, evidence=[], gap="no scale" if m_tag == "⊥" else None,
                          basis="extrap" if m_tag == "⊬" else None)
            if m_tag in ("⊥", "⊬")
            else EpistemicMark(tag=m_tag, evidence=[Evidence(source="x", signal="y")])
        ),
        review_status="needs_human",
    )


def _minimal_aggregates(mm_value: float | None, mm_tag: str) -> Aggregates:
    return Aggregates(
        wall_count=Aggregate(value=1, epistemic=EpistemicMark(tag="⊢", evidence=[Evidence(source="x", signal="y")])),
        door_count=Aggregate(value=0, epistemic=EpistemicMark(tag="⊢", evidence=[Evidence(source="x", signal="y")])),
        window_count=Aggregate(value=0, epistemic=EpistemicMark(tag="⊢", evidence=[Evidence(source="x", signal="y")])),
        measured_wall_length_mm=Aggregate(
            value=mm_value,
            epistemic=(
                EpistemicMark(tag=mm_tag, evidence=[], gap="no scale" if mm_tag == "⊥" else None,
                              basis="extrap" if mm_tag == "⊬" else None)
                if mm_tag in ("⊥", "⊬")
                else EpistemicMark(tag=mm_tag, evidence=[Evidence(source="x", signal="y")])
            ),
        ),
    )


def test_measurement_policy_no_anchor_forbids_mm_on_object() -> None:
    """No scale anchor + object carries measurement_mm → ValidationError."""
    with pytest.raises(ValidationError, match="Measurement_Policy"):
        EngineOutput(
            drawing_id="d",
            objects=[_make_object_with_mm(mm=4200.0, m_tag="⊢")],
            aggregates=_minimal_aggregates(mm_value=None, mm_tag="⊥"),
            refusals=[],
            scale_anchor=ScaleAnchor(detected=False),
        )


def test_measurement_policy_no_anchor_forbids_non_unknown_object_tag() -> None:
    """No scale anchor + object measurement_epistemic.tag != ⊥ → ValidationError."""
    with pytest.raises(ValidationError, match="Measurement_Policy"):
        EngineOutput(
            drawing_id="d",
            objects=[_make_object_with_mm(mm=None, m_tag="⊢")],
            aggregates=_minimal_aggregates(mm_value=None, mm_tag="⊥"),
            refusals=[],
            scale_anchor=ScaleAnchor(detected=False),
        )


def test_measurement_policy_no_anchor_forbids_mm_aggregate_value() -> None:
    with pytest.raises(ValidationError, match="Measurement_Policy"):
        EngineOutput(
            drawing_id="d",
            objects=[_make_object_with_mm(mm=None, m_tag="⊥")],
            aggregates=_minimal_aggregates(mm_value=12000.0, mm_tag="⊥"),
            refusals=[],
            scale_anchor=ScaleAnchor(detected=False),
        )


def test_measurement_policy_no_anchor_forbids_non_unknown_aggregate_tag() -> None:
    with pytest.raises(ValidationError, match="Measurement_Policy"):
        EngineOutput(
            drawing_id="d",
            objects=[_make_object_with_mm(mm=None, m_tag="⊥")],
            aggregates=_minimal_aggregates(mm_value=None, mm_tag="⊨"),
            refusals=[],
            scale_anchor=ScaleAnchor(detected=False),
        )


def test_scale_anchor_detected_requires_px_per_mm() -> None:
    with pytest.raises(ValidationError, match="px_per_mm"):
        ScaleAnchor(detected=True, px_per_mm=None)


def test_scale_anchor_not_detected_forbids_px_per_mm() -> None:
    with pytest.raises(ValidationError, match="px_per_mm"):
        ScaleAnchor(detected=False, px_per_mm=1.5)


# ── Provenance ──────────────────────────────────────────────────────────────


def test_provenance_record_validates_sample() -> None:
    rec = ProvenanceRecord(
        drawing_id="sample_001",
        source="floorplancad",
        license="academic",
        sha256="a" * 64,
        fetched_at=datetime.now(timezone.utc),
        original_uri="https://example.com/sample.png",
        usage="demo-only",
        domain="global",
    )
    assert rec.license == "academic"
    assert rec.usage == "demo-only"


def test_provenance_rejects_short_sha256() -> None:
    with pytest.raises(ValidationError):
        ProvenanceRecord(
            drawing_id="sample_001",
            source="x",
            license="public",
            sha256="too_short",
            fetched_at=datetime.now(timezone.utc),
            original_uri="https://example.com/x",
            domain="global",
        )
