"""认证路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import get_auth_service, get_current_user
from app.models.orm import UserORM
from app.schemas.auth import DevLoginIn, TokenOut, UserOut, WeChatLoginIn
from app.services.auth_service import AuthError, AuthService, WeChatCode2SessionService

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: UserORM) -> UserOut:
    return UserOut(
        id=user.id,
        provider=user.provider,
        subject=user.subject,
        display_name=user.display_name,
        created_at=user.created_at,
    )


@router.post("/dev-login", response_model=TokenOut)
def dev_login(
    req: DevLoginIn,
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> TokenOut:
    if not request.app.state.settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    user, token = auth.dev_login(req.subject, req.display_name)
    return TokenOut(
        access_token=token,
        expires_in=request.app.state.settings.auth_token_ttl_seconds,
        user=_user_out(user),
    )


@router.post("/wechat/login", response_model=TokenOut)
def wechat_login(
    req: WeChatLoginIn,
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> TokenOut:
    exchanger: WeChatCode2SessionService = request.app.state.wechat_code2session_service
    try:
        session = exchanger.exchange(req.code)
        configured = request.app.state.settings.wechat_allowed_openids
        allowed = {item.strip() for item in configured.split(",") if item.strip()}
        user, token = auth.wechat_login(session, allowed or None)
    except AuthError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    return TokenOut(
        access_token=token,
        expires_in=request.app.state.settings.auth_token_ttl_seconds,
        user=_user_out(user),
    )


@router.get("/me", response_model=UserOut)
def me(user: UserORM = Depends(get_current_user)) -> UserOut:
    return _user_out(user)
