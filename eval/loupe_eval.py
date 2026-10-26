"""loupe 패션 추천 봇(Dify 챗플로 "패션 추천 봇") 정량 평가.

  python3 loupe_eval.py make-tests            # tests.json 생성 (있으면 --force 로만 덮어씀)
  python3 loupe_eval.py run                   # 질문 → 링크 검사 → 좋아요 시뮬레이션 → 채점 → 요약
  python3 loupe_eval.py run --steps ask,links # 일부 단계만 (ask, links, likes)
  python3 loupe_eval.py cleanup --run-id ID   # 중간에 끊긴 실행의 테스트 기록 지우기

환경 변수
  DIFY_API_KEY          패션 추천 봇 앱 키 (app-...). web/.env.local 의 값
  DIFY_DATASET_API_KEY  지식베이스 API 키 (dataset-...). insta-crawler/.env 의 DIFY_API_KEY 값 (이름이 겹쳐서 따로 받는다)
  DIFY_DATASET_ID       기본 954e3b1b-... (insta_brand_v2)
  DIFY_API_URL          기본 http://localhost/v1
  DIFY_DB_CONTAINER     기본 docker-db_postgres-1 (테스트 실행 기록 삭제용)

사용자 데이터 분리
  - 질문마다 테스트 전용 user(loupe-eval-<run_id>-...)로 새 대화를 만든다. 실제 취향은 브라우저 localStorage
    (loupe:map:v1 → 입력 변수 taste)와 내 대화의 대화 변수(prefs)에만 있으므로 건드리지 않는다.
  - 끝나면 테스트 대화를 API로 지우고(메시지·대화 변수 삭제), API로 안 지워지는 workflow_runs /
    workflow_node_executions / end_users 행도 psql로 지운다 (explore_stats.py, brand_requests.py가 이 테이블을 읽기 때문).
    --keep-logs 를 주면 DB 행은 남긴다.
"""
import argparse
import csv
import hashlib
import html as html_lib
import json
import os
import re
import statistics
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
# 오프라인 재순위에 쓰는 '후보 정리' 코드. runs/before는 fashion-bot-v4.yml(운영과 같은 코드)로 돌렸다.
DSL = Path(os.environ.get("LOUPE_DSL", HERE.parent / "fashion-bot-v5.yml"))
BRANDS_JSON = HERE.parent / "web" / "public" / "brands.json"   # 워크플로 BRAND_TAGS와 같은 태그 (2026-10-22 확인)
API_URL = os.environ.get("DIFY_API_URL", "http://localhost/v1").rstrip("/")
DATASET_ID = os.environ.get("DIFY_DATASET_ID", "954e3b1b-82a5-4d06-8dfa-22690d87d16b")
OUT = HERE   # 결과 파일 폴더 (run --out 으로 바꾼다)
DB_CONTAINER = os.environ.get("DIFY_DB_CONTAINER", "docker-db_postgres-1")
TURN_TIMEOUT = 240   # 초. 질문 한 번의 전체 제한 (평소 7~70초)
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# 챗플로 노드 id (패션 추천 봇.yml)
N_CLASSIFY, N_PREP, N_KR, N_KR_BROAD = "classify", "prep", "1790664707557", "kr_broad"
N_CANDIDATES, N_LLM, N_FORMAT, N_EXTRAS = "candidates", "llm", "format", "extras"
ANSWER_NODES = ("answer", "answer_brand", "answer_rate", "answer_scope", "answer_empty")   # 뒤의 둘은 v5

# ---------------------------------------------------------------- 테스트 세트
# 치마는 DB에 있다 (크롤러 DOC_CATEGORY_MAP: 치마 → 하의, 2026-10-22 기준 스커트 상품 917개). 그래서 정상 질문에 넣었다.
# DB 밖 카테고리는 문서에서 빠지는 원피스·신발·가방·액세서리로 잡았다.
DEFAULT_TESTS = {
    "normal": [
        {"id": "n01", "query": "빈티지한 아우터 추천해줘", "style": "빈티지", "category": "아우터"},
        {"id": "n02", "query": "페미닌한 블라우스 보여줘", "style": "페미닌", "category": "상의"},
        {"id": "n03", "query": "스트릿 느낌 나는 와이드 팬츠", "style": "스트릿", "category": "하의"},
        {"id": "n04", "query": "미니멀한 니트 추천해줘", "style": "미니멀", "category": "상의"},
        {"id": "n05", "query": "레이어드하기 좋은 긴팔 티셔츠", "style": "레이어드", "category": "상의"},
        {"id": "n06", "query": "밀리터리 카고 팬츠 있어?", "style": "밀리터리", "category": "하의"},
        {"id": "n07", "query": "리본 달린 러블리한 상의", "style": "코케트(리본·레이스)", "category": "상의"},
        {"id": "n08", "query": "70년대 무드 부츠컷 데님", "style": "70s", "category": "하의"},
        {"id": "n09", "query": "웨스턴 스타일 자켓 찾아줘", "style": "웨스턴", "category": "아우터"},
        {"id": "n10", "query": "캐주얼한 후드 집업", "style": "캐주얼", "category": "아우터"},
        {"id": "n11", "query": "애슬레저 느낌 트랙 팬츠", "style": "애슬레저", "category": "하의"},
        {"id": "n12", "query": "데일리로 입기 좋은 셔츠", "style": "데일리", "category": "상의"},
        {"id": "n13", "query": "롱스커트 추천해줘", "category": "하의"},
        {"id": "n14", "query": "10만원 이하 가디건", "category": "아우터"},
        {"id": "n15", "query": "검정 레더 자켓", "category": "아우터"},
        {"id": "n16", "query": "로웨어 자켓 보여줘", "brand": "lowear.co.kr", "category": "아우터"},
        {"id": "n17", "query": "시즐 바지 추천해줘", "brand": "seezul.com", "category": "하의"},
        {"id": "n18", "query": "나이스고스트클럽 맨투맨", "brand": "niceghostclub.com", "category": "상의"},
        {"id": "n19", "query": "코이세이오 니트 있어?", "brand": "coyseio.com", "category": "상의"},
        {"id": "n20", "query": "seezul 빼고 빈티지 데님 팬츠", "style": "빈티지", "category": "하의", "exclude": "seezul.com"},
    ],
    # expect: refuse = 상품을 보여주지 않고 없다고 안내해야 함
    #         refuse_or_hedge = 없다고 하거나, 가까운 상품을 보여주되 다르다는 걸 밝혀야 함 (추천LLM 규칙 5)
    "ood": [
        {"id": "o01", "query": "화이트 스니커즈 추천해줘", "type": "category", "item": "신발", "expect": "refuse"},
        {"id": "o02", "query": "첼시 부츠 있어?", "type": "category", "item": "신발", "expect": "refuse"},
        {"id": "o03", "query": "하객룩 원피스 추천해줘", "type": "category", "item": "원피스", "expect": "refuse"},
        {"id": "o04", "query": "데일리 크로스백 보여줘", "type": "category", "item": "가방", "expect": "refuse"},
        {"id": "o05", "query": "겨울에 쓸 비니 추천해줘", "type": "category", "item": "모자", "expect": "refuse"},
        {"id": "o06", "query": "테크웨어 고어텍스 자켓", "type": "style", "item": "테크웨어(사전엔 있고 어느 브랜드에도 없는 태그)", "expect": "refuse_or_hedge"},
        {"id": "o07", "query": "올드머니 룩 캐시미어 코트", "type": "style", "item": "올드머니(사전엔 있고 어느 브랜드에도 없는 태그)", "expect": "refuse_or_hedge"},
        {"id": "o08", "query": "개량한복 저고리 상의 추천해줘", "type": "style", "item": "개량한복(사전 밖)", "expect": "refuse_or_hedge"},
        {"id": "o09", "query": "오르비엘 셔츠 추천해줘", "type": "brand", "item": "오르비엘", "expect": "refuse"},
        {"id": "o10", "query": "카일러스튜디오 바지 있어?", "type": "brand", "item": "카일러스튜디오", "expect": "refuse"},
    ],
    # 좋아요 시뮬레이션: 스타일 조건 없는 질문으로 취향 재순위만 보이게 한다
    "likes": {"query": "아우터 추천해줘", "style": "스트릿", "category": "아우터", "n_likes": 3},
}

