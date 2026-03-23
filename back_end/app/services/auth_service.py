"""认证服务 - 最小登录实现。"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ParamError, UnauthorizedError
from app.models.enums import UserRole
from app.models.user import User


class AuthService:
    """认证服务。"""

    # 简单的 token 存储 (生产环境应使用 Redis)
    _tokens: dict[str, dict] = {}

    @staticmethod
    def hash_password(password: str) -> str:
        """哈希密码。"""
        salt = secrets.token_hex(16)
        hash_value = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return f"{salt}${hash_value}"

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """验证密码。"""
        try:
            salt, stored_hash = password_hash.split("$")
            computed_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
            return secrets.compare_digest(computed_hash, stored_hash)
        except ValueError:
            return False

    @classmethod
    def login(cls, db: Session, username: str, password: str) -> dict:
        """用户登录。"""
        user = db.scalar(
            select(User).where(User.username == username, User.is_active == True)
        )

        if not user or not cls.verify_password(password, user.password_hash):
            raise UnauthorizedError("用户名或密码错误")

        # 生成 token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=86400)

        cls._tokens[token] = {
            "user_id": user.id,
            "expires_at": expires_at,
        }

        # 构建用户可访问邮箱范围
        mailbox_scope_ids = user.mailbox_scope_ids
        if user.role == UserRole.ADMIN.value:
            # admin 可访问全部试点邮箱，返回 None 表示不限制
            mailbox_scope_ids = None

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 86400,
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role,
                "mailbox_scope_ids": mailbox_scope_ids,
            },
        }

    @classmethod
    def get_current_user(cls, db: Session, token: str) -> User | None:
        """根据 token 获取当前用户。"""
        token_info = cls._tokens.get(token)
        if not token_info:
            return None

        if datetime.now(timezone.utc) > token_info["expires_at"]:
            del cls._tokens[token]
            return None

        user = db.scalar(select(User).where(User.id == token_info["user_id"]))
        return user

    @classmethod
    def validate_token(cls, token: str) -> dict | None:
        """验证 token 有效性。"""
        token_info = cls._tokens.get(token)
        if not token_info:
            return None

        if datetime.now(timezone.utc) > token_info["expires_at"]:
            del cls._tokens[token]
            return None

        return token_info

    @classmethod
    def create_user(
        cls,
        db: Session,
        username: str,
        password: str,
        display_name: str,
        role: str = UserRole.OPERATOR.value,
        mailbox_scope_ids: list[str] | None = None,
    ) -> User:
        """创建用户。"""
        user = User(
            username=username,
            password_hash=cls.hash_password(password),
            display_name=display_name,
            role=role,
            mailbox_scope_ids=mailbox_scope_ids,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
