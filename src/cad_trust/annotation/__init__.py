"""Annotation subpackage — schema, labeling policy, tool interchange.

Introduced by WP-ST-3 U2 (2026-08-25). AnnotationRecord is the source-of-truth
for corpus-level annotations used to train + evaluate WP-ST-4 experts. The
public EngineOutput schema (src/cad_trust/schema.py) is unchanged by this
subpackage; WP-ST-5 U1 handles additive EngineOutput evolution separately.
"""

from cad_trust.annotation.schema import (
    AnnotationClass,
    AnnotationGeometry,
    AnnotationRecord,
    AmbiguityFlag,
    ReviewStatus,
    LabelProducer,
)

__all__ = [
    "AnnotationClass",
    "AnnotationGeometry",
    "AnnotationRecord",
    "AmbiguityFlag",
    "ReviewStatus",
    "LabelProducer",
]
