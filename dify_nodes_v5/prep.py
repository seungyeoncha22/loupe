import json
import re

# insta-crawler/export_brand_similarity.py --yml 로 갱신되는 줄 (직접 고치지 말 것)
BRAND_ALIASES = json.loads(r'''{"niceghostclub.com":{"ko":"나이스고스트클럽","en":"NICE GHOST CLUB","aliases":["나이스고스트클럽","niceghostclub","niceghostclubcom"],"tags":["캐주얼","키치","레이어드","빈티지"]},"mimthe.com":{"ko":"밈더","en":"MIM THE WARDROBE","aliases":["밈더","mimthewardrobe","mimthecom","mimthe"],"tags":["스트릿","캐주얼","밀리터리"]},"secondsalt.com":{"ko":"세컨드솔트","en":"SECONDSALT","aliases":["세컨드솔트","secondsalt","secondsaltcom"],"tags":["페미닌","레이어드","빈티지","스트릿"]},"enzoblues.com":{"ko":"엔조블루스","en":"ENZO BLUES","aliases":["엔조블루스","enzoblues","enzobluescom"],"tags":["70s","아웃도어","빈티지"]},"safarispot.kr":{"ko":"사파리스팟","en":"SAFARISPOT","aliases":["사파리스팟","safarispot","safarispotkr"],"tags":["캐주얼","빈티지"]},"seezul.com":{"ko":"시즐","en":"SEEZUL","aliases":["시즐","seezul","seezulcom"],"tags":["빈티지","데일리","레이어드"]},"lowear.co.kr":{"ko":"로웨어","en":"LOWEAR","aliases":["로웨어","lowear","로웨어lowear","lowearcokr"],"tags":["웨스턴","빈티지","펑크","페미닌"]},"yeetcloset.com":{"ko":"예잇","en":"YEET CLOSET","aliases":["예잇","yeetcloset","yeetclosetcom"],"tags":["데일리","빈티지","레이어드","젠더리스"]},"dirddy.com":{"ko":"더디","en":"DIRDDY","aliases":["더디","dirddy","dirddycom"],"tags":["로맨틱","빈티지","캐주얼"]},"roughneckseoul.com":{"ko":"러프넥","en":"ROUGHNECK","aliases":["러프넥","roughneck","roughneckseoulcom","roughneckseoul"],"tags":["코케트(리본·레이스)","펑크","빈티지"]},"loaxual.com":{"ko":"로액슈얼","en":"LO AXUAL","aliases":["로액슈얼","loaxual","loaxualcom"],"tags":["코케트(리본·레이스)","레이어드","아웃도어","페미닌"]},"999humanity.kr":{"ko":"999휴머니티","en":"999HUMANITY","aliases":["999휴머니티","999humanity","999humanitykr"],"tags":["빈티지","데일리","스트릿"]},"oheshio.com":{"ko":"오헤시오","en":"OHESHIO","aliases":["오헤시오","oheshio","oheshiocom"],"tags":["로맨틱","데일리","레이어드","빈티지"]},"toomuch.tax":{"ko":"투머치택스","en":"TOOMUCHTAX","aliases":["투머치택스","toomuchtax","toomuch"],"tags":["코케트(리본·레이스)","유니크·아방가르드"]},"rockcake.co.kr":{"ko":"락케이크","en":"ROCK CAKE","aliases":["락케이크","rockcake","rockcakecokr"],"tags":["애슬레저","레이어드","놈코어"]},"painorpleasure.co.kr":{"ko":"페인오어플레저","en":"PAIN OR PLEASURE","aliases":["페인오어플레저","painorpleasure","painorpleasurecokr"],"tags":["페미닌","코케트(리본·레이스)","레이어드"]},"kimzisu.com":{"ko":"킴지수","en":"KIMZISU","aliases":["킴지수","kimzisu","kimzisucom"],"tags":["유니크·아방가르드","레이어드","페미닌","오피스·포멀"]},"coyseio.com":{"ko":"코이세이오","en":"COYSEIO","aliases":["코이세이오","coyseio","coyseiocom"],"tags":["빈티지","페미닌","스트릿"]},"tuomio.co.kr":{"ko":"투오미오","en":"TUOMIO","aliases":["투오미오","tuomio","tuomiocokr"],"tags":["코케트(리본·레이스)","레이어드","로맨틱","스트릿"]},"numaochi.imweb.me":{"ko":"누마오치","en":"NUMAOCHI","aliases":["누마오치","numaochi","numaochiimwebme"],"tags":["레이어드","빈티지","걸리시"]},"peanutdays.co.kr":{"ko":"피넛데이즈","en":"PEANUTDAYS","aliases":["피넛데이즈","peanutdays","peanutdayscokr"],"tags":["밀리터리","시티보이","캐주얼","빈티지"]},"keira.co.kr":{"ko":"키이라","en":"KEIRA","aliases":["키이라","keira","keiracokr"],"tags":["70s","빈티지"]},"partimento.com":{"ko":"파르티멘토","en":"PARTIMENTO","aliases":["파르티멘토","partimento","partimentocom"],"tags":["빈티지","레이어드","캐주얼","애슬레저"]},"leus.kr":{"ko":"리어스","en":"LEUS","aliases":["리어스","leus","리어스leus","leuskr"],"tags":["데일리","레이어드","페미닌","미니멀"]},"misekiseoul.kr":{"ko":"미세키서울","en":"MISEKI SEOUL","aliases":["미세키서울","misekiseoul","misekiseoulkr"],"tags":["레이어드","유니크·아방가르드","페미닌","스트릿"]}}''')
STYLE_ALIASES = json.loads(r'''{"캐주얼":["캐주얼"],"casual":["캐주얼"],"데일리":["데일리"],"daily":["데일리"],"놈코어":["놈코어"],"normcore":["놈코어"],"시티보이":["시티보이"],"cityboy":["시티보이"],"스트릿":["스트릿"],"street":["스트릿"],"펑크":["펑크"],"punk":["펑크"],"밀리터리":["밀리터리"],"military":["밀리터리"],"미니멀":["미니멀"],"minimal":["미니멀"],"오피스포멀":["오피스·포멀"],"오피스":["오피스·포멀"],"포멀":["오피스·포멀"],"office":["오피스·포멀"],"페미닌":["페미닌"],"feminine":["페미닌"],"걸리시":["걸리시"],"girlish":["걸리시"],"로맨틱":["로맨틱"],"romantic":["로맨틱"],"코케트리본레이스":["코케트(리본·레이스)"],"코케트":["코케트(리본·레이스)","걸리시"],"리본":["코케트(리본·레이스)"],"레이스":["코케트(리본·레이스)"],"coquette":["코케트(리본·레이스)"],"빈티지":["빈티지"],"vintage":["빈티지"],"70s":["70s"],"70년대":["70s"],"웨스턴":["웨스턴","빈티지"],"western":["웨스턴"],"애슬레저":["애슬레저"],"athleisure":["애슬레저"],"아웃도어":["아웃도어"],"outdoor":["아웃도어"],"키치":["키치"],"kitsch":["키치"],"유니크아방가르드":["유니크·아방가르드"],"유니크":["유니크·아방가르드"],"아방가르드":["유니크·아방가르드"],"avantgarde":["유니크·아방가르드"],"젠더리스":["젠더리스"],"genderless":["젠더리스"],"레이어드":["레이어드"],"layered":["레이어드"],"캐주얼한":["캐주얼","데일리"],"편하게입는옷":["캐주얼","데일리"],"막입기좋은":["캐주얼","데일리"],"부담없는스타일":["캐주얼"],"매일입는옷":["데일리","캐주얼"],"기본템":["데일리","놈코어"],"출근룩말고평소룩":["데일리","캐주얼"],"무난한":["데일리","미니멀"],"꾸안꾸":["데일리"],"꾸민듯안꾸민듯":["데일리"],"힘뺀스타일":["미니멀"],"평범한데멋있는":["놈코어","미니멀"],"튀지않는옷":["놈코어","미니멀"],"무지위주":["놈코어","미니멀"],"기본에충실한":["놈코어"],"시티보이룩":["시티보이"],"뽀빠이잡지느낌":["시티보이"],"도쿄남자스타일":["시티보이"],"넉넉한셔츠에치노":["시티보이"],"대학생룩":["데일리"],"새내기느낌":["걸리시"],"아메카지":["빈티지"],"데님많이입는":["빈티지"],"스트릿한":["스트릿","캐주얼"],"힙한":["스트릿"],"길거리패션":["스트릿"],"그래픽티위주":["스트릿","키치"],"힙합스타일":["스트릿"],"통넓은바지에큰티":["스트릿"],"래퍼느낌":["스트릿"],"스케이터룩":["스트릿"],"보드타는애들스타일":["스트릿"],"스케이트보드감성":["스트릿"],"그런지":["빈티지"],"찢어지고낡은느낌":["빈티지"],"다크하고거친":["펑크"],"펑키한":["펑크","스트릿"],"락스타일":["펑크"],"징박힌":["펑크"],"반항적인":["펑크"],"기능성옷":["아웃도어"],"등산복을일상복으로":["아웃도어"],"아웃도어감성":["아웃도어"],"카펜터팬츠스타일":["스트릿"],"군복느낌":["밀리터리"],"카고바지":["밀리터리","스트릿"],"카모무늬":["밀리터리","스트릿"],"야상좋아하는":["밀리터리","캐주얼"],"미니멀한":["미니멀"],"깔끔한":["미니멀"],"심플한옷":["미니멀","데일리"],"장식없는":["미니멀","놈코어"],"모던한":["미니멀"],"차도녀":["오피스·포멀"],"쿨한블랙위주":["미니멀"],"유행안타는":["미니멀"],"단정한":["오피스·포멀"],"조용한럭셔리":["미니멀"],"출근룩":["오피스·포멀","미니멀"],"회사갈때입을":["오피스·포멀"],"하객룩":["오피스·포멀","페미닌"],"정장스타일":["오피스·포멀"],"여성스러운":["페미닌","로맨틱"],"페미닌한":["페미닌"],"여리여리한":["페미닌"],"우아한":["페미닌"],"소녀느낌":["걸리시"],"걸리시한":["걸리시"],"귀여운여자애느낌":["걸리시"],"일본소녀느낌":["걸리시"],"러블리한":["걸리시"],"사랑스러운":["로맨틱"],"하트들어간":["키치"],"귀여운":["걸리시"],"로맨틱한":["로맨틱","페미닌"],"꽃무늬":["로맨틱"],"데이트룩":["로맨틱","페미닌"],"청순한":["페미닌"],"첫사랑느낌":["걸리시"],"깨끗하고맑은":["미니멀"],"하얀블라우스느낌":["페미닌"],"발레코어":["페미닌"],"발레리나같은":["페미닌"],"레그워머신는":["레이어드"],"볼레로코디":["레이어드"],"리본달린":["코케트(리본·레이스)"],"레이스좋아하는":["코케트(리본·레이스)","로맨틱"],"공주느낌":["코케트(리본·레이스)"],"빈티지한":["빈티지"],"구제느낌":["빈티지"],"낡은듯한워싱":["빈티지"],"물빠진색감":["빈티지"],"레트로한":["빈티지"],"옛날느낌":["빈티지"],"복고풍":["70s"],"y2k":["걸리시"],"반짝이큐빅":["키치"],"70년대느낌":["70s"],"부츠컷바지":["70s","웨스턴"],"히피같은":["70s"],"슬립드레스":["미니멀"],"90년대미니멀":["미니멀"],"카우보이느낌":["웨스턴"],"프린지달린":["웨스턴"],"일본잡지스타일":["레이어드"],"자연주의레이어드":["레이어드"],"프랑스여자느낌":["페미닌"],"성수동느낌":["스트릿"],"스포티한":["캐주얼"],"블록코어":["스트릿"],"운동복을일상복으로":["애슬레저"],"요가복느낌":["애슬레저"],"레깅스코디":["애슬레저"],"캠핑룩":["아웃도어"],"플리스입는":["아웃도어","캐주얼"],"내추럴한":["미니멀"],"키치한":["키치","스트릿"],"캐릭터들어간":["키치"],"유치한듯귀여운":["키치"],"독특한":["유니크·아방가르드"],"개성있는":["유니크·아방가르드","스트릿"],"비대칭디자인":["유니크·아방가르드"],"남녀공용":["젠더리스"],"커플로입을":["젠더리스","캐주얼"],"남자도입을수있는":["젠더리스"],"중성적인":["젠더리스","미니멀"],"겹쳐입는":["레이어드"],"레이어링스타일":["레이어드"]}''')

