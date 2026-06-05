"""Corpus provenance schema — per-drawing source/license/sha256 record.

Every drawing in data/samples/ must have a matching data/provenance/{drawing_id}.json
file that validates against ProvenanceRecord. No silent ingestion.

Per WP-Level Provenance_Visibility invariant:
    No drawing with license = None enters data/samples/ silently.
    Uncertain sources use license = "check-required" (kept), never None (refused).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

LicenseCategory = Literal[
    "CC-BY",
    "CC-BY-SA",
    "CC-BY-NC",
    "academic",
    "public",
    "check-required",
]
"""Six license categories accepted for v0.1 corpus.

CC-BY            — Creative Commons Attribution
CC-BY-SA         — Attribution-ShareAlike
CC-BY-NC         — Attribution-NonCommercial (research-only, NOT commercial-safe)
academic         — research/educational use only
public           — public domain or self-generated synthetic drawings
check-required   — surfaced for human review BEFORE commercial use
"""

DomainTag = Literal["global", "kr", "dwg_demo"]
"""Three domain tags:

global    — culturally-neutral floor plans (FloorPlanCAD, Roboflow)
kr        — Korean apartment / 적산 domain
dwg_demo  — Cal Poly DWG-rendered subset for DWG ingestion demo (NOT training)
"""

UsageTag = Literal["demo-only", "training", "evaluation"]


class ProvenanceRecord(BaseModel):
    """One row in the corpus ledger. Append-only by convention; per-file JSON for atomicity."""
    model_config = ConfigDict(extra="forbid")

    drawing_id: str = Field(..., description="Stable identifier; usually hash-based")
    source: str = Field(..., description="Named registry entry: floorplancad, calpoly_dwg, ...")
    license: LicenseCategory
    sha256: str = Field(..., min_length=64, max_length=64, description="SHA-256 hex digest")
    fetched_at: datetime = Field(..., description="ISO8601 timestamp of corpus addition")
    original_uri: str | HttpUrl = Field(..., description="URL or filesystem path to original source")
    usage: UsageTag = "demo-only"
    domain: DomainTag


EXCLUDED_SOURCES: tuple[str, ...] = (
    "분양자료",        # Korean apartment marketing materials (real-estate copyright)
    "real-estate blog",
    "Pinterest / image-search scrape",
    "construction-company internal PDF",
)
"""Categories excluded from data/samples/. Per CORPUS.md policy."""