REFUSAL_RE = re.compile(r"찾지 못했|없어요|없습니다|없네요|다루지 않|취급하지 않|준비되어 있지 않|아직 없|맞는 상품이 없|수집하지 않")
HEDGE_RE = re.compile(r"완전히 맞지|정확히 맞지|가장 가까운|가까운 상품|대신|다르지만|아니지만|비슷한 느낌|가깝")

# ---------------------------------------------------------------- 공통


def need_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"환경 변수 {name}가 없습니다 (파일 맨 위 설명 참고)")
    return value


def norm_url(url):
    url = str(url or "").strip().strip("<>\"'")
    return re.sub(r"^https?://(www\.)?", "", url).rstrip("/")


def domain_of(url):
    m = re.match(r"https?://([^/]+)", str(url or "").strip())
    return re.sub(r"^www\.", "", m.group(1).lower()) if m else ""


def jdump(x):
    return json.dumps(x, ensure_ascii=False)


# ---------------------------------------------------------------- 상품 DB (Dify 지식베이스 문단)

def load_db(refresh=False):
    """insta_brand_v2의 활성 문단 전체를 {norm_url: 상품}으로. 하루 지난 캐시는 다시 받는다 (수집기는 매일 04:00)."""
    cache = HERE / "db_cache.json"
    if cache.exists() and not refresh and time.time() - cache.stat().st_mtime < 86400:
        return json.loads(cache.read_text())
    key = need_env("DIFY_DATASET_API_KEY")
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {key}"
    docs = s.get(f"{API_URL}/datasets/{DATASET_ID}/documents", params={"limit": 100}, timeout=60).json()["data"]
    db = {}
    for doc in docs:
        page = 1
        while True:
            r = s.get(f"{API_URL}/datasets/{DATASET_ID}/documents/{doc['id']}/segments",
                      params={"page": page, "limit": 100}, timeout=60).json()
            for seg in r["data"]:
                if not seg.get("enabled", True):
                    continue
                f = dict(re.findall(r"^(브랜드|상품명|카테고리|가격|URL):\s?(.*)$", seg["content"], re.M))
                if f.get("URL"):
                    db[norm_url(f["URL"])] = {"segment_id": seg["id"], "document_id": doc["id"], "url": f["URL"].strip(),
                                              "domain": domain_of(f["URL"]), "brand": f.get("브랜드", ""),
                                              "name": f.get("상품명", ""), "category": f.get("카테고리", "")}
            if not r.get("has_more"):
                break
            page += 1
    cache.write_text(jdump(db))
    print(f"상품 DB {len(db)}개 (문서 {len(docs)}개)")
    return db


def brand_products():
    """web/public/brands.json의 브랜드 대표 상품 url. '브랜드 유사도' 답변이 이 데이터(코드 노드에 박힌 사본)를 쓴다."""
    return {norm_url(p["url"]) for b in json.loads(BRANDS_JSON.read_text())["brands"].values() for p in b.get("products") or []}


def brand_tags():
    return {d: b.get("tags") or [] for d, b in json.loads(BRANDS_JSON.read_text())["brands"].items()}


# ---------------------------------------------------------------- Dify 호출

