"""WP-ST-3 U3 — Build source-family splits + guard verdict splits.

Deterministic split derivation from data/reconciliation/eligibility_classification.json.
Enforces:
- No family_id crosses splits (object-recognition manifest).
- Test split reserved BEFORE any model tuning (frozen via SHA-256).
- Two separate manifests: object-recognition (SUPPORTED only) + guard (positive/negative/ambiguous by verdict).

Family derivation rule:
- synthetic: family_id = prefix-before-last-suffix (e.g., synth_apt_kr_balcony_01 → synth_apt_kr_balcony)
- wikimedia: family_id = drawing_id (each wm_ drawing is its own family — independent sources)

Deterministic split algorithm (object-recognition):
- Sort families alphabetically.
- Assign SHA-256(family_id)[0:2] hex → int in [0, 255].
- test if int in [0, 38] (~15%), val if [39, 76] (~15%), train otherwise (~70%).
- This is deterministic + resistant to family additions (existing families keep placement).

Run:  python scripts/build_splits.py
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RECON = REPO / "data/reconciliation/eligibility_classification.json"
OBJ_DIR = REPO / "data/splits/object_recognition"
GUARD_DIR = REPO / "data/splits/guard"
FREEZE_HASHES = REPO / "data/splits/FREEZE_HASHES.txt"
SPLITS_README = REPO / "data/splits/README.md"


_SYNTH_SUFFIX_RE = re.compile(r"^(?P<family>.+?)_(?P<num>\d+)$")


def derive_family_id(drawing_id: str, source: str | None) -> str:
    if source == "synthetic_self_generated":
        m = _SYNTH_SUFFIX_RE.match(drawing_id)
        if m:
            return f"synthetic::{m.group('family')}"
        return f"synthetic::{drawing_id}"
    if source == "wikimedia_commons":
        return f"wikimedia_commons::{drawing_id}"
    return f"{source or 'unknown'}::{drawing_id}"


def _family_sort_key(family_id: str) -> str:
    """Deterministic sort key: SHA-256 hex prefix. Same input → same key across runs."""
    return hashlib.sha256(family_id.encode("utf-8")).hexdigest()


def assign_families_to_splits(records: list[dict]) -> dict[str, str]:
    """Proportional per-source allocation with deterministic tie-break.

    Guarantees each source family-pool contributes to test + val where possible,
    so val/test aren't starved on a small corpus. Rule:
      - Group families by source-prefix.
      - Sort each group by sha256(family_id) ascending.
      - Reserve 1st family per group for test, 2nd for val, remainder for train.
      - If a group has ≤2 families, allocate all-to-train and log a note.

    Returns family_id → split mapping.
    """
    supported = [r for r in records if r["category"] == "SUPPORTED_FLOOR_PLAN"]
    families: dict[str, list[dict]] = {}
    family_source: dict[str, str] = {}
    for r in supported:
        fid = derive_family_id(r["drawing_id"], r.get("source"))
        families.setdefault(fid, []).append(r)
        family_source[fid] = (r.get("source") or "unknown")

    by_source: dict[str, list[str]] = {}
    for fid, source in family_source.items():
        by_source.setdefault(source, []).append(fid)

    mapping: dict[str, str] = {}
    for source, fids in by_source.items():
        fids_sorted = sorted(fids, key=_family_sort_key)
        # First → test, second → val, rest → train (per-source)
        if len(fids_sorted) >= 3:
            mapping[fids_sorted[0]] = "test"
            mapping[fids_sorted[1]] = "val"
            for f in fids_sorted[2:]:
                mapping[f] = "train"
        elif len(fids_sorted) == 2:
            mapping[fids_sorted[0]] = "test"
            mapping[fids_sorted[1]] = "train"
        else:  # 1 family — all-to-train
            mapping[fids_sorted[0]] = "train"
    return mapping


def build_object_recognition_splits(records: list[dict]) -> dict[str, list[dict]]:
    family_split = assign_families_to_splits(records)
    supported = [r for r in records if r["category"] == "SUPPORTED_FLOOR_PLAN"]
    splits: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    for r in supported:
        family_id = derive_family_id(r["drawing_id"], r.get("source"))
        split = family_split[family_id]
        splits[split].append(
            {
                "drawing_id": r["drawing_id"],
                "family_id": family_id,
                "split": split,
                "source": r.get("source"),
                "license": r.get("license"),
                "domain": r.get("domain"),
                "eef_tag_at_split_time": r.get("eef_tag"),
                "classification_review_status": "AI_PROVISIONAL",
            }
        )
    return splits


def build_guard_splits(records: list[dict]) -> dict[str, list[dict]]:
    verdict_map = {
        "SUPPORTED_FLOOR_PLAN": "positive",
        "GUARD_NEGATIVE": "negative",
        "GUARD_AMBIGUOUS": "ambiguous",
    }
    splits: dict[str, list[dict]] = {"positive": [], "negative": [], "ambiguous": []}
    for r in records:
        v = verdict_map.get(r["category"])
        if v is None:
            continue
        family_id = derive_family_id(r["drawing_id"], r.get("source"))
        splits[v].append(
            {
                "drawing_id": r["drawing_id"],
                "family_id": family_id,
                "guard_verdict": v,
                "source": r.get("source"),
                "license": r.get("license"),
                "domain": r.get("domain"),
                "classification_review_status": "AI_PROVISIONAL",
            }
        )
    return splits


def sha256_of_json(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    with open(RECON) as fh:
        data = json.load(fh)
    records = data["records"]

    obj_splits = build_object_recognition_splits(records)
    guard_splits = build_guard_splits(records)

    OBJ_DIR.mkdir(parents=True, exist_ok=True)
    GUARD_DIR.mkdir(parents=True, exist_ok=True)

    for name in ("train", "val", "test"):
        payload = {
            "purpose": "object_recognition",
            "split": name,
            "generated_at": "2026-08-25T13:20:00+0900",
            "generated_by": "scripts/build_splits.py from data/reconciliation/eligibility_classification.json",
            "source_review_status": "AI_PROVISIONAL — awaiting Human eligibility review per WP-ST-3 U4 policy",
            "family_derivation_rule": "synthetic → prefix-before-numeric-suffix; wikimedia_commons → per-drawing-id (each is own family)",
            "split_algorithm": "per-source proportional: sort families by sha256(family_id) asc; 1st→test, 2nd→val, rest→train per source (guarantees non-empty val/test on small corpus)",
            "entries": sorted(obj_splits[name], key=lambda x: x["drawing_id"]),
            "count": len(obj_splits[name]),
        }
        (OBJ_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    for name in ("positive", "negative", "ambiguous"):
        payload = {
            "purpose": "floorplan_guard",
            "verdict": name,
            "generated_at": "2026-08-25T13:20:00+0900",
            "generated_by": "scripts/build_splits.py from data/reconciliation/eligibility_classification.json",
            "source_review_status": "AI_PROVISIONAL — awaiting Human eligibility review per WP-ST-3 U4 policy",
            "note": "WP-ST-4 U2 further partitions this set into train/val/test for the guard classifier bake-off",
            "entries": sorted(guard_splits[name], key=lambda x: x["drawing_id"]),
            "count": len(guard_splits[name]),
        }
        (GUARD_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    # Freeze hashes
    freeze_content_lines = [
        "# WP-ST-3 U3 — SPLIT FREEZE HASHES (SHA-256)",
        f"# Generated: 2026-08-25T13:20:00+0900",
        "# These digests anchor the frozen test split(s). Any change → new digest → new freeze.",
        "",
    ]
    for path in [
        OBJ_DIR / "test.json",
        OBJ_DIR / "val.json",
        OBJ_DIR / "train.json",
        GUARD_DIR / "positive.json",
        GUARD_DIR / "negative.json",
        GUARD_DIR / "ambiguous.json",
    ]:
        freeze_content_lines.append(f"{sha256_of_json(path)}  {path.relative_to(REPO)}")
    FREEZE_HASHES.write_text("\n".join(freeze_content_lines) + "\n")

    # Family isolation check
    obj_families_per_split = {name: {e["family_id"] for e in obj_splits[name]} for name in ("train", "val", "test")}
    crossings = []
    for a in ("train", "val", "test"):
        for b in ("train", "val", "test"):
            if a >= b:
                continue
            overlap = obj_families_per_split[a] & obj_families_per_split[b]
            if overlap:
                crossings.append((a, b, sorted(overlap)))
    if crossings:
        print("FAMILY_ISOLATION_VIOLATION:", crossings)
        raise SystemExit(1)

    # Summary
    print("== Object-recognition splits ==")
    for name in ("train", "val", "test"):
        print(f"  {name}: {len(obj_splits[name])} drawings, {len(obj_families_per_split[name])} families")
    print("== Guard splits (by verdict) ==")
    for name in ("positive", "negative", "ambiguous"):
        print(f"  {name}: {len(guard_splits[name])} drawings")
    print(f"\nFreeze hashes written: {FREEZE_HASHES.relative_to(REPO)}")


if __name__ == "__main__":
    main()
