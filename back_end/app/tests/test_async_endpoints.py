"""异步任务接口测试（pull/send 返回 pending）。"""

from time import perf_counter

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import SummaryScheduleType, UserRole
from app.models.summary import SummaryConfig
from app.models.task_log import TaskLog
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.mail_pull_service import MailPullService


class TestPullEndpoint:
    """邮件拉取接口测试类。"""

    @pytest.fixture
    def setup_admin(self, db_session: Session):
        """设置 admin 用户用于测试。"""
        admin = User(
            username="admin_async_test",
            password_hash=AuthService.hash_password("password123"),
            display_name="Admin Async Test",
            role=UserRole.ADMIN.value,
        )
        db_session.add(admin)
        db_session.commit()
        return admin

    def _get_admin_token(self, client: TestClient) -> str:
        """获取 admin token。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_async_test", "password": "password123"},
        )
        return login_response.json()["data"]["access_token"]

    def test_pull_returns_pending_status(self, client: TestClient, db_session: Session, setup_admin):
        """测试拉取接口返回 pending 状态。"""
        token = self._get_admin_token(client)
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
        create_response = client.post(
            "/api/v1/mailboxes",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_response.status_code == 201
        mailbox_id = create_response.json()["data"]["id"]

        # 触发拉取
        pull_payload = {"force_full_sync": False}
        response = client.post(
            f"/api/v1/mailboxes/{mailbox_id}/pull",
            json=pull_payload,
            headers={"Authorization": f"Bearer {token}"},
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

    def test_pull_schedules_background_job_without_blocking(
        self,
        client: TestClient,
        db_session: Session,
        setup_admin,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """测试拉取接口只创建后台任务，不同步阻塞请求。"""
        token = self._get_admin_token(client)
        payload = {
            "name": "异步调度邮箱",
            "host": "imap.example.com",
            "port": 993,
            "username": "async-schedule@example.com",
            "password": "password",
            "folder": "INBOX",
            "status": "enabled",
        }
        create_response = client.post(
            "/api/v1/mailboxes",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        mailbox_id = create_response.json()["data"]["id"]

        scheduled: dict[str, str | bool] = {}

        def fake_start_background_pull(job_id: str, mailbox_id: str, force_full_sync: bool) -> None:
            scheduled["job_id"] = job_id
            scheduled["mailbox_id"] = mailbox_id
            scheduled["force_full_sync"] = force_full_sync

        monkeypatch.setattr(
            MailPullService,
            "_start_background_pull",
            fake_start_background_pull,
        )

        started_at = perf_counter()
        response = client.post(
            f"/api/v1/mailboxes/{mailbox_id}/pull",
            json={"force_full_sync": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        elapsed = perf_counter() - started_at

        assert response.status_code == 202
        data = response.json()["data"]
        assert data["status"] == "pending"
        assert elapsed < 0.5

        task_log = db_session.get(TaskLog, data["job_id"])
        assert task_log is not None
        assert task_log.status == "pending"
        assert task_log.related_mailbox_id == mailbox_id
        assert task_log.payload == {"force_full_sync": True}
        assert scheduled == {
            "job_id": data["job_id"],
            "mailbox_id": mailbox_id,
            "force_full_sync": True,
        }

    def test_pull_disabled_mailbox_error_response(self, client: TestClient, db_session: Session, setup_admin):
        """测试拉取禁用邮箱的错误响应结构。"""
        token = self._get_admin_token(client)
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
        create_response = client.post(
            "/api/v1/mailboxes",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        mailbox_id = create_response.json()["data"]["id"]

        # 尝试拉取
        response = client.post(
            f"/api/v1/mailboxes/{mailbox_id}/pull",
            json={"force_full_sync": False},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409

        # 验证统一错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40901
        assert "detail" not in data

    def test_pull_nonexistent_mailbox_error_response(self, client: TestClient, db_session: Session, setup_admin):
        """测试拉取不存在的邮箱的错误响应结构。"""
        token = self._get_admin_token(client)
        response = client.post(
            "/api/v1/mailboxes/nonexistent-id/pull",
            json={"force_full_sync": False},
            headers={"Authorization": f"Bearer {token}"},
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

    @pytest.fixture
    def setup_admin(self, db_session: Session):
        """设置 admin 用户用于测试。"""
        admin = User(
            username="admin_send_test",
            password_hash=AuthService.hash_password("password123"),
            display_name="Admin Send Test",
            role=UserRole.ADMIN.value,
        )
        db_session.add(admin)
        db_session.commit()
        return admin

    def _get_admin_token(self, client: TestClient) -> str:
        """获取 admin token。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_send_test", "password": "password123"},
        )
        return login_response.json()["data"]["access_token"]

    def test_send_returns_pending_status(self, client: TestClient, db_session: Session, setup_admin):
        """测试发送接口返回 pending 状态。"""
        token = self._get_admin_token(client)
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
            headers={"Authorization": f"Bearer {token}"},
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

    def test_send_disabled_config_error_response(self, client: TestClient, db_session: Session, setup_admin):
        """测试发送禁用配置的错误响应结构。"""
        token = self._get_admin_token(client)
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
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409

        # 验证统一错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40901
        assert "detail" not in data

    def test_send_nonexistent_config_error_response(self, client: TestClient, db_session: Session, setup_admin):
        """测试发送不存在的配置的错误响应结构。"""
        token = self._get_admin_token(client)
        payload = {
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-01-01T23:59:59Z",
        }
        response = client.post(
            "/api/v1/summary-configs/nonexistent-id/send",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

        # 验证统一错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40401
        assert "detail" not in data

    def test_send_invalid_time_format_error_response(self, client: TestClient, db_session: Session, setup_admin):
        """测试无效时间格式的错误响应结构。"""
        token = self._get_admin_token(client)
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
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400

        # 验证统一错误响应结构
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40001  # 参数错误
        assert "detail" not in data
