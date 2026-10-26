import json
import re

# insta-crawler/export_brand_similarity.py --yml 로 갱신되는 줄 (직접 고치지 말 것)
BRAND_TAGS = json.loads(r'''{"niceghostclub.com":["캐주얼","키치","레이어드","빈티지"],"mimthe.com":["스트릿","캐주얼","밀리터리"],"secondsalt.com":["페미닌","레이어드","빈티지","스트릿"],"enzoblues.com":["70s","아웃도어","빈티지"],"safarispot.kr":["캐주얼","빈티지"],"seezul.com":["빈티지","데일리","레이어드"],"lowear.co.kr":["웨스턴","빈티지","펑크","페미닌"],"yeetcloset.com":["데일리","빈티지","레이어드","젠더리스"],"dirddy.com":["로맨틱","빈티지","캐주얼"],"roughneckseoul.com":["코케트(리본·레이스)","펑크","빈티지"],"loaxual.com":["코케트(리본·레이스)","레이어드","아웃도어","페미닌"],"999humanity.kr":["빈티지","데일리","스트릿"],"oheshio.com":["로맨틱","데일리","레이어드","빈티지"],"toomuch.tax":["코케트(리본·레이스)","유니크·아방가르드"],"rockcake.co.kr":["애슬레저","레이어드","놈코어"],"painorpleasure.co.kr":["페미닌","코케트(리본·레이스)","레이어드"],"kimzisu.com":["유니크·아방가르드","레이어드","페미닌","오피스·포멀"],"coyseio.com":["빈티지","페미닌","스트릿"],"tuomio.co.kr":["코케트(리본·레이스)","레이어드","로맨틱","스트릿"],"numaochi.imweb.me":["레이어드","빈티지","걸리시"],"peanutdays.co.kr":["밀리터리","시티보이","캐주얼","빈티지"],"keira.co.kr":["70s","빈티지"],"partimento.com":["빈티지","레이어드","캐주얼","애슬레저"],"leus.kr":["데일리","레이어드","페미닌","미니멀"],"misekiseoul.kr":["레이어드","유니크·아방가르드","페미닌","스트릿"]}''')
BRAND_ALIASES = json.loads(r'''{"niceghostclub.com":{"ko":"나이스고스트클럽","en":"NICE GHOST CLUB","aliases":["나이스고스트클럽","niceghostclub","niceghostclubcom"],"tags":["캐주얼","키치","레이어드","빈티지"]},"mimthe.com":{"ko":"밈더","en":"MIM THE WARDROBE","aliases":["밈더","mimthewardrobe","mimthecom","mimthe"],"tags":["스트릿","캐주얼","밀리터리"]},"secondsalt.com":{"ko":"세컨드솔트","en":"SECONDSALT","aliases":["세컨드솔트","secondsalt","secondsaltcom"],"tags":["페미닌","레이어드","빈티지","스트릿"]},"enzoblues.com":{"ko":"엔조블루스","en":"ENZO BLUES","aliases":["엔조블루스","enzoblues","enzobluescom"],"tags":["70s","아웃도어","빈티지"]},"safarispot.kr":{"ko":"사파리스팟","en":"SAFARISPOT","aliases":["사파리스팟","safarispot","safarispotkr"],"tags":["캐주얼","빈티지"]},"seezul.com":{"ko":"시즐","en":"SEEZUL","aliases":["시즐","seezul","seezulcom"],"tags":["빈티지","데일리","레이어드"]},"lowear.co.kr":{"ko":"로웨어","en":"LOWEAR","aliases":["로웨어","lowear","로웨어lowear","lowearcokr"],"tags":["웨스턴","빈티지","펑크","페미닌"]},"yeetcloset.com":{"ko":"예잇","en":"YEET CLOSET","aliases":["예잇","yeetcloset","yeetclosetcom"],"tags":["데일리","빈티지","레이어드","젠더리스"]},"dirddy.com":{"ko":"더디","en":"DIRDDY","aliases":["더디","dirddy","dirddycom"],"tags":["로맨틱","빈티지","캐주얼"]},"roughneckseoul.com":{"ko":"러프넥","en":"ROUGHNECK","aliases":["러프넥","roughneck","roughneckseoulcom","roughneckseoul"],"tags":["코케트(리본·레이스)","펑크","빈티지"]},"loaxual.com":{"ko":"로액슈얼","en":"LO AXUAL","aliases":["로액슈얼","loaxual","loaxualcom"],"tags":["코케트(리본·레이스)","레이어드","아웃도어","페미닌"]},"999humanity.kr":{"ko":"999휴머니티","en":"999HUMANITY","aliases":["999휴머니티","999humanity","999humanitykr"],"tags":["빈티지","데일리","스트릿"]},"oheshio.com":{"ko":"오헤시오","en":"OHESHIO","aliases":["오헤시오","oheshio","oheshiocom"],"tags":["로맨틱","데일리","레이어드","빈티지"]},"toomuch.tax":{"ko":"투머치택스","en":"TOOMUCHTAX","aliases":["투머치택스","toomuchtax","toomuch"],"tags":["코케트(리본·레이스)","유니크·아방가르드"]},"rockcake.co.kr":{"ko":"락케이크","en":"ROCK CAKE","aliases":["락케이크","rockcake","rockcakecokr"],"tags":["애슬레저","레이어드","놈코어"]},"painorpleasure.co.kr":{"ko":"페인오어플레저","en":"PAIN OR PLEASURE","aliases":["페인오어플레저","painorpleasure","painorpleasurecokr"],"tags":["페미닌","코케트(리본·레이스)","레이어드"]},"kimzisu.com":{"ko":"킴지수","en":"KIMZISU","aliases":["킴지수","kimzisu","kimzisucom"],"tags":["유니크·아방가르드","레이어드","페미닌","오피스·포멀"]},"coyseio.com":{"ko":"코이세이오","en":"COYSEIO","aliases":["코이세이오","coyseio","coyseiocom"],"tags":["빈티지","페미닌","스트릿"]},"tuomio.co.kr":{"ko":"투오미오","en":"TUOMIO","aliases":["투오미오","tuomio","tuomiocokr"],"tags":["코케트(리본·레이스)","레이어드","로맨틱","스트릿"]},"numaochi.imweb.me":{"ko":"누마오치","en":"NUMAOCHI","aliases":["누마오치","numaochi","numaochiimwebme"],"tags":["레이어드","빈티지","걸리시"]},"peanutdays.co.kr":{"ko":"피넛데이즈","en":"PEANUTDAYS","aliases":["피넛데이즈","peanutdays","peanutdayscokr"],"tags":["밀리터리","시티보이","캐주얼","빈티지"]},"keira.co.kr":{"ko":"키이라","en":"KEIRA","aliases":["키이라","keira","keiracokr"],"tags":["70s","빈티지"]},"partimento.com":{"ko":"파르티멘토","en":"PARTIMENTO","aliases":["파르티멘토","partimento","partimentocom"],"tags":["빈티지","레이어드","캐주얼","애슬레저"]},"leus.kr":{"ko":"리어스","en":"LEUS","aliases":["리어스","leus","리어스leus","leuskr"],"tags":["데일리","레이어드","페미닌","미니멀"]},"misekiseoul.kr":{"ko":"미세키서울","en":"MISEKI SEOUL","aliases":["미세키서울","misekiseoul","misekiseoulkr"],"tags":["레이어드","유니크·아방가르드","페미닌","스트릿"]}}''')
NON_APPAREL = json.loads(r'''["backpack","bag","beanie","belt","boots","bracelet","brooch","bucket hat","cap","card holder","cardholder","clutch","crossbody","cushion","dust bag","dustbag","earring","eyeglasses","eyewear","flats","gift card","glasses","gloves","hat","heels","jewelry","key ring","keyring","loafer","muffler","necklace","pouch","ring","sandal","scarf","scrunchie","shoe","shoes","sneaker","sneakers","socks","sticker","sunglasses","tote","towel","umbrella","wallet","warmer","가방","곱창밴드","구두","귀걸이","기프트","넥워머","더스트백","레그워머","로퍼","마스크","머플러","모자","목걸이","반지","백팩","버킷햇","벨트","볼캡","부츠","브로치","비니","샌들","선글라스","쇼핑백","숄더백","스니커즈","스카프","스크런치","스티커","슬리퍼","신발","안경","암워머","양말","에코백","우산","워머","장갑","주얼리","지갑","카드홀더","쿠션","크로스백","클러치","키링","타월","토시","토트백","파우치","팔찌","포장","헤어밴드","헤어핀","힐"]''')