CATEGORIES = ["상의", "하의", "아우터"]
CATEGORY_WORDS = {
    "아우터": ["아우터", "자켓", "재킷", "코트", "점퍼", "가디건", "카디건", "블루종", "패딩", "블레이저", "outer", "jacket", "coat", "cardigan", "blazer"],
    "하의": ["하의", "바지", "팬츠", "슬랙스", "데님", "청바지", "스커트", "치마", "pants", "skirt", "jeans"],
    "상의": ["상의", "티셔츠", "셔츠", "니트", "블라우스", "후드", "맨투맨", "탑", "top", "shirt", "tee", "knit"],
}
# 브랜드 이름 바로 뒤에 오는 제외 표현 ("seezul 제외하고", "시즐 빼고", "로웨어 말고")
NEGATIONS_AFTER = ["제외", "빼고", "빼줘", "빼서", "말고", "없이", "아닌", "외에", "외의"]
# 브랜드 이름 바로 앞에 오는 제외 표현 ("except seezul", "without seezul")
NEGATIONS_BEFORE = ["except", "without", "excluding", "exclude"]
# 이전 조건을 이어받는 후속 질문 표현
FOLLOWUP_RE = re.compile(r"다른|더\s*(?:보여|추천|찾아|있|줘)|도\s*더|또\b|또\s|추가로|비슷한\s*거|more|another|other")
MAX_SHOWN = 30


