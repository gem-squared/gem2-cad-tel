"""U1 acceptance tests — license mapping + Wikimedia client surface.

Network-free: monkeypatches urllib.request.urlopen.
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

# Load the crawl module directly from scripts/ since it's not a package export
ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "crawl_corpus.py"

_spec = importlib.util.spec_from_file_location("_crawl_corpus_test_module", SCRIPT)
crawl = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
sys.modules["_crawl_corpus_test_module"] = crawl
assert _spec and _spec.loader
_spec.loader.exec_module(crawl)  # type: ignore[union-attr]


# ── License mapping ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("cc-by-sa-4.0", "CC-BY-SA"),
        ("CC-BY-SA-3.0", "CC-BY-SA"),
        ("cc-by-4.0", "CC-BY"),
        ("cc-by", "CC-BY"),
        ("cc-by-nc-2.0", "CC-BY-NC"),
        ("cc-by-nc-sa-4.0", "CC-BY-NC"),
        ("PD-old", "public"),
        ("PD-self", "public"),
        ("publicdomain", "public"),
        ("cc-zero", "public"),
        # v0.1.3 additions: plain 'pd' and 'public-domain'
        ("pd", "public"),
        ("PD", "public"),  # case-insensitive
        ("public-domain", "public"),
        ("Public-Domain", "public"),
        ("cc0", "public"),  # v0.1.3: plain cc0 now maps
        ("CC0", "public"),  # case-insensitive
        ("GFDL", None),
        ("", None),
        (None, None),
    ],
)
def test_license_mapping(raw, expected) -> None:
    assert crawl.map_license(raw) == expected


def test_pd_dash_regression_still_works() -> None:
    """v0.1.3 added plain 'pd' but longer 'pd-' prefix MUST still win for things like 'pd-old'."""
    # PD-old should match 'pd-' (the explicit -old suffix is preserved as 'public')
    assert crawl.map_license("PD-old") == "public"
    assert crawl.map_license("pd-self") == "public"
    assert crawl.map_license("pd-something-new") == "public"


def test_no_source_bluff_still_holds_after_pd_addition() -> None:
    """Adding plain 'pd' must NOT cause spurious matches on unknown codes.

    v0.1.3 uses exact-match for short tokens like 'pd' so 'pdf' / 'pdq' / etc.
    don't false-match into 'public'.
    """
    assert crawl.map_license("custom-corporate-eula") is None
    assert crawl.map_license("pdf") is None        # exact match — 'pdf' != 'pd'
    assert crawl.map_license("pdf-license") is None  # not 'pd-*' either
    assert crawl.map_license("pdq") is None
    assert crawl.map_license("private") is None    # not in table


def test_license_mapping_never_optimistic_on_unknown() -> None:
    """No_Source_Bluff: unknown license MUST map to None (REFUSE), not 'public'."""
    assert crawl.map_license("some-future-license") is None
    assert crawl.map_license("custom-corporate-eula") is None


# ── safe_stem + extension inference ─────────────────────────────────────────


def test_safe_stem_strips_file_prefix_and_extension() -> None:
    assert crawl.safe_stem("File:House plan (1893) - Foo.png").startswith("house_plan_1893")


def test_safe_stem_lowercases_and_replaces_non_alnum() -> None:
    s = crawl.safe_stem("File:Plan Étage 1 — détail.svg")
    assert all(ch in "abcdefghijklmnopqrstuvwxyz0123456789_-" for ch in s)


def test_infer_extension_prefers_content_type() -> None:
    assert crawl.infer_extension("https://x/y.png", {"content-type": "image/jpeg"}) == ".jpg"
    assert crawl.infer_extension("https://x/y", {"content-type": "image/png"}) == ".png"


def test_infer_extension_falls_back_to_url_suffix() -> None:
    assert crawl.infer_extension("https://x/y.jpg", {}) == ".jpg"
    assert crawl.infer_extension("https://x/y", {}) == ".png"  # default


# ── WikimediaClient.query_category with mocked HTTP ─────────────────────────


def _fake_api_response() -> bytes:
    return json.dumps({
        "query": {
            "pages": {
                "12345": {
                    "title": "File:Sample plan.png",
                    "imageinfo": [{
                        "url": "https://upload.wikimedia.org/sample.png",
                        "descriptionshorturl": "https://commons.wikimedia.org/wiki/File:Sample_plan.png",
                        "mime": "image/png",
                        "size": 50000,
                        "extmetadata": {
                            "License": {"value": "cc-by-sa-4.0"},
                            "LicenseShortName": {"value": "CC BY-SA 4.0"},
                            "Artist": {"value": "<a href='/wiki/User:X'>Some Artist</a>"},
                        },
                    }],
                },
                "67890": {
                    "title": "File:Unlicensed.jpg",
                    "imageinfo": [{
                        "url": "https://upload.wikimedia.org/unlicensed.jpg",
                        "descriptionshorturl": "https://commons.wikimedia.org/wiki/File:Unlicensed.jpg",
                        "size": 30000,
                        "extmetadata": {},  # no license metadata
                    }],
                },
            }
        }
    }).encode("utf-8")


def test_query_category_parses_candidates(monkeypatch) -> None:
    def fake_get(url, timeout=30.0):
        return 200, _fake_api_response(), {"content-type": "application/json"}
    monkeypatch.setattr(crawl, "_http_get", fake_get)
    monkeypatch.setattr(crawl, "_sleep_polite", lambda: None)
    client = crawl.WikimediaClient()
    candidates = client.query_category("Floor plans", limit=5)
    assert len(candidates) == 2
    by_file = {c.filename: c for c in candidates}
    sample = by_file["File:Sample plan.png"]
    assert sample.license_mapped == "CC-BY-SA"
    assert sample.attribution == "Some Artist"
    assert sample.url and sample.url.startswith("https://")
    unlicensed = by_file["File:Unlicensed.jpg"]
    assert unlicensed.license_raw is None
    assert unlicensed.license_mapped is None  # REFUSE candidate


def test_query_category_sends_user_agent(monkeypatch) -> None:
    """Verify _http_get is wrapped with the identifying user-agent (Polite_Crawling)."""
    captured_headers: dict[str, str] = {}

    def fake_urlopen(req, timeout=30.0):
        nonlocal captured_headers
        captured_headers = {k.lower(): v for k, v in req.header_items()}
        class FakeResp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def getcode(self): return 200
            def read(self): return _fake_api_response()
            @property
            def headers(self):
                from email.message import Message
                m = Message()
                m["Content-Type"] = "application/json"
                return m
        return FakeResp()
    monkeypatch.setattr(crawl.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(crawl, "_sleep_polite", lambda: None)
    client = crawl.WikimediaClient()
    client.query_category("Floor plans", limit=1)
    assert "user-agent" in captured_headers
    assert "gem2-vision" in captured_headers["user-agent"]


def test_query_category_handles_non_200(monkeypatch) -> None:
    monkeypatch.setattr(crawl, "_http_get", lambda url, timeout=30.0: (429, b"", {}))
    monkeypatch.setattr(crawl, "_sleep_polite", lambda: None)
    candidates = crawl.WikimediaClient().query_category("Floor plans", limit=1)
    assert candidates == []


def test_query_category_handles_bad_json(monkeypatch) -> None:
    monkeypatch.setattr(crawl, "_http_get", lambda url, timeout=30.0: (200, b"not json", {}))
    monkeypatch.setattr(crawl, "_sleep_polite", lambda: None)
    candidates = crawl.WikimediaClient().query_category("Floor plans", limit=1)
    assert candidates == []
