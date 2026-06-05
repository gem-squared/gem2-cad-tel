**한국어** · [English](README.en.md)

---

# CAD Trust Engine Lite

**v0.1.3** · [포비콘](https://www.pobicon.com) 지원용 MVP · Python 3.11+ · MIT 호환 (소스 비공개, corpus는 공개 라이선스)

> Detector는 답을 줍니다.
> **CAD Trust Engine**은 **답 + 근거 + 불확실성 + 거부(refusal) + 검수 경로**를 함께 주고, 그것을 **기억**합니다.

PNG/PDF/JPG 건축 도면 → **per-field EEF 태깅된 JSON** + Streamlit 검수 UI + SQLite audit 로그.

---

## TL;DR

이 프로젝트는 "또 하나의 OpenCV 파이프라인"이 아닙니다. **시공 단계의 비용 리스크 하에서 신뢰 가능한 CAD 도면 인식**을 위한 작은, 동작하는 trust engine입니다. 차별점은 검출 정확도가 아니라 **"무엇을 모르는지 아는 측정"**입니다.

4번의 autonomous WP 사이클로 end-to-end 빌드했습니다 (commit 26개, 태그 4개, 테스트 148개, 50장 corpus). 모든 객체는 세 개의 orthogonal epistemic claim(type / geometry / measurement)을 가지고, commit 불가능한 영역에 대해서는 명시적 refusal region을 emit하며, run / refusal / policy fire / epistemic distribution을 모두 audit DB에 기록합니다.

---

## 왜 적산(quantity takeoff) 도메인에서 다른가

건설 CAD 도면 인식은 **object detection 문제가 아닙니다**. **비용 리스크 하의 auditable measurement 문제**입니다.

벽체 한 개를 잘못 인식하면 잘못된 자재 발주가 발생하고, 수백만 KRW 단위의 손실로 이어집니다. 적산 시스템은 confidently-wrong한 측정값을 시공 단계 전까지 탐지할 수 없습니다. 그래서 이 엔진의 primary deliverable은 "detection 목록"이 아니라, 검수자가 다음 질문을 SQL로 물어볼 수 있는 **per-claim trust surface**입니다:

- **무엇**이 검출되었는가?
- 엔진이 그렇게 판단한 **근거**는 무엇인가? (evidence chain)
- 필드별 **확신 수준**은 얼마인가? (type / geometry / measurement 각각 별도)
- 엔진이 **commit하지 않기로 거부**한 영역은 어디인가? (이유 포함)
- 전체 corpus에 걸친 거부 **패턴**은 무엇인가? (history)

이것이 포비콘이 인식 결과를 산출내역서 시스템에 결합 가능하게 만드는 auditability 스토리입니다.

포비콘 지원 메시지(한국어 풀버전)는 [`docs/POBICON_PITCH.ko.md`](docs/POBICON_PITCH.ko.md)에 있습니다.

---

## EEF — Epistemic Evaluation Framework

엔진이 emit하는 모든 중요한 claim은 네 가지 태그 중 하나를 가집니다. 이 태그들은 confidence 점수가 **아니라**, **지식의 종류**입니다.

| 태그 | 이름 | 의미 | 필수 필드 |
|:---:|------|-----|-----------|
| ⊢ | **GROUNDED** | 직접 evidence (OCR 결과, 정확한 geometry 매칭) | `evidence` |
| ⊨ | **INFERRED** | ⊢ claim들로부터 도출, 도출 체인 가시화 | `evidence`, `derivation_chain` (선택) |
| ⊬ | **EXTRAPOLATED** | evidence를 넘어선 추정 — 틀릴 수 있음 | `evidence` + **`basis`** (필수) |
| ⊥ | **UNKNOWN** | 지식 갭, inference chain 정지 | **`gap`** (필수) |

`⊬`와 `⊥`는 Pydantic schema validator에 의해 **구조적으로 강제**됩니다. Contract는 `basis` 없는 extrapolation을 거부하고, `gap` 없는 unknown을 거부합니다. **스키마 레이어에서 bluff가 불가능합니다.**

### Per-field epistemic — 객체당 세 개의 orthogonal claim

모든 검출 객체는 **세 개의 독립적인 epistemic mark**를 가집니다:

| Mark | 답하는 질문 |
|------|------------|
| `type_epistemic` | 이게 정말로 벽/문/창인가? |
| `geometry_epistemic` | 모양과 범위는 정확한가? |
| `measurement_epistemic` | mm 측정값은 신뢰할 만한가? |

엔진이 *"이것은 벽이 맞다"* (⊨)는 확신, *"픽셀 모양도 정확하다"* (⊢)는 확신을 가지면서, **동시에 *"이것이 4,200 mm라고는 말할 수 없다"*** (⊥)고 거부할 수 있습니다. 이 세 가지를 하나로 압축하면 trust surface가 무너지고, **그 압축이 바로 black-box detector를 적산 시스템에 안전하게 결합할 수 없게 만드는 원인**입니다.

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

엔진이 위반을 거부하는 invariant들. 모두 schema 레이어에서 validator로 강제됩니다.

### Measurement_Policy

> **`scale_anchor.detected = True`가 아니면 `measurement_mm`을 emit하지 않는다.**

px-to-mm 변환 비율을 신뢰성 있게 추출할 수 없을 때 (dimension text와 벽체 길이의 매칭 실패), 엔진은 **모든 객체와 aggregate**에 대해 mm 변환을 거부합니다. `EngineOutput.model_validator`가 이를 강제합니다 — Measurement_Policy를 위반하는 `EngineOutput`은 **생성 자체가 불가능**합니다. 픽셀 길이는 evidence에 diagnostic으로 남을 수는 있지만, **절대 mm 출력으로 나오지 않습니다**.

### Refusal_Over_Bluff

Evidence가 부족할 때 (지지 signal이 2개 미만), 엔진은 low-confidence detection 대신 `refusal_candidate`를 emit합니다. 이것들은 `EngineOutput.refusals`의 최상위 필드로 promote됩니다. **낮은 coverage는 받아들일 수 있지만, confident-wrong detection은 받아들일 수 없습니다**. Wikimedia에서 가장 복잡한 도면 1장에서 엔진은 객체 20,267개 + 명시적 refusal 140개 + 검수 라우팅된 window/door 후보 747개를 emit했습니다.

### Refusal_Over_Bluff_Across_Time (v0.1.1 audit)

Audit DB는 이 invariant를 시간 축으로 확장합니다. 모든 refusal이 `run_id` linkage와 함께 SQLite ledger에 누적되어, 검수자가 단일 도면 snapshot이 아니라 **전체 corpus에 걸친 refusal pattern**을 SQL로 조회할 수 있습니다.

### License_Discipline (v0.1.2/3 corpus)

동일한 자세를 corpus 빌드에도 적용했습니다. 모든 sample은 `sha256` + 명시적 라이선스 태그를 가진 `ProvenanceRecord`를 동반합니다. **mapping 불가능한 라이선스의 source는 `data/samples/`에 들어갈 수 없습니다** — 미분류 source는 silently 포함되는 대신 `excluded` 로그에 surface됩니다. v0.1.3에서 license fix(`pd` + `cc0` + `public-domain` exact-match)로 PD 도면 16장이 추가로 unlock되었지만, discipline은 그대로 유지되어 라이선스 매핑이 정말 불가능한 후보 11장은 여전히 거부되었습니다.

---

## 빌드 현황 (v0.1.3 — 태그 4개)

| 릴리스 | 일자 | 핵심 변경 |
|--------:|------|----------|
| **v0.1.0** | 2026-06-05 | 9-unit 파이프라인: Ingest → Geometry → OCR → Symbols → Compose+Aggregate + Streamlit 검수 UI + 12장 synthetic corpus + 테스트 53개 |
| **v0.1.1** | 2026-06-05 | Audit 서브시스템: SQLite schema + AuditContext + 5-stage instrumentation + CLI(`list-runs`/`show-run`/`refusals`/`stats`) + Streamlit "Past Runs" 탭 + 테스트 91개 |
| **v0.1.2** | 2026-06-05 | Wikimedia Commons 크롤: 실제 도면 22장 추가 (License_Discipline으로 매핑 불가능 27장 거부) + JPG ingest 지원 + 테스트 130개 + 32장 ingestable 실제 도면 100% 파이프라인 성공 |
| **v0.1.3** | 2026-06-06 | License mapping 수정(exact-vs-prefix matcher)으로 PD 도면 16장 추가 unlock → 총 50장 + Streamlit 도면 dropdown 우측 preview pane 추가 + 테스트 148개 |

### 구체적 수치

- **5-stage 파이프라인**: Ingest → Geometry → OCR → Symbol → Compose+Aggregate
- **테스트 148개**, 모듈 9개 (fast 145개 + corpus-wide smoke 3개)
- **Corpus 50장** (synthetic 12 + Wikimedia 38, 모두 provenance + sha256 보유)
- **`main` brand commit 27개**, **태그 4개**
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

Output contract([`src/cad_trust/schema.py`](src/cad_trust/schema.py), [`docs/OUTPUT_CONTRACT.md`](docs/OUTPUT_CONTRACT.md))는 detection 코드보다 **먼저** commit되었습니다 — `Contract_Before_Implementation` invariant에 따라 schema가 구현을 gate합니다 (반대가 아니라).

---

## 기술 스택

| 레이어 | 선택 | 이유 |
|--------|------|------|
| 언어 | Python 3.11+ | 성숙한 생태계; CV + OCR + UI 결합 최단 경로 |
| Schema | Pydantic v2 | `model_validator`가 Measurement_Policy를 contract 경계에서 강제 |
| Classical CV | OpenCV (`opencv-python-headless`) | Canny + HoughLinesP + HoughCircles + contour로 v0.1.x rule-based detection 커버 |
| OCR | PaddleOCR (ko + en) | 한국어 room label과 Latin dimension text 모두 안정적 |
| PDF | `pdf2image` + Poppler | 안정적인 페이지 raster화 |
| Image I/O | Pillow | PaddleOCR 의존성으로 이미 포함; PNG/JPG/PDF preview 커버 |
| UI | Streamlit 1.58 | 빠른 반복; Run Engine + Past Runs 탭 분리; native 캐싱 |
| Audit DB | `sqlite3` (stdlib) | 외부 의존성 0; PRAGMA user_version으로 마이그레이션 gate |
| CLI | `argparse` (stdlib) | `python -m cad_trust.audit list-runs / show-run / refusals / stats` |
| 테스트 | `pytest` | 148개 테스트; fixture + parametrize + AST 기반 invariant 검사 |
| Corpus 크롤 | `urllib.request` (stdlib) | Polite user-agent, 0.5s rate-limit, sha256 dedup, license 매핑 기반 refusal |
| 타입 힌트 | PEP 585 + 604 | 전반에 `list[T]` / `T | None`; `typing.List` legacy 없음 |

**의도적으로 사용하지 않은 것** (이유는 `docs/README.md`에 상술):
- **YOLO/RT-DETR fine-tune 안 함** — labeled corpus가 아직 없음 (v0.3 영역)
- **VLM 안 씀** — 도면당 20,000+ raw HoughP candidate를 처리하기에는 비효율; expert CV cross-checking + page-type guard가 먼저 (WP-ST-5 계획)
- **DWG native ingest 안 함** — ODA/LibreDWG 의존성 결정 필요 (v0.3 영역)
- **Audit를 위한 외부 의존성 없음** — stdlib `sqlite3`로 audit 서브시스템 설치 비용 0 유지

---

## 엔지니어링 자세 (활용한 skill)

Commit 히스토리와 테스트에 가시화된 구체적 엔지니어링 실천:

- **Contract-before-implementation** — WP-ST-1 U2에서 Pydantic schema + golden JSON을 detection 코드보다 **먼저** commit; 이후 모든 unit은 새 schema를 발명하지 않고 이 schema에서 import
- **Backward-compatibility를 invariant로** — 모든 릴리스는 이전 릴리스의 전체 테스트를 통과 (53 → 91 → 130 → 148, 절대 후퇴하지 않음)
- **Refusal을 first-class output type으로** — 모든 레이어에서: 파이프라인은 commit 불가능한 region을 refuse, corpus builder는 미분류 license source를 refuse, audit DB는 그 refusal trail을 시간 축으로 기록
- **Audit-first observability** — Audit 서브시스템(WP-ST-2)은 파이프라인 contract를 변경하지 않고 순수 additive + optional 파라미터로 opt-in; 그러나 trust surface를 historically queryable하게 만듦
- **Schema-enforced invariant** — Measurement_Policy는 convention이나 주석이 아니라 `model_validator`로 데이터 레이어에서 강제. Schema가 invalid output **생성 자체를 거부**.
- **TPMN unit-work discipline** — 모든 변경 사이클은 `.gem-squared/work-plan/`에 문서화된 plan → proceed → verify → archive 루프 실행, unit별 `Acceptance` 기준 포함
- **하지 못한 작업의 honest refusal** — `data/samples/`가 100% 공개 라이선스 + provenance인 이유는, 무라이선스 데이터를 의도적으로 scrape하지 않았기 때문 ([`docs/CORPUS.md`](docs/CORPUS.md)에 기록)

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

# 전체 fast 테스트 (~97s; 145개; 10분짜리 corpus-wide smoke 제외)
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
| [`docs/AUDIT.md`](docs/AUDIT.md) | Audit 서브시스템: schema, CLI 사용, 예시 SQL 쿼리 |
| [`docs/DEMO_SCENARIOS.md`](docs/DEMO_SCENARIOS.md) | 한국 아파트 적산 refusal 데모 포함 5가지 시나리오 워크스루 |
| [`docs/POBICON_PITCH.ko.md`](docs/POBICON_PITCH.ko.md) | 포비콘 지원 메시지 (한국어) |
| `.gem-squared/work-plan/WP-ST-1.md` … `WP-ST-4.md` | TPMN work plan 4개 — unit별 A → B \| P contract + 결과 |

---

## 로드맵

**MVP 0.2 — 계획 중**

- **WP-ST-5: Expert CV cross-check + Page Type guard** — 단일 rule-based detector를 expert 모듈(WallExpert / DoorExpert / WindowExpert / SpaceExpert / TextSuppressor / PageTypeExpert)로 분리하여 각자 `claim` record를 emit하고, `CrossCheck_F`가 expert agreement 기반으로 최종 EEF 태그를 부여. UI에 expert 투표 panel 추가. Mixed-sheet 도면에서 over-detection 감소 (audit DB가 보여주는 도면 1장당 refusal 747개를 expert 레이어가 *왜* refuse했는지 설명하면서 상당수를 clean reject으로 정리)
- **WP-ST-6: 공개 Streamlit 배포** — 현재 demo를 공유 가능한 URL로 cloud-deploy; 저비용 + 제안서 가독성에 임팩트 큼
- **WP-ST-7: VLM_Verify on ⊬ crops only** — Qwen-VL / Claude vision을 extrapolated claim의 *re-checker*로만 사용, primary detector 절대 아님. VLM은 confirm / reject / abstain만. Scale_anchor policy를 절대 override하지 않음.

**MVP 0.3 — 그 이후**

- 한국 아파트 synthetic generator (label 학습 데이터 준비)
- 조립된 labeled corpus 기반 YOLO/RT-DETR fine-tuning
- ODA / LibreDWG 기반 DWG native ingest
- 산출내역서 계산에 대한 cost-aggregate ⊬-taint 완전 전파
- Audit DB retention / rotation 정책

---

## 진행 상황

- **v0.1.0** — 2026-06-05 · 9 unit · 53 tests · `Refusal Over Bluff` 도입
- **v0.1.1** — 2026-06-05 · 6 unit · 91 tests · Audit 서브시스템 (SQLite + CLI + Streamlit tab)
- **v0.1.2** — 2026-06-05 · 6 unit · 130 tests · Wikimedia corpus (12 → 34장) + JPG ingest
- **v0.1.3** — 2026-06-06 · 4 unit · 148 tests · License 수정 (34 → 50장) + preview pane

4개 work plan(`WP-ST-1` ~ `WP-ST-4`) 모두 `COMPLETED|SUCCESS`, `/archive-work` 대기.

---

*CAD Trust Engine Lite · gem-squared/gem2-cad-tel · 2026-06-06*