def _norm(text):
    return re.sub(r"[^0-9a-z가-힣]", "", (text or "").lower())


def _domain_of(name):
    """LLM이 뽑은 브랜드 이름 -> 도메인. 정확히 같은 별칭을 먼저, 없으면 서로 포함 관계로 찾는다."""
    n = _norm(name)
    if len(n) < 2:
        return ""
    for domain, brand in BRAND_ALIASES.items():
        if n in brand["aliases"]:
            return domain
    for domain, brand in BRAND_ALIASES.items():
        if any(a in n or (len(n) >= 3 and n in a) for a in brand["aliases"]):
            return domain
    return ""


# 브랜드 이름 사이를 잇는 말 ("A이랑 B", "A, B", "A랑 B", "A와 B", "A 및 B"). 정규화 후라 쉼표·공백은 사라진다.
CONNECTOR_RE = re.compile(r"(?:이랑|랑|와|과|하고|및|그리고|또는|이나|나|and|or)*")
# "A 말고 B도" 다음에 오면 B를 제외가 아니라 포함으로 보는 말
INCLUDE_AFTER = ["보여", "추천", "포함", "넣어", "찾아", "알려"]


def _mentions(q):
    """정규화된 질문 속 브랜드 언급 [(start, end, domain)]. 겹치면 긴 별칭을 우선한다."""
    hits = []
    for domain, brand in BRAND_ALIASES.items():
        for alias in brand["aliases"]:
            for m in re.finditer(re.escape(alias), q):
                hits.append((m.start(), m.end(), domain))
    hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))
    out, last_end = [], -1
    for h in hits:
        if h[0] >= last_end:
            out.append(h)
            last_end = h[1]
    return out


