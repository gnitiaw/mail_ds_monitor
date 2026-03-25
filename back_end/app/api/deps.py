from collections.abc import Generator

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import AuthService


def db_session() -> Generator[Session, None, None]:
    yield from get_db()


def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(db_session),
) -> User:
    """获取当前登录用户。"""
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("未登录")

    token = authorization[7:]
    user = AuthService.get_current_user(db, token)
    if not user:
        raise UnauthorizedError("未登录")

    return user


def admin_required(
    current_user: User = Depends(get_current_user),
) -> User:
    """要求当前用户为管理员。"""
    if current_user.role != "admin":
        raise ForbiddenError("需要管理员权限")

    return current_user


def operator_or_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """要求当前用户为操作员或管理员。"""
    if current_user.role not in ("admin", "operator"):
        raise ForbiddenError("需要操作员或管理员权限")

    return current_user


def check_mailbox_scope(
    current_user: User,
    mailbox_ids: list[str] | None,
) -> None:
    """检查用户是否有权限访问指定的邮箱范围。

    Args:
        current_user: 当前用户
        mailbox_ids: 要访问的邮箱 ID 列表，None 表示全局访问

    Raises:
        ForbiddenError: 如果 operator 尝试访问其 scope 外的邮箱
    """
    # admin 可以访问所有邮箱
    if current_user.role == "admin":
        return

    # operator 只能访问其 scope 内的邮箱
    if current_user.role == "operator":
        user_scope = current_user.mailbox_scope_ids or []

        # 如果用户没有 scope，禁止访问任何特定邮箱
        if not user_scope:
            raise ForbiddenError("您没有权限访问任何邮箱")

        # 如果请求的是全局访问（None），限制到用户的 scope
        # 这里的检查是：如果指定了 mailbox_ids，必须全部在用户 scope 内
        if mailbox_ids:
            for mid in mailbox_ids:
                if mid not in user_scope:
                    raise ForbiddenError(f"您没有权限访问邮箱 {mid}")


def filter_mailbox_scope(
    current_user: User,
    mailbox_ids: list[str] | None,
) -> list[str] | None:
    """根据用户权限过滤邮箱范围。

    Args:
        current_user: 当前用户
        mailbox_ids: 请求的邮箱 ID 列表，None 表示全局访问

    Returns:
        过滤后的邮箱 ID 列表，可能为 None（admin 全局访问）

    Raises:
        ForbiddenError: 如果 operator 尝试访问其 scope 外的邮箱
    """
    # admin 可以访问所有邮箱
    if current_user.role == "admin":
        return mailbox_ids

    # operator 只能访问其 scope 内的邮箱
    user_scope = current_user.mailbox_scope_ids or []

    if not user_scope:
        # operator 没有 scope，只能访问空集
        return []

    if mailbox_ids is None:
        # 请求全局访问，限制到用户的 scope
        return user_scope

    # 请求特定邮箱，取交集
    filtered = [mid for mid in mailbox_ids if mid in user_scope]
    return filtered
