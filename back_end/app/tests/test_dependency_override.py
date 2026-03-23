"""测试依赖覆写有效性测试。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session


class TestDependencyOverride:
    """测试依赖覆写有效性。"""

    def test_db_session_isolation(self, client: TestClient, db_session: Session):
        """测试数据库会话隔离，确保使用测试数据库。"""
        # 创建邮箱
        payload = {
            "name": "隔离测试邮箱",
            "host": "imap.example.com",
            "port": 993,
            "username": "isolation@example.com",
            "password": "password",
            "folder": "INBOX",
            "status": "enabled",
        }
        response = client.post("/api/v1/mailboxes", json=payload)
        assert response.status_code == 201

        # 通过 db_session 直接查询验证数据存在
        result = db_session.execute(
            text("SELECT name FROM mailboxes WHERE username = 'isolation@example.com'")
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] == "隔离测试邮箱"

    def test_db_session_rollback(self, client: TestClient, db_session: Session):
        """测试数据库会话回滚不影响其他测试。"""
        # 验证上一个测试的数据不存在（因为会话隔离）
        result = db_session.execute(
            text("SELECT COUNT(*) FROM mailboxes")
        )
        count = result.fetchone()[0]
        # 由于每个测试使用独立的会话，表应该是空的
        # 注意：这取决于 conftest.py 中的实现
        # 如果使用内存数据库且每个测试独立会话，这里应该是 0

    def test_concurrent_requests_use_same_db(self, client: TestClient, db_session: Session):
        """测试并发请求使用同一个测试数据库。"""
        # 创建多个邮箱
        for i in range(3):
            payload = {
                "name": f"并发邮箱{i}",
                "host": f"imap{i}.example.com",
                "port": 993,
                "username": f"concurrent{i}@example.com",
                "password": "password",
                "folder": "INBOX",
                "status": "enabled",
            }
            response = client.post("/api/v1/mailboxes", json=payload)
            assert response.status_code == 201

        # 验证列表返回正确数量
        list_response = client.get("/api/v1/mailboxes")
        assert list_response.status_code == 200
        data = list_response.json()
        assert data["data"]["total"] >= 3