class Dify:
    def __init__(self, run_id):
        self.key = need_env("DIFY_API_KEY")
        self.run_id = run_id
        self.convs = []   # (user, conversation_id) — 끝나고 지운다
        self.users = set()

    def user(self, tag):
        u = f"loupe-eval-{self.run_id}-{tag}"
        self.users.add(u)
        return u

    def ask(self, query, user, conversation_id="", inputs=None, retries=2):
        """실행 오류(OpenRouter 스트림 끊김 등)면 retries번까지 다시 부른다. 실패한 실행은 대화 변수를 바꾸지 않는다
        (변수 할당 노드가 끝에 있어서), 대화 안에서 다시 보내도 평가가 두 번 들어가지 않는다."""
        for attempt in range(retries + 1):
            out = self._ask(query, user, conversation_id, inputs)
            out["attempts"] = attempt + 1
            if not out["error"] or out["error"].startswith("HTTP 4"):
                break
            time.sleep(3)
        return out

    def _ask(self, query, user, conversation_id="", inputs=None):
        """스트리밍으로 부르고 node_finished 이벤트의 노드 출력을 모은다 (Dify 1.17.1에서 출력이 실려 오는 것 확인)."""
        body = {"inputs": inputs or {}, "query": query, "response_mode": "streaming", "user": user,
                "conversation_id": conversation_id}
        t0, nodes, out = time.time(), {}, {"conversation_id": conversation_id, "error": ""}
        try:
            with requests.post(f"{API_URL}/chat-messages", json=body, stream=True, timeout=(10, 300),
                               headers={"Authorization": f"Bearer {self.key}"}) as r:
                if r.status_code != 200:
                    out["error"] = f"HTTP {r.status_code} {r.text[:200]}"
                for line in r.iter_lines(decode_unicode=True):
                    # Dify는 기다리는 동안 ping을 보내서 읽기 타임아웃이 안 걸린다. 워크플로가 시작도 안 된 채
                    # 연결만 붙잡힌 일이 있어서(2026-10-22 o07, 22분) 한 턴 전체 시간을 따로 제한한다
                    if time.time() - t0 > TURN_TIMEOUT:
                        out["error"] = f"timeout: {TURN_TIMEOUT}초 안에 답변이 끝나지 않음"
                        break
                    if not line or not line.startswith("data:"):
                        continue
                    ev = json.loads(line[5:])
                    if ev.get("conversation_id"):
                        out["conversation_id"] = ev["conversation_id"]
                    if ev["event"] == "workflow_started":
                        out["workflow_run_id"] = ev.get("workflow_run_id")
                    elif ev["event"] == "node_finished":
                        d = ev["data"]
                        nodes[d["node_id"]] = d.get("outputs") or {}
                        if d.get("status") != "succeeded":
                            out["error"] = f"{d['node_id']}: {d.get('error')}"
                    elif ev["event"] == "error":
                        out["error"] = ev.get("message", "error")
        except requests.RequestException as e:
            out["error"] = str(e)
        if out["conversation_id"] and (user, out["conversation_id"]) not in self.convs:
            self.convs.append((user, out["conversation_id"]))
        out["nodes"], out["elapsed"] = nodes, round(time.time() - t0, 1)
        return out

    def cleanup(self, keep_logs=False):
        for user, cid in self.convs:
            r = requests.delete(f"{API_URL}/conversations/{cid}", json={"user": user},
                                headers={"Authorization": f"Bearer {self.key}"}, timeout=30)
            if r.status_code not in (200, 204, 404):
                print(f"  대화 삭제 실패 {cid}: {r.status_code} {r.text[:100]}")
        print(f"테스트 대화 {len(self.convs)}개 삭제")
        if not keep_logs:
            purge_logs(self.run_id)


def purge_logs(run_id):
    """이 run_id의 테스트 user가 남긴 workflow_runs / node_executions / app_logs / end_users 행을 지운다."""
    if not re.fullmatch(r"[0-9a-z]{6,32}", run_id):
        sys.exit("run_id 형식이 이상합니다")
    pattern = f"loupe-eval-{run_id}-%"
    sql = f"""
begin;
create temp table r as select w.id from workflow_runs w join end_users u on u.id = w.created_by
  where u.session_id like '{pattern}';
delete from workflow_node_execution_offload where node_execution_id in
  (select id from workflow_node_executions where workflow_run_id in (select id from r));
delete from workflow_node_executions where workflow_run_id in (select id from r);
delete from workflow_app_logs where workflow_run_id in (select id from r);
delete from workflow_runs where id in (select id from r);
delete from end_users where session_id like '{pattern}';
commit;"""
    p = subprocess.run(["docker", "exec", "-i", DB_CONTAINER, "psql", "-U", "postgres", "-d", "dify", "-v", "ON_ERROR_STOP=1"],
                       input=sql, capture_output=True, text=True)
    if p.returncode != 0:
        print(f"  실행 기록 삭제 실패 (직접 확인 필요): {p.stderr.strip()[:300]}")
    else:
        counts = re.findall(r"DELETE (\d+)", p.stdout)
        print(f"Dify DB 테스트 기록 삭제: offload/node_exec/app_logs/runs/end_users = {'/'.join(counts)}")


# ---------------------------------------------------------------- 응답 해석

UI_RE = re.compile(r"<!--fashion-ui (.*?) -->", re.S)
LINK_RE = re.compile(r"(!?)\[[^\]]*\]\((https?://[^)\s]+)\)")


def parse_turn(res, db):
    n = res["nodes"]
    answer = next((n[a].get("answer", "") for a in ANSWER_NODES if a in n), "")
    visible = re.sub(r"<button[^>]*>.*?</button>", "", UI_RE.sub("", answer), flags=re.S)
    llm_items = []
    m = re.search(r"\{.*\}", (n.get(N_LLM) or {}).get("text", "") or "", re.S)
    if m:
        try:
            llm_items = [it for it in (json.loads(m.group(0)).get("items") or []) if isinstance(it, dict)]
        except (json.JSONDecodeError, AttributeError):
            pass
    proposed = [str(it.get("url") or "").strip() for it in llm_items]
    cands = [c.get("url", "") for c in (n.get(N_CANDIDATES) or {}).get("candidates") or []]
    fmt = n.get(N_FORMAT) or {}
    kept = [x["url"] for x in fmt.get("shown_items") or []]
    # 탐색 추천(3번에 1번)까지 포함한 실제 노출 상품은 extras.last_shown
    final = [x["url"] for x in (n.get(N_EXTRAS) or {}).get("last_shown") or []] or kept
    cand_keys = {norm_url(u) for u in cands}
    if "dropped_urls" in fmt:   # format 노드를 고친 뒤에는 노드가 낸 값을 쓴다
        dropped = list(fmt["dropped_urls"])
    else:
        dropped = [u for u in proposed if norm_url(u) not in cand_keys]
    answer_links = [u for bang, u in LINK_RE.findall(answer) if not bang]
    for blk in UI_RE.findall(answer):
        try:
            answer_links += [c.get("url") for c in json.loads(blk).get("cards") or [] if c.get("url")]
        except json.JSONDecodeError:
            pass

    def top_score(node):
        scores = [float((d.get("metadata") or {}).get("score") or 0) for d in (n.get(node) or {}).get("result") or []]
        return round(max(scores), 4) if scores else 0.0

    return {
        "route": (n.get(N_CLASSIFY) or {}).get("class_name", "")[:20],
        # 상품 추천 경로로 갔는지 (v5는 '브랜드 유사도'로 분류돼도 분류 보정 노드가 상품 추천으로 돌릴 수 있다)
        "product_route": N_PREP in n,
        "scope": (n.get(N_PREP) or {}).get("scope", ""),
        "include": (n.get(N_PREP) or {}).get("include") or [],
        "search_query": (n.get(N_PREP) or {}).get("search_query", ""),
        "search_llm": (n.get("1792044191923") or {}).get("text", ""),   # '검색어 정리' LLM 원문 (제외 브랜드 오판 진단용)
        "exclude": (n.get(N_PREP) or {}).get("exclude") or [],
        "category": (n.get(N_PREP) or {}).get("category", ""),
        "answer": answer, "visible": visible,
        "proposed": proposed, "candidates": cands, "kept": kept, "final": final, "dropped": dropped,
        "dropped_not_in_db": [u for u in dropped if norm_url(u) not in db],
        "dropped_in_db": [u for u in dropped if norm_url(u) in db],
        "proposed_count": fmt.get("proposed_count", len(proposed)), "kept_count": fmt.get("kept_count", len(kept)),
        "answer_links": list(dict.fromkeys(answer_links)),
        "max_score": top_score(N_KR), "max_score_broad": top_score(N_KR_BROAD),
        "n_candidates": len(cands), "summary": (n.get(N_CANDIDATES) or {}).get("summary", ""),
    }


