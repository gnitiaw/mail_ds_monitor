"""失败捕获规则测试。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import RuleStatus, UserRole
from app.models.failure_capture import FailureCaptureRule
from app.models.user import User
from app.services.auth_service import AuthService


class TestFailureRulesAPI:
    """失败捕获规则 API 测试类。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        # 创建 admin 用户
        admin = User(
            username="rules_admin",
            password_hash=AuthService.hash_password("password123"),
            display_name="Rules Admin",
            role=UserRole.ADMIN.value,
        )
        db_session.add(admin)

        # 创建 operator 用户
        operator = User(
            username="rules_operator",
            password_hash=AuthService.hash_password("password123"),
            display_name="Rules Operator",
            role=UserRole.OPERATOR.value,
        )
        db_session.add(operator)

        # 创建测试规则
        rule = FailureCaptureRule(
            rule_name="测试失败规则",
            failure_rule_key="test_batch_failed",
            status=RuleStatus.ENABLED.value,
            customer_scope_type="explicit_list",
            customer_match_config={"customers": ["测试客户"]},
            mailbox_ids=["mailbox-001"],
            sender_patterns=["system@example.com"],
            subject_patterns=["执行失败"],
            body_patterns=["超时", "失败"],
            priority=100,
        )
        db_session.add(rule)
        db_session.commit()

        return {
            "admin": admin,
            "operator": operator,
            "rule": rule,
        }

    def test_list_rules_as_admin(self, client: TestClient, db_session: Session, setup_data):
        """测试 admin 查看规则列表。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "rules_admin", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.get(
            "/api/v1/failure-rules",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["code"] == 0
        assert json_data["data"]["total"] == 1

    def test_list_rules_as_operator_forbidden(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试 operator 不能查看规则列表。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "rules_operator", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.get(
            "/api/v1/failure-rules",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    def test_create_rule_success(self, client: TestClient, db_session: Session, setup_data):
        """测试创建规则成功。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "rules_admin", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.post(
            "/api/v1/failure-rules",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "rule_name": "新规则",
                "failure_rule_key": "new_batch_failed",
                "status": "enabled",
                "customer_scope_type": "explicit_list",
                "customer_match_config": {"customers": ["新客户"]},
                "mailbox_ids": ["mailbox-002"],
                "sender_patterns": ["noreply@example.com"],
                "subject_patterns": ["任务失败"],
                "body_patterns": ["错误"],
                "priority": 50,
            },
        )

        assert response.status_code == 201
        json_data = response.json()
        assert json_data["data"]["rule_name"] == "新规则"

    def test_create_rule_duplicate_key_conflict(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试创建规则 - failure_rule_key 重复。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "rules_admin", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.post(
            "/api/v1/failure-rules",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "rule_name": "重复规则",
                "failure_rule_key": "test_batch_failed",  # 已存在
                "status": "enabled",
            },
        )

        assert response.status_code == 409  # Conflict

    def test_update_rule_success(self, client: TestClient, db_session: Session, setup_data):
        """测试更新规则成功。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "rules_admin", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]
        rule_id = setup_data["rule"].id

        response = client.put(
            f"/api/v1/failure-rules/{rule_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "rule_name": "更新后的规则",
                "status": "disabled",
                "priority": 200,
            },
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["data"]["status"] == "disabled"


class TestRuleMatching:
    """规则匹配逻辑测试。"""

    @pytest.fixture
    def setup_rules(self, db_session: Session):
        """设置测试规则。"""
        rule1 = FailureCaptureRule(
            rule_name="高优先级规则",
            failure_rule_key="high_priority_failed",
            status=RuleStatus.ENABLED.value,
            sender_patterns=["system@example.com"],
            subject_patterns=["紧急", "失败"],
            priority=200,
        )
        rule2 = FailureCaptureRule(
            rule_name="低优先级规则",
            failure_rule_key="low_priority_failed",
            status=RuleStatus.ENABLED.value,
            sender_patterns=["noreply@example.com"],
            subject_patterns=["失败"],
            priority=100,
        )
        rule3 = FailureCaptureRule(
            rule_name="禁用规则",
            failure_rule_key="disabled_rule",
            status=RuleStatus.DISABLED.value,
            sender_patterns=["disabled@example.com"],
            subject_patterns=["失败"],
            priority=300,
        )
        db_session.add_all([rule1, rule2, rule3])
        db_session.commit()

        return {"rule1": rule1, "rule2": rule2, "rule3": rule3}

    def test_match_sender_and_subject(
        self, client: TestClient, db_session: Session, setup_rules
    ):
        """测试匹配发件人和主题。"""
        from app.services.capture_scheduler_service import CaptureSchedulerService

        rule = setup_rules["rule1"]
        matched = CaptureSchedulerService._match_rule(
            rule=rule,
            subject="紧急：批量任务失败通知",
            sender="system@example.com",
            body_text=None,
        )

        assert matched is True

    def test_no_match_sender(
        self, client: TestClient, db_session: Session, setup_rules
    ):
        """测试发件人不匹配。"""
        from app.services.capture_scheduler_service import CaptureSchedulerService

        rule = setup_rules["rule1"]
        matched = CaptureSchedulerService._match_rule(
            rule=rule,
            subject="紧急：批量任务失败通知",
            sender="other@example.com",  # 不匹配
            body_text=None,
        )

        assert matched is False

    def test_no_match_subject(
        self, client: TestClient, db_session: Session, setup_rules
    ):
        """测试主题不匹配。"""
        from app.services.capture_scheduler_service import CaptureSchedulerService

        rule = setup_rules["rule1"]
        matched = CaptureSchedulerService._match_rule(
            rule=rule,
            subject="正常通知",  # 不包含"紧急"或"失败"
            sender="system@example.com",
            body_text=None,
        )

        assert matched is False

    def test_body_pattern_match(
        self, client: TestClient, db_session: Session, setup_rules
    ):
        """测试正文模式匹配。"""
        from app.services.capture_scheduler_service import CaptureSchedulerService

        rule = setup_rules["rule2"]
        matched = CaptureSchedulerService._match_rule(
            rule=rule,
            subject="任务失败通知",
            sender="noreply@example.com",
            body_text="任务执行超时，请检查",  # 不需要匹配 body_patterns（规则没有设置）
        )

        assert matched is True  # sender 和 subject 都匹配
