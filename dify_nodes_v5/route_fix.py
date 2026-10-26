import json
import re

# insta-crawler/export_brand_similarity.py --yml 로 갱신되는 줄 (직접 고치지 말 것)
BRAND_ALIASES = json.loads(r'''{"niceghostclub.com":{"ko":"나이스고스트클럽","en":"NICE GHOST CLUB","aliases":["나이스고스트클럽","niceghostclub","niceghostclubcom"],"tags":["캐주얼","키치","레이어드","빈티지"]},"mimthe.com":{"ko":"밈더","en":"MIM THE WARDROBE","aliases":["밈더","mimthewardrobe","mimthecom","mimthe"],"tags":["스트릿","캐주얼","밀리터리"]},"secondsalt.com":{"ko":"세컨드솔트","en":"SECONDSALT","aliases":["세컨드솔트","secondsalt","secondsaltcom"],"tags":["페미닌","레이어드","빈티지","스트릿"]},"enzoblues.com":{"ko":"엔조블루스","en":"ENZO BLUES","aliases":["엔조블루스","enzoblues","enzobluescom"],"tags":["70s","아웃도어","빈티지"]},"safarispot.kr":{"ko":"사파리스팟","en":"SAFARISPOT","aliases":["사파리스팟","safarispot","safarispotkr"],"tags":["캐주얼","빈티지"]},"seezul.com":{"ko":"시즐","en":"SEEZUL","aliases":["시즐","seezul","seezulcom"],"tags":["빈티지","데일리","레이어드"]},"lowear.co.kr":{"ko":"로웨어","en":"LOWEAR","aliases":["로웨어","lowear","로웨어lowear","lowearcokr"],"tags":["웨스턴","빈티지","펑크","페미닌"]},"yeetcloset.com":{"ko":"예잇","en":"YEET CLOSET","aliases":["예잇","yeetcloset","yeetclosetcom"],"tags":["데일리","빈티지","레이어드","젠더리스"]},"dirddy.com":{"ko":"더디","en":"DIRDDY","aliases":["더디","dirddy","dirddycom"],"tags":["로맨틱","빈티지","캐주얼"]},"roughneckseoul.com":{"ko":"러프넥","en":"ROUGHNECK","aliases":["러프넥","roughneck","roughneckseoulcom","roughneckseoul"],"tags":["코케트(리본·레이스)","펑크","빈티지"]},"loaxual.com":{"ko":"로액슈얼","en":"LO AXUAL","aliases":["로액슈얼","loaxual","loaxualcom"],"tags":["코케트(리본·레이스)","레이어드","아웃도어","페미닌"]},"999humanity.kr":{"ko":"999휴머니티","en":"999HUMANITY","aliases":["999휴머니티","999humanity","999humanitykr"],"tags":["빈티지","데일리","스트릿"]},"oheshio.com":{"ko":"오헤시오","en":"OHESHIO","aliases":["오헤시오","oheshio","oheshiocom"],"tags":["로맨틱","데일리","레이어드","빈티지"]},"toomuch.tax":{"ko":"투머치택스","en":"TOOMUCHTAX","aliases":["투머치택스","toomuchtax","toomuch"],"tags":["코케트(리본·레이스)","유니크·아방가르드"]},"rockcake.co.kr":{"ko":"락케이크","en":"ROCK CAKE","aliases":["락케이크","rockcake","rockcakecokr"],"tags":["애슬레저","레이어드","놈코어"]},"painorpleasure.co.kr":{"ko":"페인오어플레저","en":"PAIN OR PLEASURE","aliases":["페인오어플레저","painorpleasure","painorpleasurecokr"],"tags":["페미닌","코케트(리본·레이스)","레이어드"]},"kimzisu.com":{"ko":"킴지수","en":"KIMZISU","aliases":["킴지수","kimzisu","kimzisucom"],"tags":["유니크·아방가르드","레이어드","페미닌","오피스·포멀"]},"coyseio.com":{"ko":"코이세이오","en":"COYSEIO","aliases":["코이세이오","coyseio","coyseiocom"],"tags":["빈티지","페미닌","스트릿"]},"tuomio.co.kr":{"ko":"투오미오","en":"TUOMIO","aliases":["투오미오","tuomio","tuomiocokr"],"tags":["코케트(리본·레이스)","레이어드","로맨틱","스트릿"]},"numaochi.imweb.me":{"ko":"누마오치","en":"NUMAOCHI","aliases":["누마오치","numaochi","numaochiimwebme"],"tags":["레이어드","빈티지","걸리시"]},"peanutdays.co.kr":{"ko":"피넛데이즈","en":"PEANUTDAYS","aliases":["피넛데이즈","peanutdays","peanutdayscokr"],"tags":["밀리터리","시티보이","캐주얼","빈티지"]},"keira.co.kr":{"ko":"키이라","en":"KEIRA","aliases":["키이라","keira","keiracokr"],"tags":["70s","빈티지"]},"partimento.com":{"ko":"파르티멘토","en":"PARTIMENTO","aliases":["파르티멘토","partimento","partimentocom"],"tags":["빈티지","레이어드","캐주얼","애슬레저"]},"leus.kr":{"ko":"리어스","en":"LEUS","aliases":["리어스","leus","리어스leus","leuskr"],"tags":["데일리","레이어드","페미닌","미니멀"]},"misekiseoul.kr":{"ko":"미세키서울","en":"MISEKI SEOUL","aliases":["미세키서울","misekiseoul","misekiseoulkr"],"tags":["레이어드","유니크·아방가르드","페미닌","스트릿"]}}''')

# 질문 분류가 "브랜드 유사도"로 보낸 질문 중 실제로는 상품을 찾는 것("코이세이오 니트 있어?")을 상품 추천으로 돌린다.
# 분류는 LLM이라 같은 질문도 가끔 다르게 나온다 (2026-10-21 기준선 n19). 여기서는 규칙으로 한 번 더 본다:
#   수집 브랜드 이름 + 아이템 단어가 있고, "비슷한/같은/느낌/브랜드" 같은 브랜드를 묻는 말이 없으면 상품 추천.
ITEM_WORDS = ["아우터", "자켓", "재킷", "코트", "점퍼", "가디건", "카디건", "블루종", "패딩", "블레이저", "집업", "베스트",
              "하의", "바지", "팬츠", "슬랙스", "데님", "청바지", "스커트", "치마", "쇼츠", "반바지",
              "상의", "티셔츠", "셔츠", "니트", "블라우스", "후드", "후디", "맨투맨", "스웨터", "탑", "나시",
              "jacket", "coat", "pants", "jeans", "skirt", "shirt", "knit", "tee", "hoodie", "sweater", "cardigan"]
BRAND_QUESTION_RE = re.compile(r"비슷|같은|느낌|분위기|무드|감성|브랜드|similar|like")


def _norm(text):
    return re.sub(r"[^0-9a-z가-힣]", "", (text or "").lower())


def main(query: str) -> dict:
    q = _norm(query)
    brand = any(a in q for b in BRAND_ALIASES.values() for a in b["aliases"] if len(a) >= 2)
    item = any(_norm(w) in q for w in ITEM_WORDS)
    asks_brand = bool(BRAND_QUESTION_RE.search((query or "").lower()))
    return {"to_product": "yes" if brand and item and not asks_brand else "no"}
