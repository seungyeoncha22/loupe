"""25개 브랜드의 유사 브랜드 상위 5개를 미리 계산해 JSON으로 저장하고, Dify 워크플로 Code 노드에 넣는다.

brand_profiles.json(build_brand_profiles.py 결과)과 brand_similarity.similar_brands()를 그대로 쓴다.
상품 텍스트 임베딩은 state/_brand_embeddings.json 캐시를 쓰므로, 상품 목록이 바뀐 브랜드만 Ollama로 다시 계산한다.

  python3 export_brand_similarity.py                                  # brand_similarity_top5.json만 생성
  python3 export_brand_similarity.py --yml ~/fashion-agent/fashion-bot-v2.yml   # + 워크플로 Code 노드 갱신
  python3 export_brand_similarity.py --web-only                       # 유사도 재계산 없이 웹사이트 brands.json만 다시 쓰기

워크플로에서는 세 Code 노드가 이 데이터를 쓴다 (각 노드의 한 줄을 통째로 바꾼다):
  - "유사 브랜드" 노드의  BRAND_DATA = ...     (유사 브랜드 + 별칭 + 브랜드별 대표 상품)
  - "검색 준비", "평가 기록" 노드의 BRAND_ALIASES = ...  (브랜드 매칭용 별칭)
                          STYLE_ALIASES = ...  (질문 속 스타일 표현 -> 태그, style_tags.md + style_aliases.md)
  - "후보 정리" 노드의    BRAND_TAGS = ...     (브랜드별 스타일 태그, 가산점용)
                          NON_APPAREL = ...    (상품명 끝에 있으면 잡화로 보고 빼는 말)
  - "추가 제안" 노드의    EXTRAS_DATA = ...    (브랜드 요약, 태그 IDF, 이웃 태그, 탐색 추천 후보)
웹사이트용으로 ~/fashion-agent/web/public/brands.json도 만든다 (브랜드 디깅, 발견 진행 표시).
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from brand_similarity import PROFILES_JSON, similar_brands
from build_brand_profiles import load_products, product_key, won
from crawler import DOC_CATEGORY_MAP, KEYWORD_OVERRIDE, absolute_image_url, display_name
from sites import SITES

ROOT = Path(__file__).parent
OUT_JSON = ROOT / "brand_similarity_top5.json"
STYLE_TAGS_MD = ROOT / "style_tags.md"
STYLE_ALIASES_MD = ROOT / "style_aliases.md"
TOP = 5
REP_MIN, REP_MAX = 4, 6  # 브랜드별 대표 상품 수

# state 카테고리가 상의/하의/아우터여도 상품명에 이 말이 있으면 의류가 아닌 것으로 본다.
# (2026-10-16 "스트링 데님 더스트백"이 '데님' 때문에 바지로, "FLEECE REVERSIBLE HOOD MUFFLER"가 아우터로 분류돼 있었음)
NON_APPAREL_WORDS = [kw for cat, kws in KEYWORD_OVERRIDE if cat in ("신발", "가방", "액세서리") for kw in kws] + [
    "더스트백", "dust bag", "dustbag", "머플러", "넥워머", "워머", "warmer", "키링", "keyring", "key ring", "브로치",
    "brooch", "헤어핀", "헤어밴드", "곱창밴드", "스크런치", "scrunchie", "쿠션", "cushion", "타월", "towel", "우산",
    "umbrella", "마스크", "스티커", "sticker", "기프트", "gift card", "쇼핑백", "포장", "레그워머", "암워머", "토시",
    "버킷햇", "bucket hat", "카드홀더", "card holder", "cardholder", "지갑",
]
COLOR_WORDS = {
    "mustard", "mocka", "coral", "peach", "butter", "lemon", "lime", "lilac", "sage", "teal", "terracotta", "chocolate", "espresso", "taupe", "sand", "stone", "ecru", "nude", "rose", "berry", "cobalt", "emerald", "forest", "maroon", "plum", "mauve", "rust", "tan", "vanilla", "smoke", "slate", "violet", "aqua", "turquoise", "melon", "cocoa", "latte", "milk", "oat", "pistachio", "머스타드", "코랄", "피치", "버터", "레몬", "라임", "라일락", "세이지", "테라코타", "초코", "에스프레소", "토프", "샌드", "스톤", "에크루", "누드", "로즈", "베리", "코발트", "에메랄드", "포레스트", "마룬", "플럼", "모브", "러스트", "바닐라", "스모크", "바이올렛", "아쿠아", "터콰이즈", "멜론", "코코아", "라떼", "오트밀", "피스타치오", "하늘", "보라", "노랑", "빨강", "초록", "갈색", "검정", "흰색", "네온", "아이스블루", "스카이블루",
    "black", "white", "ivory", "cream", "beige", "gray", "grey", "charcoal", "navy", "blue", "skyblue", "khaki",
    "brown", "pink", "red", "burgundy", "wine", "green", "olive", "mint", "yellow", "orange", "purple", "lavender",
    "melange", "indigo", "camel", "mocha", "oatmeal", "silver", "gold", "multi", "denim", "sky", "light", "dark",
    "deep", "pale", "dusty", "off", "블랙", "화이트", "아이보리", "크림", "베이지", "그레이", "차콜", "네이비", "블루",
    "카키", "브라운", "핑크", "레드", "버건디", "그린", "민트", "옐로우", "퍼플", "라벤더", "멜란지",
}
NOTICE_RE = re.compile(r"\d*\s*차\s*재입고|재입고|리오더|re-?order|\d*(?:st|nd|rd|th)?\s*re-?stock|주문\s*폭주|"
                       r"예약\s*(?:배송|판매|주문)|당일\s*발송|품절\s*임박|한정\s*수량|\d+\s*(?:colou?rs?|컬러|色)", re.I)


def _has_word(name, kw):
    low, kw = name.lower(), kw.lower()
    if all(ord(c) < 128 for c in kw):
        return re.search(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])", low) is not None
    return kw in low


def is_apparel(name):
    """아이템 종류는 대개 상품명 끝에 오므로 색상 등을 뗀 이름의 마지막 두 단어만 본다.
    ("HOOD MUFFLER", "데님 더스트백"은 걸러지고, "Ring zip hoodie", "CAP SLEEVE TEE"는 통과)"""
    tail = " ".join(clean_name(name).split()[-2:])
    return not any(_has_word(tail, kw) for kw in NON_APPAREL_WORDS)


def clean_name(name):
    """표시용 상품명: 앞의 [..] 접두어, 괄호 속 색상·안내 문구("(블랙)", "(2차 재입고)"), "_PINK" 같은 색상 꼬리,
    끝에 붙은 색상 단어("... JACKET BLACK", "... LIGHT GREEN")를 뗀다. 다 떼고 비면 원래 이름."""
    s = display_name(name)
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]|\{[^}]*\}", " ", s)
    s = re.split(r"\s*_\s*", s)[0]
    s = NOTICE_RE.sub(" ", s)
    tokens = s.split()
    while len(tokens) > 2 and tokens[-1].lower().strip("-/,.") in COLOR_WORDS:
        tokens.pop()
    s = " ".join(tokens).strip(" -/,.")
    return s or display_name(name)


# 상품명으로 카테고리 재확인 (워크플로 "후보 정리" 노드의 name_category와 같은 기준).
# 아우터 단어가 이름 어디든 있으면 아우터, 없으면 끝 두 단어로 상의/하의, 둘 다 아니면 state 카테고리.
OUTER_WORDS = ["카디건", "가디건", "cardigan", "자켓", "재킷", "jacket", "코트", "coat", "점퍼", "jumper", "블루종", "blouson",
               "파카", "parka", "패딩", "padding", "무스탕", "mustang", "바람막이", "windbreaker", "아노락", "anorak", "집업",
               "zip-up", "zipup", "블레이저", "blazer", "트렌치", "trench", "야상"]
TOP_WORDS = ["t", "니트", "knit", "스웨터", "sweater", "티셔츠", "티", "tee", "t-shirt", "블라우스", "blouse", "셔츠", "shirt",
             "맨투맨", "sweatshirt", "후드", "후디", "hoodie", "탑", "top", "슬리브", "sleeve", "폴로", "polo", "나시", "탱크", "tank"]
BOTTOM_WORDS = ["팬츠", "pants", "바지", "슬랙스", "slacks", "트라우저", "trousers", "진", "jeans", "스커트", "skirt", "치마",
                "쇼츠", "shorts", "반바지", "레깅스", "leggings", "조거", "jogger"]


def name_category(name, fallback):
    low = clean_name(name).lower()
    if any(_has_word(low, w) for w in OUTER_WORDS):
        return "아우터"
    tail = low.split()[-2:]

    def in_tail(words):
        return any(_has_word(t, w) if w.isascii() else t.endswith(w) for t in tail for w in words)
    if in_tail(TOP_WORDS):
        return "상의"
    if in_tail(BOTTOM_WORDS):
        return "하의"
    return fallback


def norm(s):
    return re.sub(r"[^0-9a-z가-힣]", "", (s or "").lower())


def aliases(domain, site_brand, ko, en):
    """한글명, 영문명, sites.py 표기("로웨어(LOWEAR)"는 괄호 안팎 둘 다), 도메인, 도메인 앞부분."""
    names = [ko, en, site_brand, domain, domain.split(".")[0]]
    names += re.split(r"[()]", site_brand or "")
    out = []
    for n in names:
        a = norm(n)
        if len(a) >= 2 and a not in out:
            out.append(a)
    return out


def reason_text(src_ko, src_price, r):
    parts = []
    if r["shared_tags"]:
        parts.append(f"{'·'.join(r['shared_tags'])} 무드가 겹치고")
    parts.append(f"상품명·설명 분위기가 {r['n_compared']}개 브랜드 중 {r['text_rank']}번째로 가까워요.")
    # 브랜드명 받침에 따라 와/과가 갈리므로 조사 없이 쓴다.
    feel = "비슷한 가격대" if r["price"] >= 0.7 else "가격대 차이 있음"
    parts.append(f"가격 중앙값은 {won(r['price_median'])}원이에요 ({src_ko} {won(src_price)}원, {feel}).")
    return " ".join(parts)


def representative_products(domain, profile):
    """브랜드 태그의 근거 상품(evidence) 중 상의/하의/아우터이고 이미지가 있는 것을 태그 순서대로 최대 REP_MAX개.
    REP_MIN개가 안 되면 같은 브랜드의 상의/하의/아우터 상품을 카테고리가 고루 섞이게 최근 순으로 채운다.
    색상 변형(product_key가 같은 것)은 하나만 넣는다."""
    by_url = {}
    state = json.loads((ROOT / "state" / f"{domain}.json").read_text(encoding="utf-8"))["products"]
    for url, p in state.items():
        if p.get("category") in DOC_CATEGORY_MAP and p.get("image_url") and is_apparel(p["name"]):
            by_url[url] = p
    by_name, by_key = {}, {}
    for url, p in by_url.items():
        by_name.setdefault(p["name"].strip(), url)
        by_key.setdefault(product_key(p["name"]), url)

    picked, keys = [], set()

    def add(url, source):
        key = product_key(by_url[url]["name"])
        if url in [x[0] for x in picked] or key in keys:
            return
        keys.add(key)
        picked.append((url, source))

    for tag in profile["tags"]:
        for name in tag.get("evidence", []):
            url = by_name.get(name.strip()) or by_key.get(product_key(name))
            if url:
                add(url, "evidence")
    if len(picked) < REP_MIN:
        rest = sorted(by_url, key=lambda u: by_url[u].get("first_seen", ""), reverse=True)
        cats_used = [by_url[u]["category"] for u, _ in picked]
        for cat_pass in range(2):  # 1회차: 아직 없는 카테고리 우선, 2회차: 아무거나
            for url in rest:
                if len(picked) >= REP_MIN:
                    break
                cat = name_category(by_url[url]["name"], DOC_CATEGORY_MAP[by_url[url]["category"]])
                if cat_pass == 0 and cat in [DOC_CATEGORY_MAP[c] for c in cats_used]:
                    continue
                add(url, "fill")
                cats_used.append(by_url[url]["category"])

    out = []
    for url, source in picked[:REP_MAX]:
        p = by_url[url]
        out.append({
            "name": clean_name(p["name"]), "price": p.get("price"), "url": url,
            "image": absolute_image_url(p["image_url"], url),
            "category": name_category(p["name"], DOC_CATEGORY_MAP[p["category"]]), "source": source,
        })
    return out


def style_aliases(brand_tags):
    """질문 속 표현(정규화) -> 태그 목록. 브랜드가 실제로 가진 태그만 남긴다.
    출처: style_tags.md의 태그 이름과 첫 두 키워드(대개 한글명, 영문명), style_aliases.md의 표현."""
    used = {t for tags in brand_tags.values() for t in tags}
    table = {}

    def put(expr, tags):
        key = norm(expr)
        tags = [t for t in tags if t in used]
        if len(key) >= 2 and tags:
            table.setdefault(key, [])
            table[key] += [t for t in tags if t not in table[key]]

    for line in STYLE_TAGS_MD.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^- \*\*(.+?)\*\*:\s*(.*)$", line)
        if m:
            tag = m.group(1)
            for part in [tag] + re.split(r"[()·]", tag) + [k.strip() for k in m.group(2).split(",")[:2]]:
                put(part, [tag])
    for line in STYLE_ALIASES_MD.read_text(encoding="utf-8").splitlines():
        m = re.match(r'^- "(.+?)"\s*→\s*(.+)$', line)
        if m:
            put(m.group(1), [t.strip() for t in m.group(2).split(",")])
    return table


def explore_pool(domain, profile):
    """탐색 추천 후보: 브랜드 태그마다 그 태그의 근거 상품 중 의류(상의/하의/아우터)이고 이미지가 있는 것."""
    state = json.loads((ROOT / "state" / f"{domain}.json").read_text(encoding="utf-8"))["products"]
    by_name, by_key = {}, {}
    for url, p in state.items():
        if p.get("category") in DOC_CATEGORY_MAP and p.get("image_url") and is_apparel(p["name"]):
            by_name.setdefault(p["name"].strip(), url)
            by_key.setdefault(product_key(p["name"]), url)
    out = []
    for tag in profile["tags"]:
        for name in tag.get("evidence", []):
            url = by_name.get(name.strip()) or by_key.get(product_key(name))
            if not url:
                continue
            p = state[url]
            out.append({
                "tag": tag["tag"], "domain": domain, "name": clean_name(p["name"]), "price": p.get("price"),
                "url": url, "image": absolute_image_url(p["image_url"], url), "category": name_category(p["name"], DOC_CATEGORY_MAP[p["category"]]),
            })
    return out


def tag_neighbors(brand_tags):
    """태그 -> [[이웃 태그, 같은 브랜드에 함께 붙은 횟수]] (횟수 내림차순). 탐색 추천에서 '비슷하지만 새로운' 스타일을 고를 때 쓴다."""
    counts = {}
    for tags in brand_tags.values():
        for a in tags:
            for b in tags:
                if a != b:
                    counts.setdefault(a, {}).setdefault(b, 0)
                    counts[a][b] += 1
    return {a: sorted(([b, n] for b, n in nb.items()), key=lambda x: -x[1]) for a, nb in counts.items()}


def extras_data(data):
    """'추가 제안' Code 노드용: 브랜드 요약, 태그 IDF, 이웃 태그, 탐색 후보."""
    brands = data["brands"]
    return {
        "tag_idf": data["tag_idf"],
        "neighbors": tag_neighbors({d: b["tags"] for d, b in brands.items()}),
        "brands": {d: {"ko": b["ko"], "en": b["en"], "url": b["url"], "tags": b["tags"],
                       "product": (b["products"] or [None])[0]} for d, b in brands.items()},
        "pool": [x for b in brands.values() for x in b["explore"]],
    }


def build():
    profiles_all = json.loads(PROFILES_JSON.read_text(encoding="utf-8"))
    profiles = profiles_all["brands"]
    site_brand = {s["domain"]: s["brand"] for s in SITES}
    brands = {}
    for domain, p in profiles.items():
        if not p["n_products"]:
            continue
        brands[domain] = {
            "ko": p["ko"], "en": p["en"], "url": f"https://{domain}",
            "aliases": aliases(domain, site_brand.get(domain, ""), p["ko"], p["en"]),
            "tags": [t["tag"] for t in p["tags"]],
            "products": representative_products(domain, p),
            "explore": explore_pool(domain, p),
        }
    for domain, b in brands.items():
        r = similar_brands(domain, top=TOP, log=lambda m: print(m, file=sys.stderr))
        b["similar"] = [{
            "domain": x["domain"], "ko": x["ko"], "en": brands[x["domain"]]["en"],
            "url": brands[x["domain"]]["url"], "score": x["score"],
            "common_tags": x["shared_tags"], "reason": reason_text(b["ko"], r["price_median"], x),
        } for x in r["results"]]
    brand_tags = {d: b["tags"] for d, b in brands.items()}
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        # 태그 IDF (모든 브랜드에서 같은 값). 스타일로 브랜드 찾기에서 IDF 가중 코사인 순위에 쓴다.
        "tag_idf": {t: round(w, 3) for t, w in profiles_all["tag_idf"].items() if any(t in v for v in brand_tags.values())},
        "style_aliases": style_aliases(brand_tags),
        "brands": brands,
    }


def compact(obj):
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    assert "'''" not in s and "\n" not in s
    return s


def patch_yml(path, data):
    alias_only = {d: {"ko": b["ko"], "en": b["en"], "aliases": b["aliases"], "tags": b["tags"]} for d, b in data["brands"].items()}
    brand_tags = {d: b["tags"] for d, b in data["brands"].items()}
    # 유사 브랜드 노드에는 탐색 후보(explore)가 필요 없으므로 빼서 넣는다
    brand_data = dict(data, brands={d: {k: v for k, v in b.items() if k != "explore"} for d, b in data["brands"].items()})
    text = Path(path).read_text(encoding="utf-8")
    for var, obj in (("BRAND_DATA", brand_data), ("BRAND_ALIASES", alias_only),
                     ("STYLE_ALIASES", data["style_aliases"]), ("BRAND_TAGS", brand_tags),
                     ("NON_APPAREL", sorted({w.lower() for w in NON_APPAREL_WORDS})),
                     ("EXTRAS_DATA", extras_data(data))):
        line = f"{var} = json.loads(r'''{compact(obj)}''')"
        text, n = re.subn(rf"^(\s*){var} = .*$", lambda m: m.group(1) + line, text, flags=re.M)
        if n < 1:   # BRAND_ALIASES, STYLE_ALIASES는 "검색 준비"와 "평가 기록" 두 노드에 있다
            raise SystemExit(f"{path}: '{var} = ' 줄이 없음")
    Path(path).write_text(text, encoding="utf-8")
    print(f"워크플로 갱신: {path}")


WEB_JSON = Path.home() / "fashion-agent" / "web" / "public" / "brands.json"


def write_web(data, path=WEB_JSON):
    """loupe 웹사이트용 브랜드 데이터 (취향 지도의 브랜드 디깅, '25개 브랜드 중 N개 발견').
    웹사이트 폴더가 없으면 건너뛴다."""
    if not path.parent.parent.exists():
        return
    path.parent.mkdir(exist_ok=True)
    web = {"total": len(data["brands"]), "generated_at": data["generated_at"], "brands": {
        d: {"ko": b["ko"], "en": b["en"], "url": b["url"], "tags": b["tags"],
            "products": [{k: x[k] for k in ("name", "price", "image", "url", "category")} for x in b["products"]],
            # 디깅 후보 미리보기: 비슷한 이유, 공통 무드(겹치는 스타일 태그)
            "similar": [{"domain": s["domain"], "reason": s.get("reason", ""), "mood": s.get("common_tags", [])} for s in b["similar"]]}
        for d, b in data["brands"].items()}}
    path.write_text(json.dumps(web, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"웹사이트 브랜드 데이터: {path} ({len(web['brands'])}개)")


def main():
    if "--web-only" in sys.argv:
        # 유사도는 다시 계산하지 않고, 저장된 결과로 웹사이트 데이터만 다시 쓴다
        write_web(json.loads(OUT_JSON.read_text(encoding="utf-8")))
        return
    data = build()
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"저장: {OUT_JSON} (브랜드 {len(data['brands'])}개)")
    write_web(data)
    if "--yml" in sys.argv:
        patch_yml(sys.argv[sys.argv.index("--yml") + 1], data)


if __name__ == "__main__":
    main()
