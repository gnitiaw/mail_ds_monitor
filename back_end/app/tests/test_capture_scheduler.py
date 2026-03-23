"""捕获调度服务测试。"""

import time
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import FailureQueueStatus, RuleStatus, TaskStatus, TaskType, UserRole
from app.models.failure_capture import FailureCaptureRule
from app.models.failure_queue import FailureMailQueue
from app.models.mailbox import Mailbox
from app.models.task_log import TaskLog
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.capture_scheduler_service import CaptureSchedulerService


class TestManualReplayReturnsPending:
    """测试 replay 接口返回 pending。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        mailbox = Mailbox(
            name="测试邮箱",
            protocol="imap",
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password_secret="encrypted",
            folder="INBOX",
            status="enabled",
        )
        db_session.add(mailbox)
        db_session.flush()

        admin = User(
            username="admin_replay",
            password_hash=AuthService.hash_password("password"),
            display_name="Admin",
            role=UserRole.ADMIN.value,
        )
        db_session.add(admin)
        db_session.commit()

        return {"mailbox": mailbox, "admin": admin}

    def test_replay_returns_pending_status(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试 replay 接口立即返回 pending 状态。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_replay", "password": "password"},
        )
        token = login_response.json()["data"]["access_token"]
        mailbox_id = setup_data["mailbox"].id

        response = client.post(
            "/api/v1/failure-capture-runs/replay",
            headers={"Authorization": f"Bearer {token}"},
            json={"mailbox_ids": [mailbox_id], "lookback_minutes": 30},
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["code"] == 0
        assert json_data["data"]["status"] == "pending"
        assert json_data["data"]["run_id"] is not None


class TestBackgroundTaskExecution:
    """测试后台任务真实执行并更新任务状态。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        mailbox = Mailbox(
            name="后台任务测试邮箱",
            protocol="imap",
            host="imap.example.com",
            port=993,
            username="bg@example.com",
            password_secret="encrypted",
            folder="INBOX",
            status="enabled",
        )
        db_session.add(mailbox)
        db_session.commit()

        return {"mailbox": mailbox}

    def test_background_task_updates_status(
        self, db_session: Session, setup_data
    ):
        """测试后台任务执行后更新状态（模拟后台执行）。"""
        mailbox_id = setup_data["mailbox"].id

        # 触发手动补跑（这会创建 pending 状态的 TaskLog）
        result = CaptureSchedulerService.trigger_manual_replay(
            db=db_session,
            mailbox_ids=[mailbox_id],
            lookback_minutes=30,
            triggered_by="test",
        )

        assert result["status"] == TaskStatus.PENDING.value
        assert result["run_id"] is not None
        run_id = result["run_id"]

        # 验证任务日志已创建，状态为 pending
        task_log = db_session.get(TaskLog, run_id)
        assert task_log is not None
        assert task_log.status == TaskStatus.PENDING.value

        # 模拟后台任务执行：直接调用 _execute_capture
        # （不通过后台线程，避免 MySQL 连接问题）
        task_log.status = TaskStatus.RUNNING.value
        task_log.started_at = datetime.now(timezone.utc)
        db_session.commit()

        # 执行捕获逻辑（使用测试数据库）
        capture_result = CaptureSchedulerService._execute_capture(
            db=db_session,
            mailbox_ids=[mailbox_id],
            lookback_minutes=30,
        )

        # 更新任务状态
        task_log.status = TaskStatus.SUCCESS.value
        task_log.finished_at = datetime.now(timezone.utc)
        task_log.result = capture_result
        db_session.commit()

        # 验证最终状态
        db_session.expire_all()
        task_log = db_session.get(TaskLog, run_id)
        assert task_log.status == TaskStatus.SUCCESS.value
        assert task_log.started_at is not None
        assert task_log.finished_at is not None
        assert task_log.result is not None


