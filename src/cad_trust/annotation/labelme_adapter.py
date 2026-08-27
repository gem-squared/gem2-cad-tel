"""LabelMe interchange adapter.

LabelMe emits per-image JSON with a `shapes` array. Each shape has
`{label, points, group_id, shape_type, flags}`. This adapter converts
LabelMe shapes ↔ AnnotationRecord round-trip.

Chosen tool: LabelMe (over CVAT / Roboflow) for WP-ST-3 U2 because:
- Self-hostable + no server needed for small corpus
- JSON per image = simple provenance
- shape_type ∈ {polygon, rectangle, line, linestrip, point} maps to our geometry kinds
- Widely adopted (Anaconda-maintained fork available)

If future work needs COCO or CVAT interchange, add sibling adapters here.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from cad_trust.annotation.schema import (
    AnnotationClass,
    AnnotationGeometry,
    AnnotationRecord,
    compute_annotation_digest,
)


# LabelMe shape_type → AnnotationGeometryKind
_SHAPE_TYPE_MAP = {
    "polygon": "polygon",
    "rectangle": "bbox",
    "line": "polyline",
    "linestrip": "polyline",
}

# LabelMe label field convention: "{class}[|{attrs}]"
# e.g., "door", "wall|structural", "dimension_text|value=5400"


def labelme_shape_to_annotation(
    shape: dict[str, Any],
    drawing_id: str,
    label_producer: str,
    tool_version: str,
    reviewer_identity_or_role: str | None = None,
    review_status: str = "unreviewed",
) -> AnnotationRecord:
    """Convert one LabelMe shape dict to an AnnotationRecord."""
    label = shape["label"]
    class_part, _, attrs = label.partition("|")
    kind = _SHAPE_TYPE_MAP.get(shape["shape_type"], "polygon")

    geometry_kwargs: dict[str, Any] = {"kind": kind}
    points = shape["points"]
    if kind == "polygon":
        geometry_kwargs["vertices"] = points
    elif kind == "bbox":
        # LabelMe rectangle = 2 points (top-left, bottom-right)
        geometry_kwargs["bbox"] = points
    elif kind == "polyline":
        geometry_kwargs["polyline"] = points

    geometry = AnnotationGeometry(**geometry_kwargs)

    transcription = None
    if class_part == "dimension_text" and attrs.startswith("value="):
        transcription = attrs.split("=", 1)[1]

    annotation_id = str(shape.get("group_id") or uuid.uuid4())
    payload = {
        "drawing_id": drawing_id,
        "annotation_id": annotation_id,
        "class": class_part,
        "geometry": geometry.model_dump(),
        "transcription": transcription,
        "label_producer": label_producer,
        "tool": "labelme",
        "tool_version": tool_version,
        "review_status": review_status,
        "reviewer_identity_or_role": reviewer_identity_or_role,
        "ambiguity_flag": shape.get("flags", {}).get("ambiguity_flag", "clear"),
    }
    digest = compute_annotation_digest(payload)
    payload["annotation_digest"] = digest
    return AnnotationRecord(**payload)


def annotation_to_labelme_shape(anno: AnnotationRecord) -> dict[str, Any]:
    """Convert one AnnotationRecord back to a LabelMe shape dict."""
    kind_reverse = {v: k for k, v in _SHAPE_TYPE_MAP.items() if k != "linestrip"}
    shape_type = kind_reverse.get(anno.geometry.kind, "polygon")

    if anno.geometry.kind == "polygon":
        points = anno.geometry.vertices
    elif anno.geometry.kind == "bbox":
        points = anno.geometry.bbox
    elif anno.geometry.kind == "polyline":
        points = anno.geometry.polyline
    else:
        points = anno.geometry.vertices or []

    label = anno.cls
    if anno.cls == "dimension_text" and anno.transcription:
        label = f"dimension_text|value={anno.transcription}"

    return {
        "label": label,
        "points": points,
        "group_id": anno.annotation_id,
        "shape_type": shape_type,
        "flags": {"ambiguity_flag": anno.ambiguity_flag},
    }


def load_labelme_file(
    labelme_path: Path,
    drawing_id: str,
    label_producer: str,
    tool_version: str,
    reviewer_identity_or_role: str | None = None,
    review_status: str = "unreviewed",
) -> list[AnnotationRecord]:
    """Load a LabelMe JSON file and return the list of AnnotationRecords."""
    data = json.loads(labelme_path.read_text())
    return [
        labelme_shape_to_annotation(
            shape,
            drawing_id=drawing_id,
            label_producer=label_producer,
            tool_version=tool_version,
            reviewer_identity_or_role=reviewer_identity_or_role,
            review_status=review_status,
        )
        for shape in data.get("shapes", [])
    ]


def dump_labelme_file(
    annotations: list[AnnotationRecord],
    labelme_path: Path,
    image_path: str,
    image_width: int,
    image_height: int,
) -> None:
    """Write a LabelMe JSON file from AnnotationRecords."""
    data = {
        "version": "5.0.0",
        "flags": {},
        "shapes": [annotation_to_labelme_shape(a) for a in annotations],
        "imagePath": image_path,
        "imageData": None,
        "imageHeight": image_height,
        "imageWidth": image_width,
    }
    labelme_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
