import json
import re

# 지식베이스 컬럼 이름이 다르면 여기에 추가하세요 (소문자, 공백/밑줄 없이 비교).
FIELD_ALIASES = {
    "url": ["url", "link", "링크", "상품url", "상품링크", "producturl", "주소"],
    "name": ["상품명", "name", "productname", "제품명", "title", "상품이름"],
    "brand": ["브랜드", "brand", "판매처", "seller", "shop", "쇼핑몰", "스토어"],
    "category": ["카테고리", "category", "분류"],
    "price": ["가격", "price", "판매가", "할인가", "saleprice"],
    "description": ["설명", "description", "상품설명", "desc"],
    "image": ["이미지", "image", "imageurl", "img", "thumbnail", "썸네일", "이미지url", "대표이미지"],
}
LINE_FIELD_RE = re.compile(r"^\s*([^:\n]{1,30}?)\s*:\s*(.*)$")
NOT_FOUND = "조건에 맞는 상품을 찾지 못했어요"
MAX_PER_BRAND = 2   # 후보가 부족할 때만 같은 브랜드 2개까지
MAX_ITEMS = 3
MAX_SHOWN = 30      # 대화 변수 shown_urls에 남기는 URL 수 (Code 노드 문자열 배열 최대 30)


def _won_text(text):
    """LLM 문장 속 "100,000KRW", "₩100,000"을 "100,000원"으로 바꾼다."""
    text = re.sub(r"(\d[\d,]*)\s*(?:KRW|krw)", r"\1원", text or "")
    return re.sub(r"₩\s*(\d[\d,]*)", r"\1원", text)


def _domain_of(url):
    m = re.match(r"https?://([^/]+)", str(url or "").strip())
    return re.sub(r"^www\.", "", m.group(1).lower()) if m else ""


def _norm_key(key):
    return re.sub(r"[\s_\-]", "", str(key)).lower()


def _norm_url(url):
    url = str(url or "").strip().strip("<>\"'")
    url = re.sub(r"^https?://", "", url)
    return url.rstrip("/")


def _parse_lines(parts):
    fields = {}
    for part in parts:
        m = LINE_FIELD_RE.match(part)
        if m and m.group(1).strip() not in fields:
            fields[m.group(1).strip()] = m.group(2).strip()
    return fields


