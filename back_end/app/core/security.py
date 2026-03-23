"""密码加密解密工具模块。"""

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings


def _get_fernet_key() -> bytes:
    """从 SECRET_KEY 派生 Fernet 密钥。"""
    # 使用固定的 salt（基于应用名称）确保同一密钥派生相同结果
    salt = base64.b64encode(settings.app_name.encode()).ljust(16, b'=')[:16]
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(settings.secret_key.encode()))


_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """获取或创建 Fernet 实例（懒加载单例）。"""
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_get_fernet_key())
    return _fernet


def encrypt_password(plain_password: str) -> str:
    """加密密码。

    Args:
        plain_password: 明文密码

    Returns:
        加密后的密码字符串
    """
    fernet = _get_fernet()
    encrypted = fernet.encrypt(plain_password.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_password(encrypted_password: str) -> str:
    """解密密码。

    Args:
        encrypted_password: 加密的密码字符串

    Returns:
        明文密码
    """
    fernet = _get_fernet()
    encrypted = base64.urlsafe_b64decode(encrypted_password.encode())
    return fernet.decrypt(encrypted).decode()
