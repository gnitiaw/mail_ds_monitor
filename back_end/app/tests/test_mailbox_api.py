"""邮箱配置接口测试。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import MailboxStatus
from app.models.mailbox import Mailbox


class TestMailboxAPI:
    """邮箱配置接口测试类。"""

    def test_create_mailbox(self, client: TestClient, db_session: Session):
        """测试创建邮箱配置。"""
        payload = {
            "name": "测试邮箱",
            "host": "imap.example.com",
            "port": 993,
            "username": "test@example.com",
            "password": "test_password",
            "folder": "INBOX",
            "status": "enabled",
        }

        response = client.post("/api/v1/mailboxes", json=payload)

        assert response.status_code == 201
        json_data = response.json()

        # 验证统一响应结构
        assert json_data["code"] == 0
        data = json_data["data"]

        assert data["name"] == "测试邮箱"
        assert data["host"] == "imap.example.com"
        assert data["port"] == 993
        assert data["username"] == "test@example.com"
        assert data["status"] == "enabled"
        # 密码不应返回
        assert "password" not in data
        assert "password_secret" not in data

    def test_create_duplicate_mailbox(self, client: TestClient, db_session: Session):
        """测试创建重复邮箱配置 - 应返回统一错误结构。"""
        payload = {
            "name": "重复邮箱",
            "host": "imap.example.com",
            "port": 993,
            "username": "dup@example.com",
            "password": "password",
            "folder": "INBOX",
            "status": "enabled",
        }

        response1 = client.post("/api/v1/mailboxes", json=payload)
        assert response1.status_code == 201

        # 再次创建同名邮箱
        response2 = client.post("/api/v1/mailboxes", json=payload)
        assert response2.status_code == 409

        # 验证统一错误响应结构
        data = response2.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40901
        assert "detail" not in data

    def test_list_mailboxes(self, client: TestClient, db_session: Session):
        """测试获取邮箱列表。"""
        # 创建测试数据
        for i in range(3):
            payload = {
                "name": f"邮箱{i}",
                "host": f"imap{i}.example.com",
                "port": 993,
                "username": f"user{i}@example.com",
                "password": "password",
                "folder": "INBOX",
                "status": "enabled" if i < 2 else "disabled",
            }
            client.post("/api/v1/mailboxes", json=payload)

        # 测试列表
        response = client.get("/api/v1/mailboxes")
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["code"] == 0
        data = json_data["data"]
        assert len(data["items"]) == 3
        assert data["total"] == 3

        # 测试状态筛选
        response = client.get("/api/v1/mailboxes?status=enabled")
        assert response.status_code == 200
        json_data = response.json()
        data = json_data["data"]
        assert len(data["items"]) == 2

    def test_update_mailbox(self, client: TestClient, db_session: Session):
        """测试更新邮箱配置。"""
        # 创建邮箱
        create_payload = {
            "name": "原名称",
            "host": "imap.example.com",
            "port": 993,
            "username": "test@example.com",
            "password": "password",
            "folder": "INBOX",
            "status": "enabled",
        }
        create_response = client.post("/api/v1/mailboxes", json=create_payload)
        mailbox_id = create_response.json()["data"]["id"]

        # 更新邮箱
        update_payload = {
            "name": "新名称",
            "host": "imap.new.com",
            "port": 143,
            "status": "disabled",
        }
        response = client.put(f"/api/v1/mailboxes/{mailbox_id}", json=update_payload)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["code"] == 0
        data = json_data["data"]
        assert data["name"] == "新名称"
        assert data["host"] == "imap.new.com"
        assert data["port"] == 143
        assert data["status"] == "disabled"

    def test_update_nonexistent_mailbox(self, client: TestClient, db_session: Session):
        """测试更新不存在的邮箱配置 - 应返回统一错误结构。"""
        payload = {"name": "测试"}
        response = client.put("/api/v1/mailboxes/nonexistent-id", json=payload)

        assert response.status_code == 404

        # 验证统一错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40401
        assert "detail" not in data

    def test_update_mailbox_password(self, client: TestClient, db_session: Session):
        """测试更新邮箱密码。"""
        # 创建邮箱
        create_payload = {
            "name": "密码测试邮箱",
            "host": "imap.example.com",
            "port": 993,
            "username": "pwdtest@example.com",
            "password": "old_password",
            "folder": "INBOX",
            "status": "enabled",
        }
        create_response = client.post("/api/v1/mailboxes", json=create_payload)
        mailbox_id = create_response.json()["data"]["id"]

        # 更新密码
        update_payload = {"password": "new_password"}
        response = client.put(f"/api/v1/mailboxes/{mailbox_id}", json=update_payload)
        assert response.status_code == 200

        # 验证密码已更新（通过查询数据库）
        mailbox = db_session.get(Mailbox, mailbox_id)
        assert mailbox is not None
        assert mailbox.password_secret != "old_password"
        assert mailbox.password_secret != "new_password"  # 应该是加密后的
