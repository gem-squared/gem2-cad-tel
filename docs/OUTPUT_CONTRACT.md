# CAD Trust Engine Lite — Output Contract

**Version:** 0.1.0 | **Status:** locked (gates U4-U9)

This document is the human-readable form of `src/cad_trust/schema.py`. If they disagree, the schema wins — but the schema must be brought back into agreement with this doc.

---

## The contract

```
EngineOutput = {
  drawing_id:   str,
  objects:      [Object],
  aggregates:   Aggregates,
  refusals:     [Refusal],
  scale_anchor: ScaleAnchor
}
```

### Object — three orthogonal epistemic claims

Every detected CAD object carries **three independent epistemic marks**:

| Mark                    | Question it answers                  |
|-------------------------|--------------------------------------|
| `type_epistemic`        | Is this really a wall / door / ... ? |
| `geometry_epistemic`    | Is this the right shape / extent ?   |
| `measurement_epistemic` | Is the mm measurement reliable ?     |

**Why orthogonal:** The engine may be *confident this is a wall* (⊨), *confident of its pixel shape* (⊢), and *yet refuse to claim it is 4,200 mm* (⊥). Conflating these collapses the trust surface.

### Epistemic tags (EEF)

| Tag | Name         | When to use                                                |
|-----|--------------|------------------------------------------------------------|
| ⊢   | GROUNDED     | Direct evidence (OCR hit, exact geometry match)            |
| ⊨   | INFERRED     | Derived from ⊢ with visible chain                          |
| ⊬   | EXTRAPOLATED | Beyond evidence — `basis` MUST name the leap               |
| ⊥   | UNKNOWN      | Knowledge gap — `gap` MUST name what's missing             |

`⊬` and `⊥` are **enforced** by the Pydantic validator: missing `basis` / `gap` is a `ValidationError`.

### Refusal — first-class output

```
Refusal = { region: bbox, why: str }
```

When evidence is insufficient to commit on a region, the engine emits a `Refusal` rather than a low-confidence detection. **Refusal is the structurally correct output** under the Refusal_Over_Bluff invariant; low coverage is acceptable, confident-wrong detections are not.

---

## Measurement Policy

> **Never emit `measurement_mm` unless `scale_anchor.detected = True`.**

This is enforced by `EngineOutput.model_validator`:

- When `scale_anchor.detected = False`:
  - ∀ object. `measurement_mm` must be `None` AND `measurement_epistemic.tag` must be `⊥`
  - `aggregates.measured_wall_length_mm.value` must be `None` AND its `epistemic.tag` must be `⊥`

This is non-negotiable. Pixel length may appear as a diagnostic signal inside `evidence`, but it is **never** output as mm.

**Why this matters for 적산:** a wrong millimeter conversion is worse than no conversion. The cost system can route a refusal to a human reviewer; it cannot detect a confidently-wrong number until the construction phase.

---

## Aggregate taint propagation

```
Aggregate = { value, epistemic, warning? }
```

When ⊬ / ⊥ objects contribute to a count or sum, the aggregate's `warning` field names the taint. A wall count derived from 4 ⊢ walls + 1 ⊬ wall carries `warning: "1 of 5 contributors is ⊬-tagged (basis: ...)"`.

The aggregate's own `epistemic.tag` reflects the weakest contributor: at least one ⊥ contributor → aggregate `⊥`; at least one ⊬ → aggregate ⊬ or `⊨` with warning, never ⊢.

(v0.3 will expand this into full taint propagation through cost calculations.)

---

## What is NOT in v0.1

| Postponed                       | Lands in |
|---------------------------------|----------|
| VLM semantic re-verification    | v0.2     |
| Synthetic Korean apt generator  | v0.2     |
| Automated dataset crawler       | v0.2     |
| DWG native ingest               | v0.3     |
| Full cost-aggregate taint math  | v0.3     |

---

*See also: `src/cad_trust/schema.py` (authoritative), `tests/fixtures/golden_output.json` (canonical example).*
