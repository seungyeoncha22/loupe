"""Dify 콘솔 API로 기존 앱의 워크플로를 DSL(YAML)로 덮어쓰고 게시한다.

앱 API 키(app-...)로는 워크플로를 바꿀 수 없어서 콘솔 계정으로 로그인한다 (웹 화면에서 'DSL 가져오기'로 덮어쓰는 것과 같음).
.env에 아래 세 값이 있어야 동작하고, 없으면 아무것도 하지 않는다:
  DIFY_CONSOLE_EMAIL=...       Dify 로그인 이메일
  DIFY_CONSOLE_PASSWORD=...    Dify 로그인 비밀번호
  DIFY_APP_ID=...              덮어쓸 "패션 추천 봇" 앱 ID (앱 주소 /app/<ID>/workflow 의 <ID>)
"""
import base64
import http.cookiejar
import json
import urllib.error
import urllib.request

from dify_client import load_env

CONSOLE_BASE_URL = "http://localhost/console/api"


class ConsoleError(RuntimeError):
    pass


def settings(app_key="DIFY_APP_ID"):
    env = load_env()
    keys = ("DIFY_CONSOLE_EMAIL", "DIFY_CONSOLE_PASSWORD", app_key)
    missing = [k for k in keys if not env.get(k)]
    return ({k: env.get(k, "") for k in keys}, missing)


class Console:
    def __init__(self, email, password):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf = None
        # 웹 화면과 같은 방식: 비밀번호는 base64로 보낸다 (Dify FieldEncryption)
        self._call("POST", "/login", {
            "email": email, "password": base64.b64encode(password.encode()).decode(), "remember_me": False})
        self.csrf = next((c.value for c in self.jar if c.name.endswith("csrf_token")), None)
        if not self.csrf:
            raise ConsoleError("로그인은 됐지만 csrf_token 쿠키를 받지 못함")

    def _call(self, method, path, body=None):
        req = urllib.request.Request(CONSOLE_BASE_URL + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None)
        req.add_header("Content-Type", "application/json")
        if self.csrf:
            req.add_header("X-CSRF-Token", self.csrf)
        try:
            with self.opener.open(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, (json.loads(raw) if raw.strip() else {})
        except urllib.error.HTTPError as e:
            raise ConsoleError(f"{method} {path} → {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}") from None

    def import_yaml(self, app_id, yaml_text):
        """기존 앱(app_id)을 YAML로 덮어쓴다. DSL 버전 확인이 필요하다고 하면(pending) 확인까지 한다."""
        _, result = self._call("POST", "/apps/imports", {"mode": "yaml-content", "yaml_content": yaml_text, "app_id": app_id})
        if result.get("status") == "pending":
            _, result = self._call("POST", f"/apps/imports/{result['id']}/confirm", {})
        if result.get("status") not in ("completed", "completed-with-warnings"):
            raise ConsoleError(f"가져오기 실패: {result}")
        return result

    def publish(self, app_id, name="자동 갱신"):
        _, result = self._call("POST", f"/apps/{app_id}/workflows/publish", {"marked_name": name, "marked_comment": ""})
        return result


def sync_app(yml_path, note="자동 갱신", log=print, app_key="DIFY_APP_ID"):
    """YAML을 기존 앱에 덮어쓰고 게시. 설정이 없으면 False를 돌려주고 아무것도 하지 않는다.
    app_key: 덮어쓸 앱 ID가 든 .env 항목 (브랜드 웹 디깅 앱은 DIFY_DIG_APP_ID)"""
    conf, missing = settings(app_key)
    if missing:
        log(f"Dify 앱 자동 반영 건너뜀: .env에 {', '.join(missing)} 없음 → YAML을 Dify에서 직접 가져와 주세요.")
        return False
    console = Console(conf["DIFY_CONSOLE_EMAIL"], conf["DIFY_CONSOLE_PASSWORD"])
    result = console.import_yaml(conf[app_key], open(yml_path, encoding="utf-8").read())
    console.publish(conf[app_key], note)
    log(f"Dify 앱 반영 완료: app {conf[app_key]} ({result.get('status')}), 게시함")
    return True
