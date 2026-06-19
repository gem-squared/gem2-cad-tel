"""U4 Ingest_F acceptance tests."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from cad_trust.ingest import IngestError, IngestResult, ingest

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def png_fixture() -> Path:
    candidates = sorted(SAMPLES.glob("*.png"))
    assert candidates, "no PNG samples in data/samples/ — U3 must run first"
    return candidates[0]


@pytest.fixture(scope="session")
def pdf_fixture() -> Path:
    """Create a single PDF fixture from a PNG sample (PIL can save RGB → PDF)."""
    src = sorted(SAMPLES.glob("*.png"))[0]
    out = FIXTURES / "ingest_test.pdf"
    if not out.exists():
        with Image.open(src) as img:
            img.convert("RGB").save(out, "PDF", resolution=200.0)
    assert out.exists()
    return out


def test_ingest_png_returns_canonical(png_fixture: Path) -> None:
    result = ingest(png_fixture)
    assert isinstance(result, IngestResult)
    assert result.source_format == "png"
    assert result.page_index is None
    assert result.ingest_metadata.page_count == 1
    assert isinstance(result.canonical_image, np.ndarray)
    assert result.canonical_image.dtype == np.uint8
    assert result.canonical_image.ndim == 3
    assert result.canonical_image.shape[2] == 3


def test_ingest_pdf_page_zero(pdf_fixture: Path) -> None:
    result = ingest(pdf_fixture)
    assert result.source_format == "pdf"
    assert result.page_index == 0
    assert result.canonical_image.shape[2] == 3
    assert isinstance(result.canonical_image, np.ndarray)


def test_ingest_all_corpus_pngs_without_raising() -> None:
    failures: list[str] = []
    pngs = sorted(SAMPLES.glob("*.png"))
    assert len(pngs) >= 10, "corpus must have ≥10 PNGs (U3 acceptance)"
    for p in pngs:
        try:
            result = ingest(p)
            assert result.canonical_image is not None
        except Exception as exc:
            failures.append(f"{p.name}: {exc}")
    assert not failures, f"ingest failures: {failures}"


def test_unreadable_file_raises_ingest_error(tmp_path: Path) -> None:
    bogus = tmp_path / "not_a_real_drawing.png"
    bogus.write_bytes(b"not a real PNG header")
    with pytest.raises(IngestError):
        ingest(bogus)


def test_missing_file_raises_ingest_error() -> None:
    with pytest.raises(IngestError, match="not found"):
        ingest("/tmp/nonexistent_drawing_xyz.png")


def test_unsupported_format_raises_ingest_error(tmp_path: Path) -> None:
    f = tmp_path / "drawing.txt"
    f.write_text("not a drawing")
    with pytest.raises(IngestError, match="unsupported"):
        ingest(f)


def test_aspect_ratio_preserved(png_fixture: Path) -> None:
    result = ingest(png_fixture)
    ow, oh = result.original_dims
    nw, nh = result.normalized_dims
    # v0.1 does no resizing — dims should be identical
    assert (ow, oh) == (nw, nh)
    # Aspect ratio test (for forward-compat with future resizing):
    orig_ratio = ow / oh
    norm_ratio = nw / nh
    assert abs(orig_ratio - norm_ratio) < 0.01