# ---------------------------------------------------------------- 1~2. 질문 실행

def step_ask(tests, dify, db, workers):
    cases = [dict(t, group="normal") for t in tests["normal"]] + [dict(t, group="ood") for t in tests["ood"]]

    def one(t):
        res = dify.ask(t["query"], dify.user(t["id"]))   # 질문마다 새 대화 (앞 질문 조건이 이어지지 않게)
        return t, res, parse_turn(res, db)

    rows = []
    with ThreadPoolExecutor(workers) as ex:
        for t, res, p in ex.map(one, cases):
            print(f"  {t['id']} {p['route'][:8]:<8} 후보 {p['n_candidates']:>2} 제안 {len(p['proposed'])} 최종 {len(p['final'])}"
                  f" 버림 {len(p['dropped'])} 최고유사도 {p['max_score']:.3f} {res['elapsed']}s {res['error']}")
            rows.append({"test": t, "res": {k: v for k, v in res.items() if k != "nodes"}, "p": p})
    with open(OUT / "results.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "group", "query", "route", "search_query", "category", "exclude", "answer_text", "llm_proposed_urls",
                    "kept_urls", "final_urls", "final_product_ids", "dropped_urls", "dropped_not_in_db",
                    "proposed_count", "kept_count", "max_score", "max_score_broad", "n_candidates", "elapsed", "error"])
        for r in rows:
            t, p = r["test"], r["p"]
            ids = [(db.get(norm_url(u)) or {}).get("segment_id", "NOT_IN_DB") for u in p["final"]]
            w.writerow([t["id"], t["group"], t["query"], p["route"], p["search_query"], p["category"], jdump(p.get("exclude", [])),
                        p["visible"].strip(),
                        jdump(p["proposed"]), jdump(p["kept"]), jdump(p["final"]), jdump(ids), jdump(p["dropped"]),
                        jdump(p["dropped_not_in_db"]), p["proposed_count"], p["kept_count"], p["max_score"],
                        p["max_score_broad"], p["n_candidates"], r["res"]["elapsed"], r["res"]["error"]])
    (OUT / "results_raw.json").write_text(jdump(rows))
    return rows


# ---------------------------------------------------------------- 3. 링크 검사

def _visible_text(page):
    page = re.sub(r"<!--.*?-->|<(script|style|noscript)\b.*?</\1>", " ", page, flags=re.S | re.I)
    # 카페24 템플릿은 재고 있는 상품에도 "SOLD OUT"·"품절" 요소를 displaynone으로 숨겨 둔다 (lowear, keira에서 확인)
    page = re.sub(r"<(\w+)\b[^>]*(?:displaynone|display\s*:\s*none)[^>]*>.*?</\1>", " ", page, flags=re.S | re.I)
    return html_lib.unescape(re.sub(r"<[^>]+>", " ", page))


DELETED_RE = re.compile(r"삭제된 상품|존재하지 않는 상품|판매(?:가)? 종료된 상품|상품이 존재하지 않|찾으시는 페이지가 없")
SOLDOUT_TEXT_RE = re.compile(r"품절된 상품|일시\s*품절|SOLD\s*OUT", re.I)


def check_link(url):
    out = {"url": url, "status": None, "final_url": "", "jsonld": "", "raw_soldout_word": False,
           "deleted": False, "soldout": False, "ok": False, "note": ""}
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"}, timeout=20)
    except requests.RequestException as e:
        out["note"] = f"요청 실패: {e.__class__.__name__}"
        return out
    page = r.text
    out["status"], out["final_url"] = r.status_code, r.url
    out["raw_soldout_word"] = bool(re.search(r"품절|SOLD\s*OUT", page, re.I))   # 참고용 (숨김 요소 때문에 오탐 많음)
    avail = re.findall(r'"availability"\s*:\s*"([^"]+)"', page)
    out["jsonld"] = ",".join(sorted({a.rsplit("/", 1)[-1] for a in avail}))
    out["deleted"] = bool(DELETED_RE.search(page)) or r.status_code in (404, 410)
    if avail:   # 크롤러와 같은 규칙: 옵션이 하나라도 재고 있으면 판매 중
        out["soldout"] = all("OutOfStock" in a for a in avail)
    else:
        out["soldout"] = bool(SOLDOUT_TEXT_RE.search(_visible_text(page)))
        out["note"] = "JSON-LD 없음 → 화면 문구로 판정"
    if norm_url(r.url) != norm_url(url) and domain_of(r.url) == domain_of(url) and urlparse_path(r.url) in ("", "/", "/index.html"):
        out["deleted"], out["note"] = True, "첫 화면으로 리다이렉트"
    out["ok"] = r.status_code == 200 and not out["deleted"] and not out["soldout"]
    return out


def urlparse_path(url):
    return re.sub(r"^https?://[^/]+", "", url).split("?")[0]


