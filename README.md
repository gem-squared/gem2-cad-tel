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
| `docs/DEMO_SCENARIOS.md`           | 5 walkthrough scenarios (incl. KR refusal demo)  |
| `docs/POBICON_PITCH.ko.md`         | Korean application pitch                         |

## Status

v0.1.0 — released 2026-06-05. Built end-to-end in one autonomous session
(WP-ST-1, 9 unit-works, 53 tests, 9 commits).

See `docs/README.md` for the engineering thesis and v0.2 / v0.3 roadmap.
