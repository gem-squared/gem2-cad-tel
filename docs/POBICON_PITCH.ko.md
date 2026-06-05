# 포비콘 지원 메시지 — CAD Trust Engine Lite v0.1

## 한 문장 정리

> 저는 CAD 도면 인식의 핵심을 **단순 검출 정확도가 아니라, 적산에 연결 가능한 신뢰 가능한 도면 해석**으로 봅니다.

---

## 본문

포비콘의 채용 공고와 자사 기술 페이지(창호 인식 / 습식·건식 벽 인식 / 골조 벽 인식 / 공간 인식 + 오토적산 2.0의 검증용 도면 + 객체 ID + 산출내역서)를 보고, 이 포지션의 본질은 **단순 Computer Vision 모델 개발이 아니라 CAD 도면을 실제로 읽고 산출내역서로 연결 가능하도록 구조화하는 도메인 특화 AI 파이프라인**이라고 이해했습니다.

그래서 지원 전에 직접 만들어본 MVP는 단순 검출 데모가 아니라 **CAD Trust Engine Lite** 입니다.
PNG/PDF 도면 한 장을 입력하면 벽체 / 문 / 창 / 공간 후보를 검출하는 것에 그치지 않고,
**각 객체마다 type / geometry / measurement 세 가지 epistemic 마크를 분리해 기록**하며,
신뢰할 수 없는 영역은 `refusals`로 명시적으로 거부하고, 검수자(`needs_human`)로 자동 라우팅합니다.

특히 다음 한 줄을 v0.1의 핵심 invariant로 만들었습니다.

> **scale_anchor 가 검출되지 않으면 어떤 mm 측정값도 emit하지 않는다.**

벽체 인식 결과가 산출내역서로 흘러가는 순간, **틀린 mm 값을 자신 있게 내는 것이 mm를 비워두는 것보다 훨씬 위험**합니다. 산출내역서 시스템은 거부(`⊥`)는 검수자에게 라우팅할 수 있지만, 확신에 찬 틀린 숫자는 시공 단계까지 잡아낼 수 없기 때문입니다. 그래서 Pydantic schema의 `model_validator` 레벨에서 이 정책을 **구조적으로 강제**했습니다 — 스키마 자체가 "scale_anchor 없는데 mm 값이 있는" EngineOutput을 생성할 수 없도록 거부합니다.

또한 객체 type 식별(이게 정말 벽인가?), geometry 식별(이 모양 / 위치가 맞나?), measurement 식별(mm 값이 신뢰할 만한가?) **세 가지를 별개의 epistemic claim으로 분리**했습니다. 엔진이 "이건 벽이다"라고 확신하면서도 "이게 4,200 mm 인지는 모른다"라고 말할 수 있어야, 적산 시스템과 결합 가능한 형태가 됩니다.

추가로, 규칙 기반 detector가 충분한 evidence(≥2 signals)를 모으지 못한 후보는 검출 결과로 emit되지 않고 **refusal_candidate**로 라우팅됩니다. 약한 신호를 confidence 점수로 압축해 흘려보내는 대신, "왜 거부했는가"를 자연어로 명시하는 구조입니다. 이것이 **Refusal Over Bluff** invariant입니다 — 적산 도메인에서 낮은 coverage는 받아들일 수 있지만, 확신에 찬 틀린 detection은 받아들일 수 없습니다.

v0.1 MVP는 OpenCV + PaddleOCR(ko+en) + 규칙 기반 detector + Pydantic 스키마 + Streamlit review UI로 구성된, **혼자 1주 내에 끝까지 만들 수 있는 작은 실행 가능한 demo**입니다. 의도적으로 작게 잡았습니다.

대신 v0.2 / v0.3 로드맵은 정확히 포비콘의 실제 production 문제와 정렬되어 있습니다 — Qwen-VL/InternVL VLM semantic verifier (⊬ 영역 재검증), 한국형 합성 도면 generator, 공개 데이터셋 자동 수집 + license ledger 파이프라인, DWG native ingest (ODA/LibreDWG), full cost-aggregate ⊬ taint 전파.

요약하자면, 제가 만든 것은 단순 detection 데모가 아닙니다.

> **검출 결과에 evidence + uncertainty + refusal + review path를 1급 시민으로 포함하는, 적산 시스템과 결합 가능한 형태의 trust engine** 입니다.

GitHub: (포트폴리오 repo URL)

---

## 한 줄 요약

> "Detector gives answers. CAD Trust Engine gives **answers, evidence, uncertainty, refusal, and review path** — and a 적산 시스템에 결합 가능한 형태로 출력합니다."