def _excluded_in_text(query):
    """질문 원문에서 '브랜드(들) + 제외 표현'을 찾는다 (LLM이 놓친 경우 대비).
    - "seezul이랑 로웨어 제외", "A, B 빼고", "A랑 B 말고": 잇는 말로 묶인 브랜드를 한 묶음으로 보고 묶음 뒤의 제외 표현을 모두에 적용
    - "except A and B": 묶음 앞의 제외 표현
    - "A 말고 B도": 앞에서 제외된 브랜드가 있고 B 바로 뒤가 "도"이면 B도 제외 (뒤에 "보여줘/추천" 같은 말이 오면 포함으로 봄)"""
    q = _norm(query)
    mentions = _mentions(q)
    groups = []
    for m in mentions:
        if groups and CONNECTOR_RE.fullmatch(q[groups[-1][-1][1]:m[0]]):
            groups[-1].append(m)
        else:
            groups.append([m])
    found = []
    for group in groups:
        start, end = group[0][0], group[-1][1]
        after, before = q[end:end + 10], q[max(0, start - 12):start]
        if any(neg in after for neg in NEGATIONS_AFTER) or any(before.endswith(neg) for neg in NEGATIONS_BEFORE):
            found += [m[2] for m in group]
        elif found and q[end:end + 1] == "도" and not any(w in q[end:end + 10] for w in INCLUDE_AFTER):
            found += [m[2] for m in group]
    return found


