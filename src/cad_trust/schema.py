"""CAD Trust Engine output contract — Pydantic v2 schemas.

The contract is the product. Detection serves the contract, not vice versa.

Three orthogonal epistemic claims per object:
    type_epistemic        — is this a wall / door / window / ...?
    geometry_epistemic    — is this the right shape / location / extent?
    measurement_epistemic — is the mm measurement reliable?

Measurement Policy (WP-Level Invariant):
    Never emit measurement_mm unless scale_anchor.detected = True.
    type / geometry confidence does NOT imply measurement confidence.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ── Epistemic primitives ────────────────────────────────────────────────────

EpistemicTagLiteral = Literal["⊢", "⊨", "⊬", "⊥"]
"""Universal EEF taxonomy.
⊢ GROUNDED      — claim from direct evidence (file, geometry match, OCR hit)
⊨ INFERRED      — derived from ⊢ claims with visible chain
⊬ EXTRAPOLATED  — beyond evidence; basis MUST be stated
⊥ UNKNOWN       — knowledge gap; stops inference chain
"""


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str = Field(..., description="Producer: opencv_line, paddleocr, opencv_arc, ...")
    signal: str = Field(..., description="What was observed, in human terms")


class EpistemicMark(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tag: EpistemicTagLiteral
    evidence: list[Evidence] = Field(default_factory=list)
    basis: str | None = Field(
        default=None,
        description="Required when tag = ⊬ — names the extrapolation basis",
    )
    gap: str | None = Field(
        default=None,
        description="Required when tag = ⊥ — names the knowledge gap",
    )

    @model_validator(mode="after")
    def _check_basis_and_gap(self) -> EpistemicMark:
        if self.tag == "⊬" and not self.basis:
            raise ValueError("EpistemicMark.tag = ⊬ requires non-empty `basis`")
        if self.tag == "⊥" and not self.gap:
            raise ValueError("EpistemicMark.tag = ⊥ requires non-empty `gap`")
        return self


# ── Geometry primitives ─────────────────────────────────────────────────────

GeometryKind = Literal["bbox", "polyline", "polygon"]


class Geometry(BaseModel):
    """Pixel-space geometry. mm conversion is separate (see Object.measurement_mm)."""
    model_config = ConfigDict(extra="forbid")
    kind: GeometryKind
    coords_px: list[list[float]] = Field(
        ...,
        description=(
            "bbox: [[x0,y0],[x1,y1]] (2 points). "
            "polyline: [[x0,y0],[x1,y1],...] (≥2 points). "
            "polygon: [[x0,y0],...] closed (first ≠ last; closure implied)."
        ),
    )


# ── Object taxonomy ─────────────────────────────────────────────────────────

ObjectType = Literal[
    "wall_wet",
    "wall_dry",
    "wall_structural",
    "door",
    "window",
    "balcony_sash",
    "inspection_hatch",
    "dimension_text",
    "room_label",
    "space_polygon",
]

ReviewStatus = Literal["auto_accepted", "needs_human", "rejected"]


class Object(BaseModel):
    """One detected CAD object with three orthogonal epistemic claims."""
    model_config = ConfigDict(extra="forbid")
    object_id: str
    type: ObjectType
    type_epistemic: EpistemicMark
    geometry: Geometry
    geometry_epistemic: EpistemicMark
    measurement_mm: float | None = Field(
        default=None,
        description="Length / area in mm. MUST be None unless scale_anchor.detected = True.",
    )
    measurement_epistemic: EpistemicMark
    review_status: ReviewStatus


# ── Top-level engine output ─────────────────────────────────────────────────

class Refusal(BaseModel):
    """A region the engine REFUSED to commit on. First-class output, not silence."""
    model_config = ConfigDict(extra="forbid")
    region: list[list[float]] = Field(
        ..., description="bbox [[x0,y0],[x1,y1]] of the refused region in pixel space"
    )
    why: str = Field(..., description="Human-readable reason — never generic 'unknown'")


class ScaleAnchor(BaseModel):
    """Whether the engine found a reliable px→mm conversion factor."""
    model_config = ConfigDict(extra="forbid")
    detected: bool
    px_per_mm: float | None = None
    source: str | None = Field(
        default=None,
        description="Method used: 'dimension_text_match' | 'user_provided' | None",
    )

    @model_validator(mode="after")
    def _check_consistency(self) -> ScaleAnchor:
        if self.detected and self.px_per_mm is None:
            raise ValueError("ScaleAnchor.detected=True requires px_per_mm")
        if not self.detected and self.px_per_mm is not None:
            raise ValueError("ScaleAnchor.detected=False forbids px_per_mm")
        return self


class Aggregate(BaseModel):
    """One aggregate value with its own epistemic mark.

    Per Measurement_Policy: when source measurements are ⊥, aggregate is ⊥ too.
    """
    model_config = ConfigDict(extra="forbid")
    value: float | int | None
    epistemic: EpistemicMark
    warning: str | None = Field(
        default=None,
        description="Set when ⊬/⊥ objects contributed — names the taint",
    )


class Aggregates(BaseModel):
    model_config = ConfigDict(extra="forbid")
    wall_count: Aggregate
    door_count: Aggregate
    window_count: Aggregate
    measured_wall_length_mm: Aggregate


class EngineOutput(BaseModel):
    """The full v0.1 contract. One drawing in → this out."""
    model_config = ConfigDict(extra="forbid")
    drawing_id: str
    objects: list[Object]
    aggregates: Aggregates
    refusals: list[Refusal]
    scale_anchor: ScaleAnchor

    @model_validator(mode="after")
    def _enforce_measurement_policy(self) -> EngineOutput:
        """When no scale anchor, no object may carry measurement_mm and the mm aggregate must be ⊥."""
        if not self.scale_anchor.detected:
            for obj in self.objects:
                if obj.measurement_mm is not None:
                    raise ValueError(
                        f"Measurement_Policy violation: object {obj.object_id} "
                        f"has measurement_mm={obj.measurement_mm} but scale_anchor.detected=False"
                    )
                if obj.measurement_epistemic.tag != "⊥":
                    raise ValueError(
                        f"Measurement_Policy violation: object {obj.object_id} "
                        f"has measurement_epistemic.tag={obj.measurement_epistemic.tag} but scale_anchor.detected=False"
                    )
            mm_agg = self.aggregates.measured_wall_length_mm
            if mm_agg.value is not None:
                raise ValueError(
                    "Measurement_Policy violation: aggregates.measured_wall_length_mm.value "
                    "must be None when scale_anchor.detected=False"
                )
            if mm_agg.epistemic.tag != "⊥":
                raise ValueError(
                    "Measurement_Policy violation: aggregates.measured_wall_length_mm.epistemic.tag "
                    "must be ⊥ when scale_anchor.detected=False"
                )
        return self
