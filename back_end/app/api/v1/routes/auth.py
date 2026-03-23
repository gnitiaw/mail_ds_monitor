"""认证路由。"""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.exceptions import UnauthorizedError
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    UserInfo,
)
from app.schemas.common import success
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(
    request: LoginRequest,
    db: Session = Depends(db_session),
) -> dict:
    """用户登录。"""
    result = AuthService.login(db, request.username, request.password)
    return success(result)


@router.get("/me")
def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(db_session),
) -> dict:
    """获取当前登录用户信息。"""
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("未登录")

    token = authorization[7:]
    user = AuthService.get_current_user(db, token)
    if not user:
        raise UnauthorizedError("未登录")

    # operator 只能访问其 mailbox_scope_ids 范围内数据
    mailbox_scope_ids = user.mailbox_scope_ids

    return success(
        CurrentUserResponse(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            mailbox_scope_ids=mailbox_scope_ids,
        ).model_dump()
    )
