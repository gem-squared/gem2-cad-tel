"""Annotation schema for WP-ST-3 U2 — labeling contract for the corpus.

Preserves the existing public ObjectType taxonomy from src/cad_trust/schema.py
verbatim and adds generic `wall` + dimension_line + scale_anchor_evidence
required by hybrid vision annotation. AnnotationRecord is an INTERNAL corpus
contract; it does NOT modify the public EngineOutput surface.
"""
from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ── Annotation class taxonomy ────────────────────────────────────────────────
# Preserves all 10 existing public ObjectType literals verbatim + adds three
# generic/derived types needed for annotation-time claims.
AnnotationClass = Literal[
    # Preserved verbatim from public ObjectType:
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
    # Added at annotation layer (WP-ST-3 U2, CD Mission Directive 2026-08-25):
    "wall",                    # generic — unclassified wall not mislabeled as wall_structural
    "dimension_line",          # dimension geometry with endpoints + extension lines
    "scale_anchor_evidence",   # dimension_text ↔ dimension_line ↔ measured-object triple
]


AnnotationGeometryKind = Literal["mask", "polygon", "bbox", "polyline", "quad"]


class AnnotationGeometry(BaseModel):
    """Class-appropriate geometry per spec §4.2. Kind chosen per AnnotationClass."""
    model_config = ConfigDict(extra="forbid")

    kind: AnnotationGeometryKind
    # For mask: RLE-encoded string or path to mask PNG
    mask_ref: str | None = None
    # For polygon/quad: list of [x, y] vertices in source-pixel space (CW ordering)
    vertices: list[list[float]] | None = None
    # For bbox: [[x0,y0],[x1,y1]]
    bbox: list[list[float]] | None = None
    # For polyline (dimension_line etc.): ordered vertices + optional extension-line endpoints
    polyline: list[list[float]] | None = None
    extension_lines: list[list[list[float]]] | None = None

    @model_validator(mode="after")
    def _validate_kind_matches_fields(self) -> "AnnotationGeometry":
        # Enforce that the field matching the kind is populated (and only it).
        # Non-required fields for other kinds may remain None.
        required = {
            "mask": "mask_ref",
            "polygon": "vertices",
            "quad": "vertices",
            "bbox": "bbox",
            "polyline": "polyline",
        }[self.kind]
        if getattr(self, required) is None:
            raise ValueError(
                f"AnnotationGeometry(kind={self.kind!r}) requires {required!r} to be populated"
            )
        if self.kind == "quad" and len(self.vertices or []) != 4:
            raise ValueError("quad geometry requires exactly 4 vertices")
        return self


AmbiguityFlag = Literal["clear", "ambiguous", "illegible", "out_of_scope"]

ReviewStatus = Literal[
    "unreviewed",
    "ai_silver",              # AI-produced, not yet human-reviewed
    "human_reviewed",         # single human reviewer signed off
    "human_double_reviewed",  # two independent human reviewers agreed
]

LabelProducer = Literal[
    "human",
    "ai_claude",
    "ai_codex",
    "ai_approved_vision_pipeline",
    "programmatic_synthetic",  # ground truth from synthesizer
]


class AnnotationRecord(BaseModel):
    """One annotation on one drawing.

    Ambiguous / illegible instances stay marked ambiguous — never forced into a
    positive class. AI-only annotations (review_status in {unreviewed, ai_silver})
    are forbidden from frozen test/val splits per WP-ST-3 U4 labeling policy.
    """
    model_config = ConfigDict(extra="forbid")

    drawing_id: str
    annotation_id: str
    cls: AnnotationClass = Field(alias="class")
    geometry: AnnotationGeometry
    # For dimension_text
    transcription: str | None = None
    # For doors / windows — the wall span they attach to (referenced by wall annotation_id)
    attachment_span_ref: str | None = None
    # For dimensions — the object/span this dimension measures
    association_ref: str | None = None
    ambiguity_flag: AmbiguityFlag = "clear"
    # Provenance of the label itself
    label_producer: LabelProducer
    tool: str
    tool_version: str
    review_status: ReviewStatus = "unreviewed"
    reviewer_identity_or_role: str | None = None
    annotation_digest: str

    @field_validator("annotation_digest")
    @classmethod
    def _digest_format(cls, v: str) -> str:
        if len(v) != 64 or not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError("annotation_digest must be a 64-char hex SHA-256")
        return v.lower()

    @model_validator(mode="after")
    def _enforce_labeling_policy(self) -> "AnnotationRecord":
        # Ambiguous instances MUST have ambiguity_flag != "clear"
        # (Positive spec — do not force into class; represented by ambiguity_flag)
        # Doors/windows recommended to have attachment_span_ref (soft — attachment
        # may not always be visible; validators log a warning rather than fail)
        # dimension_text should have transcription:
        if self.cls == "dimension_text" and self.transcription is None:
            raise ValueError("dimension_text annotation requires transcription")
        # dimension_line/scale_anchor_evidence should NOT have transcription:
        if self.cls in ("dimension_line", "scale_anchor_evidence") and self.transcription is not None:
            raise ValueError(f"{self.cls} annotation must not carry transcription")
        # scale_anchor_evidence requires association_ref (the measured object)
        if self.cls == "scale_anchor_evidence" and self.association_ref is None:
            raise ValueError("scale_anchor_evidence requires association_ref to measured object")
        return self


def compute_annotation_digest(payload: dict) -> str:
    """Deterministic SHA-256 over a normalized annotation payload.

    Callers should pass the AnnotationRecord dict WITHOUT the `annotation_digest`
    field itself (since the digest is over the semantic content). Sort keys +
    UTF-8 encoding = deterministic content addressing.
    """
    payload_normalized = {k: v for k, v in payload.items() if k != "annotation_digest"}
    canonical = json.dumps(payload_normalized, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