def _styles_in(texts):
    """스타일 표현 -> 브랜드 태그 (style_tags.md 태그명 + style_aliases.md 표현). 긴 표현부터 매칭."""
    found = []
    for text in texts:
        q = _norm(text)
        for expr in sorted(STYLE_ALIASES, key=len, reverse=True):
            if expr in q:
                found += [t for t in STYLE_ALIASES[expr] if t not in found]
    return found


def _category_of(value, query):
    """질문의 아이템 단어가 한 카테고리만 가리키면 그것을 LLM 값보다 우선한다. 후보 정리는 상품명으로 카테고리를 다시 보는데
    (가디건·카디건 → 아우터) LLM은 가디건을 상의로 내기도 해서, 둘이 어긋나면 검색된 가디건이 전부 '다른 카테고리'로 빠졌다
    (2026-10-22 수정 후 평가 n14 "10만원 이하 가디건"). 여러 카테고리 단어가 섞이면 ("데님 자켓") LLM 값을 쓴다."""
    value = str(value or "").strip()
    q = (query or "").lower()
    hits = [cat for cat, words in CATEGORY_WORDS.items() if any(w in q for w in words)]
    if len(hits) == 1:
        return hits[0]
    if value in CATEGORIES:
        return value
    for cat, words in CATEGORY_WORDS.items():
        if any(w in q for w in words):
            return cat
    return ""


def _uniq(items):
    out = []
    for x in items:
        if x and x not in out:
            out.append(x)
    return out


# "다음 추천 보기" 버튼 / 직접 입력
NEXT_RE = re.compile(r"다음\s*추천|다음\s*거\s*보여|다음\s*꺼|next")
RATE_CLASS = "취향 평가"   # 질문 분류의 class_label (분류 라벨을 바꾸면 여기도 바꿀 것)
# 넓힌 검색어: 스타일 단어 없이 카테고리만 ("후보 정리"가 같은 카테고리 후보가 모자랄 때 쓴다)
BROAD_QUERY = {
    "아우터": "아우터 자켓 재킷 코트 점퍼 블루종 가디건 베스트 outer jacket coat cardigan",
    "하의": "하의 바지 팬츠 슬랙스 데님 청바지 스커트 치마 pants trousers jeans skirt",
    "상의": "상의 티셔츠 셔츠 니트 블라우스 맨투맨 후드 탑 top shirt tee knit blouse",
}   # 질문 분류의 "취향 평가": 직전 추천을 모두 평가해서 바로 다음 추천으로 넘어온 경우


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


