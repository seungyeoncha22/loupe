"""운영 DSL(original/live.yml) + 이 폴더의 노드 코드·프롬프트 → ~/fashion-agent/fashion-bot-v5.yml

  python3 build_nodes.py && python3 assemble_v5.py

바꾸는 것 (자세한 이유는 각 코드 파일의 주석):
  - 검색어 정리: 프롬프트 교체, temperature 0
  - 질문 분류: 브랜드+아이템이면 상품 추천이라는 설명 추가
  - 분류 보정(route_fix) + 상품 찾는 질문인가?(route_check): '브랜드 유사도'로 분류된 질문을 규칙으로 한 번 더 확인
  - 검색 준비: 범위 판정·브랜드 지정·요청 안 한 스타일 제거·취향 검색어
  - 범위 확인(scope_check) → Answer (범위 밖)
  - 취향 검색(kr_taste): 좋아요 브랜드 이름 + 검색어
  - 후보 정리: 브랜드 필터·취향 검색 섞기·n_candidates/max_score/empty_reply
  - 후보 있나?(empty_check) → Answer (후보 없음): 후보 0개면 추천LLM을 부르지 않는다
  - 추천LLM: 지정 브랜드 규칙 한 줄
  - 상품 정보 붙이기: proposed_count/kept_count/dropped_urls, brand_only, 주소 오타 구제
"""
import copy
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "fashion-bot-v5.yml"

d = yaml.safe_load((HERE / "original" / "live.yml").read_text(encoding="utf-8"))
g = d["workflow"]["graph"]
N = {n["id"]: n for n in g["nodes"]}
SEARCH_LLM = "1792044191923"
KR_MAIN = "1790664707557"


def read(name):
    return (HERE / name).read_text(encoding="utf-8")


def out_types(**types):
    return {k: {"children": None, "type": t} for k, t in types.items()}


def var(name, selector, value_type):
    return {"value_selector": selector, "value_type": value_type, "variable": name}


def add_node(node_id, data, x, y, height=90):
    g["nodes"].append({"data": dict(data, selected=False), "height": height, "id": node_id, "position": {"x": x, "y": y},
                       "positionAbsolute": {"x": x, "y": y}, "selected": False, "sourcePosition": "right",
                       "targetPosition": "left", "type": "custom", "width": 242, "zIndex": 0})
    N[node_id] = g["nodes"][-1]


def edge(source, target, handle="source"):
    g["edges"].append({"data": {"isInIteration": False, "isInLoop": False, "sourceType": N[source]["data"]["type"],
                                "targetType": N[target]["data"]["type"]},
                       "id": f"{source}-{handle}-{target}-target", "selected": False, "source": source, "sourceHandle": handle,
                       "target": target, "targetHandle": "target", "type": "custom", "zIndex": 0})


def drop_edge(source, target, handle="source"):
    before = len(g["edges"])
    g["edges"] = [e for e in g["edges"] if not (e["source"] == source and e["target"] == target and e.get("sourceHandle") == handle)]
    assert len(g["edges"]) == before - 1, (source, target, handle)


def if_node(title, selector, op, value, var_type):
    return {"cases": [{"case_id": "true", "conditions": [{"comparison_operator": op, "id": f"{selector[0]}-{selector[1]}-cond",
                                                          "value": value, "varType": var_type, "variable_selector": selector}],
                       "logical_operator": "and"}], "title": title, "type": "if-else"}


# 자리 만들기: 범위 확인(본 검색 앞), 후보 있나?(추천LLM 앞)가 들어갈 칸만큼 오른쪽 노드를 민다
for n in g["nodes"]:
    x = n["position"]["x"]
    shift = (300 if x >= 2300 else 0) + (300 if x >= 2900 else 0)
    n["position"]["x"] = n["positionAbsolute"]["x"] = x + shift

# ---- 1. 검색어 정리
N[SEARCH_LLM]["data"]["prompt_template"][0]["text"] = read("search_prompt.txt")
N[SEARCH_LLM]["data"]["model"]["completion_params"]["temperature"] = 0