MAX_CANDIDATES = 12   # 추천LLM에 넘기는 전체 후보 수
MIN_CANDIDATES = 3    # 같은 카테고리 후보가 이보다 적으면 조건을 단계적으로 푼다
STYLE_BONUS = 0.06    # 질문 스타일이 브랜드 태그에 있을 때 태그 하나당 가산점 (검색 점수는 대개 0.3~0.55)
MAX_STYLE_MATCH = 2
BRAND_PREF_W = 0.04   # 취향 점수(브랜드 -3~3) 1점당 가감
TAG_PREF_W = 0.02     # 취향 점수(태그 -3~3)를 그 브랜드 태그에 대해 합한 값 1점당 가감
TASTE_MAX = 3         # v5: 취향 검색(좋아요 브랜드 이름 + 검색어)에서 후보에 섞는 상품 수 (브랜드당 1개)
PREF_CAP = 0.12       # 취향으로 움직이는 점수 상한 (검색 점수 차이를 다 뒤집지 않도록)


def _field(content, name):
    m = re.search(r"^\s*" + name + r"\s*:\s*(.+)$", content or "", re.M | re.I)
    return m.group(1).strip() if m else ""


def _is_apparel(name):
    """지식베이스에 상의/하의/아우터로 잘못 분류된 잡화(가방, 지갑, 모자, 머플러 등)를 거른다.
    아이템 종류는 대개 상품명 끝에 오므로 괄호·"_색상"을 뗀 이름의 마지막 두 단어만 본다."""
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", name or "")
    tail = " ".join(re.split(r"\s*_\s*", s)[0].lower().split()[-2:])
    for w in NON_APPAREL:
        if all(ord(c) < 128 for c in w):
            if re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", tail):
                return False
        elif w in tail:
            return False
    return True


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


