# Bilingual Portfolio README Design

**Date:** 2026-08-28  
**Target:** `README.md` (Korean) and `README.en.md` (English)  
**Audience:** Freelance clients first; technical reviewers second
**Status:** Human-approved direction; implementation pending README review gate

## 1. Objective

Rewrite the Korean and English README files as synchronized, bid-oriented portfolio documents. The opening must let a prospective client understand the business problem, the contributor's role, the delivered system, and the evidence boundary quickly. The live demo is the primary proof and call to action. A minimal local installation path is secondary evidence for technical reviewers.

The README is a sales and capability artifact, not an implementation handbook. It must establish credibility without disclosing enough of the pipeline, model strategy, data strategy, thresholds, or decision logic for a competitor to reproduce the project's differentiated know-how.

The README must describe the repository as it exists now. It must distinguish the stable v0.1.6 runtime from the partially implemented v0.2 benchmark and annotation foundation, and it must not imply validated object-recognition quality before Human-reviewed ground truth and a frozen benchmark exist.

## 2. Selected approach

Maintain two mirrored files with the same section order and equivalent claims:

- `README.md`: primary Korean portfolio document;
- `README.en.md`: English translation with equivalent technical meaning.

This preserves the current language-switch pattern while avoiding a single oversized bilingual file. The two files may use natural language appropriate to each audience, but all numbers, statuses, commands, limitations, and links must match.

## 3. Information architecture

Both files use this order:

1. Project identity, current stable version, and prominent live-demo call to action.
2. Portfolio summary: client problem, solution, role, and delivered outcome.
3. Current capability boundary: available now versus in progress.
4. Core trust design: EEF, refusal, Measurement Policy, and audit trail.
5. High-level capability flow without implementation internals.
6. Technology stack at category level with concise selection rationale.
7. Evidence and evaluation posture without dataset or benchmark recipes.
8. Verification evidence and explicit limitations.
9. Minimal local installation; live demo remains the primary path.
10. Release/status summary, documentation map, and bounded roadmap.

The top portion is client-readable. Deeper implementation detail remains available below it rather than dominating the opening.

## 4. Public disclosure and IP boundary

### 4.1 Public capability evidence

The README may disclose:

- the client problem and quantity-takeoff risk being addressed;
- the contributor's role and delivered product surfaces;
- supported input formats and reviewable output categories;
- a simplified flow of floor-plan input to trust-aware analysis to reviewable result;
- schema-enforced uncertainty, refusal, measurement gating, and auditability as product behaviors;
- technology categories and major frameworks already visible to an evaluator;
- carefully bounded repository counts and implementation status;
- the live demo URL and a minimal local launch path; and
- honest limitations and the distinction between stable and in-progress capability.

### 4.2 Protected know-how

The README must not disclose or summarize:

- detailed stage/module composition or internal class/function/file mapping;
- detection algorithms, heuristics, thresholds, geometry rules, or post-processing recipes;
- expert composition, fusion matrices, calibration methods, refusal-routing rules, or model-selection details;
- annotation production workflow, source-acquisition strategy, split derivation, coverage thresholds, benchmark weights, or promotion-predicate logic;
- spatial scale-anchor association mechanics beyond the public safety guarantee;
- internal WP contracts, status mechanics, execution governance, or evidence-store layout;
- production host topology, tenant details, deployment commands, credentials, rollback mechanics, or artifact-distribution design; and
- forward-looking implementation details that would provide a ready-made competitive blueprint.

The governing rule is: disclose the problem, capability, observable behavior, and evidence boundary; protect the implementation recipe.

## 5. Authoritative facts and claim boundaries

### 5.1 Stable runtime

- The packaged stable version remains `0.1.6`.
- The current executable recognition path is a classical CV/OCR floor-plan analysis pipeline. Its internal stage composition is not described in the public README.
- Supported ingest formats are PNG, JPG/JPEG, and rasterized PDF page 0.
- The public result boundary is the Pydantic `EngineOutput` schema.
- Every object separates type, geometry, and measurement epistemic marks.
- Without `scale_anchor.detected=True`, `measurement_mm` remains absent and measurement epistemic state remains unknown.
- Refusals are first-class output and SQLite audit records preserve run/stage/refusal/policy evidence.
- The Streamlit UI and audit CLI are implemented.

### 5.2 v0.2 foundation implemented in the repository

