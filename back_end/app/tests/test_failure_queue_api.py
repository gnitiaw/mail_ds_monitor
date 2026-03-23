"""失败队列 API 测试。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import FailureQueueStatus, UserRole
from app.models.failure_queue import FailureMailQueue
from app.models.mailbox import Mailbox
from app.models.user import User
from app.services.auth_service import AuthService


class TestFailureQueueAPI:
    """失败队列 API 测试类。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        # 创建邮箱
        mailbox = Mailbox(
            name="失败队列测试邮箱",
            protocol="imap",
            host="imap.example.com",
            port=993,
            username="failure@example.com",
            password_secret="encrypted_password",
            folder="INBOX",
            status="enabled",
        )
        db_session.add(mailbox)
        db_session.flush()

        # 创建 admin 用户
        admin = User(
            username="admin_test",
            password_hash=AuthService.hash_password("password123"),
            display_name="Admin Test",
            role=UserRole.ADMIN.value,
        )
        db_session.add(admin)
        db_session.flush()

        # 创建 operator 用户（带邮箱范围限制）
        operator = User(
            username="operator_test",
            password_hash=AuthService.hash_password("password123"),
            display_name="Operator Test",
            role=UserRole.OPERATOR.value,
            mailbox_scope_ids=[mailbox.id],
        )
        db_session.add(operator)
        db_session.flush()

        # 创建失败队列记录
        queue_item = FailureMailQueue(
            mailbox_id=mailbox.id,
            source_message_id="<test-failure-001@example.com>",
            provider_uid="uid-001",
            failure_rule_key="batch_task_failed",
            customer_name="测试客户A",
            task_identifier="TASK-20260323-001",
            subject="批量任务执行失败通知",
            sender="system@example.com",
            status=FailureQueueStatus.NEW.value,
            matched_snapshot={
                "matched_fields": {"subject_keywords": ["执行失败"]},
                "extracted_fields": {"customer_name": "测试客户A"},
            },
        )
        db_session.add(queue_item)
        db_session.commit()

        return {
            "mailbox": mailbox,
            "admin": admin,
            "operator": operator,
            "queue_item": queue_item,
        }

    def test_login_success(self, client: TestClient, db_session: Session, setup_data):
        """测试登录成功。"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_test", "password": "password123"},
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["code"] == 0
        assert "access_token" in json_data["data"]
        assert json_data["data"]["user"]["role"] == UserRole.ADMIN.value

    def test_login_wrong_password(self, client: TestClient, db_session: Session, setup_data):
        """测试登录失败 - 密码错误。"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_test", "password": "wrong_password"},
        )

        assert response.status_code == 401

    def test_get_current_user(self, client: TestClient, db_session: Session, setup_data):
        """测试获取当前用户信息。"""
        # 先登录
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_test", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        # 获取用户信息
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["data"]["role"] == UserRole.OPERATOR.value
        assert len(json_data["data"]["mailbox_scope_ids"]) == 1

    def test_list_failure_queue_as_admin(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试 admin 查看失败队列列表。"""
        # 登录 admin
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_test", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        # 获取列表
        response = client.get(
            "/api/v1/failure-queue",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["code"] == 0
        assert json_data["data"]["total"] == 1
        assert len(json_data["data"]["items"]) == 1

    def test_list_failure_queue_with_status_filter(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试按状态筛选失败队列。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_test", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.get(
            "/api/v1/failure-queue?status=new",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["data"]["total"] == 1

    def test_get_failure_queue_detail(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试获取失败队列详情。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_test", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]
        queue_id = setup_data["queue_item"].id

        response = client.get(
            f"/api/v1/failure-queue/{queue_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["data"]["queue_id"] == queue_id
        assert json_data["data"]["failure_rule_key"] == "batch_task_failed"

    def test_update_status_new_to_acknowledged(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试状态流转: new -> acknowledged。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_test", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]
        queue_id = setup_data["queue_item"].id

        response = client.patch(
            f"/api/v1/failure-queue/{queue_id}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "acknowledged"},
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["data"]["status"] == "acknowledged"
        assert json_data["data"]["acknowledged_at"] is not None

    def test_update_status_acknowledged_to_resolved(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试状态流转: acknowledged -> resolved。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_test", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]
        queue_id = setup_data["queue_item"].id

        # 先改为 acknowledged
        client.patch(
            f"/api/v1/failure-queue/{queue_id}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "acknowledged"},
        )

        # 再改为 resolved
        response = client.patch(
            f"/api/v1/failure-queue/{queue_id}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "resolved"},
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["data"]["status"] == "resolved"
        assert json_data["data"]["resolved_at"] is not None

    def test_update_status_invalid_transition(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试非法状态流转: new -> resolved（跳过 acknowledged）。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_test", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]
        queue_id = setup_data["queue_item"].id

        response = client.patch(
            f"/api/v1/failure-queue/{queue_id}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "resolved"},
        )

        assert response.status_code == 409  # Conflict

    def test_update_status_idempotent(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试幂等性：重复提交同一状态。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_test", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]
        queue_id = setup_data["queue_item"].id

        # 第一次提交
        response1 = client.patch(
            f"/api/v1/failure-queue/{queue_id}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "acknowledged"},
        )
        assert response1.status_code == 200

        # 重复提交
        response2 = client.patch(
            f"/api/v1/failure-queue/{queue_id}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "acknowledged"},
        )
        assert response2.status_code == 200  # 幂等返回成功

    def test_operator_cannot_access_out_of_scope(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试 operator 不能访问范围外邮箱的数据。"""
        # 创建另一个邮箱和队列项
        other_mailbox = Mailbox(
            name="其他邮箱",
            protocol="imap",
            host="imap.other.com",
            port=993,
            username="other@example.com",
            password_secret="encrypted",
            folder="INBOX",
            status="enabled",
        )
        db_session.add(other_mailbox)
        db_session.flush()

        other_queue = FailureMailQueue(
            mailbox_id=other_mailbox.id,
            source_message_id="<other@example.com>",
            failure_rule_key="batch_task_failed",
            status=FailureQueueStatus.NEW.value,
        )
        db_session.add(other_queue)
        db_session.commit()

        # 以 operator 登录
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_test", "password": "password123"},
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.json()}"
        token = login_response.json()["data"]["access_token"]
        assert token, "Token should not be empty"

        # 先验证 token 有效
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200, f"Auth me failed: {me_response.json()}"

        # 尝试访问范围外的队列项
        response = client.get(
            f"/api/v1/failure-queue/{other_queue.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # 403 Forbidden 因为邮箱不在 operator 的范围内
        # 注意：如果返回 404 也是可以接受的（不暴露是否存在）
        assert response.status_code in [403, 404], f"Expected 403/404, got {response.status_code}: {response.json()}"


class TestFailureQueueNotFound:
    """测试失败队列 404 场景。"""

    def test_get_nonexistent_queue(self, client: TestClient, db_session: Session):
        """测试获取不存在的队列项。"""
        # 创建用户并登录
        from app.models.user import User

        user = User(
            username="admin_nf",
            password_hash=AuthService.hash_password("password"),
            display_name="Admin",
            role=UserRole.ADMIN.value,
        )
        db_session.add(user)
        db_session.commit()

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_nf", "password": "password"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.get(
            "/api/v1/failure-queue/nonexistent-id",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
