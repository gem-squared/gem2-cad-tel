"""WP-ST-3: crawl real public-source CAD/floor plan drawings from Wikimedia Commons.

Stdlib-only. License discipline non-negotiable: any candidate whose license
cannot be mapped to our LicenseCategory whitelist is REFUSED (surfaced in
the crawl summary, not silently included).

Usage:
    python scripts/crawl_corpus.py [--target N] [--dry-run] [--categories Cat1 Cat2 ...]
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure project src/ is on sys.path so we can import cad_trust.provenance
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from cad_trust.provenance import ProvenanceRecord  # noqa: E402

WIKIMEDIA_BASE = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "gem2-vision/0.1.2 (educational; david@gineers.ai)"
REQUEST_SLEEP_SEC = 0.5

DEFAULT_CATEGORIES = ("Floor plans", "Architectural drawings", "House plans")
SAMPLES_DIR_DEFAULT = ROOT / "data" / "samples"
PROVENANCE_DIR_DEFAULT = ROOT / "data" / "provenance"
SUMMARY_PATH_DEFAULT = ROOT / ".gem-squared" / "crawl_summary.json"


# ── data model ──────────────────────────────────────────────────────────────


@dataclasses.dataclass
class Candidate:
    filename: str          # Wikimedia file title, e.g. "File:House_plan_X.png"
    url: str | None        # direct image URL
    license_raw: str | None
    license_mapped: str | None
    attribution: str | None
    source_page_url: str | None


@dataclasses.dataclass
class CrawlSummary:
    started_at: str
    completed_at: str | None = None
    downloaded: int = 0
    refused_by_license: int = 0
    refused_by_404: int = 0
    refused_by_too_small: int = 0
    by_source: dict[str, int] = dataclasses.field(default_factory=dict)
    refused_details: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    downloaded_files: list[str] = dataclasses.field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ── license mapping ─────────────────────────────────────────────────────────


def _license_mapping_table() -> tuple[tuple[str, str], ...]:
    """Order matters — first match wins; longer prefixes first to avoid
    'cc-by-nc' getting matched by 'cc-by-'."""
    return (
        ("cc-zero", "public"),
        ("publicdomain", "public"),
        ("pd-", "public"),
        ("cc-by-nc-sa", "CC-BY-NC"),
        ("cc-by-nc-", "CC-BY-NC"),
        ("cc-by-nc", "CC-BY-NC"),
        ("cc-by-sa-", "CC-BY-SA"),
        ("cc-by-sa", "CC-BY-SA"),
        ("cc-by-", "CC-BY"),
        ("cc-by", "CC-BY"),
    )


def map_license(license_raw: str | None) -> str | None:
    """Map a raw Wikimedia license code (lowercased) to LicenseCategory.

    Returns None when the code can't be confidently mapped — caller MUST refuse.
    NEVER guesses "public" or "CC-BY" — that would violate No_Source_Bluff.
    """
    if not license_raw:
        return None
    key = str(license_raw).strip().lower()
    for prefix, mapped in _license_mapping_table():
        if key.startswith(prefix):
            return mapped
    return None


# ── HTTP ────────────────────────────────────────────────────────────────────


def _http_get(url: str, timeout: float = 30.0) -> tuple[int, bytes, dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            body = resp.read()
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return status, body, headers
    except urllib.error.HTTPError as exc:
        return exc.code, b"", {}
    except urllib.error.URLError as exc:
        # Network unreachable / DNS failure — surface as 0 so caller can refuse_by_404
        print(f"  ! URLError on {url}: {exc}", file=sys.stderr)
        return 0, b"", {}


def _sleep_polite() -> None:
    time.sleep(REQUEST_SLEEP_SEC)


# ── Wikimedia Commons client ────────────────────────────────────────────────


class WikimediaClient:
    """Minimal stdlib Commons API client.

    Honors `Polite_Crawling` invariant: identifying user-agent, rate-limit,
    no parallelism.
    """

    def __init__(self, base_url: str = WIKIMEDIA_BASE) -> None:
        self.base_url = base_url

    def query_category(self, category: str, limit: int = 20) -> list[Candidate]:
        """Return up to `limit` Candidate(s) for files in `Category:{category}`.

        Uses generator=categorymembers + prop=imageinfo&iiprop=url|extmetadata
        so license info comes back in a single round-trip.
        """
        params = {
            "action": "query",
            "format": "json",
            "generator": "categorymembers",
            "gcmtitle": f"Category:{category}",
            "gcmtype": "file",
            "gcmlimit": str(limit),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime|size",
            "iiextmetadatafilter": "License|LicenseShortName|Artist|LicenseUrl",
        }
        url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
        _sleep_polite()
        status, body, _ = _http_get(url)
        if status != 200 or not body:
            return []
        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return []
        pages = (data.get("query") or {}).get("pages") or {}
        out: list[Candidate] = []
        for _pid, page in pages.items():
            iinfo = page.get("imageinfo") or []
            if not iinfo:
                continue
            first = iinfo[0]
            extmeta = first.get("extmetadata") or {}
            license_raw = (
                (extmeta.get("License") or {}).get("value")
                or (extmeta.get("LicenseShortName") or {}).get("value")
            )
            artist_html = (extmeta.get("Artist") or {}).get("value") or ""
            attribution = re.sub(r"<[^>]+>", "", artist_html).strip() or None
            mapped = map_license(license_raw)
            out.append(Candidate(
                filename=page.get("title") or first.get("descriptionshorturl") or "unknown",
                url=first.get("url"),
                license_raw=license_raw,
                license_mapped=mapped,
                attribution=attribution,
                source_page_url=first.get("descriptionshorturl"),
            ))
        return out


# ── safe filename + extension ───────────────────────────────────────────────


_SAFE_STEM_RE = re.compile(r"[^a-z0-9_\-]+")


def safe_stem(title: str) -> str:
    """Convert 'File:House Plan (1893) - Foo.png' → 'house_plan_1893_foo'."""
    s = title
    if s.lower().startswith("file:"):
        s = s[5:]
    s = Path(s).stem  # drop extension
    s = s.lower().replace(" ", "_")
    s = _SAFE_STEM_RE.sub("_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:80] or "untitled"


def infer_extension(url: str, headers: dict[str, str]) -> str:
    """Prefer Content-Type, fall back to URL suffix. Default: .png."""
    ct = (headers.get("content-type") or "").lower()
    if "png" in ct:
        return ".png"
    if "jpeg" in ct or "jpg" in ct:
        return ".jpg"
    if "pdf" in ct:
        return ".pdf"
    if "svg" in ct:
        return ".svg"
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".pdf"}:
        return suffix if suffix != ".jpeg" else ".jpg"
    return ".png"


# ── download + provenance ───────────────────────────────────────────────────

MIN_BYTES = 8 * 1024  # ≥8KB to skip thumbnail-only / 1×1 dummies


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def download_and_record(
    candidates: list[Candidate],
    samples_dir: Path = SAMPLES_DIR_DEFAULT,
    provenance_dir: Path = PROVENANCE_DIR_DEFAULT,
    audit_log_path: Path = SUMMARY_PATH_DEFAULT,
    source_label: str = "wikimedia_commons",
) -> CrawlSummary:
    """Walk candidates: refuse anything without a mapped license; otherwise
    download bytes, compute sha256, write {sample, provenance}.

    Updates `audit_log_path` with the run summary (incremental — re-runs append).
    """
    samples_dir.mkdir(parents=True, exist_ok=True)
    provenance_dir.mkdir(parents=True, exist_ok=True)
    audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    summary = CrawlSummary(started_at=_now_iso(), completed_at=None)

    existing_hashes: set[str] = set()
    for p in provenance_dir.glob("*.json"):
        try:
            existing_hashes.add(json.loads(p.read_text()).get("sha256", ""))
        except (json.JSONDecodeError, OSError):
            pass

    for cand in candidates:
        if not cand.license_mapped:
            summary.refused_by_license += 1
            summary.refused_details.append({
                "filename": cand.filename,
                "reason": f"license could not be mapped (raw: {cand.license_raw!r})",
                "stage": "license_check",
            })
            print(f"  ! refused (license): {cand.filename}  raw={cand.license_raw!r}", file=sys.stderr)
            continue
        if not cand.url:
            summary.refused_by_404 += 1
            summary.refused_details.append({
                "filename": cand.filename,
                "reason": "candidate has no URL",
                "stage": "url_check",
            })
            continue
        _sleep_polite()
        status, body, headers = _http_get(cand.url)
        if status != 200 or not body:
            summary.refused_by_404 += 1
            summary.refused_details.append({
                "filename": cand.filename,
                "reason": f"HTTP {status}",
                "stage": "download",
            })
            print(f"  ! refused (HTTP {status}): {cand.filename}", file=sys.stderr)
            continue
        if len(body) < MIN_BYTES:
            summary.refused_by_too_small += 1
            summary.refused_details.append({
                "filename": cand.filename,
                "reason": f"image too small ({len(body)} bytes < {MIN_BYTES})",
                "stage": "size_check",
            })
            continue
        sha = hashlib.sha256(body).hexdigest()
        if sha in existing_hashes:
            # Dedup against prior runs (synthetic too — though unlikely to collide)
            summary.refused_details.append({
                "filename": cand.filename,
                "reason": "duplicate sha256 (already in corpus)",
                "stage": "dedup",
            })
            continue

        stem = safe_stem(cand.filename)
        # Avoid stem collision with synthetic (which use 'synth_' prefix)
        if not stem.startswith("wm_"):
            stem = f"wm_{stem}"
        ext = infer_extension(cand.url, headers)
        # Disambiguate if stem already taken by a non-matching file
        out_image = samples_dir / f"{stem}{ext}"
        n = 2
        while out_image.exists():
            out_image = samples_dir / f"{stem}_{n}{ext}"
            n += 1
        out_prov = provenance_dir / f"{out_image.stem}.json"

        out_image.write_bytes(body)
        record = ProvenanceRecord(
            drawing_id=out_image.stem,
            source=source_label,
            license=cand.license_mapped,  # type: ignore[arg-type]  # validated by Literal
            sha256=sha,
            fetched_at=datetime.now(timezone.utc),
            original_uri=cand.source_page_url or cand.url,
            usage="demo-only",
            domain="global",
        )
        out_prov.write_text(record.model_dump_json(indent=2))
        existing_hashes.add(sha)
        summary.downloaded += 1
        try:
            rel_path = str(out_image.relative_to(ROOT))
        except ValueError:
            # Test or external dir — fall back to absolute path
            rel_path = str(out_image)
        summary.downloaded_files.append(rel_path)
        summary.by_source[source_label] = summary.by_source.get(source_label, 0) + 1
        print(f"  + {out_image.name}  license={cand.license_mapped}  sha={sha[:10]}…")

    summary.completed_at = _now_iso()
    audit_log_path.write_text(json.dumps(summary.as_dict(), indent=2))
    return summary


# ── orchestrator + CLI ──────────────────────────────────────────────────────


def crawl_corpus(
    target_count: int = 20,
    categories: tuple[str, ...] = DEFAULT_CATEGORIES,
    samples_dir: Path = SAMPLES_DIR_DEFAULT,
    provenance_dir: Path = PROVENANCE_DIR_DEFAULT,
    audit_log_path: Path = SUMMARY_PATH_DEFAULT,
    dry_run: bool = False,
) -> CrawlSummary:
    client = WikimediaClient()
    pool: list[Candidate] = []
    per_category = max(target_count, 10)
    for cat in categories:
        print(f"[query] Category:{cat}  (up to {per_category})", file=sys.stderr)
        try:
            pool.extend(client.query_category(cat, limit=per_category))
        except Exception as exc:
            print(f"  ! query failed for {cat!r}: {exc}", file=sys.stderr)
    print(f"[pool] {len(pool)} candidates total", file=sys.stderr)
    if dry_run:
        # Just produce a summary of license distribution without downloading
        summary = CrawlSummary(started_at=_now_iso())
        for c in pool:
            if c.license_mapped:
                summary.by_source[c.license_mapped] = summary.by_source.get(c.license_mapped, 0) + 1
            else:
                summary.refused_by_license += 1
        summary.completed_at = _now_iso()
        audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        audit_log_path.write_text(json.dumps(summary.as_dict(), indent=2))
        return summary
    # Cap candidates to (roughly) target_count × 3 to leave room for refusals
    pool = pool[: target_count * 3]
    summary = download_and_record(
        pool,
        samples_dir=samples_dir,
        provenance_dir=provenance_dir,
        audit_log_path=audit_log_path,
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crawl_corpus", description=__doc__)
    parser.add_argument("--target", type=int, default=20, help="approximate number of drawings to acquire")
    parser.add_argument("--categories", nargs="+", default=list(DEFAULT_CATEGORIES))
    parser.add_argument("--dry-run", action="store_true", help="query only; do not download")
    parser.add_argument("--samples-dir", type=Path, default=SAMPLES_DIR_DEFAULT)
    parser.add_argument("--provenance-dir", type=Path, default=PROVENANCE_DIR_DEFAULT)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH_DEFAULT)
    args = parser.parse_args(argv)
    summary = crawl_corpus(
        target_count=args.target,
        categories=tuple(args.categories),
        samples_dir=args.samples_dir,
        provenance_dir=args.provenance_dir,
        audit_log_path=args.summary,
        dry_run=args.dry_run,
    )
    print(json.dumps(summary.as_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
