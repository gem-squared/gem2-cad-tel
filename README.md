# CAD Trust Engine Lite — gem2-vision

**v0.1.0** — MVP for 포비콘 application.

PNG/PDF Korean floor plan → per-field EEF-tagged JSON + Streamlit review UI.

## The wedge

Not "another OpenCV pipeline." A **trust engine** — every detection carries
per-field epistemic tags (type / geometry / measurement orthogonal),
evidence chains, and explicit refusal regions for uncommittable areas.

> A detector gives answers. A CAD Trust Engine gives
> **answers, evidence, uncertainty, refusal, and review path**.

## Quickstart

```bash
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
.venv/bin/python scripts/build_corpus.py    # regenerate 12 synthetic drawings
pytest                                       # 53 tests, full suite
streamlit run ui/app.py                      # localhost demo
```

## Documentation

| Doc                                | Purpose                                          |
|------------------------------------|--------------------------------------------------|
| `docs/README.md`                   | Engineering thesis (start here)                  |
| `docs/OUTPUT_CONTRACT.md`          | Formal contract spec + Measurement Policy        |
| `docs/CORPUS.md`                   | Corpus license posture + provenance schema       |
| `docs/AUDIT.md`                    | Audit subsystem (Refusal Over Bluff, remembered) |
| `docs/DEMO_SCENARIOS.md`           | 5 walkthrough scenarios (incl. KR refusal demo)  |
| `docs/POBICON_PITCH.ko.md`         | Korean application pitch                         |

## Audit subsystem (v0.1.1)

Every pipeline run can log to a SQLite audit DB — stage events, refusals,
Measurement_Policy fires, epistemic-tag distributions, errors. The audit trail
extends Refusal Over Bluff across time:

```bash
# Default audit DB at .gem-squared/audit.sqlite
streamlit run ui/app.py    # the Past Runs tab queries the DB

# CLI
python -m cad_trust.audit list-runs
python -m cad_trust.audit show-run <run_id>
python -m cad_trust.audit refusals --attempted-type door
python -m cad_trust.audit stats
```

See `docs/AUDIT.md` for schema, invariants, and example queries.

## Status

- **v0.1.0** — 2026-06-05: CAD Trust Engine Lite, 9 units, 53 tests
- **v0.1.1** — 2026-06-05: Audit subsystem, +6 units, +38 tests (91 total)

See `docs/README.md` for the engineering thesis and v0.2 / v0.3 roadmap.
