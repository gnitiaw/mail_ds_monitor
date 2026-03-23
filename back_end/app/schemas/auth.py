"""认证相关 schemas。"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class UserInfo(BaseModel):
    """用户信息。"""

    id: str
    username: str
    display_name: str
    role: str
    mailbox_scope_ids: list[str] | None = None


class LoginResponse(BaseModel):
    """登录响应。"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400
    user: UserInfo


class CurrentUserResponse(BaseModel):
    """当前用户信息响应。"""

    id: str
    username: str
    display_name: str
    role: str
    mailbox_scope_ids: list[str] | None = None
