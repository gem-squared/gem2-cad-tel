"""Evaluation subpackage — metrics, macro weighting, promotion predicate.

Introduced by WP-ST-3 U6 (2026-08-25). Depends only on the AnnotationRecord
schema (WP-ST-3 U2) + the public EngineOutput schema (src/cad_trust/schema.py) —
does NOT depend on annotations actually existing. That means this module is
usable as a library even before U4 completes.
"""

from cad_trust.eval.metrics import (
    boundary_quality,
    character_error_rate,
    dimension_association_accuracy,
    false_anchor_rate,
    instance_recall,
    map_at_ious,
    mask_polygon_iou,
    relative_scale_error,
    risk_coverage_curve,
    topology_connectivity,
)
from cad_trust.eval.promotion import (
    Waiver,
    PromotionVerdict,
    evaluate_promotion,
    load_benchmark_contract,
)

__all__ = [
    "boundary_quality",
    "character_error_rate",
    "dimension_association_accuracy",
    "false_anchor_rate",
    "instance_recall",
    "map_at_ious",
    "mask_polygon_iou",
    "relative_scale_error",
    "risk_coverage_curve",
    "topology_connectivity",
    "Waiver",
    "PromotionVerdict",
    "evaluate_promotion",
    "load_benchmark_contract",
]