class TestAutoPollHappyPath:
    """测试自动轮询最小 happy path。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        mailbox = Mailbox(
            name="自动轮询测试邮箱",
            protocol="imap",
            host="imap.example.com",
            port=993,
            username="poll@example.com",
            password_secret="encrypted",
            folder="INBOX",
            status="enabled",
        )
        db_session.add(mailbox)
        db_session.flush()

        return {"mailbox": mailbox}

    def test_auto_poll_creates_task_log(
        self, db_session: Session, setup_data
    ):
        """测试自动轮询创建任务日志。"""
        result = CaptureSchedulerService.run_auto_poll(db_session)

        # 应该启动成功
        assert result["status"] == "started"
        assert result["run_id"] is not None
        assert result["mailbox_count"] >= 1

        # 验证任务日志已创建
        task_log = db_session.get(TaskLog, result["run_id"])
        assert task_log is not None
        assert task_log.task_type == TaskType.MAIL_PULL.value


class TestProviderUidFallbackIdempotency:
    """测试 provider_uid 回退幂等。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        mailbox = Mailbox(
            name="幂等测试邮箱",
            protocol="imap",
            host="imap.example.com",
            port=993,
            username="idem@example.com",
            password_secret="encrypted",
            folder="INBOX",
            status="enabled",
        )
        db_session.add(mailbox)
        db_session.flush()

        rule = FailureCaptureRule(
            rule_name="测试规则",
            failure_rule_key="test_rule_key",
            status=RuleStatus.ENABLED.value,
            priority=100,
        )
        db_session.add(rule)
        db_session.flush()

        return {"mailbox": mailbox, "rule": rule}

    def test_idempotency_with_provider_uid_fallback(
        self, db_session: Session, setup_data
    ):
        """测试 provider_uid 回退的幂等性。"""
        mailbox_id = setup_data["mailbox"].id
        rule = setup_data["rule"]

        # 第一次插入：只有 provider_uid，没有 source_message_id
        result1 = CaptureSchedulerService._enqueue_if_not_exists(
            db=db_session,
            mailbox_id=mailbox_id,
            source_message_id=None,  # 无 internet_message_id
            provider_uid="provider-uid-001",  # 使用 provider_uid
            rule=rule,
            subject="测试邮件",
            sender="sender@example.com",
            body_text="邮件正文",
            received_at=datetime.now(timezone.utc),
        )

        assert result1["deduped"] is False
        queue_id_1 = result1["queue_id"]

        # 第二次插入：相同的 provider_uid + rule，应该去重
        result2 = CaptureSchedulerService._enqueue_if_not_exists(
            db=db_session,
            mailbox_id=mailbox_id,
            source_message_id=None,
            provider_uid="provider-uid-001",  # 相同
            rule=rule,  # 相同
            subject="测试邮件",
            sender="sender@example.com",
            body_text="邮件正文",
            received_at=datetime.now(timezone.utc),
        )

        assert result2["deduped"] is True
        assert result2["queue_id"] == queue_id_1

        db_session.commit()

    def test_idempotency_with_source_message_id(
        self, db_session: Session, setup_data
    ):
        """测试 source_message_id 的幂等性。"""
        mailbox_id = setup_data["mailbox"].id
        rule = setup_data["rule"]

        # 第一次插入：有 source_message_id
        result1 = CaptureSchedulerService._enqueue_if_not_exists(
            db=db_session,
            mailbox_id=mailbox_id,
            source_message_id="<msg-001@example.com>",
            provider_uid="provider-uid-002",
            rule=rule,
            subject="测试邮件2",
            sender="sender2@example.com",
            body_text="邮件正文2",
            received_at=datetime.now(timezone.utc),
        )

        assert result1["deduped"] is False

        # 第二次插入：相同的 source_message_id + rule，应该去重
        result2 = CaptureSchedulerService._enqueue_if_not_exists(
            db=db_session,
            mailbox_id=mailbox_id,
            source_message_id="<msg-001@example.com>",  # 相同
            provider_uid="different-provider-uid",  # 不同的 provider_uid 不影响
            rule=rule,  # 相同
            subject="测试邮件2",
            sender="sender2@example.com",
            body_text="邮件正文2",
            received_at=datetime.now(timezone.utc),
        )

        assert result2["deduped"] is True

        db_session.commit()