# ---- 2. 질문 분류 + 분류 보정
cls = json.loads(read("classify.json"))
N["classify"]["data"]["classes"] = cls["classes"]
N["classify"]["data"]["instruction"] = cls["instruction"]
add_node("route_fix", {"code": read("route_fix.py"), "code_language": "python3", "title": "분류 보정", "type": "code",
                       "outputs": out_types(to_product="string"), "variables": [var("query", ["sys", "query"], "string")]},
         1700, -1050)
add_node("route_check", if_node("상품 찾는 질문인가?", ["route_fix", "to_product"], "is", "yes", "string"), 2000, -1050, 123)
drop_edge("classify", "brand_sim", "1")
edge("classify", "route_fix", "1")
edge("route_fix", "route_check")
edge("route_check", SEARCH_LLM, "true")
edge("route_check", "brand_sim", "false")

# ---- 3. 검색 준비 + 범위 확인
prep = N["prep"]["data"]
prep["code"] = read("prep.py")
prep["outputs"].update(out_types(scope="string", scope_reply="string", include="array[string]", brand_only="string",
                                 taste_query="string"))
add_node("scope_check", if_node("범위 확인", ["prep", "scope"], "is", "ok", "string"), 2300, -450, 123)
add_node("answer_scope", {"answer": "{{#prep.scope_reply#}}", "title": "Answer (범위 밖)", "type": "answer", "variables": []},
         2600, -150, 124)
for target in (KR_MAIN, "kr_broad"):
    drop_edge("prep", target)
edge("prep", "scope_check")
edge("scope_check", KR_MAIN, "true")
edge("scope_check", "kr_broad", "true")
edge("scope_check", "answer_scope", "false")

# ---- 4. 취향 검색
taste = copy.deepcopy(N["kr_broad"]["data"])
taste.update(title="취향 검색 (좋아요 브랜드)", query_variable_selector=["prep", "taste_query"])
add_node("kr_taste", taste, 2600, -750, 89)
edge("scope_check", "kr_taste", "true")
edge("kr_taste", "candidates")

# ---- 5. 후보 정리 + 후보 있나?
cand = N["candidates"]["data"]
cand["code"] = read("candidates.py")
cand["variables"] += [var("docs_taste", ["kr_taste", "result"], "array[object]"),
                      var("include", ["prep", "include"], "array[string]")]
cand["outputs"].update(out_types(n_candidates="number", max_score="number", empty_reply="string"))
add_node("empty_check", if_node("후보 있나?", ["candidates", "n_candidates"], ">", "0", "number"), 3200, -450, 123)
add_node("answer_empty", {"answer": "{{#candidates.relax_note#}}{{#candidates.empty_reply#}}", "title": "Answer (후보 없음)",
                          "type": "answer", "variables": []}, 3500, -150, 124)
drop_edge("candidates", "llm")
edge("candidates", "empty_check")
edge("empty_check", "llm", "true")
edge("empty_check", "answer_empty", "false")

# ---- 6. 추천LLM, 상품 정보 붙이기
N["llm"]["data"]["prompt_template"][0]["text"] = read("llm_prompt.txt")
fmt = N["format"]["data"]
fmt["code"] = read("format.py")
fmt["variables"].append(var("brand_only", ["prep", "brand_only"], "string"))
fmt["outputs"].update(out_types(proposed_count="number", kept_count="number", dropped_urls="array[string]"))

# ---- 검증: 연결선 끝이 모두 있는 노드인지, 코드 노드 입력과 main() 인자가 맞는지
ids = {n["id"] for n in g["nodes"]}
assert all(e["source"] in ids and e["target"] in ids for e in g["edges"])
assert len({e["id"] for e in g["edges"]}) == len(g["edges"])
for n in g["nodes"]:
    data = n["data"]
    if data["type"] == "code":
        ns = {}
        exec(data["code"], ns)
        args = list(ns["main"].__code__.co_varnames[:ns["main"].__code__.co_argcount])
        assert sorted(args) == sorted(v["variable"] for v in data["variables"]), (n["id"], args)

OUT.write_text(yaml.dump(d, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")
print(f"{OUT}: 노드 {len(g['nodes'])}개, 연결 {len(g['edges'])}개")
