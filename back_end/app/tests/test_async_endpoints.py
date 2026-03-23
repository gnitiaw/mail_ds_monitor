"""异步任务接口测试（pull/send 返回 pending）。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import SummaryScheduleType
from app.models.summary import SummaryConfig


class TestPullEndpoint:
    """邮件拉取接口测试类。"""

    def test_pull_returns_pending_status(self, client: TestClient, db_session: Session):
        """测试拉取接口返回 pending 状态。"""
        # 创建邮箱
        payload = {
            "name": "拉取测试邮箱",
            "host": "imap.example.com",
            "port": 993,
            "username": "pull@example.com",
            "password": "password",
            "folder": "INBOX",
            "status": "enabled",
        }
        create_response = client.post("/api/v1/mailboxes", json=payload)
        assert create_response.status_code == 201
        mailbox_id = create_response.json()["data"]["id"]

        # 触发拉取
        pull_payload = {"force_full_sync": False}
        response = client.post(
            f"/api/v1/mailboxes/{mailbox_id}/pull",
            json=pull_payload,
        )

        # 验证响应
        assert response.status_code == 202
        data = response.json()

        # 验证统一响应结构
        assert "code" in data
        assert "message" in data
        assert "data" in data

        # 验证返回 pending 状态
        assert data["data"]["status"] == "pending"
        assert "job_id" in data["data"]
        assert data["data"]["mailbox_id"] == mailbox_id

    def test_pull_disabled_mailbox_error_response(self, client: TestClient, db_session: Session):
        """测试拉取禁用邮箱的错误响应结构。"""
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

        # 验证统一错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40901
        assert "detail" not in data

    def test_pull_nonexistent_mailbox_error_response(self, client: TestClient, db_session: Session):
        """测试拉取不存在的邮箱的错误响应结构。"""
        response = client.post(
            "/api/v1/mailboxes/nonexistent-id/pull",
            json={"force_full_sync": False},
        )

        assert response.status_code == 404

        # 验证统一错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40401
        assert "detail" not in data


class TestSendEndpoint:
    """汇总发送接口测试类。"""

    def test_send_returns_pending_status(self, client: TestClient, db_session: Session):
        """测试发送接口返回 pending 状态。"""
        # 创建汇总配置
        config = SummaryConfig(
            name="测试配置",
            enabled=True,
            schedule_type=SummaryScheduleType.DAILY.value,
            recipient_emails=["test@example.com"],
            send_time="09:00",
        )
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)

        # 触发发送
        payload = {
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-01-01T23:59:59Z",
        }
        response = client.post(
            f"/api/v1/summary-configs/{config.id}/send",
            json=payload,
        )

        # 验证响应
        assert response.status_code == 202
        data = response.json()

        # 验证统一响应结构
        assert "code" in data
        assert "message" in data
        assert "data" in data

        # 验证返回 pending 状态
        assert data["data"]["status"] == "pending"
        assert "send_id" in data["data"]

    def test_send_disabled_config_error_response(self, client: TestClient, db_session: Session):
        """测试发送禁用配置的错误响应结构。"""
        config = SummaryConfig(
            name="禁用配置",
            enabled=False,
            recipient_emails=["test@example.com"],
            send_time="09:00",
        )
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)

        payload = {
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-01-01T23:59:59Z",
        }
        response = client.post(
            f"/api/v1/summary-configs/{config.id}/send",
            json=payload,
        )

        assert response.status_code == 409

        # 验证统一错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40901
        assert "detail" not in data

    def test_send_nonexistent_config_error_response(self, client: TestClient, db_session: Session):
        """测试发送不存在的配置的错误响应结构。"""
        payload = {
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-01-01T23:59:59Z",
        }
        response = client.post(
            "/api/v1/summary-configs/nonexistent-id/send",
            json=payload,
        )

        assert response.status_code == 404

        # 验证统一错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40401
        assert "detail" not in data

    def test_send_invalid_time_format_error_response(self, client: TestClient, db_session: Session):
        """测试无效时间格式的错误响应结构。"""
        config = SummaryConfig(
            name="时间测试配置",
            enabled=True,
            recipient_emails=["test@example.com"],
            send_time="09:00",
        )
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)

        payload = {
            "start_time": "invalid-time",
            "end_time": "2024-01-01T23:59:59Z",
        }
        response = client.post(
            f"/api/v1/summary-configs/{config.id}/send",
            json=payload,
        )

        assert response.status_code == 400

        # 验证统一错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40001  # 参数错误
        assert "detail" not in data
