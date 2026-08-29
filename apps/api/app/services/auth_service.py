"""轻量 Bearer token 与微信 code2Session 服务边界。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.models.orm import UserORM
from app.repositories.user_repo import UserRepository


class AuthError(Exception):
    pass


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class TokenService:
    def __init__(self, secret: str, ttl_seconds: int) -> None:
        self._secret = secret.encode("utf-8")
        self._ttl_seconds = ttl_seconds

    def issue(self, user: UserORM) -> str:
        payload = {"sub": user.id, "iat": int(time.time()), "exp": int(time.time()) + self._ttl_seconds}
        encoded = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = _b64encode(hmac.new(self._secret, encoded.encode("ascii"), hashlib.sha256).digest())
        return f"{encoded}.{signature}"

    def verify(self, token: str) -> str:
        try:
            encoded, signature = token.split(".", 1)
            expected = _b64encode(hmac.new(self._secret, encoded.encode("ascii"), hashlib.sha256).digest())
            if not hmac.compare_digest(signature, expected):
                raise AuthError("invalid token")
            payload = json.loads(_b64decode(encoded))
            if not isinstance(payload, dict) or int(payload["exp"]) < int(time.time()):
                raise AuthError("expired token")
            subject = payload["sub"]
            if not isinstance(subject, str) or not subject:
                raise AuthError("invalid subject")
            return subject
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise AuthError("invalid token") from exc


class HttpClient(Protocol):
    def get(self, url: str, *, params: dict[str, str], timeout: float) -> Any: ...


@dataclass(frozen=True, slots=True)
class WeChatSession:
    openid: str
    session_key: str
    unionid: str | None = None


class WeChatCode2SessionService:
    """可注入 HTTP 客户端；未配置 AppID/Secret 时在发起网络请求前失败。"""

    def __init__(
        self,
        *,
        app_id: str | None,
        app_secret: str | None,
        base_url: str,
        client: HttpClient | None = None,
    ) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._base_url = base_url
        self._client = client or httpx.Client()

    @property
    def configured(self) -> bool:
        return bool(self._app_id and self._app_secret)

    def exchange(self, code: str) -> WeChatSession:
        if not self.configured:
            raise AuthError("wechat code2Session is not configured")
        response = self._client.get(
            self._base_url,
            params={
                "appid": self._app_id or "",
                "secret": self._app_secret or "",
                "js_code": code,
                "grant_type": "authorization_code",
            },
            timeout=5.0,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("errcode") or not data.get("openid") or not data.get("session_key"):
            raise AuthError(data.get("errmsg", "wechat code2Session failed"))
        return WeChatSession(
            openid=data["openid"],
            session_key=data["session_key"],
            unionid=data.get("unionid"),
        )


class AuthService:
    def __init__(self, users: UserRepository, tokens: TokenService) -> None:
        self._users = users
        self._tokens = tokens

    def dev_login(self, subject: str, display_name: str | None = None) -> tuple[UserORM, str]:
        user = self._users.get_or_create(provider="dev", subject=subject, display_name=display_name)
        return user, self._tokens.issue(user)

    def wechat_login(
        self,
        session: WeChatSession,
        allowed_openids: set[str] | None = None,
    ) -> tuple[UserORM, str]:
        if allowed_openids and session.openid not in allowed_openids:
            raise AuthError("wechat user is not allowed")
        user = self._users.get_or_create(provider="wechat", subject=session.openid)
        return user, self._tokens.issue(user)

    def legacy_user(self) -> UserORM:
        return self._users.get_or_create(provider="local", subject="legacy", display_name="Legacy Local User")

    def authenticate(self, token: str) -> UserORM:
        user = self._users.get(self._tokens.verify(token))
        if user is None:
            raise AuthError("user not found")
        return user
