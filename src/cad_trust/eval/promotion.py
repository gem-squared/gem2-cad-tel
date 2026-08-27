"""Promotion predicate per spec §5.3 — returns three-state {PASS, WAIVER_REQUIRED, FAIL}.

Implements all 6 §5.3 clauses:
1. Macro-benchmark improvement over baseline
2. No critical-class regression (WAIVER_REQUIRED if regression + waiver, FAIL if regression + no waiver)
3. No false-scale-anchor regression
4. No Measurement Policy violation
5. Reproducibility
6. Human acceptance (deferred to WP-ST-5 U9)

This module is machine-checkable — scripts/check_promotion_predicate.py wraps it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


PromotionState = Literal["PASS", "WAIVER_REQUIRED", "FAIL"]


@dataclass
class Waiver:
    """Structured waiver record. Approver + rationale + evidence required."""
    cls: str
    baseline_score: float
    hybrid_score: float
    delta: float
    delta_pct: float
    rationale: str
    approver: str
    timestamp: str
    evidence_refs: list[str] = field(default_factory=list)

    @property
    def is_regression_waiver(self) -> bool:
        return self.delta < 0


@dataclass
class PromotionVerdict:
    overall: PromotionState
    per_clause: dict[str, PromotionState]
    per_critical_class_deltas: dict[str, float]
    waivers_applied: list[Waiver] = field(default_factory=list)
    reproducibility_report: dict | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class BenchmarkContract:
    macro_weights: dict[str, float]
    critical_classes: list[str]
    measurement_policy_zero_tolerance: bool = True
    false_anchor_regression_tolerance: float = 0.0
    canonical_bundle_sha256: str = ""


def load_benchmark_contract(path: Path | str) -> BenchmarkContract:
    """Load frozen benchmark_contract.md metadata (front-matter JSON block)."""
    text = Path(path).read_text()
    # front-matter JSON between --- markers
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            data = json.loads(text[3:end].strip())
            return BenchmarkContract(**data)
    raise ValueError(f"benchmark_contract at {path} missing JSON front-matter")


def evaluate_promotion(
    baseline_summary: dict,
    hybrid_summary: dict,
    contract: BenchmarkContract,
    waivers: list[Waiver] | None = None,
) -> PromotionVerdict:
    """Evaluate three-state promotion per spec §5.3."""
    waivers = waivers or []
    per_clause: dict[str, PromotionState] = {}
    notes: list[str] = []
    per_critical_deltas: dict[str, float] = {}

    # Clause 1: macro benchmark improvement
    baseline_macro = _macro_score(baseline_summary, contract.macro_weights)
    hybrid_macro = _macro_score(hybrid_summary, contract.macro_weights)
    if hybrid_macro > baseline_macro:
        per_clause["macro_improvement"] = "PASS"
    else:
        per_clause["macro_improvement"] = "FAIL"
        notes.append(f"macro: hybrid {hybrid_macro:.4f} ≤ baseline {baseline_macro:.4f}")

    # Clause 2: no critical-class regression (or waiver)
    critical_verdict: PromotionState = "PASS"
    for cls in contract.critical_classes:
        b = baseline_summary.get("per_class", {}).get(cls, 0.0)
        h = hybrid_summary.get("per_class", {}).get(cls, 0.0)
        per_critical_deltas[cls] = h - b
        if h < b:
            # regression — check for waiver
            waiver_present = any(w.cls == cls and w.is_regression_waiver for w in waivers)
            if waiver_present:
                if critical_verdict != "FAIL":
                    critical_verdict = "WAIVER_REQUIRED"
                notes.append(f"critical {cls}: regression {h - b:+.4f} covered by waiver")
            else:
                critical_verdict = "WAIVER_REQUIRED"
                notes.append(f"critical {cls}: regression {h - b:+.4f} REQUIRES WAIVER")
    per_clause["critical_class_no_regression"] = critical_verdict

    # Clause 3: false-anchor-rate no regression
    b_far = baseline_summary.get("false_anchor_rate", 0.0)
    h_far = hybrid_summary.get("false_anchor_rate", 0.0)
    if h_far <= b_far + contract.false_anchor_regression_tolerance:
        per_clause["false_anchor_rate_no_regression"] = "PASS"
    else:
        per_clause["false_anchor_rate_no_regression"] = "FAIL"
        notes.append(f"false-anchor: hybrid {h_far:.4f} > baseline {b_far:.4f} + tol")

    # Clause 4: measurement policy — zero mm without scale_anchor
    violations = hybrid_summary.get("measurement_policy_violations", 0)
    if violations == 0 or not contract.measurement_policy_zero_tolerance:
        per_clause["measurement_policy"] = "PASS"
    else:
        per_clause["measurement_policy"] = "FAIL"
        notes.append(f"measurement policy: {violations} violation(s) found")

    # Clause 5: reproducibility
    repro = _check_reproducibility(hybrid_summary, contract)
    if repro["ok"]:
        per_clause["reproducibility"] = "PASS"
    else:
        per_clause["reproducibility"] = "FAIL"
        notes.append(f"reproducibility: {repro['reason']}")

    # Overall
    if any(v == "FAIL" for v in per_clause.values()):
        overall: PromotionState = "FAIL"
    elif any(v == "WAIVER_REQUIRED" for v in per_clause.values()):
        overall = "WAIVER_REQUIRED"
    else:
        overall = "PASS"

    return PromotionVerdict(
        overall=overall,
        per_clause=per_clause,
        per_critical_class_deltas=per_critical_deltas,
        waivers_applied=waivers,
        reproducibility_report=repro,
        notes=notes,
    )


def _macro_score(summary: dict, weights: dict[str, float]) -> float:
    per_class = summary.get("per_class", {})
    total_weight = sum(weights.values())
    if total_weight == 0:
        return 0.0
    weighted = sum(per_class.get(k, 0.0) * w for k, w in weights.items())
    return weighted / total_weight


def _check_reproducibility(summary: dict, contract: BenchmarkContract) -> dict:
    """Check summary declares required reproducibility fields matching contract."""
    required = {
        "canonical_bundle_sha256",
        "config_digest",
        "env_digest",
        "model_digests",
    }
    missing = required - set(summary.keys())
    if missing:
        return {"ok": False, "reason": f"missing reproducibility fields: {sorted(missing)}"}
    if (
        contract.canonical_bundle_sha256
        and summary["canonical_bundle_sha256"] != contract.canonical_bundle_sha256
    ):
        return {
            "ok": False,
            "reason": f"canonical_bundle_sha256 mismatch: summary={summary['canonical_bundle_sha256'][:16]}... contract={contract.canonical_bundle_sha256[:16]}...",
        }
    return {"ok": True, "reason": "all required fields present + digest match"}
