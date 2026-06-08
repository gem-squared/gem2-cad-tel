"""U3 acceptance — preview helpers (no Streamlit runtime needed).

The cached-loader test verifies @st.cache_data is wired on the cached layer.
The Preview_Is_Read_Only invariant is verified by grep / AST inspection.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"


def _import_ui_helpers():
    """Load ui/app.py top-level helpers without running Streamlit's app flow.

    The module-level Streamlit calls (st.set_page_config, st.title, st.tabs, etc.)
    will fire when we import — that's fine; they're idempotent + no-op in non-runtime.
    """
    spec = importlib.util.spec_from_file_location("_ui_app_helpers", ROOT / "ui" / "app.py")
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules["_ui_app_helpers"] = mod
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.fixture(scope="module")
def helpers():
    return _import_ui_helpers()


def _first_with_suffix(suffixes: tuple[str, ...]) -> Path | None:
    for p in sorted(SAMPLES.iterdir()):
        if p.suffix.lower() in suffixes:
            return p
    return None


# ── load_preview_image returns PIL.Image for supported formats ──────────────


def test_load_preview_image_png(helpers) -> None:
    png = _first_with_suffix((".png",))
    assert png, "no PNG sample in corpus"
    img = helpers.load_preview_image(png)
    assert isinstance(img, Image.Image)
    # Thumbnail dimensions: long edge ≤ max_width*2 (400*2 = 800), short edge ≤ max_width
    assert max(img.size) <= helpers.PREVIEW_MAX_WIDTH * 2


def test_load_preview_image_jpg(helpers) -> None:
    jpg = _first_with_suffix((".jpg", ".jpeg"))
    if not jpg:
        pytest.skip("no JPG sample in corpus")
    img = helpers.load_preview_image(jpg)
    assert isinstance(img, Image.Image)


def test_load_preview_image_pdf(helpers) -> None:
    pdf = _first_with_suffix((".pdf",))
    if not pdf:
        pytest.skip("no PDF sample in corpus")
    img = helpers.load_preview_image(pdf)
    assert isinstance(img, Image.Image)


# ── load_preview_image returns None for unsupported / missing ───────────────


def test_load_preview_image_svg_returns_none(helpers) -> None:
    svg = _first_with_suffix((".svg",))
    if not svg:
        pytest.skip("no SVG sample in corpus")
    assert helpers.load_preview_image(svg) is None


def test_load_preview_image_nonexistent_returns_none(helpers, tmp_path: Path) -> None:
    ghost = tmp_path / "nothing.png"
    assert helpers.load_preview_image(ghost) is None


# ── preview_status_message ──────────────────────────────────────────────────


def test_preview_status_message_for_svg(helpers) -> None:
    svg = _first_with_suffix((".svg",))
    if not svg:
        pytest.skip("no SVG sample in corpus")
    msg = helpers.preview_status_message(svg)
    assert msg is not None
    assert "SVG" in msg.upper()


def test_preview_status_message_for_png_returns_none(helpers) -> None:
    png = _first_with_suffix((".png",))
    assert png
    assert helpers.preview_status_message(png) is None


def test_preview_status_message_for_missing_file(helpers, tmp_path: Path) -> None:
    ghost = tmp_path / "ghost.png"
    msg = helpers.preview_status_message(ghost)
    assert msg is not None
    assert "not found" in msg


# ── cache wiring + invariant checks ─────────────────────────────────────────


def test_preview_loader_is_cached(helpers) -> None:
    """Cached_Preview invariant: the inner cached loader must carry st.cache_data wrapping."""
    cached = helpers._load_preview_image_cached
    # Streamlit cache_data wraps callables; check the cached function exposes the cache_data marker
    assert callable(cached)
    # The actual marker varies across streamlit versions; we look for cache_data hallmarks
    marker_present = (
        hasattr(cached, "clear")            # CachedFunc.clear()
        or hasattr(cached, "__wrapped__")    # decorator wrapping
        or hasattr(cached, "_cache_func")
    )
    assert marker_present, (
        f"_load_preview_image_cached doesn't appear to be cached: dir={dir(cached)[:5]}…"
    )


def test_preview_is_read_only_invariant() -> None:
    """AST check: each preview helper FUNCTION BODY must not call run_pipeline / AuditContext / init_audit_db.

    (Module-level imports of those names are OK — they're used by the Run Engine tab.)
    """
    import ast
    src = (ROOT / "ui" / "app.py").read_text()
    tree = ast.parse(src)
    PREVIEW_FUNCS = {
        "load_preview_image",
        "_load_preview_image_impl",
        "_load_preview_image_cached",
        "preview_status_message",
    }
    FORBIDDEN_CALLS = {"run_pipeline", "AuditContext", "init_audit_db", "ingest"}
    offenders: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in PREVIEW_FUNCS:
            for sub in ast.walk(node):
                # Check Call nodes specifically — references that aren't called are OK
                if isinstance(sub, ast.Call):
                    f = sub.func
                    name = None
                    if isinstance(f, ast.Name):
                        name = f.id
                    elif isinstance(f, ast.Attribute):
                        name = f.attr
                    if name in FORBIDDEN_CALLS:
                        offenders.append((node.name, name))
    assert not offenders, (
        f"Preview helpers call forbidden functions: {offenders} — "
        f"Preview_Is_Read_Only invariant violated"
    )


# ── WP-ST-6 U2: Drawing dropdown ordering — wm_* first, synth_* second ──────


def test_sort_samples_wm_before_synth(helpers) -> None:
    """Dropdown_Ordering invariant: _sort_samples_for_dropdown puts wm_* first,
    synth_* second, others last; alphabetical within each group."""
    paths = [
        Path("synth_apt_kr_balcony_03.png"),
        Path("wm_zebra.png"),
        Path("wm_alpha.png"),
        Path("synth_apt_kr_balcony_01.png"),
        Path("other_drawing.png"),
    ]
    out = [p.name for p in helpers._sort_samples_for_dropdown(paths)]
    assert out == [
        "wm_alpha.png",
        "wm_zebra.png",
        "synth_apt_kr_balcony_01.png",
        "synth_apt_kr_balcony_03.png",
        "other_drawing.png",
    ], f"unexpected ordering: {out}"


def test_sort_samples_real_corpus_wm_indices_precede_synth(helpers) -> None:
    """Live-corpus check: across data/samples/, every wm_* index < every synth_* index."""
    actual = (
        list(SAMPLES.glob("*.png"))
        + list(SAMPLES.glob("*.pdf"))
        + list(SAMPLES.glob("*.jpg"))
        + list(SAMPLES.glob("*.jpeg"))
        + list(SAMPLES.glob("*.svg"))
    )
    sorted_names = [p.name for p in helpers._sort_samples_for_dropdown(actual)]
    wm_idx = [i for i, n in enumerate(sorted_names) if n.startswith("wm_")]
    synth_idx = [i for i, n in enumerate(sorted_names) if n.startswith("synth_")]
    if not wm_idx or not synth_idx:
        pytest.skip("corpus lacks either wm_* or synth_* — ordering test trivially holds")
    assert max(wm_idx) < min(synth_idx), (
        f"wm_* must all precede synth_*. max(wm_idx)={max(wm_idx)} "
        f"min(synth_idx)={min(synth_idx)}; sample order head={sorted_names[:5]}"
    )


def test_ui_app_imports_cleanly() -> None:
    """Smoke: the entire ui/app.py compiles to bytecode."""
    src = (ROOT / "ui" / "app.py").read_text()
    compile(src, "ui/app.py", "exec")
