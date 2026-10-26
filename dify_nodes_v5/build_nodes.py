"""original/의 운영 노드 코드·프롬프트에 v5 수정을 적용해 dify_nodes_v5/에 쓴다.

  python3 build_nodes.py

원본의 바뀌는 부분만 치환하므로 데이터 줄(BRAND_ALIASES 등, export_brand_similarity.py가 갱신)은 그대로 남는다.
치환 대상이 원본에 정확히 한 번 있지 않으면 멈춘다 (운영 코드가 바뀌었는데 모르고 덮어쓰는 것을 막는다).
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORIG = HERE / "original"


def patch(name, pairs, out=None):
    text = (ORIG / name).read_text(encoding="utf-8")
    for old, new in pairs:
        if text.count(old) != 1:
            raise SystemExit(f"{name}: 치환 대상이 {text.count(old)}번 있음:\n{old[:200]}")
        text = text.replace(old, new)
    (HERE / (out or name)).write_text(text, encoding="utf-8")
    print(f"{out or name}: {len(pairs)}곳 수정")


# ---------------------------------------------------------------- 검색 준비 (prep)
PREP_HELPERS = '''

# ---------------- 범위 확인 (v5) ----------------
# 지식베이스에는 상의·하의·아우터만 있다. 이 아이템만 찾는 질문은 검색하지 않고 바로 안내한다.
# 질문에 상의·하의·아우터 단어가 같이 있으면 범위 안으로 본다 ("첼시 부츠랑 어울리는 바지", "부츠컷 데님").
OUT_ITEMS = {
    "신발": ["신발", "스니커즈", "운동화", "구두", "로퍼", "부츠", "샌들", "슬리퍼", "슬링백", "뮬", "sneakers", "sneaker", "shoes", "boots", "loafer"],
    "원피스": ["원피스", "드레스", "dress", "onepiece"],
    "가방": ["가방", "크로스백", "숄더백", "토트백", "백팩", "에코백", "클러치", "bag", "backpack"],
    "모자": ["모자", "비니", "볼캡", "버킷햇", "카스켓", "베레모", "beanie", "cap", "hat"],
    "액세서리": ["액세서리", "목걸이", "반지", "귀걸이", "팔찌", "선글라스", "양말", "장갑", "지갑", "머플러", "스카프", "necklace", "ring"],
}
OUT_EXCEPT_RE = re.compile(r"부츠\\s*컷|boots?\\s*cut|bootcut|드레스\\s*셔츠|dress\\s*shirts?", re.I)
IN_WORDS = sorted({w for ws in CATEGORY_WORDS.values() for w in ws} | {
    "카디건", "블레이저", "베스트", "조끼", "집업", "후디", "트레이닝", "트랙", "쇼츠", "반바지", "레깅스", "조거", "슬리브", "나시",
    "blazer", "cardigan", "vest", "hoodie", "shorts", "trousers", "slacks", "blouse", "sweater", "sweatshirt"})
# 브랜드 이름 뒤에 오면 "그 브랜드 상품만"이 아니라 분위기 기준으로 본다 ("코이세이오 느낌 니트", "로웨어 같은 자켓")
REFERENCE_AFTER = ["느낌", "같은", "같이", "스타일", "st", "풍", "처럼", "비슷", "무드", "감성"]
NEGATION_WORDS = NEGATIONS_AFTER + NEGATIONS_BEFORE
MAX_TASTE_BRANDS = 3   # 취향 검색에 넣는 좋아요 브랜드 수


def _has_word(text, word):
    if word.isascii():
        return re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", text) is not None
    return word in text


def _out_of_scope_item(query, llm_category, llm_item):
    """다루지 않는 아이템만 찾는 질문이면 그 아이템 이름, 아니면 ""."""
    q = OUT_EXCEPT_RE.sub(" ", (query or "").lower())
    if any(_has_word(q, w) for w in IN_WORDS):
        return ""
    for item, words in OUT_ITEMS.items():
        if any(_has_word(q, w) for w in words):
            return next((w for w in words if _has_word(q, w)), item)
    if str(llm_category or "").strip() == "기타":
        return str(llm_item or "").strip() or "이 아이템"
    return ""


def _unknown_brands(names, query):
    """검색어 정리 LLM이 뽑은 브랜드 중 수집하지 않은 것. LLM이 지어낸 이름을 막으려고 질문에 실제로 있는 것만 본다."""
    q = _norm(query)
    out = []
    for name in names:
        n = _norm(name)
        if len(n) < 2 or n not in q or _domain_of(name) or n in STYLE_ALIASES or n == "브랜드":
            continue
        if any(_norm(w) == n for w in IN_WORDS) or any(_norm(w) == n for ws in OUT_ITEMS.values() for w in ws):
            continue
        out.append(str(name).strip())
    return _uniq(out)


def _is_reference(q, domain):
    """정규화된 질문에서 그 브랜드 언급 바로 뒤가 '느낌/같은/스타일...'이면 분위기 기준으로 말한 것."""
    for start, end, d in _mentions(q):
        if d == domain and any(q[end:end + 6].startswith(w) for w in REFERENCE_AFTER):
            return True
    return False


def _included(query, names, excluded):
    """보여 달라고 지정한 수집 브랜드 (그 브랜드 상품만 검색한다). 제외 브랜드와 분위기 기준 언급은 뺀다."""
    q = _norm(query)
    found = [_domain_of(n) for n in names] + [m[2] for m in _mentions(q)]
    return [d for d in _uniq(found) if d and d not in excluded and not _is_reference(q, d)]


def _strip_unasked_styles(search, styles):
    """사용자가 요청하지 않은 스타일 단어(검색어 정리 LLM이 붙인 '빈티지 vintage 캐주얼 casual' 등)와 반복 단어를 뺀다.
    평가는 점수로만 반영하므로 좋아한 스타일도 요청하지 않았으면 같이 빠진다."""
    words, seen = [], set()
    for w in search.split():
        tags = STYLE_ALIASES.get(_norm(w))
        if tags and not any(t in styles for t in tags):
            continue
        if w.lower() in seen:
            continue
        seen.add(w.lower())
        words.append(w)
    return " ".join(words) or search


def _with_styles(search, styles):
    """요청한 스타일인데 검색어에 그 스타일 단어가 없으면 붙인다 (검색어 정리 LLM이 빼먹는 경우가 있다).
    태그 이름(한글)과, 그 태그 하나만 가리키는 영문 표현을 하나 붙인다 (빈티지 → 빈티지 vintage)."""
    have = {t for w in search.split() for t in STYLE_ALIASES.get(_norm(w), [])}
    extra = []
    for s in styles:
        if s in have:
            continue
        en = next((k for k, v in STYLE_ALIASES.items() if v == [s] and k.isascii()), "")
        extra += [s] + ([en] if en else [])
    return " ".join(extra + [search]).strip() if extra else search


def _names(domain):
    b = BRAND_ALIASES.get(domain) or {}
    return " ".join(x for x in [b.get("ko"), b.get("en")] if x)


def _with_names(search, include):
    """지정 브랜드 이름(한글·영문)이 검색어에 없으면 붙인다 (키워드 검색이 그 브랜드 문단을 잘 찾도록)."""
    q = _norm(search)
    extra = [_names(d) for d in include if not any(a in q for a in (BRAND_ALIASES.get(d) or {}).get("aliases", []))]
    return " ".join([search] + extra).strip()


def _taste_query(search, prefs, exclude):
    """좋아요한 브랜드 이름 + 이번 검색어. 본 검색 40건에 좋아요 브랜드가 없어도 후보에 들어올 수 있게 따로 검색한다.
    좋아요가 없으면 본 검색어 그대로 (같은 결과라 후보 정리에서 중복으로 빠진다)."""
    scores = []
    for d, v in ((prefs.get("brands") or {}).items()):
        try:
            if float(v) > 0 and d in BRAND_ALIASES and d not in exclude:
                scores.append((float(v), d))
        except (TypeError, ValueError):
            pass
    top = [d for _, d in sorted(scores, reverse=True)[:MAX_TASTE_BRANDS]]
    return (" ".join(_names(d) for d in top) + " " + search).strip() if top else search


def ui_block(payload):
    """웹사이트가 읽는 숨은 데이터 블록 (다른 노드와 같은 형식)."""
    return "\\n\\n<!--fashion-ui " + json.dumps(dict(payload, v=1), ensure_ascii=False) + " -->"


def _scope_reply(scope, item, unknown, styles):
    if scope == "category":
        return ("지금 loupe는 상의·하의·아우터만 모아 두고 있어서 {}{} 추천해 드릴 수 없어요. "
                "상의·하의·아우터 중에서 찾으시면 바로 골라 드릴게요.").format(item, _josa(item, "은", "는"))
    name = unknown[0]
    text = ("'{}'{} 아직 loupe에 없는 브랜드라 상품을 보여 드릴 수 없어요. 지금은 수집한 {}개 브랜드의 상품만 추천해요. "
            "비슷한 분위기의 브랜드는 웹에서 찾아볼 수 있어요.").format(name, _josa(name, "은", "는"), len(BRAND_ALIASES))
    return text + ui_block({"type": "no_match", "reason": "brand", "brand": name, "styles": styles, "text": text})


def _josa(word, with_final, without_final):
    last = (word or " ")[-1]
    if "가" <= last <= "힣":
        return with_final if (ord(last) - 0xAC00) % 28 else without_final
    return without_final
'''

PREP_MAIN_OLD = '''    else:
        search = str(data.get("query") or "").strip() or (str(last.get("query") or "") if followup else "") or (query or "").strip()
        styles = _uniq(_styles_in([query] + [str(s) for s in (data.get("styles") or [])]))
        category = _category_of(data.get("category"), query)
        names = [str(x) for x in (data.get("exclude_brands") or []) if str(x).strip()]
        exclude = _uniq([_domain_of(n) for n in names] + _excluded_in_text(query))
        if followup:
            # 새 질문에 없는 조건만 이전 조건에서 이어받는다
            styles = styles or list(last.get("styles") or [])
            category = category or str(last.get("category") or "")
            exclude = _uniq(exclude + list(last.get("exclude") or []))
    exclude_urls = [str(u) for u in (shown_urls or [])][-MAX_SHOWN:] if followup else []
    search = _strip_liked_styles(search, styles, prefs)
    broad = BROAD_QUERY.get(category) or search
'''
PREP_MAIN_NEW = '''        include = list(last.get("include") or [])
        scope, item, unknown = "ok", "", []
    else:
        search = str(data.get("query") or "").strip() or (str(last.get("query") or "") if followup else "") or (query or "").strip()
        # 스타일은 사용자 질문에 있는 것만 (검색어 정리 LLM의 styles는 질문에 없는 스타일을 붙이기도 해서 쓰지 않는다)
        styles = _uniq(_styles_in([query]))
        category = _category_of(data.get("category"), query)
        names = [str(x) for x in (data.get("exclude_brands") or []) if str(x).strip()]
        # LLM의 제외 브랜드는 질문에 제외 표현(빼고, 말고, 제외...)이 있을 때만 믿는다.
        # 프롬프트 예시 때문에 "로웨어 자켓 보여줘"에도 로웨어를 제외로 내는 일이 있었다 (2026-10-22, 12번 중 3번)
        q_norm = _norm(query)
        llm_exclude = [_domain_of(n) for n in names] if any(w in q_norm for w in NEGATION_WORDS) else []
        exclude = _uniq(llm_exclude + _excluded_in_text(query))
        brand_names = [str(x) for x in (data.get("brands") or []) if str(x).strip()]
        include = _included(query, brand_names, exclude)
        unknown = [] if include else _unknown_brands(brand_names, query)
        item = _out_of_scope_item(query, data.get("category"), data.get("item"))
        scope = "category" if item else "brand" if unknown else "ok"
        if followup:
            # 새 질문에 없는 조건만 이전 조건에서 이어받는다
            styles = styles or list(last.get("styles") or [])
            category = category or str(last.get("category") or "")
            exclude = _uniq(exclude + list(last.get("exclude") or []))
            include = include or [d for d in (last.get("include") or []) if d not in exclude]
    exclude_urls = [str(u) for u in (shown_urls or [])][-MAX_SHOWN:] if followup else []
    search = _with_names(_with_styles(_strip_unasked_styles(search, styles), styles), include)
    broad = BROAD_QUERY.get(category) or search
    if include:
        # 넓힌 검색도 그 브랜드 안에서: 브랜드 이름 + 카테고리 단어
        broad = (" ".join(_names(d) for d in include) + " " + broad).strip()
'''
PREP_COND_OLD = '''    lines.append("제외 브랜드: " + (", ".join(BRAND_ALIASES[d]["ko"] for d in exclude) if exclude else "없음"))'''
PREP_COND_NEW = '''    lines.append("제외 브랜드: " + (", ".join(BRAND_ALIASES[d]["ko"] for d in exclude) if exclude else "없음"))
    if include:
        lines.append("지정 브랜드: " + ", ".join(BRAND_ALIASES[d]["ko"] for d in include)
                     + " (목록에는 이 브랜드 상품만 있어요. 같은 브랜드에서 3개까지 골라도 돼요)")'''
PREP_RET_OLD = '''        "next_search": {"query": search, "styles": styles, "category": category, "exclude": exclude},
        "base_shown": exclude_urls,
        "reaction": (reaction + "\\n\\n") if reaction else "",
    }'''
PREP_RET_NEW = '''        "next_search": {"query": search, "styles": styles, "category": category, "exclude": exclude, "include": include},
        "base_shown": exclude_urls,
        "reaction": (reaction + "\\n\\n") if reaction else "",
        # v5: 범위 확인 (ok / category / brand). ok가 아니면 '범위 확인' 분기가 검색 없이 scope_reply로 답한다
        "scope": scope,
        "scope_reply": _scope_reply(scope, item, unknown, styles) if scope != "ok" else "",
        "include": include,
        "brand_only": "yes" if include else "no",
        "taste_query": search if include else _taste_query(search, prefs, exclude),
    }'''

PREP_CAT_OLD = '''def _category_of(value, query):
    value = str(value or "").strip()
    if value in CATEGORIES:
        return value
    q = (query or "").lower()'''
PREP_CAT_NEW = '''def _category_of(value, query):
    """질문의 아이템 단어가 한 카테고리만 가리키면 그것을 LLM 값보다 우선한다. 후보 정리는 상품명으로 카테고리를 다시 보는데
    (가디건·카디건 → 아우터) LLM은 가디건을 상의로 내기도 해서, 둘이 어긋나면 검색된 가디건이 전부 '다른 카테고리'로 빠졌다
    (2026-10-22 수정 후 평가 n14 "10만원 이하 가디건"). 여러 카테고리 단어가 섞이면 ("데님 자켓") LLM 값을 쓴다."""
    value = str(value or "").strip()
    q = (query or "").lower()
    hits = [cat for cat, words in CATEGORY_WORDS.items() if any(w in q for w in words)]
    if len(hits) == 1:
        return hits[0]
    if value in CATEGORIES:
        return value'''

patch("prep.py", [
    (PREP_CAT_OLD, PREP_CAT_NEW),
    ('"아우터": ["아우터", "자켓", "재킷", "코트", "점퍼", "가디건", "블루종", "패딩", "outer", "jacket", "coat"],',
     '"아우터": ["아우터", "자켓", "재킷", "코트", "점퍼", "가디건", "카디건", "블루종", "패딩", "블레이저", "outer", "jacket", "coat", "cardigan", "blazer"],'),
    ("\n\ndef main(llm_text: str, query: str", PREP_HELPERS + "\n\ndef main(llm_text: str, query: str"),
    (PREP_MAIN_OLD, PREP_MAIN_NEW),
    (PREP_COND_OLD, PREP_COND_NEW),
    (PREP_RET_OLD, PREP_RET_NEW),
])


# ---------------------------------------------------------------- 후보 정리 (candidates)
CAND_CONST_OLD = '''PREF_CAP = 0.12'''
CAND_CONST_NEW = '''TASTE_MAX = 3         # v5: 취향 검색(좋아요 브랜드 이름 + 검색어)에서 후보에 섞는 상품 수 (브랜드당 1개)
PREF_CAP = 0.12'''
CAND_SIG_OLD = '''def main(docs: list, docs_broad: list, exclude: list, exclude_urls: list, styles: list, category: str, prefs: dict, taste: str,
         item_index: dict) -> dict:'''
CAND_SIG_NEW = '''def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def ui_block(payload):
    return "\\n\\n<!--fashion-ui " + json.dumps(dict(payload, v=1), ensure_ascii=False) + " -->"


def _empty_reply(include, styles, category, searched=True):
    """후보가 하나도 없을 때 ('후보 있나?' 분기가 추천LLM을 부르지 않고 이 문장으로 답한다).
    searched=False: 본 검색·넓힌 검색이 둘 다 0건. 넓힌 검색(카테고리 단어)은 평소 항상 결과가 있어서 검색 쪽 문제로 본다
    (원인 미확인, 2026-10-21 기준선 n20·2026-10-22 수정 후 n15에서 30문항 중 1번씩)."""
    if not searched:
        return "지금 상품 검색이 잠시 원활하지 않았어요. 같은 질문을 한 번 더 보내 주세요."
    what = category or "상품"
    if include:
        names = ", ".join((BRAND_ALIASES.get(d) or {}).get("ko") or d for d in include)
        return "지금 {}에는 조건에 맞는 {}{} 없어요. 브랜드를 빼고 다시 찾아 드릴까요?".format(names, what, _josa(what, "이", "가"))
    label = " ".join(x for x in [" ".join(styles[:2]), category or "상품"] if x)
    text = "지금 수집한 상품 중에는 조건에 맞는 {}{} 없어요. 비슷한 분위기의 브랜드를 웹에서 찾아볼 수 있어요.".format(
        label, _josa(label, "이", "가"))
    return text + ui_block({"type": "no_match", "reason": "empty", "brand": "", "styles": styles, "category": category, "text": text})


def main(docs: list, docs_broad: list, exclude: list, exclude_urls: list, styles: list, category: str, prefs: dict, taste: str,
         item_index: dict, docs_taste: list, include: list) -> dict:'''
CAND_INC_OLD = '''    prefs = with_taste(prefs, taste)
    shown = {str(u).strip() for u in (exclude_urls or [])}'''
CAND_INC_NEW = '''    prefs = with_taste(prefs, taste)
    # v5: 브랜드를 지정한 질문은 그 브랜드 상품만 (검색 준비의 include)
    include = [re.sub(r"^www\\.", "", str(d).lower()) for d in (include or [])]
    shown = {str(u).strip() for u in (exclude_urls or [])}'''
CAND_COUNT_OLD = '''    counts = {"brand": 0, "shown": 0, "disliked": 0, "not_apparel": 0, "category": 0, "variant": 0}'''
CAND_COUNT_NEW = '''    counts = {"brand": 0, "shown": 0, "disliked": 0, "not_apparel": 0, "category": 0, "variant": 0, "not_included": 0}'''
CAND_FILTER_OLD = '''            if domain in excluded:
                counts["brand"] += 1
                continue'''
CAND_FILTER_NEW = '''            if domain in excluded:
                counts["brand"] += 1
                continue
            if include and domain not in include:
                counts["not_included"] += 1
                continue'''
CAND_TAKE_OLD = '''    main_pool = usable(docs, 0)
    broad_pool = usable(docs_broad, 1000)
    picked, per_brand, stage = [], {}, "base"
    take(main_pool, picked, per_brand, 1)
    if len(picked) < MIN_CANDIDATES:
        stage = "brand2"
        take(main_pool, picked, per_brand, 2)
    if len(picked) < MIN_CANDIDATES and broad_pool:
        stage = "broad"
        take(broad_pool, picked, per_brand, 1)
        if len(picked) < MIN_CANDIDATES:
            take(broad_pool, picked, per_brand, 2)
    if stage == "brand2" and len(picked) == len([x for x in picked if per_brand[x["domain"]] == 1]):
        stage = "base"   # 2개까지 풀었지만 실제로 같은 브랜드 두 번째 상품이 들어가지 않았으면 안내하지 않는다
'''
CAND_TAKE_NEW = '''    main_pool = usable(docs, 0)
    broad_pool = usable(docs_broad, 1000)
    # v5 취향 검색: 본 검색 40건에 좋아요 브랜드가 없으면 점수를 더해 줄 상품 자체가 없어서(기준선 측정),
    # '좋아요 브랜드 이름 + 검색어'로 따로 찾은 결과에서 좋아요 브랜드 상품을 브랜드당 1개, TASTE_MAX개까지 섞는다.
    # 같은 상품이 본 검색에 있으면 앞에서 이미 봤으므로(seen) 빠진다. 브랜드 지정 질문에는 섞지 않는다.
    liked = {d for d, v in (prefs.get("brands") or {}).items() if _num(v) > 0}
    taste_pool, taste_brands = [], set()
    if liked and not include:
        for it in usable(docs_taste, 2000):
            if it["domain"] in liked and it["domain"] not in taste_brands and len(taste_pool) < TASTE_MAX:
                taste_pool.append(it)
                taste_brands.add(it["domain"])
        main_pool = sorted(main_pool + taste_pool, key=lambda x: (-x["score"], x["rank"]))
    # 브랜드 지정 질문은 그 브랜드에서만 고르므로 브랜드당 개수 제한을 두지 않는다
    first, second = (MAX_CANDIDATES, MAX_CANDIDATES) if include else (1, 2)
    picked, per_brand, stage = [], {}, "base"
    take(main_pool, picked, per_brand, first)
    if len(picked) < MIN_CANDIDATES:
        stage = "brand2"
        take(main_pool, picked, per_brand, second)
    if len(picked) < MIN_CANDIDATES and broad_pool:
        stage = "broad"
        take(broad_pool, picked, per_brand, first)
        if len(picked) < MIN_CANDIDATES:
            take(broad_pool, picked, per_brand, second)
    if stage == "brand2" and (include or len(picked) == len([x for x in picked if per_brand[x["domain"]] == 1])):
        stage = "base"   # 2개까지 풀었지만 실제로 같은 브랜드 두 번째 상품이 들어가지 않았으면 안내하지 않는다
'''
CAND_RET_OLD = '''    return {
        "context": context,
        "candidates": kept,'''
CAND_RET_NEW = '''    scores = [_num((d.get("metadata") or {}).get("score")) for d in (docs or []) if isinstance(d, dict)]
    return {
        # v5: '후보 있나?' 분기용 후보 수, 본 검색 최고 유사도(기록용, 분기 기준값은 아직 정하지 않음), 후보 0개일 때 답변
        "n_candidates": len(kept),
        "max_score": round(max(scores), 4) if scores else 0.0,
        "empty_reply": "" if kept else _empty_reply(include, styles, category, bool(docs or docs_broad)),
        "context": context,
        "candidates": kept,'''
CAND_SUM_OLD = '''            counts["category"], counts["variant"], stage, len(kept), len(per_brand), sum(1 for it in picked if it["rank"] >= 1000),
            sum(1 for it in picked if it["matched"]), sum(1 for it in picked if _pref_bonus(it["domain"], prefs))),
    }'''
CAND_SUM_NEW = '''            counts["category"], counts["variant"], stage, len(kept), len(per_brand),
            sum(1 for it in picked if 1000 <= it["rank"] < 2000),
            sum(1 for it in picked if it["matched"]), sum(1 for it in picked if _pref_bonus(it["domain"], prefs)))
        + " / 지정 브랜드 밖 {}건 제외 · 취향 검색에서 {}건".format(counts["not_included"], sum(1 for it in picked if it["rank"] >= 2000)),
    }'''

patch("candidates.py", [
    (CAND_CONST_OLD, CAND_CONST_NEW), (CAND_SIG_OLD, CAND_SIG_NEW), (CAND_INC_OLD, CAND_INC_NEW),
    (CAND_COUNT_OLD, CAND_COUNT_NEW), (CAND_FILTER_OLD, CAND_FILTER_NEW), (CAND_TAKE_OLD, CAND_TAKE_NEW),
    (CAND_RET_OLD, CAND_RET_NEW), (CAND_SUM_OLD, CAND_SUM_NEW),
])


# ---------------------------------------------------------------- 상품 정보 붙이기 (format)
# original/format_with_stats.py = 운영 코드 + proposed_count/kept_count/dropped_urls (eval/format_node_patched.py)
FMT_NORM_OLD = '''def _norm_url(url):
    url = str(url or "").strip().strip("<>\\"'")
    url = re.sub(r"^https?://", "", url)
    return url.rstrip("/")'''
FMT_NORM_NEW = '''def _unquote(url):
    """%EC%9B%A8 같은 퍼센트 인코딩을 푼다 (LLM이 한글 주소를 인코딩해서 옮기기도 한다)."""
    return re.sub(r"(?:%[0-9A-Fa-f]{2})+", lambda m: bytes.fromhex(m.group(0).replace("%", "")).decode("utf-8", "replace"), url)


def _norm_url(url):
    url = _unquote(str(url or "").strip().strip("<>\\"'"))
    url = re.sub(r"^https?://(www\\.)?", "", url)
    return url.rstrip("/")


def _product_id(url):
    """(도메인, 상품 번호). 카페24 /product/<이름>/<번호>/, product_no=<번호>, 아임웹 /shop_view/<번호>"""
    url = _unquote(str(url or ""))
    m = re.search(r"product_no=(\\d+)", url) or re.search(r"/(\\d+)/?(?:[?#].*)?$", url)
    return (_domain_of(url), m.group(1)) if m else None'''
FMT_MATCH_OLD = '''        if match is not None and not match["url"]:
            match = dict(match, url=str(item.get("url")).strip())
    return match, key'''
FMT_MATCH_NEW = '''        if match is not None and not match["url"]:
            match = dict(match, url=str(item.get("url")).strip())
    if match is None:
        # LLM이 주소를 옮기며 글자를 틀린 경우 ("…데님-블루종…/2014/" → "…데닌-블루종…/2014/", 2026-10-21 기준선 n09):
        # 같은 도메인·같은 상품 번호인 후보가 하나뿐이면 그 상품으로 본다
        pid = _product_id(item.get("url"))
        same = [p for p in products if pid and p["url"] and _product_id(p["url"]) == pid]
        if len(same) == 1:
            match = same[0]
            key = _norm_url(match["url"])
    return match, key'''
FMT_SIG_OLD = '''def main(llm_text: str, docs: list, base_shown: list) -> dict:'''
FMT_SIG_NEW = '''def main(llm_text: str, docs: list, base_shown: list, brand_only: str) -> dict:'''
FMT_LIMIT_OLD = '''    for limit in (1, MAX_PER_BRAND):'''
FMT_LIMIT_NEW = '''    # 브랜드를 지정한 질문(검색 준비 brand_only)은 그 브랜드에서만 고르므로 같은 브랜드로 MAX_ITEMS개까지
    for limit in ((MAX_ITEMS,) if brand_only == "yes" else (1, MAX_PER_BRAND)):'''

patch("format_with_stats.py", [(FMT_NORM_OLD, FMT_NORM_NEW), (FMT_MATCH_OLD, FMT_MATCH_NEW),
                               (FMT_SIG_OLD, FMT_SIG_NEW), (FMT_LIMIT_OLD, FMT_LIMIT_NEW)], out="format.py")


# ---------------------------------------------------------------- 추천LLM (llm) 프롬프트
patch("llm_prompt.txt", [(
    "4. 서로 다른 브랜드에서 1개씩 골라. 서로 다른 브랜드로 3개를 채울 수 없을 때만 같은 브랜드에서 2개까지 골라.",
    "4. 서로 다른 브랜드에서 1개씩 골라. 서로 다른 브랜드로 3개를 채울 수 없을 때만 같은 브랜드에서 2개까지 골라.\n"
    "   단, \"정리된 검색 조건\"에 지정 브랜드가 있으면 목록은 모두 그 브랜드 상품이니 그 브랜드에서 3개까지 골라.")])
