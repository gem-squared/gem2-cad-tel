"""WP-ST-8 U1 — default-sample-index resolution for the Streamlit dropdown.

Tests the `_default_sample_index` helper in `ui/app.py`. Pure function — no
Streamlit runtime needed; mirrors the import pattern in test_ui_preview.py.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _import_ui_helpers():
    spec = importlib.util.spec_from_file_location("_ui_app_helpers_u8", ROOT / "ui" / "app.py")
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules["_ui_app_helpers_u8"] = mod
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.fixture(scope="module")
def helpers():
    return _import_ui_helpers()


def test_default_sample_constant_is_ash_pits(helpers) -> None:
    """The default sample is the wm_00104 ash_pits cross-section (high-signal demo)."""
    assert "ash_pits" in helpers.DEFAULT_SAMPLE_NAME
    assert helpers.DEFAULT_SAMPLE_NAME.startswith("wm_00104")
    assert helpers.DEFAULT_SAMPLE_NAME.endswith(".jpg")


def test_default_index_when_present(helpers) -> None:
    """When DEFAULT_SAMPLE_NAME is in options, return its position."""
    options = [
        "(upload your own)",
        "synth_a.png",
        helpers.DEFAULT_SAMPLE_NAME,
        "wm_other.jpg",
    ]
    assert helpers._default_sample_index(options) == 2


def test_default_index_when_absent_with_samples(helpers) -> None:
    """When DEFAULT_SAMPLE_NAME is missing but samples exist, fall back to index 1."""
    options = ["(upload your own)", "synth_a.png", "synth_b.png"]
    assert helpers._default_sample_index(options) == 1


def test_default_index_when_no_samples(helpers) -> None:
    """When only the upload-your-own placeholder exists, return 0."""
    options = ["(upload your own)"]
    assert helpers._default_sample_index(options) == 0


def test_default_sample_actually_in_corpus() -> None:
    """The named default file must exist on disk, or production UI fallbacks to index 1."""
    samples = ROOT / "data" / "samples"
    target = samples / "wm_00104_bm--cross_section_of_ash_pits--wabash_railroad--decatur_il_50f7feda-0ce0-4.jpg"
    assert target.exists(), f"DEFAULT_SAMPLE_NAME not found in {samples}"
