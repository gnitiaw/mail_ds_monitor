"""密码加密测试。"""

import pytest

from app.core.security import decrypt_password, encrypt_password


class TestSecurity:
    """安全工具测试类。"""

    def test_encrypt_decrypt_password(self):
        """测试密码加密和解密。"""
        plain_password = "my_secret_password_123"

        encrypted = encrypt_password(plain_password)
        assert encrypted != plain_password
        assert len(encrypted) > 0

        decrypted = decrypt_password(encrypted)
        assert decrypted == plain_password

    def test_encrypt_different_passwords(self):
        """测试不同密码产生不同加密结果。"""
        password1 = "password1"
        password2 = "password2"

        encrypted1 = encrypt_password(password1)
        encrypted2 = encrypt_password(password2)

        assert encrypted1 != encrypted2

    def test_encrypt_same_password_twice(self):
        """测试同一密码加密两次结果不同（因为 Fernet 包含时间戳）。"""
        password = "same_password"

        encrypted1 = encrypt_password(password)
        encrypted2 = encrypt_password(password)

        # Fernet 每次加密结果不同，但都可以解密
        assert decrypt_password(encrypted1) == password
        assert decrypt_password(encrypted2) == password

    def test_encrypt_empty_password(self):
        """测试空密码加密。"""
        plain_password = ""

        encrypted = encrypt_password(plain_password)
        decrypted = decrypt_password(encrypted)

        assert decrypted == ""

    def test_encrypt_special_characters(self):
        """测试特殊字符密码。"""
        plain_password = "p@ssw0rd!#$%^&*()_+-=[]{}|;':\",./<>?"

        encrypted = encrypt_password(plain_password)
        decrypted = decrypt_password(encrypted)

        assert decrypted == plain_password

    def test_encrypt_unicode_password(self):
        """测试 Unicode 密码。"""
        plain_password = "密码测试123🔐"

        encrypted = encrypt_password(plain_password)
        decrypted = decrypt_password(encrypted)

        assert decrypted == plain_password

    def test_encrypt_long_password(self):
        """测试长密码。"""
        plain_password = "a" * 512

        encrypted = encrypt_password(plain_password)
        decrypted = decrypt_password(encrypted)

        assert decrypted == plain_password