def variant_key(domain, name):
    """색상 변형을 같은 상품으로 보는 키: 브랜드 + 정리된 이름 (대소문자·공백·기호 무시)."""
    return domain + "|" + re.sub(r"[^0-9a-z가-힣]", "", clean_name(name).lower())


def _domain_of(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return re.sub(r"^www\.", "", m.group(1).lower()) if m else ""


def with_taste(prefs, taste):
    """웹사이트가 새 대화 첫 메시지에 넘긴 '저장된 취향'(입력 변수 taste, JSON 문자열)을 바닥에 깔고
    이 대화에서 한 평가(prefs)를 더한다. Dify는 첫 메시지의 입력을 대화 내내 유지하므로 모든 턴에서 같은 taste가 온다."""
    prefs = prefs if isinstance(prefs, dict) else {}
    try:
        base = json.loads(taste) if taste else {}
    except Exception:
        base = {}
    base = base if isinstance(base, dict) else {}
    out = dict(prefs)
    for k in ("brands", "tags"):
        merged = {}
        for src in (base.get(k) or {}, prefs.get(k) or {}):
            for key, v in (src.items() if isinstance(src, dict) else []):
                try:
                    merged[key] = round(max(-3.0, min(3.0, float(merged.get(key, 0)) + float(v))), 2)
                except (TypeError, ValueError):
                    pass
        out[k] = merged
    out["liked_urls"] = list(dict.fromkeys(list(base.get("liked_urls") or []) + list(prefs.get("liked_urls") or [])))[-30:]
    return out


def _pref_bonus(domain, prefs):
    brand = float((prefs.get("brands") or {}).get(domain, 0))
    tags = sum(float((prefs.get("tags") or {}).get(t, 0)) for t in BRAND_TAGS.get(domain, []))
    return max(-PREF_CAP, min(PREF_CAP, BRAND_PREF_W * brand + TAG_PREF_W * tags))


def prefs_text(prefs):
    """추천LLM에 넘기는 사용자 취향 기록. 점수가 0보다 큰 스타일·브랜드를 점수 높은 순으로 3개씩.
    브랜드 키는 도메인이라 BRAND_ALIASES의 한글 이름으로 바꾼다. 남는 게 없으면 빈 문자열."""
    def top(scores):
        out = []
        for key, v in (scores.items() if isinstance(scores, dict) else []):
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
            if v > 0:
                out.append((key, v))
        out.sort(key=lambda x: -x[1])
        return [key for key, _ in out[:3]]

    styles = top(prefs.get("tags"))
    brands = [(BRAND_ALIASES.get(d) or {}).get("ko") or (BRAND_ALIASES.get(d) or {}).get("en") or d
              for d in top(prefs.get("brands"))]
    lines = []
    if styles:
        lines.append("좋아요한 스타일: " + ", ".join(styles))
    if brands:
        lines.append("좋아요·저장한 브랜드: " + ", ".join(brands))
    return "\n".join(lines)


def _josa(word, with_final, without_final):
    """받침 있으면 with_final, 없으면 without_final ("아우터는", "빈티지 상품은")."""
    last = (word or " ")[-1]
    if "가" <= last <= "힣":
        return with_final if (ord(last) - 0xAC00) % 28 else without_final
    return without_final


def _relax_note(stage, styles, category, any_shown):
    label = " ".join(x for x in [" ".join(styles[:2]), category] if x) or "조건에 맞는 상품"
    if stage == "brand2":
        return "{}{} 많지 않아서 같은 브랜드에서도 골라봤어요.".format(label, _josa(label, "이", "가"))
    if stage == "broad":
        if any_shown:
            return "{}{} 거의 다 보여드려서 비슷한 무드까지 넓혀봤어요.".format(label, _josa(label, "은", "는"))
        return "{}{} 많지 않아서 비슷한 무드까지 넓혀봤어요.".format(label, _josa(label, "이", "가"))
    return ""


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def ui_block(payload):
    return "\n\n<!--fashion-ui " + json.dumps(dict(payload, v=1), ensure_ascii=False) + " -->"


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
         item_index: dict, docs_taste: list, include: list) -> dict:
    """검색 결과에서 제외 브랜드·이미 보여준 상품·별로 상품·잡화를 빼고, 질문 카테고리가 있으면 그 카테고리만 남긴다.
    점수 = 검색 점수 + 질문 스타일이 브랜드 태그에 있을 때 가산 + 취향(평가) 가감. 평가는 검색어가 아니라 이 점수로만 반영한다.
    같은 카테고리 후보가 MIN_CANDIDATES보다 적으면 단계적으로 푼다:
      1) 기본: 본 검색, 브랜드당 1개
      2) brand2: 본 검색, 브랜드당 2개까지
      3) broad: 스타일 단어를 뺀 넓힌 검색(docs_broad) 결과를 뒤에 붙인다 (같은 카테고리, 스타일 가산점은 유지)
    브랜드는 상품 URL의 도메인으로 판별한다."""
    excluded = {re.sub(r"^www\.", "", str(d).lower()) for d in (exclude or [])}
    prefs = with_taste(prefs, taste)
    # v5: 브랜드를 지정한 질문은 그 브랜드 상품만 (검색 준비의 include)
    include = [re.sub(r"^www\.", "", str(d).lower()) for d in (include or [])]
    shown = {str(u).strip() for u in (exclude_urls or [])}
    disliked = {str(u).strip() for u in (prefs.get("disliked_urls") or [])}
    styles = [str(s) for s in (styles or [])]
    seen = set()
    counts = {"brand": 0, "shown": 0, "disliked": 0, "not_apparel": 0, "category": 0, "variant": 0, "not_included": 0}
    # 이미 보여준 상품의 색상 변형도 뺀다 (보여준 상품 이름은 item_index에 있다)
    shown_keys = {variant_key(v.get("domain", ""), v.get("name", "")) for v in (item_index or {}).values()
                  if isinstance(v, dict) and v.get("url") in shown}
    picked_keys = set()

    def usable(source_docs, offset):
        out = []
        for i, doc in enumerate(source_docs or []):
            if not isinstance(doc, dict):
                continue
            content = str(doc.get("content") or "")
            url = _field(content, "URL")
            domain = _domain_of(url)
            if not url or url in seen:
                continue
            seen.add(url)
            if domain in excluded:
                counts["brand"] += 1
                continue
            if include and domain not in include:
                counts["not_included"] += 1
                continue
            if url in shown:
                counts["shown"] += 1
                continue
            if url in disliked:
                counts["disliked"] += 1
                continue
            name = _field(content, "상품명")
            if not _is_apparel(name):
                counts["not_apparel"] += 1
                continue
            if category and name_category(name, _field(content, "카테고리")) != category:
                counts["category"] += 1
                continue
            key = variant_key(domain, name)
            if key in shown_keys:
                counts["variant"] += 1
                continue
            score = float((doc.get("metadata") or {}).get("score") or 0)
            matched = [s for s in styles if s in BRAND_TAGS.get(domain, [])][:MAX_STYLE_MATCH]
            out.append({"content": content, "url": url, "domain": domain, "rank": offset + i, "key": key,
                        "score": score + STYLE_BONUS * len(matched) + _pref_bonus(domain, prefs), "matched": matched})
        out.sort(key=lambda x: (-x["score"], x["rank"]))
        return out

    def take(pool, picked, per_brand, limit):
        for it in pool:
            if len(picked) >= MAX_CANDIDATES:
                break
            if it in picked or it["key"] in picked_keys or per_brand.get(it["domain"], 0) >= limit:
                continue
            picked.append(it)
            picked_keys.add(it["key"])
            per_brand[it["domain"]] = per_brand.get(it["domain"], 0) + 1

    main_pool = usable(docs, 0)
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

    kept = [{"content": it["content"], "url": it["url"]} for it in picked]
    # 추천LLM에는 이미지 줄을 빼고, 추천 이유에 쓸 브랜드 무드(브랜드 스타일 태그)를 붙여 넘긴다.
    # "태그"라는 말을 넘기면 답변에 그대로 나와서 "브랜드 무드"라고 이름 붙인다.
    context = "\n\n".join(
        re.sub(r"^\s*이미지\s*:.*$\n?", "", it["content"], flags=re.M).strip()
        + "\n브랜드 무드: " + (", ".join(BRAND_TAGS.get(it["domain"], [])) or "없음")
        for it in picked)
    note = _relax_note(stage, styles, category, bool(shown)) if picked else ""
    scores = [_num((d.get("metadata") or {}).get("score")) for d in (docs or []) if isinstance(d, dict)]
    return {
        # v5: '후보 있나?' 분기용 후보 수, 본 검색 최고 유사도(기록용, 분기 기준값은 아직 정하지 않음), 후보 0개일 때 답변
        "n_candidates": len(kept),
        "max_score": round(max(scores), 4) if scores else 0.0,
        "empty_reply": "" if kept else _empty_reply(include, styles, category, bool(docs or docs_broad)),
        "context": context,
        "candidates": kept,
        "relax_note": (note + "\n\n") if note else "",
        "prefs_text": prefs_text(prefs),
        "summary": "본 검색 {}건 + 넓힌 검색 {}건 / 제외 브랜드 {} · 이미 보여준 상품 {} · 별로 {} · 잡화 {} · 다른 카테고리 {} · 색상 변형 {}건 제외 / 단계 {} / 후보 {}건 (브랜드 {}곳, 넓힌 검색에서 {}건, 스타일 가산 {}건, 취향 반영 {}건)".format(
            len(docs or []), len(docs_broad or []), counts["brand"], counts["shown"], counts["disliked"], counts["not_apparel"],
            counts["category"], counts["variant"], stage, len(kept), len(per_brand),
            sum(1 for it in picked if 1000 <= it["rank"] < 2000),
            sum(1 for it in picked if it["matched"]), sum(1 for it in picked if _pref_bonus(it["domain"], prefs)))
        + " / 지정 브랜드 밖 {}건 제외 · 취향 검색에서 {}건".format(counts["not_included"], sum(1 for it in picked if it["rank"] >= 2000)),
    }