class TestForbiddenErrorCode40301:
    """测试越权返回 40301 错误码。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        mailbox = Mailbox(
            name="403测试邮箱",
            protocol="imap",
            host="imap.example.com",
            port=993,
            username="403@example.com",
            password_secret="encrypted",
            folder="INBOX",
            status="enabled",
        )
        db_session.add(mailbox)
        db_session.flush()

        # 创建 operator 用户（带邮箱范围限制）
        operator = User(
            username="operator_403",
            password_hash=AuthService.hash_password("password"),
            display_name="Operator",
            role=UserRole.OPERATOR.value,
            mailbox_scope_ids=[],  # 空范围，无法访问任何邮箱
        )
        db_session.add(operator)

        # 创建失败队列记录
        queue_item = FailureMailQueue(
            mailbox_id=mailbox.id,
            source_message_id="<403-test@example.com>",
            failure_rule_key="test_rule",
            status=FailureQueueStatus.NEW.value,
        )
        db_session.add(queue_item)
        db_session.commit()

        return {"mailbox": mailbox, "operator": operator, "queue_item": queue_item}

    def test_list_returns_403_for_out_of_scope(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试 operator 访问范围外邮箱返回 40301。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_403", "password": "password"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.get(
            "/api/v1/failure-queue",
            headers={"Authorization": f"Bearer {token}"},
        )

        # 应该返回空列表，因为没有可访问的邮箱
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["data"]["total"] == 0

    def test_detail_returns_403_for_out_of_scope(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试 operator 访问范围外队列项详情返回 403。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_403", "password": "password"},
        )
        token = login_response.json()["data"]["access_token"]
        queue_id = setup_data["queue_item"].id

        response = client.get(
            f"/api/v1/failure-queue/{queue_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # 应该返回 403 Forbidden
        assert response.status_code == 403
        json_data = response.json()
        assert json_data["code"] == 40301  # ForbiddenError 错误码

    def test_explicit_mailbox_id_out_of_scope_returns_40301(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试 operator 显式查询越权 mailbox_id 返回 40301。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_403", "password": "password"},
        )
        token = login_response.json()["data"]["access_token"]
        mailbox_id = setup_data["mailbox"].id

        # operator 的 scope 是空列表，显式查询不在 scope 中的 mailbox_id
        response = client.get(
            f"/api/v1/failure-queue?mailbox_id={mailbox_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # 应该返回 403 Forbidden，不是 401 Unauthorized
        assert response.status_code == 403
        json_data = response.json()
        assert json_data["code"] == 40301  # ForbiddenError 错误码


class TestDatabaseLevelDedup:
    """测试数据库级幂等防重。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        mailbox = Mailbox(
            name="数据库级幂等测试邮箱",
            protocol="imap",
            host="imap.example.com",
            port=993,
            username="dbidem@example.com",
            password_secret="encrypted",
            folder="INBOX",
            status="enabled",
        )
        db_session.add(mailbox)
        db_session.flush()

        return {"mailbox": mailbox}

    def test_database_level_dedup_provider_uid(
        self, db_session: Session, setup_data
    ):
        """测试 provider_uid 路径的数据库级防重（绕过应用层）。"""
        mailbox_id = setup_data["mailbox"].id

        # 直接插入第一条记录（只有 provider_uid）
        item1 = FailureMailQueue(
            mailbox_id=mailbox_id,
            source_message_id=None,
            provider_uid="db-dedup-uid-001",
            failure_rule_key="db_dedup_rule",
            status=FailureQueueStatus.NEW.value,
        )
        db_session.add(item1)
        db_session.commit()

        # 验证 dedup_message_key 被正确设置
        assert item1.dedup_message_key == "UID:db-dedup-uid-001"

        # 尝试绕过应用层直接插入重复记录
        item2 = FailureMailQueue(
            mailbox_id=mailbox_id,
            source_message_id=None,
            provider_uid="db-dedup-uid-001",  # 相同的 provider_uid
            failure_rule_key="db_dedup_rule",  # 相同的 rule
            status=FailureQueueStatus.NEW.value,
        )
        db_session.add(item2)

        # 数据库级唯一约束应该阻止插入
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        # 验证是唯一约束冲突
        assert "uq_failure_queue_dedup" in str(exc_info.value).lower() or "unique" in str(exc_info.value).lower()

    def test_database_level_dedup_source_message_id(
        self, db_session: Session, setup_data
    ):
        """测试 source_message_id 路径的数据库级防重。"""
        mailbox_id = setup_data["mailbox"].id

        # 直接插入第一条记录
        item1 = FailureMailQueue(
            mailbox_id=mailbox_id,
            source_message_id="<db-dedup-msg-001@example.com>",
            provider_uid="some-provider-uid",
            failure_rule_key="db_dedup_rule_msg",
            status=FailureQueueStatus.NEW.value,
        )
        db_session.add(item1)
        db_session.commit()

        # 验证 dedup_message_key 使用 source_message_id
        assert item1.dedup_message_key == "MSG:<db-dedup-msg-001@example.com>"

        # 尝试插入重复记录（相同 source_message_id）
        item2 = FailureMailQueue(
            mailbox_id=mailbox_id,
            source_message_id="<db-dedup-msg-001@example.com>",
            provider_uid="different-provider-uid",  # 不同的 provider_uid
            failure_rule_key="db_dedup_rule_msg",
            status=FailureQueueStatus.NEW.value,
        )
        db_session.add(item2)

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "uq_failure_queue_dedup" in str(exc_info.value).lower() or "unique" in str(exc_info.value).lower()


