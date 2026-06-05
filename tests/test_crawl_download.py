"""U2 acceptance tests — download_and_record (refuse / 404 / valid / dedup paths).

Network-free: monkeypatches _http_get + uses tmp directories.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "crawl_corpus.py"

_spec = importlib.util.spec_from_file_location("_crawl_download_test_module", SCRIPT)
crawl = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
sys.modules["_crawl_download_test_module"] = crawl
assert _spec and _spec.loader
_spec.loader.exec_module(crawl)  # type: ignore[union-attr]


def _fake_png_bytes() -> bytes:
    """A ~9KB PNG-like blob (>MIN_BYTES) — just bytes; doesn't need to decode."""
    return b"\x89PNG\r\n\x1a\n" + b"x" * 10_000


def _candidate(filename: str, license_mapped: str | None, url: str | None = "https://x/y.png") -> object:
    return crawl.Candidate(
        filename=filename,
        url=url,
        license_raw="cc-by-sa" if license_mapped == "CC-BY-SA" else None,
        license_mapped=license_mapped,
        attribution="Tester",
        source_page_url="https://commons.wikimedia.org/wiki/" + filename,
    )


@pytest.fixture
def dirs(tmp_path: Path):
    return {
        "samples": tmp_path / "samples",
        "provenance": tmp_path / "provenance",
        "audit": tmp_path / "summary.json",
    }


# ── REFUSE: license not mapped ──────────────────────────────────────────────


def test_refuses_when_license_not_mapped(dirs, monkeypatch) -> None:
    # _http_get should NOT be called for license-refused candidates
    called = {"n": 0}
    def fake_get(url, timeout=30.0):
        called["n"] += 1
        return 200, _fake_png_bytes(), {"content-type": "image/png"}
    monkeypatch.setattr(crawl, "_http_get", fake_get)
    monkeypatch.setattr(crawl, "_sleep_polite", lambda: None)
    candidates = [_candidate("File:Bad.png", license_mapped=None)]
    summary = crawl.download_and_record(
        candidates,
        samples_dir=dirs["samples"],
        provenance_dir=dirs["provenance"],
        audit_log_path=dirs["audit"],
    )
    assert summary.refused_by_license == 1
    assert summary.downloaded == 0
    assert called["n"] == 0  # never hit network for refused candidate
    assert not dirs["samples"].exists() or not any(dirs["samples"].iterdir())
    assert dirs["audit"].exists()
    assert summary.refused_details[0]["stage"] == "license_check"


# ── REFUSE: HTTP 404 ────────────────────────────────────────────────────────


def test_refuses_on_http_404(dirs, monkeypatch) -> None:
    monkeypatch.setattr(crawl, "_http_get", lambda url, timeout=30.0: (404, b"", {}))
    monkeypatch.setattr(crawl, "_sleep_polite", lambda: None)
    candidates = [_candidate("File:Gone.png", license_mapped="CC-BY-SA")]
    summary = crawl.download_and_record(
        candidates,
        samples_dir=dirs["samples"],
        provenance_dir=dirs["provenance"],
        audit_log_path=dirs["audit"],
    )
    assert summary.refused_by_404 == 1
    assert summary.downloaded == 0


# ── REFUSE: image too small ─────────────────────────────────────────────────


def test_refuses_when_too_small(dirs, monkeypatch) -> None:
    monkeypatch.setattr(crawl, "_http_get",
                        lambda url, timeout=30.0: (200, b"tiny", {"content-type": "image/png"}))
    monkeypatch.setattr(crawl, "_sleep_polite", lambda: None)
    candidates = [_candidate("File:Thumb.png", license_mapped="CC-BY")]
    summary = crawl.download_and_record(
        candidates,
        samples_dir=dirs["samples"],
        provenance_dir=dirs["provenance"],
        audit_log_path=dirs["audit"],
    )
    assert summary.refused_by_too_small == 1
    assert summary.downloaded == 0


# ── DOWNLOAD: valid candidate writes file + provenance JSON ─────────────────


def test_downloads_valid_candidate(dirs, monkeypatch) -> None:
    body = _fake_png_bytes()
    monkeypatch.setattr(crawl, "_http_get",
                        lambda url, timeout=30.0: (200, body, {"content-type": "image/png"}))
    monkeypatch.setattr(crawl, "_sleep_polite", lambda: None)
    candidates = [_candidate("File:Good plan.png", license_mapped="CC-BY-SA")]
    summary = crawl.download_and_record(
        candidates,
        samples_dir=dirs["samples"],
        provenance_dir=dirs["provenance"],
        audit_log_path=dirs["audit"],
    )
    assert summary.downloaded == 1
    assert summary.by_source["wikimedia_commons"] == 1
    # File present
    written = list(dirs["samples"].glob("*.png"))
    assert len(written) == 1
    assert written[0].name.startswith("wm_")
    # Provenance JSON validates against ProvenanceRecord
    prov_files = list(dirs["provenance"].glob("*.json"))
    assert len(prov_files) == 1
    from cad_trust.provenance import ProvenanceRecord
    prov = json.loads(prov_files[0].read_text())
    rec = ProvenanceRecord.model_validate(prov)
    assert rec.license == "CC-BY-SA"
    assert rec.sha256 == hashlib.sha256(body).hexdigest()
    assert rec.source == "wikimedia_commons"
    assert rec.usage == "demo-only"
    assert rec.domain == "global"
    # Summary file written
    summary_disk = json.loads(dirs["audit"].read_text())
    assert summary_disk["downloaded"] == 1


# ── DEDUP: re-running same candidate is idempotent ──────────────────────────


def test_dedup_idempotent_by_sha256(dirs, monkeypatch) -> None:
    body = _fake_png_bytes()
    monkeypatch.setattr(crawl, "_http_get",
                        lambda url, timeout=30.0: (200, body, {"content-type": "image/png"}))
    monkeypatch.setattr(crawl, "_sleep_polite", lambda: None)
    candidates = [_candidate("File:Same.png", license_mapped="CC-BY")]
    crawl.download_and_record(
        candidates,
        samples_dir=dirs["samples"],
        provenance_dir=dirs["provenance"],
        audit_log_path=dirs["audit"],
    )
    # Second invocation must NOT add a duplicate (different filename but same bytes)
    candidates2 = [_candidate("File:Same2.png", license_mapped="CC-BY")]
    summary2 = crawl.download_and_record(
        candidates2,
        samples_dir=dirs["samples"],
        provenance_dir=dirs["provenance"],
        audit_log_path=dirs["audit"],
    )
    assert summary2.downloaded == 0
    # Refusal details mention dedup
    assert any(d["stage"] == "dedup" for d in summary2.refused_details)
    # Still only 1 file on disk
    assert len(list(dirs["samples"].glob("*.png"))) == 1


def test_summary_json_has_required_keys(dirs, monkeypatch) -> None:
    monkeypatch.setattr(crawl, "_http_get",
                        lambda url, timeout=30.0: (200, _fake_png_bytes(), {"content-type": "image/png"}))
    monkeypatch.setattr(crawl, "_sleep_polite", lambda: None)
    crawl.download_and_record(
        [_candidate("File:Ok.png", license_mapped="CC-BY")],
        samples_dir=dirs["samples"],
        provenance_dir=dirs["provenance"],
        audit_log_path=dirs["audit"],
    )
    data = json.loads(dirs["audit"].read_text())
    for key in (
        "started_at", "completed_at", "downloaded",
        "refused_by_license", "refused_by_404", "refused_by_too_small",
        "by_source", "refused_details", "downloaded_files",
    ):
        assert key in data, f"summary missing key: {key}"