- The repository contains the foundations for governed data preparation and benchmark-driven improvement. Public wording stays at this capability level.
- There are 42 sample files and 50 provenance records; eight provenance-only orphans are preserved and excluded non-destructively.
- Current AI-provisional eligibility assigns 20 supported floor plans, eight guard negatives, and 14 guard-ambiguous samples. These classifications are not frozen Human truth.
- Evaluation data has separated development and held-out roles, but the public README does not expose the split recipe.
- Annotation files currently contain empty skeletons, not object ground truth.
- Validation/test Human review, annotation QA, dataset freeze, evaluation harness, and frozen v0.1 baseline remain blocked or pending.
- The hybrid recognition upgrade remains in progress and is not presented as current runtime capability. Internal component contracts are not named publicly.

### 5.3 Evidence language

The README may claim structural implementation, schema enforcement, artifact presence, and historical deployment evidence. It must not claim current accuracy, precision, recall, IoU, model superiority, universal floor-plan coverage, or production-ready hybrid detection until the corresponding labeled benchmark is executed and accepted.

Historical release counts may remain in a compact release table when explicitly labeled historical. Current-summary metrics must use live checkout facts. The README must not claim 50 usable sample images, 30-plus commits in this repository, or eight completed work plans. Internal WP identifiers and unit status do not belong in the public README.

The demo URL may be linked, but current online availability must not be asserted as verified unless it is rechecked successfully during README validation.

## 6. Portfolio framing

The opening will present the project as an auditable floor-plan-recognition and quantity-takeoff foundation rather than an accuracy-proven automated estimator.

The role statement will cover:

- end-to-end Python product architecture and implementation;
- typed output and epistemic contract design;
- classical CV/OCR pipeline integration;
- review UI and SQLite auditability;
- provenance-controlled data governance;
- containerized delivery and hosted-demo operation; and
- benchmark-driven improvement design and partial evaluation foundation.

The outcome statement will emphasize a demonstrable vertical slice that exposes evidence, uncertainty, refusals, and measurement gates. It will not present the system as a replacement for professional quantity-surveyor review.

## 7. Live demo and local-install design

The hosted demo is the primary README call to action and appears in the opening block. The README describes what a client can evaluate in the demo without exposing how the internal analysis is produced.

The local-install section is a secondary technical-verification path. It contains only commands needed to install the existing package and launch the Streamlit application:

- create and activate a virtual environment;
- install the project in editable mode; and
- launch the Streamlit application.

The public README will not include corpus-building, crawling, annotation, benchmark, model-training, Docker-production, Caddy, VPS, CI, artifact-distribution, or deployment commands. Those are implementation and operational know-how, not bid evidence. It may state that a hosted containerized demo exists without exposing its topology.

## 8. Bilingual parity rules

- Identical heading order and section coverage.
- Equivalent facts, status terms, numbers, commands, links, and limitations.
- Korean domain terms may retain an English term in parentheses on first use.
- English prose may retain `적산` once with the translation “quantity takeoff.”
- No section may exist in only one language unless it is solely the language-switch link.

## 9. Verification

After editing:

1. Compare heading sequences between both files.
2. Scan for stale claims: `50 drawings`, `148 tests`, `30+ commits`, `all WPs completed`, implemented hybrid experts, and bundled-Caddy production topology.
3. Confirm every local Markdown link resolves.
4. Confirm minimal local setup commands match `pyproject.toml` and repository paths.
5. Count current sample/provenance/annotation artifacts and reconcile the README numbers.
6. Run lightweight source/document checks available in the current environment.
7. If the project environment is available, collect or run tests; otherwise state that runtime tests were not re-executed.
8. Check Korean and English claims side by side.
9. Scan for protected disclosures: algorithms, thresholds, fusion rules, data/split recipes, benchmark weights, internal WP details, and production topology.

## 10. Non-goals

- No source-code, model, annotation, WP, deployment, or infrastructure changes.
- No new accuracy claims or benchmark results.
- No production rollout or demo mutation.
- No redesign of the deeper project documentation.
- No claim that AI-provisional labels or classifications are Human-accepted ground truth.
- No public technical recipe that materially reduces the effort required to reproduce the differentiated pipeline.

## 11. Acceptance criteria

The README update is accepted when:

- both files follow the mirrored structure;
- a client can identify the problem, role, deliverable, and limitation from the opening sections;
- current stable functionality is separated from v0.2 work in progress;
- all quantitative and deployment claims are traceable to current repository artifacts or explicitly identified historical evidence;
- commands and local links validate;
- no claim implies recognition quality that the frozen labeled benchmark has not yet established;
- the live demo is the primary call to action and local installation is visibly secondary; and
- no protected pipeline, model, dataset, benchmark, or deployment know-how is disclosed.
