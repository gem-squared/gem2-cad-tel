"""WP-ST-3 U3 — Verify no family_id crosses object-recognition splits.

Exit codes:
- 0: splits are isolated (no cross-split leakage)
- 1: at least one family_id appears in >1 split

CI-checkable predicate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OBJ_DIR = REPO / "data/splits/object_recognition"


def main() -> int:
    splits = {}
    for name in ("train", "val", "test"):
        path = OBJ_DIR / f"{name}.json"
        if not path.exists():
            print(f"MISSING: {path}", file=sys.stderr)
            return 1
        data = json.loads(path.read_text())
        splits[name] = {e["family_id"] for e in data["entries"]}

    violations = []
    for a in ("train", "val", "test"):
        for b in ("train", "val", "test"):
            if a >= b:
                continue
            overlap = splits[a] & splits[b]
            if overlap:
                violations.append((a, b, sorted(overlap)))

    if violations:
        print("SPLIT_ISOLATION_VIOLATION:")
        for a, b, fams in violations:
            print(f"  {a} ∩ {b}: {fams}")
        return 1

    print("SPLITS_ISOLATED ✓")
    print(f"  train: {len(splits['train'])} families")
    print(f"  val:   {len(splits['val'])} families")
    print(f"  test:  {len(splits['test'])} families")
    return 0


if __name__ == "__main__":
    sys.exit(main())
