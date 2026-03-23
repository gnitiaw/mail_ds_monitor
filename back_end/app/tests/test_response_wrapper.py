"""统一响应结构测试（包含成功和错误响应）。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestSuccessResponseWrapper:
    """成功响应结构测试类。"""

    def test_mailbox_list_response_structure(self, client: TestClient, db_session: Session):
        """测试邮箱列表响应结构。"""
        response = client.get("/api/v1/mailboxes")

        assert response.status_code == 200
        data = response.json()

        # 验证统一响应结构
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 0
        assert data["message"] == "success"

        # 验证分页数据结构
        assert "items" in data["data"]
        assert "page" in data["data"]
        assert "page_size" in data["data"]
        assert "total" in data["data"]

    def test_mailbox_create_response_structure(self, client: TestClient, db_session: Session):
        """测试邮箱创建响应结构。"""
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
        data = response.json()

        # 验证统一响应结构
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 0

        # 验证数据字段
        assert "id" in data["data"]
        assert "name" in data["data"]
        assert data["data"]["name"] == "测试邮箱"

    def test_archive_list_response_structure(self, client: TestClient, db_session: Session):
        """测试归档列表响应结构。"""
        response = client.get("/api/v1/archives")

        assert response.status_code == 200
        data = response.json()

        # 验证统一响应结构
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 0

    def test_summary_config_list_response_structure(self, client: TestClient, db_session: Session):
        """测试汇总配置列表响应结构。"""
        response = client.get("/api/v1/summary-configs")

        assert response.status_code == 200
        data = response.json()

        # 验证统一响应结构
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 0


class TestErrorResponseWrapper:
    """错误响应结构测试类 - 验证所有错误都返回统一结构。"""

    def test_duplicate_mailbox_error_response(self, client: TestClient, db_session: Session):
        """测试重复创建邮箱的错误响应结构 - 应返回 40901。"""
        payload = {
            "name": "重复邮箱",
            "host": "imap.example.com",
            "port": 993,
            "username": "dup@example.com",
            "password": "password",
            "folder": "INBOX",
            "status": "enabled",
        }

        # 第一次创建成功
        response1 = client.post("/api/v1/mailboxes", json=payload)
        assert response1.status_code == 201

        # 第二次创建应返回错误
        response2 = client.post("/api/v1/mailboxes", json=payload)
        assert response2.status_code == 409

        # 验证错误响应结构
        data = response2.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40901
        assert "detail" not in data  # 不应包含 detail 字段

    def test_not_found_mailbox_error_response(self, client: TestClient, db_session: Session):
        """测试不存在的邮箱错误响应结构 - 应返回 40401。"""
        response = client.put(
            "/api/v1/mailboxes/nonexistent-id",
            json={"name": "测试"},
        )

        assert response.status_code == 404

        # 验证错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40401
        assert "detail" not in data

    def test_not_found_archive_error_response(self, client: TestClient, db_session: Session):
        """测试不存在的归档错误响应结构 - 应返回 40401。"""
        response = client.get("/api/v1/archives/nonexistent-id")

        assert response.status_code == 404

        # 验证错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40401
        assert "detail" not in data

    def test_disabled_mailbox_pull_error_response(self, client: TestClient, db_session: Session):
        """测试禁用邮箱拉取的错误响应结构 - 应返回 40901。"""
        # 创建禁用邮箱
        payload = {
            "name": "禁用邮箱",
            "host": "imap.example.com",
            "port": 993,
            "username": "disabled@example.com",
            "password": "password",
            "folder": "INBOX",
            "status": "disabled",
        }
        create_response = client.post("/api/v1/mailboxes", json=payload)
        mailbox_id = create_response.json()["data"]["id"]

        # 尝试拉取
        response = client.post(
            f"/api/v1/mailboxes/{mailbox_id}/pull",
            json={"force_full_sync": False},
        )

        assert response.status_code == 409

        # 验证错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40901
        assert "detail" not in data

    def test_disabled_summary_send_error_response(self, client: TestClient, db_session: Session):
        """测试禁用汇总配置发送的错误响应结构 - 应返回 40901。"""
        from app.models.summary import SummaryConfig

        config = SummaryConfig(
            name="禁用配置",
            enabled=False,
            recipient_emails=["test@example.com"],
            send_time="09:00",
        )
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)

        response = client.post(
            f"/api/v1/summary-configs/{config.id}/send",
            json={
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-01T23:59:59Z",
            },
        )

        assert response.status_code == 409

        # 验证错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40901
        assert "detail" not in data

    def test_invalid_time_format_error_response(self, client: TestClient, db_session: Session):
        """测试非法时间格式的错误响应结构 - 应返回 40001。"""
        from app.models.summary import SummaryConfig

        config = SummaryConfig(
            name="时间测试配置",
            enabled=True,
            recipient_emails=["test@example.com"],
            send_time="09:00",
        )
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)

        response = client.post(
            f"/api/v1/summary-configs/{config.id}/send",
            json={
                "start_time": "invalid-time",
                "end_time": "2024-01-01T23:59:59Z",
            },
        )

        assert response.status_code == 400

        # 验证错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40001
        assert "detail" not in data

    def test_validation_error_response(self, client: TestClient, db_session: Session):
        """测试请求验证错误的响应结构 - 应返回 40001。"""
        # 缺少必填字段
        payload = {
            "name": "测试邮箱",
            # 缺少 host, port, username, password
        }

        response = client.post("/api/v1/mailboxes", json=payload)

        assert response.status_code == 422

        # 验证错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40001  # 验证错误映射到参数错误
        assert "detail" not in data

    def test_not_found_summary_config_error_response(self, client: TestClient, db_session: Session):
        """测试不存在的汇总配置错误响应结构 - 应返回 40401。"""
        response = client.post(
            "/api/v1/summary-configs/nonexistent-id/send",
            json={
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-01T23:59:59Z",
            },
        )

        assert response.status_code == 404

        # 验证错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40401
        assert "detail" not in data

    def test_duplicate_summary_config_error_response(self, client: TestClient, db_session: Session):
        """测试重复创建汇总配置的错误响应结构 - 应返回 40901。"""
        payload = {
            "name": "重复配置",
            "enabled": True,
            "recipient_emails": ["test@example.com"],
            "send_time": "10:00",
        }

        # 第一次创建成功
        response1 = client.post("/api/v1/summary-configs", json=payload)
        assert response1.status_code == 201

        # 第二次创建应返回错误
        response2 = client.post("/api/v1/summary-configs", json=payload)
        assert response2.status_code == 409

        # 验证错误响应结构
        data = response2.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40901
        assert "detail" not in data