def _reaction(prefs):
    """이어서 추천할 때 첫 줄. 평가가 없으면 넣지 않는다."""
    tags = prefs.get("tags") or {}
    liked = [t for t, v in sorted(tags.items(), key=lambda x: -float(x[1])) if float(v) > 0][:2]
    if liked:
        return "지금까지 평가를 반영해서 {} 쪽으로 골라봤어요.".format("·".join(liked))
    if any(float(v) < 0 for v in (prefs.get("brands") or {}).values()):
        return "별로라고 하신 쪽은 줄여서 골라봤어요."
    return ""


def _strip_liked_styles(search, styles, prefs):
    """평가는 점수로만 반영한다. 검색어에 사용자가 직접 요청하지 않은 '좋아한 스타일' 단어가 들어가 있으면 뺀다."""
    liked = {t for t, v in (prefs.get("tags") or {}).items() if float(v) > 0} - set(styles)
    if not liked:
        return search
    words = [w for w in search.split() if not any(t in STYLE_ALIASES.get(_norm(w), []) for t in liked)]
    return " ".join(words) or search


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
OUT_EXCEPT_RE = re.compile(r"부츠\s*컷|boots?\s*cut|bootcut|드레스\s*셔츠|dress\s*shirts?", re.I)
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
    return "\n\n<!--fashion-ui " + json.dumps(dict(payload, v=1), ensure_ascii=False) + " -->"


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


def main(llm_text: str, query: str, class_label: str, last_search: dict, shown_urls: list, prefs: dict, taste: str) -> dict:
    data = {}
    match = re.search(r"\{.*\}", llm_text or "", re.S)
    if match:
        try:
            data = json.loads(match.group(0))
        except Exception:
            data = {}
    last = last_search if isinstance(last_search, dict) else {}
    prefs = with_taste(prefs, taste)

    # 다음 추천: 평가를 다 해서 넘어왔거나 "다음 추천 보기"를 누른 경우. 이전 조건 그대로, 이미 보여준 상품만 뺀다.
    continue_last = bool(last.get("query")) and (str(class_label).strip() == RATE_CLASS or bool(NEXT_RE.search(query or "")))
    followup = continue_last or (bool(last.get("query")) and (bool(data.get("followup")) or bool(FOLLOWUP_RE.search(query or ""))))
    if continue_last:
        search = str(last.get("query"))
        styles = list(last.get("styles") or [])
        category = str(last.get("category") or "")
        exclude = list(last.get("exclude") or [])
        include = list(last.get("include") or [])
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

    lines = []
    if continue_last:
        lines.append("같은 조건으로 다음 추천을 이어가요. 사용자의 평가는 목록 순서에 이미 반영했어요.")
    elif followup:
        lines.append("이전 질문을 이어받은 후속 질문이에요. 이전에 보여준 상품 {}개는 목록에서 이미 뺐어요.".format(len(exclude_urls)))
    lines.append("스타일: " + (", ".join(styles) if styles else "지정 없음"))
    lines.append("카테고리: " + (category or "지정 없음"))
    lines.append("제외 브랜드: " + (", ".join(BRAND_ALIASES[d]["ko"] for d in exclude) if exclude else "없음"))
    if include:
        lines.append("지정 브랜드: " + ", ".join(BRAND_ALIASES[d]["ko"] for d in include)
                     + " (목록에는 이 브랜드 상품만 있어요. 같은 브랜드에서 3개까지 골라도 돼요)")
    reaction = _reaction(prefs) if continue_last else ""
    return {
        "search_query": search,
        "broad_query": broad,
        "exclude": exclude,
        "exclude_urls": exclude_urls,
        "styles": styles,
        "category": category,
        "conditions": "\n".join(lines),
        "next_search": {"query": search, "styles": styles, "category": category, "exclude": exclude, "include": include},
        "base_shown": exclude_urls,
        "reaction": (reaction + "\n\n") if reaction else "",
        # v5: 범위 확인 (ok / category / brand). ok가 아니면 '범위 확인' 분기가 검색 없이 scope_reply로 답한다
        "scope": scope,
        "scope_reply": _scope_reply(scope, item, unknown, styles) if scope != "ok" else "",
        "include": include,
        "brand_only": "yes" if include else "no",
        "taste_query": search if include else _taste_query(search, prefs, exclude),
    }