def step_links(rows):
    urls = list(dict.fromkeys(u for r in rows for u in r["p"]["final"]))
    with ThreadPoolExecutor(6) as ex:
        checks = list(ex.map(check_link, urls))
    with open(OUT / "links.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(checks[0]) if checks else ["url"])
        w.writeheader()
        w.writerows(checks)
    bad = [c for c in checks if not c["ok"]]
    for c in bad:
        print(f"  ✗ {c['status']} 삭제={c['deleted']} 품절={c['soldout']} {c['url']} {c['note']}")
    return checks


# ---------------------------------------------------------------- 4. 좋아요 시뮬레이션

def _like_targets(db, tags, style, category, n, avoid):
    """좋아할 상품: 그 스타일 태그를 가진 브랜드의 같은 카테고리 상품, 브랜드가 겹치지 않게 n개."""
    picked, brands = [], set()
    for key in sorted(db):
        p = db[key]
        if p["domain"] in brands or style not in tags.get(p["domain"], []) or p["category"] != category or key in avoid:
            continue
        picked.append(p)
        brands.add(p["domain"])
        if len(picked) == n:
            break
    return picked


def taste_input(liked, style):
    """web/components/loupe/map-store.ts tasteInput과 같은 형식: 좋아요 상품마다 브랜드 +1, 그 상품 스타일 +0.5."""
    brands, tag_scores = {}, {}
    for p in liked:
        brands[p["domain"]] = min(3, brands.get(p["domain"], 0) + 1)
        tag_scores[style] = min(3, tag_scores.get(style, 0) + 0.5)
    return jdump({"brands": brands, "tags": tag_scores, "liked_urls": [p["url"] for p in liked]})


def _ranking_stats(urls, style, liked_domains, tags):
    """상위 10개 중 선호 스타일 브랜드·좋아요 브랜드 비율, 좋아요 브랜드의 평균 순위(후보에 없으면 13위로 친다).
    후보는 브랜드당 1개라 비율은 잘 안 움직이므로 순위도 같이 본다."""
    top = urls[:10]
    ranks = {}
    for i, u in enumerate(urls, 1):
        ranks.setdefault(domain_of(u), i)
    return {"n": len(top), "style_ratio": sum(style in tags.get(domain_of(u), []) for u in top) / max(len(top), 1),
            "brand_ratio": sum(domain_of(u) in liked_domains for u in top) / max(len(top), 1),
            "liked_rank": statistics.mean(ranks.get(d, 13) for d in liked_domains) if liked_domains else 0.0}


def overlap(a, b):
    a, b = [norm_url(u) for u in a[:10]], [norm_url(u) for u in b[:10]]
    return len(set(a) & set(b)) / max(len(a), len(b), 1)


def offline_rerank(nodes, taste):
    """같은 검색 결과(본 검색·넓힌 검색)로 '후보 정리' 노드 코드를 로컬에서 다시 돌린다. 검색어 LLM의 흔들림 없이
    취향 가산점만의 효과를 본다. 반환: 후보 url 순서."""
    import yaml
    node = next(n for n in yaml.safe_load(DSL.read_text())["workflow"]["graph"]["nodes"] if n["id"] == N_CANDIDATES)
    ns = {}
    exec(node["data"]["code"], ns)
    prep = nodes.get(N_PREP) or {}
    kwargs = dict(docs=(nodes.get(N_KR) or {}).get("result") or [], docs_broad=(nodes.get(N_KR_BROAD) or {}).get("result") or [],
                  exclude=prep.get("exclude") or [], exclude_urls=prep.get("exclude_urls") or [], styles=prep.get("styles") or [],
                  category=prep.get("category") or "", prefs={}, taste=taste, item_index={},
                  # v5 입력. 취향 검색 결과는 좋아요 없이 돌린 실행의 것이라 본 검색과 같다 → 여기서는 가산점 효과만 본다
                  docs_taste=(nodes.get("kr_taste") or {}).get("result") or [], include=prep.get("include") or [])
    params = ns["main"].__code__.co_varnames[:ns["main"].__code__.co_argcount]
    out = ns["main"](**{k: v for k, v in kwargs.items() if k in params})
    return [c["url"] for c in out["candidates"]]


def _mean_stats(stats):
    return {k: statistics.mean(s[k] for s in stats) for k in stats[0]}


def step_likes(cfg, dify, db, mode, repeats):
    """상위 10개 = '후보 정리' 노드가 취향 점수까지 반영해 정렬한 후보(최대 12개)의 앞 10개.
    화면에는 이 중 추천LLM이 고른 최대 3개만 나오므로, 재순위 효과는 후보 순서로 잰다.
    '검색어 정리' LLM이 매번 조금씩 다른 검색어를 써서 순위가 원래 흔들리므로, 좋아요 없이 한 번 더 돌린 값(noise)과
    비교하고 repeats번 반복해 평균낸다. 좋아요할 상품은 첫 회에 정해 매회 같게 쓴다."""
    tags, q, style = brand_tags(), cfg["query"], cfg["style"]
    liked, runs = None, []
    for i in range(repeats):
        before_raw = dify.ask(q, dify.user(f"like{i}-before"))
        before = parse_turn(before_raw, db)
        noise_raw = dify.ask(q, dify.user(f"like{i}-noise"))
        noise = parse_turn(noise_raw, db)
        if mode == "taste":
            liked = liked or _like_targets(db, tags, style, cfg["category"], cfg["n_likes"], set())
            after_raw = dify.ask(q, dify.user(f"like{i}-after"), inputs={"taste": taste_input(liked, style)})
            after = parse_turn(after_raw, db)
            excluded = 0
            if before_raw["error"] or noise_raw["error"] or after_raw["error"]:
                print(f"  {i + 1}/{repeats}: 실행 오류로 이 회차는 뺌")
                continue
        else:
            liked, after, excluded = _like_in_chat(dify, db, tags, q, style, cfg["n_likes"], f"like{i}-chat")
        domains = {p["domain"] for p in liked}
        run = {"before_top10": before["candidates"][:10], "after_top10": after["candidates"][:10],
               "noise_top10": noise["candidates"][:10], "after_shown": after["final"],
               "search_query": [before["search_query"], noise["search_query"], after["search_query"]],
               "overlap_after": overlap(before["candidates"], after["candidates"]),
               "overlap_noise": overlap(before["candidates"], noise["candidates"]),
               "before": _ranking_stats(before["candidates"], style, domains, tags),
               "after": _ranking_stats(after["candidates"], style, domains, tags),
               "noise": _ranking_stats(noise["candidates"], style, domains, tags), "followup_excluded": excluded}
        # 같은 검색 결과에 취향만 얹었을 때 (taste 형식으로 넣는다. chat 모드도 rate 노드 점수와 같은 규칙)
        off_before = offline_rerank(before_raw["nodes"], "")
        off_after = offline_rerank(before_raw["nodes"], taste_input(liked, style))
        run["offline"] = {"before_top10": off_before[:10], "after_top10": off_after[:10],
                          "overlap": overlap(off_before, off_after),
                          "before": _ranking_stats(off_before, style, domains, tags),
                          "after": _ranking_stats(off_after, style, domains, tags)}
        runs.append(run)
        print(f"  {i + 1}/{repeats}: 겹침 {run['overlap_after']:.0%} (재실행 {run['overlap_noise']:.0%}),"
              f" 좋아요 브랜드 평균 순위 {run['before']['liked_rank']:.1f} → {run['after']['liked_rank']:.1f}"
              f" (재실행 {run['noise']['liked_rank']:.1f}) / 검색 고정: 겹침 {run['offline']['overlap']:.0%},"
              f" 순위 {run['offline']['before']['liked_rank']:.1f} → {run['offline']['after']['liked_rank']:.1f}")
    if not runs:
        print("  좋아요 시뮬레이션: 성공한 회차 없음")
        return None
    res = {"mode": mode, "query": q, "style": style, "repeats": len(runs), "liked": [p["url"] for p in liked],
           "overlap_after": statistics.mean(r["overlap_after"] for r in runs),
           "overlap_noise": statistics.mean(r["overlap_noise"] for r in runs),
           "before": _mean_stats([r["before"] for r in runs]), "after": _mean_stats([r["after"] for r in runs]),
           "noise": _mean_stats([r["noise"] for r in runs]),
           "offline": {"overlap": statistics.mean(r["offline"]["overlap"] for r in runs),
                       "before": _mean_stats([r["offline"]["before"] for r in runs]),
                       "after": _mean_stats([r["offline"]["after"] for r in runs])}, "runs": runs}
    (OUT / "likes.json").write_text(jdump(res))
    return res


def _like_in_chat(dify, db, tags, q, style, n_likes, tag, max_rounds=6):
    """웹사이트 👍 버튼과 같은 메시지("1번 좋아 #코드")로 한 대화 안에서 평가한 뒤 같은 질문을 다시 한다.
    보여준 상품 중 그 스타일 브랜드 상품만 좋아요하고, 모자라면 '다음 추천 보기'로 더 받는다."""
    user = dify.user(tag)
    turn = dify.ask(q, user)
    cid, liked = turn["conversation_id"], []
    for _ in range(max_rounds):
        shown = (turn["nodes"].get(N_EXTRAS) or {}).get("last_shown") or []
        for it in shown:
            if len(liked) < n_likes and style in tags.get(it.get("domain", ""), []) and it["url"] not in [p["url"] for p in liked]:
                dify.ask(f"{it['n']}번 좋아 #{it['code']}", user, cid)
                liked.append(db.get(norm_url(it["url"])) or {"url": it["url"], "domain": it.get("domain", "")})
        if len(liked) >= n_likes:
            break
        turn = dify.ask("다음 추천 보기", user, cid)
    again = dify.ask(q, user, cid)
    excluded = len((again["nodes"].get(N_PREP) or {}).get("exclude_urls") or [])
    if excluded:
        print(f"  주의: 재질문이 후속 질문으로 처리되어 이미 본 상품 {excluded}개가 빠졌습니다 (겹침 비율이 낮게 나옴)")
    return liked, parse_turn(again, db), excluded


# ---------------------------------------------------------------- 5. DB 밖 질문 채점

def grade(row, db):
    t, p = row["test"], row["p"]
    links = list(dict.fromkeys(p["answer_links"] + p["final"]))
    # "이 스타일 브랜드 더 보기"의 수집 브랜드 홈 링크(https://coyseio.com)는 상품이 아니므로 뺀다
    homes = {d for d in brand_tags()}
    missing = [u for u in links if norm_url(u) not in db
               and not (domain_of(u) in homes and urlparse_path(u) in ("", "/"))]
    # brands.json 대표 상품에는 있는데 DB에서 빠진 것 = 지어낸 게 아니라 대표 상품 데이터가 오래된 것 (품절·삭제)
    reps = brand_products()
    stale = [u for u in missing if norm_url(u) in reps]
    invented = [u for u in missing if norm_url(u) not in reps]
    shown = len(p["final"])
    refused = bool(REFUSAL_RE.search(p["visible"]))
    hedged = bool(HEDGE_RE.search(p["visible"]))
    brand_claim = False
    if t.get("type") == "brand" and shown:   # 없는 브랜드 이름을 대며 상품을 보여주면 지어낸 것으로 본다
        brand_claim = re.sub(r"\s", "", t["item"]) in re.sub(r"\s", "", p["visible"])
    if t.get("expect") == "refuse":
        ok = shown == 0 and refused
    else:
        ok = (shown == 0 and refused) or (shown > 0 and (hedged or refused))
    return {"invented_urls": invented, "stale_urls": stale, "brand_claim": brand_claim, "shown": shown, "refused": refused,
            "hedged": hedged, "appropriate": ok and not invented and not brand_claim}


# ---------------------------------------------------------------- 유사도 기준값

def is_product(p):
    """검색까지 간 상품 추천 질문인지 (runs/before 결과에는 product_route가 없어서 분류 이름으로 본다)."""
    return p.get("product_route", p["route"].startswith("상품"))


def threshold_report(rows):
    """정상/DB 밖 질문의 '본 검색' 최고 유사도 분포와 후보 기준값.
    Dify 하이브리드 점수(벡터 0.7 + 키워드 0.3)이고 검색어는 사용자 원문이 아니라 '검색어 정리' LLM이 쓴 search_query다."""
    # 점수 0 = 검색 결과 0건 (유사도와 무관한 이상 실행)이라 뺀다
    def scores(group):
        return sorted(r["p"]["max_score"] for r in rows
                      if r["test"]["group"] == group and is_product(r["p"]) and r["p"]["max_score"] > 0)
    pos, neg = scores("normal"), scores("ood")
    if not pos or not neg:
        return {"pos": pos, "neg": neg, "best": None}
    best = None
    for t in sorted(set(pos + neg)):
        tpr = sum(s >= t for s in pos) / len(pos)   # 통과해야 할 정상 질문 중 통과
        fpr = sum(s >= t for s in neg) / len(neg)   # 막아야 할 DB 밖 질문 중 통과
        if best is None or tpr - fpr > best[1] - best[2]:
            best = (t, tpr, fpr)
    q = statistics.quantiles(pos, n=20) if len(pos) >= 2 else pos

    def desc(xs):
        return f"min {xs[0]:.3f} / 중앙 {statistics.median(xs):.3f} / max {xs[-1]:.3f} (n={len(xs)})"
    return {"pos": pos, "neg": neg, "pos_desc": desc(pos), "neg_desc": desc(neg), "best": best, "pos_p5": q[0]}


# ---------------------------------------------------------------- 6. 요약

def pct(a, b):
    return f"{a / b:.0%} ({a}/{b})" if b else "측정 안 함"


def summarize(rows, links, likes, args, quiet=False):
    lines = ["| 성공 기준 | 목표값 | 측정 결과 |", "|---|---|---|"]
    failed = [r["test"]["id"] for r in rows if r["res"]["error"]]
    rows = [r for r in rows if not r["res"]["error"]]   # 재시도해도 실패한 실행은 채점에서 뺀다
    if failed:
        lines.append(f"| (주의) 실행 오류로 채점에서 뺀 질문 | 0 | {len(failed)} {failed} |")
    if links is not None:
        ok = sum(c["ok"] for c in links)
        detail = f"삭제·404 {sum(c['deleted'] for c in links)}, 품절 {sum(c['soldout'] for c in links)}, 요청 실패 {sum(c['status'] is None for c in links)}"
        lines.append(f"| 링크 정상 비율 (200·판매 중) | 100% | {pct(ok, len(links))} — {detail} |")
    if rows:
        prop = sum(len(r["p"]["proposed"]) for r in rows)
        drop = sum(len(r["p"]["dropped"]) for r in rows)
        fake = sum(len(r["p"]["dropped_not_in_db"]) for r in rows)
        lines.append(f"| LLM 제안 URL 중 버려진 비율 | 낮을수록 좋음 (참고) | {pct(drop, prop)} — DB에 아예 없음 {fake}, "
                     f"DB엔 있지만 이번 후보 밖 {drop - fake} |")
    if likes:
        lines.append(f"| 좋아요 후 상위 10개 변화량 (1−겹침) | 좋아요 없는 재실행보다 커야 함 | "
                     f"{1 - likes['overlap_after']:.0%} (좋아요 없는 재실행 {1 - likes['overlap_noise']:.0%}) |")
        b, a, nz = likes["before"], likes["after"], likes["noise"]
        lines.append(f"| 선호 태그({likes['style']}) 비율 변화 | 증가 | {b['style_ratio']:.0%} → {a['style_ratio']:.0%}"
                     f" (재실행 {nz['style_ratio']:.0%}) |")
        lines.append(f"| 좋아요 브랜드 비율 변화 | 증가 | {b['brand_ratio']:.0%} → {a['brand_ratio']:.0%} (재실행 {nz['brand_ratio']:.0%}) |")
        lines.append(f"| 좋아요 브랜드 평균 순위 (후보 12개 중) | 올라감(숫자↓) | {b['liked_rank']:.1f}위 → {a['liked_rank']:.1f}위"
                     f" (재실행 {nz['liked_rank']:.1f}위, {likes['repeats']}회 평균) |")
        off = likes["offline"]
        lines.append(f"| 검색 고정 재순위: 상위 10개 변화량 / {likes['style']} 비율 / 좋아요 브랜드 순위 | 변화 > 0 |"
                     f" {1 - off['overlap']:.0%} / {off['before']['style_ratio']:.0%} → {off['after']['style_ratio']:.0%} /"
                     f" {off['before']['liked_rank']:.1f}위 → {off['after']['liked_rank']:.1f}위 |")
    ood = [r for r in rows if r["test"]["group"] == "ood"]
    if ood:
        graded = [grade(r, args.db) for r in ood]
        invented = sum(len(g["invented_urls"]) for g in graded)
        claims = [r["test"]["id"] for r, g in zip(ood, graded) if g["brand_claim"]]
        lines.append(f"| DB 밖 질문에서 지어낸 상품 수 | 0 | DB에 없는 상품 URL {invented}, "
                     f"없는 브랜드를 아는 척하며 다른 상품 제시 {len(claims)} {claims or ''} |")
        lines.append(f"| DB 밖 질문 적절한 거절 비율 | 100% | {pct(sum(g['appropriate'] for g in graded), len(graded))} |")
        normal = [grade(r, args.db) for r in rows if r["test"]["group"] == "normal"]
        lines.append(f"| (참고) 정상 질문에서 지어낸 상품 수 | 0 | {sum(len(g['invented_urls']) for g in normal)} |")
        stale = sum(len(g["stale_urls"]) for g in normal + graded)
        lines.append(f"| (참고) DB에서 빠진 브랜드 대표 상품 링크 (brands.json이 오래됨) | 0 | {stale} |")
        brand_qs = [r for r in rows if r["test"].get("brand")]
        hit = sum(any(domain_of(u) == r["test"]["brand"] for u in r["p"]["final"]) for r in brand_qs)
        lines.append(f"| (참고) 브랜드 지정 질문에 그 브랜드 상품이 나온 비율 | 100% | {pct(hit, len(brand_qs))} |")
        only = sum(bool(r["p"]["final"]) and all(domain_of(u) == r["test"]["brand"] for u in r["p"]["final"]) for r in brand_qs)
        lines.append(f"| (참고) 브랜드 지정 질문에 그 브랜드 상품만 나온 비율 | 100% | {pct(only, len(brand_qs))} |")
        with open(OUT / "ood_grades.csv" if not quiet else os.devnull, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["id", "type", "query", "expect", "route", "shown", "refused", "hedged", "invented_urls", "stale_urls", "brand_claim",
                        "appropriate", "answer_text"])
            for r, g in zip(ood, graded):
                w.writerow([r["test"]["id"], r["test"]["type"], r["test"]["query"], r["test"]["expect"], r["p"]["route"],
                            g["shown"], g["refused"], g["hedged"], jdump(g["invented_urls"]), jdump(g["stale_urls"]), g["brand_claim"],
                            g["appropriate"], r["p"]["visible"].strip()[:500]])
    th = threshold_report(rows) if rows else None
    if th and th["best"]:
        t, tpr, fpr = th["best"]
        lines.append(f"| (참고) 유사도 기준값 후보 | 정상 통과↑·DB 밖 통과↓ | {t:.3f} → 정상 통과 {tpr:.0%}, DB 밖 통과 {fpr:.0%} |")
    out = "\n".join(lines)
    if th and th["best"]:
        out += (f"\n\n본 검색 최고 유사도  정상: {th['pos_desc']}\n                    DB 밖: {th['neg_desc']}"
                f"\n정상 질문 하위 5% 지점: {th['pos_p5']:.3f}")
    if not quiet:
        print("\n" + out)
        (OUT / "summary.md").write_text(out + "\n")
    # compare 명령용 (기준 이름, 목표값, 결과)
    table = [[c.strip() for c in line.strip("|").split(" | ")] for line in lines[2:]]
    if not quiet:
        (OUT / "summary.json").write_text(jdump(table))
    return table


def load_run(path, db):
    """저장된 결과 폴더 → (rows, links, likes). summarize, compare가 쓴다."""
    path = Path(path).resolve()
    rows = json.loads((path / "results_raw.json").read_text())
    links = None
    if (path / "links.csv").exists():
        with open(path / "links.csv", encoding="utf-8-sig") as f:
            links = [dict(c, ok=c["ok"] == "True", deleted=c["deleted"] == "True", soldout=c["soldout"] == "True",
                          status=int(c["status"]) if c["status"] else None) for c in csv.DictReader(f)]
    likes = json.loads((path / "likes.json").read_text()) if (path / "likes.json").exists() else None
    return rows, links, likes


def compare(before, after, args):
    """두 실행의 요약을 '성공 기준 | 목표값 | 수정 전 | 수정 후'로.
    각 폴더의 summary.json(실행 당시 채점)을 쓴다. 다시 채점하면 그사이 바뀐 brands.json·상품 DB로 판정이 달라진다
    (예: 기준선 n19의 대표 상품 링크 2개는 당시 brands.json에 있어서 '오래된 데이터'였지만, 갱신 뒤 다시 채점하면 '지어냄'이 된다).
    summary.json이 없는 폴더만 다시 계산한다."""
    global OUT
    tables = []
    for path in (before, after):
        OUT = Path(path).resolve()
        saved = OUT / "summary.json"
        tables.append(json.loads(saved.read_text()) if saved.exists() else summarize(*load_run(path, args.db), args, quiet=True))
    names = list(dict.fromkeys([t[0] for t in tables[0]] + [t[0] for t in tables[1]]))
    by = [{t[0]: t for t in table} for table in tables]
    lines = ["| 성공 기준 | 목표값 | 수정 전 | 수정 후 |", "|---|---|---|---|"]
    for name in names:
        target = (by[1].get(name) or by[0].get(name))[1]
        lines.append(f"| {name} | {target} | {(by[0].get(name) or ['', '', '—'])[2]} | {(by[1].get(name) or ['', '', '—'])[2]} |")
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI

def main():
    global OUT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    mk = sub.add_parser("make-tests")
    mk.add_argument("--force", action="store_true")
    run = sub.add_parser("run")
    run.add_argument("--steps", default="ask,links,likes")
    run.add_argument("--tests", default=str(HERE / "tests.json"))
    run.add_argument("--like-mode", choices=["taste", "chat"], default="taste",
                     help="taste: 저장된 취향(웹 지도)을 새 대화 입력으로 넘김 / chat: 한 대화 안에서 👍 메시지로 평가")
    run.add_argument("--out", default=str(HERE), help="결과 파일 폴더 (예: runs/before)")
    run.add_argument("--like-repeats", type=int, default=3, help="좋아요 시뮬레이션 반복 횟수 (평균)")
    run.add_argument("--workers", type=int, default=2, help="질문 동시 실행 수")
    run.add_argument("--refresh-db", action="store_true")
    run.add_argument("--keep-logs", action="store_true", help="Dify DB의 테스트 실행 기록을 지우지 않음")
    sm = sub.add_parser("summarize", help="저장된 결과 파일로 summary.md만 다시 만든다 (API 호출 없음)")
    sm.add_argument("--out", required=True)
    cp = sub.add_parser("compare", help="두 결과 폴더를 '성공 기준 | 목표값 | 수정 전 | 수정 후' 표로 (API 호출 없음)")
    cp.add_argument("before")
    cp.add_argument("after")
    cp.add_argument("--save", help="표를 저장할 파일 (예: runs/compare.md)")
    cl = sub.add_parser("cleanup")
    cl.add_argument("--run-id", required=True)
    args = ap.parse_args()

    if args.cmd == "make-tests":
        path = HERE / "tests.json"
        if path.exists() and not args.force:
            sys.exit(f"{path} 가 이미 있습니다 (--force 로 덮어쓰기)")
        path.write_text(json.dumps(DEFAULT_TESTS, ensure_ascii=False, indent=2) + "\n")
        print(f"{path}: 정상 {len(DEFAULT_TESTS['normal'])}개, DB 밖 {len(DEFAULT_TESTS['ood'])}개")
        return
    if args.cmd == "summarize":
        OUT = Path(args.out).resolve()
        args.db = load_db()
        summarize(*load_run(OUT, args.db), args)
        return
    if args.cmd == "compare":
        args.db = load_db()
        table = compare(args.before, args.after, args)
        print(table)
        if args.save:
            Path(args.save).write_text(table + "\n")
        return
    if args.cmd == "cleanup":
        if not re.fullmatch(r"[0-9a-z]{6,32}", args.run_id):
            sys.exit("run_id 형식이 이상합니다")
        dify = Dify(args.run_id)
        sql = ("select u.session_id || ' ' || c.id from conversations c join end_users u on u.id = c.from_end_user_id"
               f" where u.session_id like 'loupe-eval-{args.run_id}-%' and c.is_deleted = false")
        p = subprocess.run(["docker", "exec", "-i", DB_CONTAINER, "psql", "-U", "postgres", "-d", "dify", "-At", "-c", sql],
                           capture_output=True, text=True)
        dify.convs = [tuple(line.split()) for line in p.stdout.splitlines() if line.strip()]
        dify.cleanup()
        return

    OUT = Path(args.out).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    tests = json.loads(Path(args.tests).read_text())
    steps = set(args.steps.split(","))
    args.db = load_db(args.refresh_db)
    run_id = uuid.uuid4().hex[:10]
    print(f"run_id {run_id} (중간에 끊기면: python3 loupe_eval.py cleanup --run-id {run_id})")
    dify = Dify(run_id)
    # 나중에 수정 후 결과와 비교할 때 같은 조건인지 확인하려고 실행 조건을 남긴다
    (OUT / "tests.json").write_text(json.dumps(tests, ensure_ascii=False, indent=2) + "\n")
    (OUT / "brands.json").write_text(BRANDS_JSON.read_text())   # 채점 당시 대표 상품 (매일 갱신된다)
    (OUT / "run_meta.json").write_text(jdump({
        "run_id": run_id, "started_at": time.strftime("%Y-%m-%d %H:%M:%S"), "steps": sorted(steps),
        "like_mode": args.like_mode, "like_repeats": args.like_repeats, "db_products": len(args.db),
        "dsl": str(DSL), "dsl_sha256": hashlib.sha256(DSL.read_bytes()).hexdigest()[:16],
        "app_dsl_note": "Dify에 실제로 올라간 앱과 같은지는 export한 yml의 해시로 확인"}))
    rows, links, likes = [], None, None
    try:
        if "ask" in steps:
            print("질문 실행")
            rows = step_ask(tests, dify, args.db, args.workers)
        elif (OUT / "results_raw.json").exists():
            rows = json.loads((OUT / "results_raw.json").read_text())
        if "links" in steps and rows:
            print("링크 검사")
            links = step_links(rows)
        if "likes" in steps:
            print(f"좋아요 시뮬레이션 ({args.like_mode})")
            likes = step_likes(tests["likes"], dify, args.db, args.like_mode, args.like_repeats)
    finally:
        dify.cleanup(args.keep_logs)
    summarize(rows, links, likes, args)


if __name__ == "__main__":
    main()