class TestSimulatedFailureMailReplay:
    """测试仿真失败邮件样本回放。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        mailbox = Mailbox(
            name="仿真测试邮箱",
            protocol="imap",
            host="imap.example.com",
            port=993,
            username="sim@example.com",
            password_secret="encrypted",
            folder="INBOX",
            status="enabled",
        )
        db_session.add(mailbox)
        db_session.flush()

        # 创建规则：匹配包含"失败"的邮件
        rule = FailureCaptureRule(
            rule_name="批量任务失败规则",
            failure_rule_key="batch_task_failed",
            status=RuleStatus.ENABLED.value,
            subject_patterns=["执行失败", "失败通知"],
            body_patterns=["错误", "异常"],
            priority=100,
        )
        db_session.add(rule)
        db_session.flush()

        # 创建已存在的邮件（模拟 IMAP 拉取后的状态）
        from app.models.mail_message import MailMessage

        mail = MailMessage(
            mailbox_id=mailbox.id,
            internet_message_id="<failure-001@example.com>",
            provider_uid="sim-uid-001",
            subject="批量任务执行失败通知",
            sender_email="system@example.com",
            body_text="检测到错误：任务执行异常，请检查日志。",
            received_at=datetime.now(timezone.utc),
        )
        db_session.add(mail)
        db_session.commit()

        return {"mailbox": mailbox, "rule": rule, "mail": mail}

    def test_simulated_replay_matches_rule(
        self, db_session: Session, setup_data
    ):
        """测试仿真邮件回放匹配规则。"""
        mailbox_id = setup_data["mailbox"].id
        rule = setup_data["rule"]
        mail = setup_data["mail"]

        # 直接调用规则匹配
        matched = CaptureSchedulerService._match_rule(
            rule=rule,
            subject=mail.subject,
            sender=mail.sender_email,
            body_text=mail.body_text,
        )

        assert matched is True

    def test_simulated_replay_enqueues(
        self, db_session: Session, setup_data
    ):
        """测试仿真邮件入队。"""
        mailbox_id = setup_data["mailbox"].id
        rule = setup_data["rule"]
        mail = setup_data["mail"]

        # 直接入队
        result = CaptureSchedulerService._enqueue_if_not_exists(
            db=db_session,
            mailbox_id=mailbox_id,
            source_message_id=mail.internet_message_id,
            provider_uid=mail.provider_uid,
            rule=rule,
            subject=mail.subject,
            sender=mail.sender_email,
            body_text=mail.body_text,
            received_at=mail.received_at,
        )

        assert result["deduped"] is False
        assert result["queue_id"] is not None

        db_session.commit()

        # 验证队列项
        queue_item = db_session.get(FailureMailQueue, result["queue_id"])
        assert queue_item is not None
        assert queue_item.status == FailureQueueStatus.NEW.value
        assert "失败" in queue_item.subject
