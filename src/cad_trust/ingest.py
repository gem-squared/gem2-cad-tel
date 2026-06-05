"""U4: Ingest_F — PNG/PDF → normalized raster.

Contract:
    A: drawing_path: Path, dpi_target: int = 200
    B: IngestResult { canonical_image: np.ndarray (H,W,3) uint8,
                      source_format: 'png' | 'pdf',
                      page_index: int | None,
                      original_dims: (W, H),
                      normalized_dims: (W', H'),
                      ingest_metadata: { filename, page_count, ingest_timestamp_iso8601 } }
    P: drawing_path readable; PDF requires pdf2image + poppler

NEVER returns silent None — unreadable → IngestError.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image


class IngestError(Exception):
    """Raised when a drawing cannot be ingested. Typed; never returned as None."""


@dataclass
class IngestMetadata:
    filename: str
    page_count: int
    ingest_timestamp_iso8601: str


@dataclass
class IngestResult:
    canonical_image: np.ndarray
    source_format: str  # 'png' | 'pdf'
    page_index: int | None
    original_dims: tuple[int, int]   # (W, H)
    normalized_dims: tuple[int, int]  # (W, H)
    ingest_metadata: IngestMetadata
    warnings: list[str] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pil_to_ndarray(img: Image.Image) -> np.ndarray:
    rgb = img.convert("RGB")
    return np.asarray(rgb, dtype=np.uint8)


def _ingest_png(path: Path) -> IngestResult:
    try:
        with Image.open(path) as img:
            img.load()
            original = img.size  # (W, H)
            arr = _pil_to_ndarray(img)
    except Exception as exc:
        raise IngestError(f"failed to read PNG {path}: {exc}") from exc
    h, w = arr.shape[:2]
    return IngestResult(
        canonical_image=arr,
        source_format="png",
        page_index=None,
        original_dims=original,
        normalized_dims=(w, h),
        ingest_metadata=IngestMetadata(
            filename=path.name, page_count=1, ingest_timestamp_iso8601=_now_iso()
        ),
    )


def _ingest_pdf(path: Path, dpi_target: int) -> IngestResult:
    try:
        from pdf2image import convert_from_path
        from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError
    except ImportError as exc:
        raise IngestError(f"pdf2image not available: {exc}") from exc
    try:
        pages = convert_from_path(str(path), dpi=dpi_target)
    except (PDFInfoNotInstalledError, PDFPageCountError) as exc:
        raise IngestError(f"failed to read PDF {path}: {exc}") from exc
    except Exception as exc:
        raise IngestError(f"unexpected PDF failure for {path}: {exc}") from exc
    if not pages:
        raise IngestError(f"PDF {path} produced 0 pages")
    page_count = len(pages)
    first = pages[0]
    original = first.size
    arr = _pil_to_ndarray(first)
    h, w = arr.shape[:2]
    warnings: list[str] = []
    if page_count > 1:
        warnings.append(
            f"PDF has {page_count} pages; v0.1 ingests page 0 only — multi-page deferred to v0.2"
        )
    return IngestResult(
        canonical_image=arr,
        source_format="pdf",
        page_index=0,
        original_dims=original,
        normalized_dims=(w, h),
        ingest_metadata=IngestMetadata(
            filename=path.name, page_count=page_count, ingest_timestamp_iso8601=_now_iso()
        ),
        warnings=warnings,
    )


def ingest(drawing_path: Path | str, dpi_target: int = 200) -> IngestResult:
    """Public entry. PNG → direct PIL load. PDF → pdf2image (poppler). Other → IngestError."""
    path = Path(drawing_path)
    if not path.exists():
        raise IngestError(f"file not found: {path}")
    if not path.is_file():
        raise IngestError(f"not a regular file: {path}")
    suffix = path.suffix.lower()
    if suffix == ".png":
        return _ingest_png(path)
    if suffix == ".pdf":
        return _ingest_pdf(path, dpi_target=dpi_target)
    raise IngestError(f"unsupported format {suffix} (v0.1 supports .png + .pdf only)")
