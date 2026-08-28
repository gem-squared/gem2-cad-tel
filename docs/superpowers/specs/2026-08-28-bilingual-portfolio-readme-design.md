# Bilingual Portfolio README Design

**Date:** 2026-08-28  
**Target:** `README.md` (Korean) and `README.en.md` (English)  
**Audience:** Freelance clients and technical reviewers  
**Status:** Human-approved direction; implementation pending README review gate

## 1. Objective

Rewrite the Korean and English README files as synchronized portfolio documents. The opening must let a prospective client understand the business problem, the contributor's role, the delivered system, and the evidence boundary quickly. The remainder must give a technical reviewer enough architecture, contract, setup, and limitation detail to assess the work.

The README must describe the repository as it exists now. It must distinguish the stable v0.1.6 runtime from the partially implemented v0.2 benchmark and annotation foundation, and it must not imply validated object-recognition quality before Human-reviewed ground truth and a frozen benchmark exist.

## 2. Selected approach

Maintain two mirrored files with the same section order and equivalent claims:

- `README.md`: primary Korean portfolio document;
- `README.en.md`: English translation with equivalent technical meaning.

This preserves the current language-switch pattern while avoiding a single oversized bilingual file. The two files may use natural language appropriate to each audience, but all numbers, statuses, commands, limitations, and links must match.

## 3. Information architecture

Both files use this order:

1. Project identity, current stable version, and demo URL.
2. Portfolio summary: client problem, solution, role, and delivered outcome.
3. Current capability boundary: available now versus in progress.
4. Core trust design: EEF, refusal, Measurement Policy, and audit trail.
5. Runtime architecture and data flow.
6. Technology stack with concise selection rationale.
7. Corpus, annotation, and benchmark foundation.
8. Verification evidence and explicit limitations.
9. Local and Docker quick start.
10. Release/status summary, documentation map, and bounded roadmap.

The top portion is client-readable. Deeper implementation detail remains available below it rather than dominating the opening.

## 4. Authoritative facts and claim boundaries

### 4.1 Stable runtime

- The packaged stable version remains `0.1.6`.
- The current executable recognition path is the five-stage classical pipeline: ingest, geometry, OCR, symbols, and compose/aggregate.
- Supported ingest formats are PNG, JPG/JPEG, and rasterized PDF page 0.
- The public result boundary is the Pydantic `EngineOutput` schema.
- Every object separates type, geometry, and measurement epistemic marks.
- Without `scale_anchor.detected=True`, `measurement_mm` remains absent and measurement epistemic state remains unknown.
- Refusals are first-class output and SQLite audit records preserve run/stage/refusal/policy evidence.
- The Streamlit UI and audit CLI are implemented.

### 4.2 v0.2 foundation implemented in the repository

- The repository contains reconciliation, eligibility, split, annotation-schema, metric, and promotion-predicate foundations.
- There are 42 sample files and 50 provenance records; eight provenance-only orphans are preserved and excluded non-destructively.
- Current AI-provisional eligibility assigns 20 supported floor plans, eight guard negatives, and 14 guard-ambiguous samples. These classifications are not frozen Human truth.
- Object-recognition manifests reserve train/validation/test groups, and FloorPlanGuard has separate positive/negative/ambiguous manifests.
- Annotation files currently contain empty skeletons, not object ground truth.
- Validation/test Human review, annotation QA, dataset freeze, evaluation harness, and frozen v0.1 baseline remain blocked or pending.
- Hybrid experts, `FloorPlanGuard`, `FusedVisionResult`, expert fusion, and the evolved hybrid runtime are planned contracts, not current runtime capability.

### 4.3 Evidence language

The README may claim structural implementation, schema enforcement, artifact presence, and historical deployment evidence. It must not claim current accuracy, precision, recall, IoU, model superiority, universal floor-plan coverage, or production-ready hybrid detection until the corresponding labeled benchmark is executed and accepted.

Historical release counts may remain in a release table when explicitly labeled historical. Current-summary metrics must use live checkout facts. The README must not claim 50 usable sample images, 30-plus commits in this repository, or eight completed work plans.

The demo URL may be linked, but current online availability must not be asserted as verified unless it is rechecked successfully during README validation.

## 5. Portfolio framing

The opening will present the project as an auditable floor-plan-recognition and quantity-takeoff foundation rather than an accuracy-proven automated estimator.

The role statement will cover:

- end-to-end Python architecture and implementation;
- typed output and epistemic contract design;
- classical CV/OCR pipeline integration;
- review UI and SQLite auditability;
- provenance-controlled corpus tooling;
- Docker/shared-host deployment discipline; and
- benchmark-driven hybrid-vision program design and partial foundation implementation.

The outcome statement will emphasize a demonstrable vertical slice that exposes evidence, uncertainty, refusals, and measurement gates. It will not present the system as a replacement for professional quantity-surveyor review.

## 6. Quick-start design

The quick start will contain only commands that correspond to current paths:

- local editable installation and Streamlit launch;
- optional synthetic-corpus regeneration;
- fast-test command, described without claiming a fresh passing run unless executed;
- Docker launch using `docker compose -f deploy/docker-compose.yml up --build` or the equivalent `cd deploy` form.

Production deployment instructions will link to `docs/DEPLOY.md`. The README will state that the current shared-host topology uses one loopback-bound Streamlit service behind host-installed Caddy. It will not describe the repository `deploy/Caddyfile` as the live shared-host configuration.

## 7. Bilingual parity rules

- Identical heading order and section coverage.
- Equivalent facts, status terms, numbers, commands, links, and limitations.
- Korean domain terms may retain an English term in parentheses on first use.
- English prose may retain `적산` once with the translation “quantity takeoff.”
- No section may exist in only one language unless it is solely the language-switch link.

## 8. Verification

After editing:

1. Compare heading sequences between both files.
2. Scan for stale claims: `50 drawings`, `148 tests`, `30+ commits`, `all WPs completed`, implemented hybrid experts, and bundled-Caddy production topology.
3. Confirm every local Markdown link resolves.
4. Confirm setup commands match `pyproject.toml`, `deploy/docker-compose.yml`, and repository paths.
5. Count current sample/provenance/annotation artifacts and reconcile the README numbers.
6. Run lightweight source/document checks available in the current environment.
7. If the project environment is available, collect or run tests; otherwise state that runtime tests were not re-executed.
8. Check Korean and English claims side by side.

## 9. Non-goals

- No source-code, model, annotation, WP, deployment, or infrastructure changes.
- No new accuracy claims or benchmark results.
- No production rollout or demo mutation.
- No redesign of the deeper project documentation.
- No claim that AI-provisional labels or classifications are Human-accepted ground truth.

## 10. Acceptance criteria

The README update is accepted when:

- both files follow the mirrored structure;
- a client can identify the problem, role, deliverable, and limitation from the opening sections;
- current stable functionality is separated from v0.2 work in progress;
- all quantitative and deployment claims are traceable to current repository artifacts or explicitly identified historical evidence;
- commands and local links validate; and
- no claim implies recognition quality that the frozen labeled benchmark has not yet established.
