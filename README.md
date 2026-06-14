**한국어** · [English](README.en.md)

---

# CAD Trust Engine Lite

**v0.1.6** · Portfolio · Auditable CAD floor-plan recognition (Korean ConTech 적산 wedge) · Python 3.11+ · MIT 호환 (소스 비공개, corpus는 공개 라이선스)

🟢 **라이브 데모: [cad-tel.gemsquared.ai](https://cad-tel.gemsquared.ai)** — 브라우저에서 바로 클릭 가능. 첫 OCR 호출 시 PaddleOCR 모델 다운로드(~1-2분)로 느릴 수 있음.

> CAD Trust Engine은 단순히 도면 객체를 검출하는 데서 끝나지 않습니다.
> **각 판단의 근거와 불확실성, 검수가 필요한 영역까지 함께 기록**해, 적산 시스템에 연결 가능한 신뢰 표면(trust surface)을 제공합니다.

PNG/PDF/JPG 건축 도면 → **per-field EEF 태깅된 JSON** + Streamlit 검수 UI + SQLite audit 로그.

---

## TL;DR

이 프로젝트는 단순한 OpenCV 기반 도면 인식 파이프라인이 아닙니다.
시공 단계의 비용 리스크를 고려해, CAD 도면 인식 결과를 신뢰하고 검수할 수 있도록 설계한 demo-grade trust engine입니다.

핵심 차별점은 "더 많이 검출하는 것"이 아니라, **무엇을 알고 무엇을 모르는지 명확히 구분하는 것**입니다.

v0.1.4까지 총 5번의 autonomous WP 사이클을 통해 end-to-end 파이프라인과 라이브 데모 배포까지 구축했습니다. 현재 버전은 50장의 공개 라이선스 기반 corpus, 148개의 테스트, Streamlit 검수 UI, SQLite audit 로그, Vultr VPS 위 Docker + Caddy 배포를 포함합니다.

모든 검출 객체는 type, geometry, measurement 세 가지 독립적인 epistemic claim을 가지며, 신뢰할 수 없는 영역은 low-confidence 결과로 숨기지 않고 명시적인 refusal region으로 기록합니다. 또한 run, refusal, policy fire, epistemic distribution을 모두 audit DB에 저장해 시간에 따른 오류와 거부 패턴을 추적할 수 있습니다.

---

## 🧱 기술 스택 — 무엇을, 왜 사용했는가

| 레이어 | 선택 | 이 도메인에서 이걸 고른 이유 |
|--------|------|------|
| 언어 | **Python 3.11+** | CV + OCR + UI 결합 최단 경로. PEP 585/604 타입 힌트로 `list[T]` / `T \| None` 일관 적용. |
| Schema | **Pydantic v2** | `model_validator`가 Measurement_Policy를 contract 경계에서 강제. 잘못된 `EngineOutput`은 생성 자체가 불가능. |
| Classical CV | **OpenCV** (`opencv-python-headless`) | Canny + HoughLinesP + parallel-pair fusion + HoughCircles로 v0.1.x rule-based detection 커버. headless 빌드라 컨테이너/Streamlit Cloud 어디서나 동작. |
| OCR | **PaddleOCR (ko + en)** | 한국어 room label + Latin dimension text 모두 안정적. 단일 모델로 두 언어 커버. |
| PDF 처리 | **`pdf2image` + Poppler** | 안정적인 페이지 raster화; 다중 페이지는 명시적 warn 후 page 0만 ingest. |
| Image I/O | **Pillow** | PaddleOCR 의존성에 포함; PNG/JPG/PDF preview 모두 커버. |
| Review UI | **Streamlit 1.58** | 빠른 반복 + native 캐싱. Run Engine / Past Runs (Audit) 두 탭으로 분리. |
| Audit DB | **`sqlite3`** (stdlib) | 외부 의존성 0개. `PRAGMA user_version`으로 schema 마이그레이션 게이팅. |
| CLI | **`argparse`** (stdlib) | `python -m cad_trust.audit list-runs / show-run / refusals / stats` — audit DB를 SQL 없이 조회. |
| 테스트 | **`pytest`** | 148개; fixtures + parametrize + AST 기반 invariant 검사. fast 145개 + corpus-wide smoke 3개. |
| Corpus 크롤 | **`urllib.request`** (stdlib) | 외부 의존성 0개. polite UA, 0.5s rate-limit, sha256 dedup, license 매핑 기반 refusal. |
| 컨테이너 | **Docker + docker-compose** | 단일 host 배포. paddleocr/opencv 시스템 의존성(`libgl1`, `libglib2.0-0`)을 이미지로 봉인. |
| Reverse proxy | **Caddy 2** | 도메인 있으면 auto-TLS via Let's Encrypt, 없으면 plain HTTP fallback — 양쪽 모드 모두 검증. |
| 배포 호스트 | **Vultr VPS** (Debian/Ubuntu, $6/mo) | 1GB RAM + 2GB swap 만으로 PaddleOCR + Streamlit + audit 운영 검증. 라이브: [`cad-tel.gemsquared.ai`](https://cad-tel.gemsquared.ai) |
| 보안 · LLM 키 | **BYO (Bring-Your-Own)** | LLM API key는 절대 서버 측 env에 저장하지 않음. 방문자가 UI sidebar에 직접 paste → `st.session_state`에만 존재 → 탭 닫으면 사라짐. v0.2 VLM_Verify는 이 패턴으로만 활성화. |

**의도적으로 사용하지 않은 것** (자세한 이유는 [`docs/README.md`](docs/README.md)):
- ❌ **YOLO / RT-DETR fine-tune** — labeled corpus 부족, v0.3 이후.
- ❌ **VLM 기반 primary detection** — 도면당 20,000+ HoughP 후보를 통째로 처리하기에 비효율적. expert CV cross-checking + page-type guard가 먼저 (v0.2). VLM은 `⊬` crop에 한정한 *re-checker*로만 도입.
- ❌ **DWG native ingest** — ODA / LibreDWG 의존성 결정 필요, v0.3.
- ❌ **외부 audit 의존성** — stdlib `sqlite3`만 사용해 설치 부담 0.

---

## 🛠 빌드 방법 — 3가지 경로

### 경로 1 · 로컬 개발 (가장 빠른 진입)

```bash
# 1. Clone
git clone https://github.com/gem-squared/gem2-cad-tel.git gem2-vision
cd gem2-vision

# 2. venv + dev 의존성 (uv 권장 — 일반 pip도 OK)
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
# (uv 없으면)  python3.12 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

# 3. Synthetic corpus baseline 생성 (12장)
.venv/bin/python scripts/build_corpus.py

# 4. (선택) Wikimedia Commons에서 corpus 확장 (~22장 PNG/JPG/PDF)
.venv/bin/python scripts/crawl_corpus.py --target 25

# 5. 전체 fast 테스트 (~97초; 145개; 10분짜리 corpus-wide smoke 제외)
.venv/bin/python -m pytest --ignore=tests/test_corpus_pipeline_smoke.py

# 6. Demo UI 실행 (http://localhost:8501)
.venv/bin/python -m streamlit run ui/app.py
```

요구사항: Python 3.11+, ~2GB RAM, `pdf2image`가 호출하는 Poppler (`brew install poppler` / `apt install poppler-utils`).

### 경로 2 · Docker (compose 한 줄 빌드)

```bash
cd deploy
docker compose up --build
# → http://localhost:8501
```

`deploy/docker-compose.yml`은 Streamlit 컨테이너 + Caddy reverse proxy를 함께 띄웁니다. `audit_data`는 named volume이라 `down`/`up` 사이에서 보존됩니다.

이미지에 다음이 포함됩니다: Python 3.12-slim + paddleocr + opencv-headless + 시스템 의존성(`libgl1`, `libglib2.0-0`) + 본 저장소 소스 + 50장 corpus.

### 경로 3 · VPS 라이브 배포 (Vultr / Debian / Ubuntu)

`cad-tel.gemsquared.ai`를 띄우는 데 사용한 4-command flow:

```bash
# 1. VPS에 SSH 키 등록 (한 번)
PUBKEY=$(cat ~/.ssh/id_ed25519_aio_deploy.pub)
ssh user@your.vps.ip "echo '$PUBKEY' >> ~/.ssh/authorized_keys"

# 2. 호스트 부트스트랩 (idempotent — Docker + ufw + 2GB swap + /opt/cad-tel/)
ssh -i ~/.ssh/id_ed25519_aio_deploy user@your.vps.ip 'bash -s' < deploy/bootstrap.sh

# 3. 배포 (도메인 없으면 IP only, 있으면 Let's Encrypt auto-TLS)
./deploy/deploy.sh user@your.vps.ip                              # IP 접근
./deploy/deploy.sh user@your.vps.ip --domain cad-tel.example.com # 도메인 + TLS

# 4. 자동 verify: HTTP 200 + body에 "CAD Trust Engine" 포함 확인 후 URL 출력
```

자세한 prerequisite / rollback / 트러블슈팅은 [`docs/DEPLOY.md`](docs/DEPLOY.md).

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

## 빌드 현황 (v0.1.6 — 태그 7개)

| 릴리스 | 일자 | 핵심 변경 |
|--------:|------|----------|
| **v0.1.0** | 2026-06-05 | 9-unit 파이프라인 (Ingest → Geometry → OCR → Symbols → Compose+Aggregate) + Streamlit 검수 UI + 12장 synthetic corpus + 테스트 53개 |
| **v0.1.1** | 2026-06-05 | Audit 서브시스템 도입: SQLite schema + AuditContext + 5-stage instrumentation + CLI(`list-runs`/`show-run`/`refusals`/`stats`) + Streamlit "Past Runs" 탭 + 테스트 91개 |
| **v0.1.2** | 2026-06-05 | Wikimedia Commons 크롤로 실제 도면 22장 확보 (License Discipline에 따라 27장 제외) + JPG ingest 지원 + 테스트 130개 + ingestable 실제 도면 32장 100% 파이프라인 성공 |
| **v0.1.3** | 2026-06-06 | License mapping 보정(exact-vs-prefix matcher)으로 public domain 도면 16장 추가 확보 → 총 50장 + Streamlit 도면 dropdown 우측 preview pane 추가 + 테스트 148개 |
| **v0.1.4** | 2026-06-06 | Vultr VPS 라이브 배포 (Docker + 호스트 Caddy 통합) → 공개 URL `cad-tel.gemsquared.ai` |
| **v0.1.5** | 2026-06-14 | Portfolio reframing — README tech-stack/build flow emphasis + BYO LLM-key 패턴 (UI sidebar scaffold + docs/DEPLOY.md secrets-section 재작성) |
| **v0.1.6** | 2026-06-14 | ash_pits 기본 데모 + 메인 패널 BYO 프롬프트 (상단 banner + 거부 영역 발생 시 post-run callout) + 라이브 배포 |

### 구체적 수치

- **5-stage 파이프라인**: Ingest → Geometry → OCR → Symbol → Compose+Aggregate
- **테스트 148개**, 모듈 9개 (fast 145개 + corpus-wide smoke 3개)
- **Corpus 50장** (synthetic 12 + Wikimedia 38, 모두 provenance + sha256 보유)
- **`main` 브랜치 commit 30+개**, **태그 5개**
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

## 문서 안내

| 파일 | 목적 |
|------|-----|
| [`docs/README.md`](docs/README.md) | 엔지니어링 thesis — 전체 TPMN 논증의 시작점 |
| [`docs/OUTPUT_CONTRACT.md`](docs/OUTPUT_CONTRACT.md) | 공식 contract 사양 + Measurement Policy 레퍼런스 |
| [`docs/CORPUS.md`](docs/CORPUS.md) | Corpus 라이선스 자세, 사용 source, 제외 정책 |
| [`docs/AUDIT.md`](docs/AUDIT.md) | Audit 서브시스템: schema, CLI 사용법, 예시 SQL 쿼리 |
| [`docs/DEMO_SCENARIOS.md`](docs/DEMO_SCENARIOS.md) | 한국 아파트 적산 refusal 데모 포함 5가지 시나리오 워크스루 |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | VPS 배포 가이드 (Docker + Caddy + rollback + 트러블슈팅) |
| `.gem-squared/work-plan/WP-ST-1.md` … `WP-ST-6.md` | TPMN work plan — unit별 A → B \| P contract와 결과 |

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

### MVP 0.2 — VLM_Verify on ⊬ crops only (BYO key)

`⊬` 태그가 붙은 crop에 한해 Qwen-VL / Claude vision을 *re-checker*로 호출합니다. 검수자가 자신의 API key를 UI sidebar에 직접 입력하는 **BYO (Bring-Your-Own) 패턴**으로, 서버 측 환경 변수에는 어떤 LLM API key도 저장되지 않습니다. VLM은 confirm / reject / abstain만 수행하며, `scale_anchor` policy를 절대 override 하지 않습니다.

### MVP 0.3 이후

- 한국 아파트형 synthetic generator
- 자동 label 생성 및 labeled corpus 구축
- YOLO / RT-DETR fine-tuning
- DWG / DXF native ingest
- cost aggregate taint propagation 고도화

---

## 진행 상황

- **v0.1.0** — 2026-06-05 · 9 unit · 53 tests · `Refusal Over Bluff` 도입
- **v0.1.1** — 2026-06-05 · 6 unit · 91 tests · Audit 서브시스템 (SQLite + CLI + Streamlit 탭)
- **v0.1.2** — 2026-06-05 · 6 unit · 130 tests · Wikimedia corpus (12 → 34장) + JPG ingest
- **v0.1.3** — 2026-06-06 · 4 unit · 148 tests · License 보정 (34 → 50장) + preview pane
- **v0.1.4** — 2026-06-06 · 6 unit · Vultr VPS 라이브 배포 (`cad-tel.gemsquared.ai`) · Docker + 호스트 Caddy 통합
- **v0.1.5** — 2026-06-14 · 3 unit · Portfolio 재포지셔닝 + BYO LLM-key 패턴 (README 기술스택/빌드 강조, `docs/DEPLOY.md` secrets-section 재작성, `ui/app.py` BYO sidebar scaffold)
- **v0.1.6** — 2026-06-14 · 3 unit · ash_pits Wikimedia 단면도를 기본 데모로 + 메인 패널 BYO 프롬프트 (상단 banner + 거부 영역 발생 시 post-run callout) + Vultr VPS 라이브 재배포

8개 work plan(`WP-ST-1` ~ `WP-ST-8`)이 `COMPLETED|SUCCESS` 상태이며, 일부는 `/archive-work` 대기 중.

---

*CAD Trust Engine Lite · gem-squared/gem2-cad-tel · Portfolio*
