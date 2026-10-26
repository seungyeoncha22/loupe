# 패션 추천 봇 v5 — 노드별 수정 내용

`fashion-bot-v5.yml`은 `python3 build_nodes.py && python3 assemble_v5.py`로 만든다.
운영 앱에는 아래 순서로 반영했다 (2026-10-22). 두 번째 줄을 빼먹으면 대표 상품·별칭 데이터가 `original/live.yml` 시점으로 되돌아간다.
```
cd ~/insta-crawler && python3 sync_dify_app.py ~/fashion-agent/fashion-bot-v5.yml
python3 export_brand_similarity.py --live
```
Dify 화면에서 직접 고칠 때는 아래 표의 파일 내용을 그대로 붙여 넣는다. `original/`은 v5 직전 운영 앱(되돌릴 때: `original/live.yml` 가져오기).

## 기존 노드 (내용 교체)

| 노드 이름 | 노드 id | 바꿀 것 | 파일 |
|---|---|---|---|
| 검색어 정리 | 1792044191923 | SYSTEM 프롬프트 전체, 모델 파라미터 temperature 0 | `search_prompt.txt` |
| 질문 분류 | classify | 분류 1·2의 설명, 지시(instruction) | `classify.json` |
| 검색 준비 | prep | 코드 전체 + 출력 변수 추가: `scope`(String) `scope_reply`(String) `include`(Array[String]) `brand_only`(String) `taste_query`(String) | `prep.py` |
| 후보 정리 | candidates | 코드 전체 + 입력 변수 추가: `docs_taste` = 취향 검색 / result, `include` = 검색 준비 / include + 출력 변수 추가: `n_candidates`(Number) `max_score`(Number) `empty_reply`(String) | `candidates.py` |
| 추천LLM | llm | SYSTEM 프롬프트의 4번 규칙 아래 한 줄 | `llm_prompt.txt` |
| 상품 정보 붙이기 | format | 코드 전체 + 입력 변수 추가: `brand_only` = 검색 준비 / brand_only + 출력 변수 추가: `proposed_count`(Number) `kept_count`(Number) `dropped_urls`(Array[String]) | `format.py` |

## 새 노드

| 노드 이름 | 종류 | 설정 | 연결 |
|---|---|---|---|
| 분류 보정 (route_fix) | Code | 입력 `query` = sys.query, 출력 `to_product`(String), 코드 `route_fix.py` | 질문 분류의 "브랜드 유사도" → 여기 |
| 상품 찾는 질문인가? (route_check) | IF/ELSE | `분류 보정.to_product` is `yes` | IF → 검색어 정리 / ELSE → 유사 브랜드 |
| 범위 확인 (scope_check) | IF/ELSE | `검색 준비.scope` is `ok` | 검색 준비 → 여기. IF → Knowledge Retrieval, 넓힌 검색, 취향 검색 / ELSE → Answer (범위 밖) |
| Answer (범위 밖) | Answer | `{{#prep.scope_reply#}}` | |
| 취향 검색 (좋아요 브랜드) (kr_taste) | Knowledge Retrieval | 넓힌 검색과 같은 설정(insta_brand_v2, 하이브리드 0.7/0.3, top 40, 0.3), 검색어 = 검색 준비 / taste_query | → 후보 정리 |
| 후보 있나? (empty_check) | IF/ELSE | `후보 정리.n_candidates` > `0` | 후보 정리 → 여기. IF → 추천LLM / ELSE → Answer (후보 없음) |
| Answer (후보 없음) | Answer | `{{#candidates.relax_note#}}{{#candidates.empty_reply#}}` | |

지울 연결: 질문 분류(브랜드 유사도) → 유사 브랜드, 검색 준비 → Knowledge Retrieval, 검색 준비 → 넓힌 검색, 후보 정리 → 추천LLM

## 주의
- temperature는 OpenRouter의 gpt-5-mini가 지원하지 않아 실제로는 무시된다 (지원 파라미터에 없음, 2026-10-22 확인).
  흔들림은 프롬프트 규칙과 검색 준비 코드(`_strip_unasked_styles`, `_with_styles`)로 줄였다.
- 데이터 줄(`BRAND_ALIASES = json.loads(...)` 등)은 매일 04:00 수집 뒤 `export_brand_similarity.py --live`가 운영 앱에서 직접 바꾼다.
  Dify에서 게시하지 않은 초안 수정이 있으면 그날은 건너뛴다.
- 웹사이트: `no_match` 답변(모르는 브랜드, 후보 0개)에 "비슷한 브랜드 웹에서 찾아보기" 버튼이 생겼다
  (`web/app/components/fashion/no-match-answer.tsx`). 반영하려면 웹을 다시 빌드·재시작해야 한다.
