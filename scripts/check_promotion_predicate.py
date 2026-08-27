"""WP-ST-3 U6 — Machine-checkable promotion predicate CLI.

Usage:
  python scripts/check_promotion_predicate.py \\
    --baseline PATH \\
    --hybrid PATH \\
    --contract PATH \\
    [--waivers PATH_GLOB]

Exit codes:
  0 = PASS
  2 = WAIVER_REQUIRED
  3 = FAIL
  4 = reproducibility broken (subset of FAIL, distinct exit code for CI clarity)
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cad_trust.eval.promotion import (  # noqa: E402
    Waiver,
    evaluate_promotion,
    load_benchmark_contract,
)


def _load_waivers(patterns: list[str]) -> list[Waiver]:
    waivers = []
    for pattern in patterns:
        for path in glob.glob(pattern):
            data = json.loads(Path(path).read_text())
            waivers.append(Waiver(**data))
    return waivers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, help="Path to baseline_result.json")
    parser.add_argument("--hybrid", required=True, help="Path to hybrid_result.json")
    parser.add_argument("--contract", required=True, help="Path to benchmark_contract.md")
    parser.add_argument("--waivers", nargs="*", default=[], help="Glob(s) for waiver JSON files")
    args = parser.parse_args()

    baseline = json.loads(Path(args.baseline).read_text())
    hybrid = json.loads(Path(args.hybrid).read_text())
    contract = load_benchmark_contract(args.contract)
    waivers = _load_waivers(args.waivers)

    verdict = evaluate_promotion(baseline, hybrid, contract, waivers)

    print(f"Overall: {verdict.overall}")
    print("Per-clause:")
    for k, v in verdict.per_clause.items():
        print(f"  {k}: {v}")
    print("Per-critical-class deltas:")
    for k, v in verdict.per_critical_class_deltas.items():
        print(f"  {k}: {v:+.4f}")
    if verdict.waivers_applied:
        print(f"Waivers applied: {len(verdict.waivers_applied)}")
    if verdict.notes:
        print("Notes:")
        for n in verdict.notes:
            print(f"  - {n}")

    if verdict.overall == "PASS":
        return 0
    if verdict.overall == "WAIVER_REQUIRED":
        return 2
    # FAIL — distinguish reproducibility-broken for CI
    if verdict.per_clause.get("reproducibility") == "FAIL":
        return 4
    return 3


if __name__ == "__main__":
    sys.exit(main())