def _parse_content(text):
    """청크 텍스트를 {키: 값}으로 바꾼다.
    기본 형식은 insta_brand_v2의 줄 단위 "키: 값" (브랜드/상품명/카테고리/가격/URL/설명/이미지)이고,
    JSON, "키":"값"; (엑셀), 키: 값; (CSV)도 처리한다."""
    text = (text or "").strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    lines = [l for l in text.split("\n") if l.strip()]
    if len(lines) >= 2 and sum(bool(LINE_FIELD_RE.match(l)) for l in lines) >= 2:
        return _parse_lines(lines)
    pairs = re.findall(r'"([^"]+)"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    if pairs:
        return {k: v for k, v in pairs}
    return _parse_lines(re.split(r";\s*", text))


def _pick(fields, name):
    normalized = {_norm_key(k): v for k, v in fields.items()}
    for alias in FIELD_ALIASES[name]:
        value = normalized.get(alias)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _product(doc):
    fields = {}
    meta = doc.get("metadata") or {}
    doc_meta = meta.get("doc_metadata") if isinstance(meta, dict) else None
    if isinstance(doc_meta, dict):
        fields.update({k: v for k, v in doc_meta.items() if v not in (None, "")})
    fields.update(_parse_content(doc.get("content", "")))
    product = {name: _pick(fields, name) for name in FIELD_ALIASES}
    product["content"] = doc.get("content", "") or ""
    return product


def _format_price(price):
    """138,000KRW / ₩138,000 / 138000 / 138,000원 -> 138,000원. 가격 정보가 없으면 빈 문자열."""
    price = (price or "").strip()
    if not price or price in ("정보 없음", "None"):
        return ""
    m = re.fullmatch(r"(?:₩|KRW)?\s*([\d,]+)(?:\.\d+)?\s*(?:원|KRW|krw|₩)?", price)
    if m and m.group(1).replace(",", ""):
        return "{:,}원".format(int(m.group(1).replace(",", "")))
    return price


def _md_text(text):
    return text.replace("[", "(").replace("]", ")")


def _parse_llm(text):
    text = (text or "").strip()
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


# ---------------- 표시용 상품명 정리 ----------------
COLOR_WORDS = {
    "mustard", "mocka", "coral", "peach", "butter", "lemon", "lime", "lilac", "sage", "teal", "terracotta", "chocolate", "espresso", "taupe", "sand", "stone", "ecru", "nude", "rose", "berry", "cobalt", "emerald", "forest", "maroon", "plum", "mauve", "rust", "tan", "vanilla", "smoke", "slate", "violet", "aqua", "turquoise", "melon", "cocoa", "latte", "milk", "oat", "pistachio", "머스타드", "코랄", "피치", "버터", "레몬", "라임", "라일락", "세이지", "테라코타", "초코", "에스프레소", "토프", "샌드", "스톤", "에크루", "누드", "로즈", "베리", "코발트", "에메랄드", "포레스트", "마룬", "플럼", "모브", "러스트", "바닐라", "스모크", "바이올렛", "아쿠아", "터콰이즈", "멜론", "코코아", "라떼", "오트밀", "피스타치오", "하늘", "보라", "노랑", "빨강", "초록", "갈색", "검정", "흰색", "네온", "아이스블루", "스카이블루",
    "black", "white", "ivory", "cream", "beige", "gray", "grey", "charcoal", "navy", "blue", "skyblue", "khaki", "brown",
    "pink", "red", "burgundy", "wine", "green", "olive", "mint", "yellow", "orange", "purple", "lavender", "melange",
    "indigo", "camel", "mocha", "oatmeal", "silver", "gold", "multi", "denim", "블랙", "화이트", "아이보리", "크림", "베이지",
    "그레이", "회색", "차콜", "네이비", "블루", "청", "카키", "브라운", "핑크", "레드", "버건디", "와인", "그린", "올리브", "민트",
    "옐로우", "오렌지", "퍼플", "라벤더", "멜란지", "인디고", "카멜", "모카", "실버", "골드", "소라", "연청", "중청", "진청", "흑청",
}
COLOR_MODIFIERS = {"light", "dark", "deep", "pale", "dusty", "off", "sky", "ash", "vintage", "washed", "heather", "mid",
                   "라이트", "다크", "딥", "연", "진", "빈티지", "워시드", "더스티", "오프", "스카이", "애쉬"}
NOTICE_RE = re.compile(r"\d*\s*차\s*재입고|재입고|리오더|re-?order|\d*(?:st|nd|rd|th)?\s*re-?stock|주문\s*폭주|예약\s*(?:배송|판매|주문)|"
                       r"당일\s*발송|품절\s*임박|한정\s*수량|\d+\s*(?:colou?rs?|컬러|色)", re.I)


def _is_color_token(tok):
    t = tok.lower()
    return t in COLOR_WORDS or any(t.endswith(c) for c in COLOR_WORDS if len(c) >= 2 and not c.isascii())


def _is_noise_group(inner):
    """괄호 안이 색상·N컬러·안내 문구로만 되어 있으면 True ("(Beige)", "(2color/주문폭주)", "(Vintage Green)", "[2nd restock]").
    "(속기모)", "( pli hoodie cardigan )"처럼 다른 정보가 있으면 False."""
    rest = NOTICE_RE.sub(" ", inner)
    toks = [t for t in re.split(r"[\s/,·&+|]+", rest) if t and t.lower() not in ("and", "or", "&")]
    has_signal = rest != inner or any(_is_color_token(t) for t in toks)
    return has_signal and all(_is_color_token(t) or t.lower() in COLOR_MODIFIERS for t in toks)


def clean_name(name):
    """표시용 상품명. 괄호/대괄호 속 색상·N컬러·안내 문구, "_PINK" 같은 색상 꼬리, 괄호 밖 안내 문구, 끝에 붙은 색상 단어를 뗀다.
    다 떼고 비면 원래 이름. ("빈티지 워싱 바이커자켓(2color/주문폭주)" -> "빈티지 워싱 바이커자켓")"""
    original = (name or "").strip()
    s = re.sub(r"\(([^)]*)\)|\[([^\]]*)\]", lambda m: " " if _is_noise_group(m.group(1) or m.group(2) or "") else m.group(0), original)
    s = re.sub(r"\s*_\s*[^_]+$", lambda m: "" if all(_is_color_token(t) or t.lower() in COLOR_MODIFIERS
                                                      for t in m.group(0).strip(" _").split()) else m.group(0), s)
    s = NOTICE_RE.sub(" ", s)
    toks = s.split()
    while len(toks) > 2 and (_is_color_token(toks[-1].strip("-/,.")) or
                             (toks[-1].lower() in COLOR_MODIFIERS and _is_color_token(toks[-2]))):
        toks.pop()
    s = re.sub(r"\(\s*\)|\[\s*\]", " ", " ".join(toks))
    s = re.sub(r"\s+", " ", s).strip(" -/,.")
    return s or original


# ---------------- 상품명으로 카테고리 재확인 ----------------
# 지식베이스 카테고리가 틀린 경우가 있어(2026-10-16 오헤시오 "…OVERSIZED KNIT"가 아우터) 상품명으로 한 번 더 확인한다.
# 아우터 단어가 이름 어디든 있으면 아우터("SHIRT JACKET", "KNIT CARDIGAN"), 없으면 끝 두 단어로 상의/하의를 본다.
OUTER_WORDS = ["카디건", "가디건", "cardigan", "자켓", "재킷", "jacket", "코트", "coat", "점퍼", "jumper", "블루종", "blouson",
               "파카", "parka", "패딩", "padding", "무스탕", "mustang", "바람막이", "windbreaker", "아노락", "anorak", "집업",
               "zip-up", "zipup", "블레이저", "blazer", "트렌치", "trench", "야상"]
TOP_WORDS = ["t", "니트", "knit", "스웨터", "sweater", "티셔츠", "티", "tee", "t-shirt", "블라우스", "blouse", "셔츠", "shirt",
             "맨투맨", "sweatshirt", "후드", "후디", "hoodie", "탑", "top", "슬리브", "sleeve", "폴로", "polo", "나시", "탱크", "tank"]
BOTTOM_WORDS = ["팬츠", "pants", "바지", "슬랙스", "slacks", "트라우저", "trousers", "진", "jeans", "스커트", "skirt", "치마",
                "쇼츠", "shorts", "반바지", "레깅스", "leggings", "조거", "jogger"]


def _has_word(text, word):
    if word.isascii():
        return re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", text) is not None
    return word in text


def name_category(name, fallback):
    low = clean_name(name).lower()
    if any(_has_word(low, w) for w in OUTER_WORDS):
        return "아우터"
    tail = low.split()[-2:]

    def in_tail(words):
        # 영문은 단어 단위, 한글은 단어 끝에 올 때만 ("반팔티", "크롭탑"은 맞고 "빈티지"의 '티'는 아님)
        return any(_has_word(t, w) if w.isascii() else t.endswith(w) for t in tail for w in words)
    if in_tail(TOP_WORDS):
        return "상의"
    if in_tail(BOTTOM_WORDS):
        return "하의"
    return fallback


def item_code(url):
    """상품 URL -> 4자리 코드 (FNV-1a 32비트를 base36으로). 버튼 data-message에 붙여 예전 답변의 버튼도 정확한 상품으로 평가한다.
    "추가 제안", "평가 기록" 노드와 같은 함수여야 한다."""
    h = 2166136261
    for b in str(url or "").encode("utf-8"):
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    out = ""
    for _ in range(4):
        h, r = divmod(h, 36)
        out = "0123456789abcdefghijklmnopqrstuvwxyz"[r] + out
    return out


def feedback_buttons(n, code):
    """Dify 채팅 마크다운의 <button data-message>는 누르면 그 문장을 사용자 메시지로 보낸다 (MarkdownButton -> onSend).
    "1번 좋아 #k3f9"처럼 상품 코드를 붙여, 예전 답변의 버튼을 눌러도 그 상품으로 평가되게 한다."""
    return ('<button data-variant="secondary" data-size="small" data-message="{0}번 좋아 #{1}">👍 좋아요</button> '
            '<button data-variant="secondary" data-size="small" data-message="{0}번 별로 #{1}">👎 별로</button>').format(n, code)


def _match(item, products):
    key = _norm_url(item.get("url"))
    if not key:
        return None, ""
    match = next((p for p in products if p["url"] and _norm_url(p["url"]) == key), None)
    if match is None:
        # url 컬럼 이름을 못 찾은 경우, 청크 본문에 url이 그대로 들어 있는지로 확인
        pattern = re.escape(key) + r"/?(?![\w\-./?=&%#])"
        match = next((p for p in products if re.search(pattern, p["content"])), None)
        if match is not None and not match["url"]:
            match = dict(match, url=str(item.get("url")).strip())
    return match, key


def main(llm_text: str, docs: list, base_shown: list) -> dict:
    shown_before = [str(u) for u in (base_shown or [])]
    data = _parse_llm(llm_text)
    if data is None:
        return {"result": "추천 결과를 정리하지 못했어요. 다시 한 번 질문해 주세요.", "shown_urls": shown_before[-MAX_SHOWN:],
                "shown_items": [], "cards": [], "intro": "", "proposed_count": 0, "kept_count": 0, "dropped_urls": []}

    products = [_product(d) for d in (docs or []) if isinstance(d, dict)]
    matched, seen = [], set()
    # 평가용: LLM이 낸 상품 수, 후보(검색 결과)에 없어서 버린 url. 같은 url 중복이나 MAX_ITEMS를 넘친 상품은 버린 url에 넣지 않는다
    proposed, dropped = 0, []
    for item in data.get("items") or []:
        if not isinstance(item, dict):
            continue
        proposed += 1
        match, key = _match(item, products)
        if match is None:
            dropped.append(str(item.get("url") or "").strip())
            continue  # 검색 결과(후보)에 없는 url은 버린다
        if key in seen:
            continue
        seen.add(key)
        matched.append((item, match, _domain_of(match["url"]) or match["brand"]))

    # 브랜드당 1개를 먼저 채우고, MAX_ITEMS개가 안 될 때만 같은 브랜드의 두 번째 상품을 넣는다
    picked, per_brand = [], {}
    for limit in (1, MAX_PER_BRAND):
        for entry in matched:
            if len(picked) >= MAX_ITEMS:
                break
            if entry in picked or per_brand.get(entry[2], 0) >= limit:
                continue
            picked.append(entry)
            per_brand[entry[2]] = per_brand.get(entry[2], 0) + 1
    picked.sort(key=lambda e: matched.index(e))
    stats = {"proposed_count": proposed, "kept_count": len(picked), "dropped_urls": dropped[:MAX_SHOWN]}

    blocks, items, cards = [], [], []
    for n, (item, match, brand_key) in enumerate(picked, 1):
        name = clean_name(match["name"]) or "상품"
        lines = []
        if match["image"]:
            lines.append("![{}]({})".format(_md_text(name), match["image"]))
        info = " · ".join(x for x in ["**{}. {}**".format(n, name), match["brand"], _format_price(match["price"])] if x)
        lines.append(info)
        reason = _won_text(str(item.get("reason") or "").strip())
        if reason:
            lines.append(reason)
        lines.append("[상품 보러가기]({})".format(match["url"]))
        code = item_code(match["url"])
        lines.append(feedback_buttons(n, code))
        blocks.append("\n\n".join(lines))
        items.append({"n": n, "code": code, "url": match["url"], "domain": _domain_of(match["url"]), "name": name, "explore": False})
        # 웹사이트 카드용 구조화 데이터 ("추가 제안" 노드가 답변 끝 숨은 JSON 블록으로 붙인다)
        cards.append({"n": n, "code": code, "name": name, "brand": match["brand"], "price": _format_price(match["price"]),
                      "image": match["image"], "url": match["url"], "reason": reason,
                      # 웹사이트 취향 지도의 구역(상의·하의·아우터). 후보 정리 노드와 같은 상품명 재확인 규칙
                      "category": name_category(match["name"], match.get("category") or ""), "domain": _domain_of(match["url"])})

    shown = shown_before + [m["url"] for _, m, _ in picked if m["url"] not in shown_before]
    if not blocks:
        return {"result": NOT_FOUND, "shown_urls": shown[-MAX_SHOWN:], "shown_items": [], "cards": [], "intro": NOT_FOUND, **stats}
    intro = _won_text(str(data.get("intro") or "").strip())
    body = "\n\n---\n\n".join(blocks)
    return {"result": "{}\n\n{}".format(intro, body) if intro else body, "shown_urls": shown[-MAX_SHOWN:], "shown_items": items,
            "cards": cards, "intro": intro, **stats}
