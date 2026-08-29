"""认证 API schema。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DevLoginIn(BaseModel):
    subject: str = Field("legacy", min_length=1, max_length=128)
    display_name: str | None = Field(None, max_length=128)


class WeChatLoginIn(BaseModel):
    code: str = Field(..., min_length=1, max_length=256)


class UserOut(BaseModel):
    id: str
    provider: str
    subject: str
    display_name: str | None
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
