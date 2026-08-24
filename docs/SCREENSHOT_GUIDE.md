# 포트폴리오 스크린샷 가이드

스크린샷은 결과 화면만 모으는 것이 아니라, **데이터 출처 → 데이터 엔지니어링 → 검색 평가 →
생성형 RAG → human review → 감사 추적 → 운영 재현성**의 흐름을 증명하도록 구성합니다.
핵심 8장과 선택 2장으로 구성합니다.

## 1. 원본 데이터 출처

- 대상: LLM-jp/NII 데이터셋 설명 페이지 또는 사용한 Hugging Face 미러의 dataset card
- 한 화면에 반드시 포함: 데이터셋 이름, Japanese patent 설명, 라이선스 `CC BY 4.0`, 제공 기관
- 브라우저 주소 표시줄도 포함
- 파일 다운로드 버튼만 크게 찍는 화면은 피합니다.

캡션 예시: `Source corpus — Japanese patent text from NII LLM-jp Corpus v4 (CC BY 4.0)`

## 2. 실제 일본 특허 원문 레코드

VS Code에서 [sample_record_ai_2020151725.txt](sample_record_ai_2020151725.txt)를 엽니다.

- 화면 위: `Source year: 2020`, `Publication kind: A`, `Document ID: 2020151725`
- 화면 중간: `【要約】`, `【課題】`, `【解決手段】`
- 가능한 경우 아래: `【特許請求の範囲】`, `【請求項1】`
- 오른쪽 미니맵과 불필요한 사이드바는 닫고 본문 18~25줄 정도만 보이게 합니다.

캡션 예시: `Raw Japanese patent evidence — abstract and claims preserved before chunking`

## 3. 데이터 품질 리포트 — 첫 번째 핵심 샷

명령:

```powershell
uv run patent-rag report
Start-Process .\artifacts\reports\data_quality.html
```

한 화면에 `DOCUMENTS WRITTEN`, `VALID JSON`, `AI DOCUMENTS`, `EVIDENCE CHUNKS`, 연도 분포,
section extraction coverage가 모두 보이게 브라우저를 90% 정도로 축소합니다.

캡션 예시: `Reproducible preprocessing — 46,794 records validated with section-level coverage`

## 4. 검색 품질 비교 — 두 번째 핵심 샷

명령:

```powershell
uv run patent-rag evaluate
Start-Process .\artifacts\reports\retrieval_evaluation.html
```

`BM25`, `DENSE`, `HYBRID`의 MRR@10과 Recall@5가 동시에 보이게 찍습니다. 숫자가 나온 뒤에만
촬영하고, 이것이 abstract-derived silver benchmark라는 캡션을 붙입니다.

캡션 예시: `Measured retrieval — BM25 vs multilingual dense search vs reciprocal-rank fusion`

### 선택 4A. 임베딩 문맥 품질 게이트

다음 리포트를 엽니다.

```powershell
Start-Process .\artifacts\reports\embedding_context_audit.html
```

`31,270 chunks`, `MAX OBSERVED 491`, `OVER LIMIT 0`, `QUALITY GATE PASS`와 토큰 분포가
한 화면에 보이게 찍습니다. 모델을 실데이터 전체에서 검증했다는 엔지니어링 근거로 좋지만,
대표 README 이미지는 검색 평가와 최종 RAG 화면을 우선합니다.

권장 파일명: `docs/screenshots/04a-embedding-context-audit.png`

캡션 예시: `Full-corpus context audit — all 31,270 passages fit the 512-token embedding window`

## 5. 최종 RAG 답변 — 대표 썸네일

웹 앱에서 아래 질문을 실행합니다.

`機械学習を用いたレーザ加工技術の課題と解決手段を比較してください`

- 상단의 `$0 · LOCAL ONLY`
- 질문
- `OLLAMA STRUCTURED / qwen3:1.7b` 또는 답변 모드
- 본문 안의 `[S1]`, `[S2]` 인용
- 아래 특허 번호 카드 2개 이상

이 다섯 요소가 한 화면에 보이도록 합니다. GitHub README의 첫 이미지로 가장 좋습니다.

### 선택 5A. Human-in-the-loop 승인

최종 RAG 답변 직후 review note를 짧게 입력하고 `APPROVE`를 누릅니다.

- `REVIEW / APPROVED`
- `CHAIN VALID`
- answer audit ID와 review audit ID
- 승인·수정요청·거절 버튼

이 네 요소가 답변 일부와 함께 보이게 찍습니다. `actor_id`는 실제 로그인 신원이 아니라 로컬
operator label이라는 안내도 유지합니다.

권장 파일명: `docs/screenshots/05b-human-review-approved.png`

캡션 예시: `Human-in-the-loop governance — the generated draft is approved through a separate chained audit event`

## 6. 근거 상세 보기

최종 화면에서 `[S1]`이나 source card를 눌러 원문 dialog를 엽니다.

- `JP 공개번호`, 연도, section명
- 일본어 원문
- `SOURCE PATH`

캡션 예시: `Citation traceability — every generated claim opens the exact local source passage`

## 7. Docker 운영 증거

PowerShell에서 다음을 실행한 결과를 찍습니다.

```powershell
docker compose ps
docker exec jp-patent-ollama ollama list
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

컨테이너 상태, `qwen3:1.7b`, API의 `retrieval_ready`, `$0 local-only`가 보이면 충분합니다.
모델 다운로드 진행률이나 2.5GB 파일 자체는 찍지 않습니다.

## 8. 감사 추적 화면

`http://127.0.0.1:8000/audit`를 엽니다.

- `CHAIN STATUS VALID`
- 검사된 event 수와 head hash
- `ANSWER_GENERATED`와 `REVIEW_DECISION` 행
- 작업자 label과 prompt 요약

개별 이벤트 JSON 전체보다 위 네 요소가 한 화면에 보이는 목록 화면을 우선합니다.
두 번째 보조 증거가 필요하면 `ANSWER_GENERATED` 상세 창을 열어 `model_input`의 system/user
prompt와 generation options가 함께 기록된 부분만 촬영합니다. 특허 원문 전체가 길게 펼쳐진
JSON 화면은 대표 이미지로 쓰지 않습니다.

권장 파일명: `docs/screenshots/08-audit-trail.png`

캡션 예시: `Tamper-evident local audit — prompts, evidence, drafts, and human decisions linked by SHA-256`

## 촬영하지 말아야 할 것

- `.env`, 토큰, 사용자 홈 경로 전체, Docker 내부 키
- 4만여 파일을 펼쳐 놓은 Explorer 화면
- 테스트가 실패한 터미널
- 설명 없이 코드만 가득한 화면
- 현재 드라이버 경고를 대표 이미지로 사용하기
