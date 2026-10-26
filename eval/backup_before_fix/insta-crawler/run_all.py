"""
25개 브랜드 전체 크롤링 오케스트레이터.

- 사이트 단위로 최대 N개 동시 실행 (기본 5개). 같은 사이트 내부 요청 간 딜레이는 유지.
- 상품 처리 결과는 crawler.update_site()가 건건이 state/<domain>.json에 즉시 저장하므로
  중간에 멈춰도 재실행하면 이미 처리한 상품은 건너뛰고 이어서 진행한다.
- 사이트 한 곳의 수집이 끝나면 바로 그 브랜드 문서를 Dify에 업로드한다.
- 로그는 stdout으로 출력 (nohup 등으로 리다이렉트해서 logs/ 에 쌓는 것을 가정).
- 시작 전에 DNS로 네트워크를 확인하고, 안 되면 30초 간격으로 최대 10분 기다린다.
  끝내 안 되면 "네트워크 없음"만 한 번 남기고 종료 (다음 타이머 실행 때 재시도).
- 절반 넘게 실패하면 네트워크 문제로 보고 30분 뒤 실패한 사이트만 한 번 재시도.
"""
import socket
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import crawler
import dify_client
from sites import SITES

MAX_WORKERS = 5
NET_CHECK_HOSTS = ["www.google.com", SITES[0]["domain"]]
NET_WAIT_INTERVAL = 30       # 초
NET_WAIT_MAX = 10 * 60       # 초
RETRY_DELAY = 30 * 60        # 초
_print_lock = threading.Lock()


def log(msg, domain=None):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tag = f"[{domain}]" if domain else ""
    with _print_lock:
        print(f"{ts} {tag} {msg}", flush=True)


def process_site(site):
    domain, brand = site["domain"], site["brand"]
    try:
        state = crawler.update_site(
            domain, brand, force_fallback=site.get("sitemap_fallback", False), log=log
        )
        path, n = crawler.generate_brand_document(domain, brand, state)
        log(f"문서 생성: {path} ({n}개 문단)", domain)

        text = path.read_text(encoding="utf-8")
        if text.strip():
            dify_client.upsert_brand_document(domain, brand, text)
            log("Dify 업로드 완료", domain)
        else:
            log("패션 상품이 0건이라 Dify 업로드 생략", domain)

        return domain, True, n
    except crawler.SuspiciousShrinkError as e:
        log(f"⚠ 경고: 상품 수 급감으로 이 사이트는 건너뜀 (state·Dify 문서 유지). {e}", domain)
        return domain, False, 0
    except Exception as e:
        log(f"오류 발생: {e}\n{traceback.format_exc()}", domain)
        return domain, False, 0


def network_ok():
    for host in NET_CHECK_HOSTS:
        try:
            socket.getaddrinfo(host, 443)
            return True
        except OSError:
            pass
    return False


def wait_for_network():
    """DNS가 될 때까지 NET_WAIT_INTERVAL 간격으로 최대 NET_WAIT_MAX 동안 기다린다."""
    deadline = time.monotonic() + NET_WAIT_MAX
    waited = False
    while not network_ok():
        if time.monotonic() >= deadline:
            return False
        if not waited:
            log(f"네트워크 연결 대기 중... ({NET_WAIT_INTERVAL}초 간격, 최대 {NET_WAIT_MAX // 60}분)")
            waited = True
        time.sleep(NET_WAIT_INTERVAL)
    if waited:
        log("네트워크 연결 확인됨")
    return True


def run_sites(sites, label):
    log(f"{label} {len(sites)}개 사이트 크롤링 시작 (동시 실행 {MAX_WORKERS}개)")
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(process_site, s): s for s in sites}
        for fut in as_completed(futures):
            domain, ok, n = fut.result()
            results.append((domain, ok, n))

    ok_count = sum(1 for _, ok, _ in results if ok)
    fail = [d for d, ok, _ in results if not ok]
    total_items = sum(n for _, ok, n in results if ok)
    log(f"{label} 완료: 성공 {ok_count}/{len(sites)}, 총 업로드 상품 {total_items}건")
    if fail:
        log(f"실패한 사이트: {fail}")
    return fail


def main():
    if not wait_for_network():
        log(f"⚠ 네트워크 없음: {NET_WAIT_MAX // 60}분 기다려도 DNS 확인 실패. 이번 수집은 건너뜀 (다음 실행 때 재시도)")
        return

    fail = run_sites(SITES, "전체")
    if len(fail) * 2 <= len(SITES):
        return

    log(f"⚠ {len(fail)}/{len(SITES)}개 실패 → 네트워크 문제로 보고 {RETRY_DELAY // 60}분 뒤 실패 사이트만 한 번 재시도")
    time.sleep(RETRY_DELAY)
    if not wait_for_network():
        log("⚠ 네트워크 없음: 재시도도 건너뜀 (다음 실행 때 재시도)")
        return
    failed = set(fail)
    run_sites([s for s in SITES if s["domain"] in failed], "재시도")


if __name__ == "__main__":
    main()
