**한국어** · [English](README.en.md)

---

# CAD Trust Engine Lite

**v0.1.4** · [포비콘](https://www.pobicon.com) 지원용 MVP · Python 3.11+ · MIT 호환 (소스 비공개, corpus는 공개 라이선스)

🟢 **라이브 데모: [cad-tel.gemsquared.ai](https://cad-tel.gemsquared.ai)** — 브라우저에서 바로 클릭 가능. 첫 OCR 호출 시 PaddleOCR 모델 다운로드(~1-2분)로 느릴 수 있음.

> CAD Trust Engine은 단순히 도면 객체를 검출하는 데서 끝나지 않습니다.
> **각 판단의 근거와 불확실성, 검수가 필요한 영역까지 함께 기록**해, 적산 시스템에 연결 가능한 신뢰 표면(trust surface)을 제공합니다.

PNG/PDF/JPG 건축 도면 → **per-field EEF 태깅된 JSON** + Streamlit 검수 UI + SQLite audit 로그.

---

## TL;DR

이 프로젝트는 단순한 OpenCV 기반 도면 인식 파이프라인이 아닙니다.
시공 단계의 비용 리스크를 고려해, CAD 도면 인식 결과를 신뢰하고 검수할 수 있도록 설계한 demo-grade trust engine입니다.

핵심 차별점은 "더 많이 검출하는 것"이 아니라, **무엇을 알고 무엇을 모르는지 명확히 구분하는 것**입니다.

v0.1.3까지 총 4번의 autonomous WP 사이클을 통해 end-to-end 파이프라인을 구축했습니다. 현재 버전은 50장의 공개 라이선스 기반 corpus, 148개의 테스트, Streamlit 검수 UI, SQLite audit 로그를 포함합니다.

모든 검출 객체는 type, geometry, measurement 세 가지 독립적인 epistemic claim을 가지며, 신뢰할 수 없는 영역은 low-confidence 결과로 숨기지 않고 명시적인 refusal region으로 기록합니다. 또한 run, refusal, policy fire, epistemic distribution을 모두 audit DB에 저장해 시간에 따른 오류와 거부 패턴을 추적할 수 있습니다.

---

## 왜 적산(quantity takeoff) 도메인에서 중요한가

건설 CAD 도면 인식은 단순한 object detection 문제가 아닙니다.
실제 적산 업무에서는 검출 결과가 자재 물량, 공사비, 발주 판단으로 이어지기 때문에, 도면 인식은 곧 **비용 리스크가 걸린 측정 문제**가 됩니다.

벽체 하나를 잘못 인식하거나 길이를 잘못 산출하면, 잘못된 자재 발주나 공사비 산정으로 이어질 수 있습니다. 문제는 이런 오류가 시공 단계 전까지 드러나지 않을 수 있다는 점입니다.

따라서 이 엔진의 핵심 산출물은 단순한 detection list가 아닙니다.
검수자가 다음 질문을 직접 확인할 수 있는 **per-claim trust surface**입니다.

- 무엇이 검출되었는가?
- 엔진은 어떤 근거로 그렇게 판단했는가?
- type, geometry, measurement 각각의 확신 수준은 어떻게 다른가?
- 엔진이 판단을 보류하거나 거부한 영역은 어디인가?
- 전체 corpus에서 반복적으로 발생하는 refusal pattern은 무엇인가?

이 구조가 있어야 CAD 인식 결과를 산출내역서 시스템에 안전하게 연결할 수 있습니다.

포비콘 지원 메시지 한국어 풀버전은 [`docs/POBICON_PITCH.ko.md`](docs/POBICON_PITCH.ko.md)에 있습니다.

---

## EEF — Epistemic Evaluation Framework

엔진이 출력하는 모든 중요한 claim은 네 가지 태그 중 하나를 가집니다. 이 태그들은 confidence 점수가 **아니라**, **지식의 종류**를 구분하는 표시입니다.

| 태그 | 이름 | 의미 | 필수 필드 |
|:---:|------|-----|-----------|
| ⊢ | **GROUNDED** | OCR 결과나 geometry 매칭처럼 직접 확인된 근거 | `evidence` |
| ⊨ | **INFERRED** | ⊢ claim에서 추론된 결과, 추론 체인이 명시됨 | `evidence`, `derivation_chain` (선택) |
| ⊬ | **EXTRAPOLATED** | evidence만으로는 단정할 수 없는 추정 — `basis` 필수 | `evidence` + **`basis`** |
| ⊥ | **UNKNOWN** | 확인할 수 없는 영역, inference chain이 여기서 멈춤 | **`gap`** |

`⊬`와 `⊥`는 Pydantic schema validator가 **구조적으로 강제**합니다. `basis` 없는 extrapolation은 contract 단계에서 생성이 거부되고, `gap` 없는 unknown도 마찬가지로 거부됩니다. **schema 레이어에서 근거 없는 출력을 사전에 차단**합니다.

### Per-field epistemic — 객체당 세 개의 독립적인 판단

모든 검출 객체는 하나의 confidence 값으로 표현되지 않습니다.
대신 다음 세 가지 판단을 분리해 기록합니다.

| Mark | 답하는 질문 |
|------|------------|
| `type_epistemic` | 이 객체가 정말 벽/문/창인가? |
| `geometry_epistemic` | 객체의 위치와 형상은 신뢰할 수 있는가? |
| `measurement_epistemic` | mm 단위 측정값을 신뢰할 수 있는가? |

예를 들어 엔진은 어떤 객체에 대해 "벽일 가능성이 높다"고 판단할 수 있습니다.
동시에 픽셀상의 형상도 비교적 명확하다고 볼 수 있습니다.
하지만 신뢰 가능한 scale anchor가 없다면, "이 벽이 4,200mm다"라고 말해서는 안 됩니다.

이 세 가지 판단을 하나의 confidence로 압축하면 trust surface가 무너집니다.
바로 그 압축 때문에 일반적인 black-box detector를 적산 시스템에 그대로 연결하기 어렵습니다.

**Audit DB에서 추출한 실제 예시:**

```json
{
  "object_id": "obj_0042",
  "type": "wall_structural",
  "type_epistemic":        { "tag": "⊨", "evidence": [{"source":"opencv_line_pair","signal":"parallel pair gap=12px"}] },
  "geometry_epistemic":    { "tag": "⊨", "evidence": [{"source":"opencv_line_pair","signal":"endpoints from paired Hough"}] },
  "measurement_mm":        null,
  "measurement_epistemic": { "tag": "⊥", "gap": "no scale_anchor; mm refused per Measurement_Policy" },
  "review_status":         "needs_human"
}
```

---

## 핵심 Invariant

이 엔진은 다음 원칙을 코드와 schema 레벨에서 강제합니다.

### Measurement Policy

> `scale_anchor.detected = true`가 아니면 `measurement_mm`을 출력하지 않습니다.

dimension text와 도면 내 geometry를 안정적으로 매칭할 수 없을 때, 엔진은 mm 단위 변환을 수행하지 않습니다.
픽셀 길이는 diagnostic evidence로 남길 수 있지만, 신뢰 가능한 기준점 없이 mm 값으로 변환하지는 않습니다.

이 정책은 단순한 주석이나 convention이 아니라, Pydantic `model_validator`를 통해 강제됩니다.
즉, Measurement Policy를 위반하는 `EngineOutput`은 생성 자체가 불가능합니다.

### Refusal Over Bluff

근거가 부족한 경우, 엔진은 낮은 confidence의 결과를 억지로 내보내지 않습니다.
대신 해당 영역을 `refusal_candidate`로 기록하고, 최종 출력의 `refusals` 필드에 명시적으로 표시합니다.

낮은 coverage는 받아들일 수 있습니다.
하지만 자신 있게 틀리는 detection은 적산 시스템에 연결되어서는 안 됩니다.

가장 복잡한 Wikimedia 도면 한 장에서는 객체 20,267개, 명시적 refusal 140개, 검수 라우팅된 window/door 후보 747개가 함께 출력되었습니다.

### Refusal Over Bluff — across time (v0.1.1 audit)

Audit DB는 같은 원칙을 시간 축으로 확장합니다.
모든 refusal은 `run_id`와 함께 SQLite ledger에 누적되어, 검수자가 단일 도면 결과뿐 아니라 **corpus 전체에 걸친 refusal pattern**을 SQL로 조회할 수 있습니다.

### License Discipline

동일한 원칙은 corpus 구축에도 적용됩니다.
모든 sample은 `sha256`과 명시적인 license tag를 가진 provenance record를 동반합니다.
라이선스를 해석할 수 없는 source는 조용히 포함하지 않고, excluded log에 기록합니다.

v0.1.3에서 license mapping 보정(`pd` / `cc0` / `public-domain` 정확 매칭)으로 public domain 도면 16장을 추가로 확보했지만, discipline은 그대로 유지되어 라이선스 매핑이 정말 불가능한 후보 11장은 여전히 제외했습니다.

즉, 이 프로젝트는 도면 인식 결과뿐 아니라 학습·검증 데이터의 출처까지 audit 가능하도록 설계되었습니다.

---

## 빌드 현황 (v0.1.3 — 태그 4개)

| 릴리스 | 일자 | 핵심 변경 |
|--------:|------|----------|
| **v0.1.0** | 2026-06-05 | 9-unit 파이프라인 (Ingest → Geometry → OCR → Symbols → Compose+Aggregate) + Streamlit 검수 UI + 12장 synthetic corpus + 테스트 53개 |
| **v0.1.1** | 2026-06-05 | Audit 서브시스템 도입: SQLite schema + AuditContext + 5-stage instrumentation + CLI(`list-runs`/`show-run`/`refusals`/`stats`) + Streamlit "Past Runs" 탭 + 테스트 91개 |
| **v0.1.2** | 2026-06-05 | Wikimedia Commons 크롤로 실제 도면 22장 확보 (License Discipline에 따라 27장 제외) + JPG ingest 지원 + 테스트 130개 + ingestable 실제 도면 32장 100% 파이프라인 성공 |
| **v0.1.3** | 2026-06-06 | License mapping 보정(exact-vs-prefix matcher)으로 public domain 도면 16장 추가 확보 → 총 50장 + Streamlit 도면 dropdown 우측 preview pane 추가 + 테스트 148개 |

### 구체적 수치

- **5-stage 파이프라인**: Ingest → Geometry → OCR → Symbol → Compose+Aggregate
- **테스트 148개**, 모듈 9개 (fast 145개 + corpus-wide smoke 3개)
- **Corpus 50장** (synthetic 12 + Wikimedia 38, 모두 provenance + sha256 보유)
- **`main` 브랜치 commit 27개**, **태그 4개**
- **WP-level invariant 6개** 코드 전반에 강제
- **실제 도면 32장 100% 파이프라인 성공**; 객체 수 11–20,267; refusal 수 도면당 0–931

---

## 아키텍처

```
PNG/JPG/PDF 도면
       │
       ▼  Ingest_F          → IngestResult (canonical RGB ndarray + metadata)
       │
       ▼  Geometry_F        → lines / contours / wall_candidates  (OpenCV Canny + HoughLinesP + parallel-pair fusion)
       │
       ▼  OCR_F             → texts + dim/label classification    (PaddleOCR ko + en + regex classifier)
       │
       ▼  Symbol_F          → doors / windows / spaces + refusal_candidates  (HoughCircles + double-line + wall_proximity)
       │
       ▼  Compose_F+Agg_F   → EngineOutput (full schema)
       │                         ↳ objects (per-field EEF: type / geometry / measurement)
       │                         ↳ aggregates (⊬/⊥ taint warning 포함)
       │                         ↳ refusals  (first-class output)
       │                         ↳ scale_anchor (모든 mm 출력의 gate)
       │
       ▼
   Streamlit 검수 UI   +   SQLite Audit DB   +   CLI 쿼리
   (preview + overlay         (runs, stage_events,    (list-runs /
    + evidence panel +         refusals_log,          show-run /
    Past Runs 탭)              policy_fires,          refusals /
                               epistemic_counts)      stats)
```

Output contract([`src/cad_trust/schema.py`](src/cad_trust/schema.py), [`docs/OUTPUT_CONTRACT.md`](docs/OUTPUT_CONTRACT.md))는 detection 코드보다 **먼저** 정의되었습니다. `Contract_Before_Implementation` invariant에 따라, schema가 구현 방향을 가이드합니다 (반대 방향이 아니라).

---

## 기술 스택

| 레이어 | 선택 | 이유 |
|--------|------|------|
| 언어 | Python 3.11+ | 성숙한 생태계; CV + OCR + UI 결합 최단 경로 |
| Schema | Pydantic v2 | `model_validator`가 Measurement Policy를 contract 경계에서 강제 |
| Classical CV | OpenCV (`opencv-python-headless`) | Canny + HoughLinesP + HoughCircles + contour로 v0.1.x rule-based detection 커버 |
| OCR | PaddleOCR (ko + en) | 한국어 room label과 Latin dimension text 모두 안정적으로 인식 |
| PDF | `pdf2image` + Poppler | 안정적인 페이지 raster화 |
| Image I/O | Pillow | PaddleOCR 의존성에 포함; PNG/JPG/PDF preview 커버 |
| UI | Streamlit 1.58 | 빠른 반복; Run Engine + Past Runs 탭 분리; native 캐싱 |
| Audit DB | `sqlite3` (stdlib) | 외부 의존성 없음; PRAGMA user_version으로 마이그레이션 관리 |
| CLI | `argparse` (stdlib) | `python -m cad_trust.audit list-runs / show-run / refusals / stats` |
| 테스트 | `pytest` | 148개 테스트; fixture + parametrize + AST 기반 invariant 검사 |
| Corpus 크롤 | `urllib.request` (stdlib) | polite user-agent, 0.5s rate-limit, sha256 dedup, license 매핑 기반 refusal |
| 타입 힌트 | PEP 585 + 604 | 전반에 `list[T]` / `T | None`; `typing.List` legacy 미사용 |

## 의도적으로 제외한 것

이번 v0.1.x에서는 다음 기능을 의도적으로 제외했습니다.

- **YOLO / RT-DETR fine-tuning**
  아직 안정적인 labeled corpus가 없기 때문에 fine-tuning은 MVP 0.3 이후로 보류했습니다.

- **VLM 기반 primary detection**
  VLM은 도면 전체를 직접 해석하는 primary detector로 사용하지 않습니다.
  향후에는 expert CV layer가 걸러낸 uncertain crop에 대해 confirm / reject / abstain을 수행하는 verifier로만 사용할 계획입니다.

- **DWG native ingest**
  ODA / LibreDWG 의존성 선택과 배포 전략이 필요하므로 v0.3 영역으로 분리했습니다.

- **외부 audit 의존성**
  audit subsystem은 stdlib `sqlite3`만 사용해 설치 부담을 최소화했습니다.

---

## 엔지니어링 자세 (활용한 skill)

Commit 히스토리와 테스트에 가시화된 구체적 엔지니어링 실천:

- **Contract-before-implementation** — WP-ST-1 U2에서 Pydantic schema와 golden JSON을 detection 코드보다 **먼저** 정의했습니다. 이후 모든 unit은 새 schema를 따로 만들지 않고 이 schema에서 import합니다.
- **Backward compatibility를 invariant로** — 모든 릴리스는 이전 릴리스의 전체 테스트를 그대로 통과합니다 (53 → 91 → 130 → 148). 회귀가 발생하면 릴리스를 진행하지 않습니다.
- **Refusal을 first-class output type으로** — 파이프라인은 판단할 수 없는 region을 거부하고, corpus builder는 미분류 license source를 거부하며, audit DB는 그 refusal 기록을 시간 축으로 보존합니다.
- **Audit-first observability** — Audit 서브시스템(WP-ST-2)은 기존 파이프라인 contract를 변경하지 않습니다. 순수 additive + optional 파라미터로 opt-in이지만, trust surface를 시간 축에서 조회 가능하게 만듭니다.
- **Schema-enforced invariant** — Measurement Policy는 주석이나 convention이 아니라 `model_validator`로 데이터 레이어에서 강제됩니다. Schema가 invalid output을 생성 단계에서 거부합니다.
- **TPMN unit-work discipline** — 모든 변경 사이클은 `.gem-squared/work-plan/`에 문서화된 plan → proceed → verify → archive 루프를 따르며, unit별 `Acceptance` 기준을 함께 기록합니다.
- **하지 못한 작업의 honest refusal** — `data/samples/`가 100% 공개 라이선스 + provenance인 이유는, 무라이선스 데이터를 의도적으로 수집하지 않았기 때문입니다 ([`docs/CORPUS.md`](docs/CORPUS.md)에 기록).

---

## Quickstart

```bash
# Clone + venv
git clone https://github.com/gem-squared/gem2-cad-tel.git gem2-vision
cd gem2-vision
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Synthetic corpus baseline 생성 (12장)
.venv/bin/python scripts/build_corpus.py

# (선택) Wikimedia Commons에서 corpus 확장 (~22장 PNG/JPG/PDF)
.venv/bin/python scripts/crawl_corpus.py --target 25

# 전체 fast 테스트 (~97초; 145개; 10분짜리 corpus-wide smoke 제외)
.venv/bin/python -m pytest --ignore=tests/test_corpus_pipeline_smoke.py

# Demo UI 실행 (http://localhost:8501)
.venv/bin/python -m streamlit run ui/app.py
```

Streamlit UI 실행 후:

- **Run Engine 탭** — 도면 선택 → preview 즉시 표시 → Run Engine 클릭 → overlay + per-field epistemic 뱃지 + JSON 다운로드
- **Past Runs (Audit) 탭** — 기록된 run 드릴다운, corpus 전체에 걸친 `attempted_type`별 refusal pattern 집계

CLI audit 쿼리:

```bash
.venv/bin/python -m cad_trust.audit list-runs
.venv/bin/python -m cad_trust.audit show-run <run_id>
.venv/bin/python -m cad_trust.audit refusals --attempted-type door
.venv/bin/python -m cad_trust.audit stats
```

---

## 문서 안내

| 파일 | 목적 |
|------|-----|
| [`docs/README.md`](docs/README.md) | 엔지니어링 thesis — 전체 TPMN 논증의 시작점 |
| [`docs/OUTPUT_CONTRACT.md`](docs/OUTPUT_CONTRACT.md) | 공식 contract 사양 + Measurement Policy 레퍼런스 |
| [`docs/CORPUS.md`](docs/CORPUS.md) | Corpus 라이선스 자세, 사용 source, 제외 정책 |
| [`docs/AUDIT.md`](docs/AUDIT.md) | Audit 서브시스템: schema, CLI 사용법, 예시 SQL 쿼리 |
| [`docs/DEMO_SCENARIOS.md`](docs/DEMO_SCENARIOS.md) | 한국 아파트 적산 refusal 데모 포함 5가지 시나리오 워크스루 |
| [`docs/POBICON_PITCH.ko.md`](docs/POBICON_PITCH.ko.md) | 포비콘 지원 메시지 (한국어) |
| `.gem-squared/work-plan/WP-ST-1.md` … `WP-ST-4.md` | TPMN work plan 4개 — unit별 A → B \| P contract와 결과 |

---

## 포비콘 지원 핵심 메시지

> 저는 CAD 도면 인식의 핵심을 단순 검출 정확도가 아니라, 적산에 연결 가능한 신뢰 가능한 도면 해석으로 봅니다.
>
> 그래서 CAD Trust Engine Lite는 벽체, 문, 창호, 공간 후보를 검출하는 데서 끝나지 않고, 각 판단을 type / geometry / measurement로 분리해 근거와 불확실성을 함께 기록합니다. 신뢰할 수 없는 영역은 낮은 confidence 값으로 숨기지 않고, 명시적인 refusal region으로 남겨 검수자가 확인할 수 있도록 합니다.
>
> 이 구조는 *"더 많이 맞히는 detector"보다 "모르는 것을 모른다고 말할 수 있는 engine"이 적산 시스템에 더 안전하게 결합될 수 있다*는 문제의식에서 출발했습니다.

---

## 로드맵

### MVP 0.2 — Expert CV CrossCheck + Page Type Guard

MVP 0.2의 핵심은 fine-tuning이 아니라 **expert CV cross-checking**입니다.

현재의 단일 rule-based detector를 다음과 같은 expert module로 분리합니다.

- WallExpert
- DoorExpert
- WindowExpert
- SpaceExpert
- TextSuppressor
- PageTypeExpert

각 expert는 최종 객체를 직접 확정하지 않고, claim과 evidence만 생성합니다.
이후 `CrossCheck_F`가 expert 간 agreement / disagreement를 바탕으로 최종 EEF tag와 refusal 사유를 결정합니다.

특히 mixed-sheet 도면에서는 elevation, section, floor plan 영역을 구분해 over-detection을 줄이고, UI에서는 각 expert가 어떤 근거로 후보를 승인·거부·보류했는지 확인할 수 있도록 합니다.

### MVP 0.2-public — 공개 데모 배포

현재 Streamlit 기반 demo를 유지하면서, 공유 가능한 URL로 배포합니다.
목표는 별도 React/Next.js 프론트엔드를 새로 만드는 것이 아니라, **포비콘이 바로 클릭해 볼 수 있는 검수형 데모**를 제공하는 것입니다.

### MVP 0.3 이후

- 한국 아파트형 synthetic generator
- 자동 label 생성 및 labeled corpus 구축
- YOLO / RT-DETR fine-tuning
- 불확실한 crop에 한정한 VLM_Verify
- DWG / DXF native ingest
- cost aggregate taint propagation 고도화

---

## 진행 상황

- **v0.1.0** — 2026-06-05 · 9 unit · 53 tests · `Refusal Over Bluff` 도입
- **v0.1.1** — 2026-06-05 · 6 unit · 91 tests · Audit 서브시스템 (SQLite + CLI + Streamlit 탭)
- **v0.1.2** — 2026-06-05 · 6 unit · 130 tests · Wikimedia corpus (12 → 34장) + JPG ingest
- **v0.1.3** — 2026-06-06 · 4 unit · 148 tests · License 보정 (34 → 50장) + preview pane
- **v0.1.4** — 2026-06-06 · 6 unit · Vultr VPS 라이브 배포 (`cad-tel.gemsquared.ai`) · Docker + 호스트 Caddy 통합

5개 work plan(`WP-ST-1` ~ `WP-ST-5`) 모두 `COMPLETED|SUCCESS`, `/archive-work` 대기 중.

---

*CAD Trust Engine Lite · gem-squared/gem2-cad-tel · 2026-06-06*
