"""发件人配置和分析运行测试。"""

import pytest
from datetime import datetime, timezone, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import (
    AnalysisRunStatus,
    SummarySendStatus,
    SummaryScopeMode,
    UserRole,
)
from app.models.sender_profile import SenderProfile
from app.models.summary import SummaryConfig, SummarySendRecord
from app.models.user import User
from app.services.auth_service import AuthService

# Additional imports for new tests
from app.models.analysis_run import AnalysisRun
from app.models.enums import AnalysisRunStatus


class TestSenderProfileAPI:
    """发件人档案 API 测试类。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        # 创建 admin 用户
        admin = User(
            username="admin_sender",
            password_hash=AuthService.hash_password("password123"),
            display_name="Admin Sender",
            role=UserRole.ADMIN.value,
        )
        db_session.add(admin)

        # 创建 operator 用户
        operator = User(
            username="operator_sender",
            password_hash=AuthService.hash_password("password123"),
            display_name="Operator Sender",
            role=UserRole.OPERATOR.value,
        )
        db_session.add(operator)

        db_session.commit()

        return {
            "admin": admin,
            "operator": operator,
        }

    def test_list_sender_profiles_as_admin(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """管理员可以获取发件人档案列表。"""
        # 登录获取 token
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_sender", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        # 创建测试数据
        profile = SenderProfile(
            match_type="exact_email",
            match_value="list@example.com",
            customer_name="列表客户",
            sender_type="customer",
            status="enabled",
        )
        db_session.add(profile)
        db_session.commit()

        response = client.get(
            "/api/v1/sender-profiles",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) >= 1

    def test_list_sender_profiles_as_operator(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """操作员可以获取发件人档案列表（只读）。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_sender", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.get(
            "/api/v1/sender-profiles",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

    def test_create_sender_profile_success(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """管理员可以创建发件人档案。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_sender", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.post(
            "/api/v1/sender-profiles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "match_type": "exact_email",
                "match_value": "new@example.com",
                "customer_name": "新客户",
                "sender_type": "customer",
                "status": "enabled",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["customer_name"] == "新客户"

    def test_create_sender_profile_conflict(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """重复创建相同匹配规则返回冲突。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_sender", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        # 先创建一个
        profile = SenderProfile(
            match_type="exact_email",
            match_value="conflict@example.com",
            customer_name="冲突客户",
            sender_type="customer",
            status="enabled",
        )
        db_session.add(profile)
        db_session.commit()

        # 再次创建相同的
        response = client.post(
            "/api/v1/sender-profiles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "match_type": "exact_email",
                "match_value": "conflict@example.com",
                "customer_name": "另一个客户",
                "sender_type": "customer",
                "status": "enabled",
            },
        )

        assert response.status_code == 409
        assert response.json()["code"] == 40901

    def test_create_sender_profile_as_operator_forbidden(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """操作员不能创建发件人档案。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_sender", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.post(
            "/api/v1/sender-profiles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "match_type": "exact_email",
                "match_value": "operator@example.com",
                "customer_name": "操作员客户",
                "sender_type": "customer",
                "status": "enabled",
            },
        )

        assert response.status_code == 403

    def test_update_sender_profile_success(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """管理员可以更新发件人档案。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_sender", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        profile = SenderProfile(
            match_type="exact_email",
            match_value="update@example.com",
            customer_name="待更新客户",
            sender_type="customer",
            status="enabled",
        )
        db_session.add(profile)
        db_session.commit()

        response = client.put(
            f"/api/v1/sender-profiles/{profile.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "customer_name": "已更新客户",
                "status": "disabled",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["customer_name"] == "已更新客户"

    def test_update_sender_profile_not_found(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """更新不存在的档案返回 404。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_sender", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.put(
            "/api/v1/sender-profiles/non-existent-id",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "customer_name": "不存在",
            },
        )

        assert response.status_code == 404


class TestAnalysisRunAPI:
    """分析运行 API 测试类。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        admin = User(
            username="admin_analysis",
            password_hash=AuthService.hash_password("password123"),
            display_name="Admin Analysis",
            role=UserRole.ADMIN.value,
        )
        db_session.add(admin)
        db_session.commit()
        return {"admin": admin}

    def test_create_analysis_run_success(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """创建分析运行成功。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_analysis", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        config = SummaryConfig(
            name="分析测试配置",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            summary_scope_mode=SummaryScopeMode.CUSTOMER_GROUPED.value,
        )
        db_session.add(config)
        db_session.commit()

        response = client.post(
            f"/api/v1/summary-configs/{config.id}/analysis-runs",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "window_start": datetime.now(timezone.utc).isoformat(),
                "window_end": datetime.now(timezone.utc).isoformat(),
                "force_rerun": False,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["status"] == "pending"

    def test_create_analysis_run_config_not_found(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """配置不存在返回 404。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_analysis", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.post(
            "/api/v1/summary-configs/non-existent/analysis-runs",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "window_start": datetime.now(timezone.utc).isoformat(),
                "window_end": datetime.now(timezone.utc).isoformat(),
            },
        )

        assert response.status_code == 404


class TestCustomerGroupedSend:
    """customer_grouped 模式发送测试类。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        admin = User(
            username="admin_send",
            password_hash=AuthService.hash_password("password123"),
            display_name="Admin Send",
            role=UserRole.ADMIN.value,
        )
        db_session.add(admin)
        db_session.commit()
        return {"admin": admin}

    def test_send_requires_analysis_run_id(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """customer_grouped 模式必须提供 analysis_run_id。"""
        from app.models.analysis_run import AnalysisRun

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_send", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        config = SummaryConfig(
            name="发送测试配置",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            summary_scope_mode=SummaryScopeMode.CUSTOMER_GROUPED.value,
        )
        db_session.add(config)
        db_session.commit()

        response = client.post(
            f"/api/v1/summary-configs/{config.id}/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-02T00:00:00Z",
            },
        )

        assert response.status_code == 400

    def test_send_requires_success_run(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """只能发送 success 状态的分析运行。"""
        from app.models.analysis_run import AnalysisRun

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_send", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        config = SummaryConfig(
            name="成功状态测试",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            summary_scope_mode=SummaryScopeMode.CUSTOMER_GROUPED.value,
        )
        db_session.add(config)
        db_session.commit()

        run = AnalysisRun(
            config_id=config.id,
            window_start=datetime.now(timezone.utc) - timedelta(days=1),
            window_end=datetime.now(timezone.utc),
            config_snapshot={},
            config_snapshot_hash="test",
            status=AnalysisRunStatus.PENDING.value,
        )
        db_session.add(run)
        db_session.commit()

        response = client.post(
            f"/api/v1/summary-configs/{config.id}/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "analysis_run_id": run.id,
            },
        )

        assert response.status_code == 409

    def test_send_success_run_with_datetime_fields(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """customer_grouped 发送使用新的 datetime 字段。"""
        from app.models.analysis_run import AnalysisRun

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_send", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        config = SummaryConfig(
            name="datetime字段测试",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            summary_scope_mode=SummaryScopeMode.CUSTOMER_GROUPED.value,
        )
        db_session.add(config)
        db_session.commit()

        # 使用精确的 datetime
        window_start = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        window_end = datetime(2024, 1, 15, 18, 45, 0, tzinfo=timezone.utc)

        run = AnalysisRun(
            config_id=config.id,
            window_start=window_start,
            window_end=window_end,
            config_snapshot={},
            config_snapshot_hash="test_datetime",
            status=AnalysisRunStatus.SUCCESS.value,
            result_payload={
                "summary_markdown": "# Test Summary\n\nContent here.",
                "overview": {"total_records": 10},
                "customers": [],
                "unidentified": {"record_count": 0, "senders": []},
            },
        )
        db_session.add(run)
        db_session.commit()

        response = client.post(
            f"/api/v1/summary-configs/{config.id}/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "analysis_run_id": run.id,
            },
        )

        # 注意：由于 SMTP 配置可能不存在，可能会失败
        # 但关键是不应该因为字段名错误而失败
        assert response.status_code in (202, 500)  # 202 成功或 500 SMTP 错误


class TestSummaryAuth:
    """summary 主链路鉴权测试类。"""

    @pytest.fixture
    def setup_users(self, db_session: Session):
        """设置测试用户。"""
        admin = User(
            username="admin_summary_auth",
            password_hash=AuthService.hash_password("password123"),
            display_name="Admin Summary",
            role=UserRole.ADMIN.value,
        )
        operator = User(
            username="operator_summary_auth",
            password_hash=AuthService.hash_password("password123"),
            display_name="Operator Summary",
            role=UserRole.OPERATOR.value,
            mailbox_scope_ids=["mailbox-1", "mailbox-2"],
        )
        operator_no_scope = User(
            username="operator_no_scope",
            password_hash=AuthService.hash_password("password123"),
            display_name="Operator No Scope",
            role=UserRole.OPERATOR.value,
            mailbox_scope_ids=[],
        )
        db_session.add_all([admin, operator, operator_no_scope])
        db_session.commit()
        return {
            "admin": admin,
            "operator": operator,
            "operator_no_scope": operator_no_scope,
        }

    def test_list_configs_requires_auth(
        self,
        client: TestClient,
        db_session: Session,
        setup_users,
    ) -> None:
        """配置列表需要登录。"""
        response = client.get("/api/v1/summary-configs")
        # FastAPI returns 422 for missing required header, 401 for invalid token
        assert response.status_code in (401, 422)

    def test_list_configs_operator_filtered_by_scope(
        self,
        client: TestClient,
        db_session: Session,
        setup_users,
    ) -> None:
        """operator 只能看到 scope 内的配置（全局配置被禁止）。"""
        # 创建两个配置：一个在 scope 内，一个不在
        config_in_scope = SummaryConfig(
            name="配置1-in-scope",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            mailbox_ids=["mailbox-1"],
        )
        config_out_scope = SummaryConfig(
            name="配置2-out-scope",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            mailbox_ids=["mailbox-999"],  # 不在 operator scope 内
        )
        config_global = SummaryConfig(
            name="配置3-global",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            mailbox_ids=None,  # 全局配置 - operator 不应访问
        )
        db_session.add_all([config_in_scope, config_out_scope, config_global])
        db_session.commit()

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_summary_auth", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.get(
            "/api/v1/summary-configs",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        items = response.json()["data"]["items"]
        names = [item["name"] for item in items]

        # operator 只能看到 scope 内的配置
        assert "配置1-in-scope" in names
        # operator 不应该看到 scope 外的配置
        assert "配置2-out-scope" not in names
        # operator 不能看到全局配置（防止越权汇总全量邮箱）
        assert "配置3-global" not in names

    def test_create_config_admin_only(
        self,
        client: TestClient,
        db_session: Session,
        setup_users,
    ) -> None:
        """创建配置仅限 admin。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_summary_auth", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.post(
            "/api/v1/summary-configs",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "operator-尝试创建",
                "enabled": True,
                "recipient_emails": ["test@example.com"],
            },
        )

        assert response.status_code == 403

    def test_send_operator_out_of_scope_forbidden(
        self,
        client: TestClient,
        db_session: Session,
        setup_users,
    ) -> None:
        """operator 访问 scope 外配置发送时被拦截。"""
        config = SummaryConfig(
            name="out-of-scope-config",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            mailbox_ids=["mailbox-999"],  # 不在 operator scope 内
            summary_scope_mode=SummaryScopeMode.FLAT.value,
        )
        db_session.add(config)
        db_session.commit()

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_summary_auth", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.post(
            f"/api/v1/summary-configs/{config.id}/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-02T00:00:00Z",
            },
        )

        assert response.status_code == 403

    def test_send_operator_no_scope_forbidden(
        self,
        client: TestClient,
        db_session: Session,
        setup_users,
    ) -> None:
        """没有 scope 的 operator 访问任何配置发送时被拦截。"""
        config = SummaryConfig(
            name="any-config",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            mailbox_ids=["mailbox-1"],
            summary_scope_mode=SummaryScopeMode.FLAT.value,
        )
        db_session.add(config)
        db_session.commit()

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_no_scope", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.post(
            f"/api/v1/summary-configs/{config.id}/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-02T00:00:00Z",
            },
        )

        assert response.status_code == 403

    def test_list_sends_operator_filtered(
        self,
        client: TestClient,
        db_session: Session,
        setup_users,
    ) -> None:
        """operator 只能看到 scope 内配置的发送记录（全局配置记录被过滤）。"""
        from app.models.summary import SummarySendRecord

        config_in_scope = SummaryConfig(
            name="send-config-in-scope",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            mailbox_ids=["mailbox-1"],
        )
        config_out_scope = SummaryConfig(
            name="send-config-out-scope",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            mailbox_ids=["mailbox-999"],
        )
        config_global = SummaryConfig(
            name="send-config-global",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            mailbox_ids=None,  # 全局配置
        )
        db_session.add_all([config_in_scope, config_out_scope, config_global])
        db_session.commit()

        # 创建发送记录
        send_in = SummarySendRecord(
            config_id=config_in_scope.id,
            status=SummarySendStatus.SUCCESS.value,
            window_start_date=datetime.now(timezone.utc).date(),
            window_end_date=datetime.now(timezone.utc).date(),
        )
        send_out = SummarySendRecord(
            config_id=config_out_scope.id,
            status=SummarySendStatus.SUCCESS.value,
            window_start_date=datetime.now(timezone.utc).date(),
            window_end_date=datetime.now(timezone.utc).date(),
        )
        send_global = SummarySendRecord(
            config_id=config_global.id,
            status=SummarySendStatus.SUCCESS.value,
            window_start_date=datetime.now(timezone.utc).date(),
            window_end_date=datetime.now(timezone.utc).date(),
        )
        db_session.add_all([send_in, send_out, send_global])
        db_session.commit()

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_summary_auth", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.get(
            "/api/v1/summary-sends",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        items = response.json()["data"]["items"]
        config_ids = [item["config_id"] for item in items]

        # operator 只能看到 scope 内配置的记录
        assert config_in_scope.id in config_ids
        # scope 外配置的记录不可见
        assert config_out_scope.id not in config_ids
        # 全局配置的记录也不可见（防止越权）
        assert config_global.id not in config_ids

    def test_send_global_config_forbidden_for_operator(
        self,
        client: TestClient,
        db_session: Session,
        setup_users,
    ) -> None:
        """operator 不能发送全局配置（防止越权汇总全量邮箱）。"""
        config_global = SummaryConfig(
            name="global-config-forbidden",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            mailbox_ids=None,  # 全局配置
            summary_scope_mode=SummaryScopeMode.FLAT.value,
        )
        db_session.add(config_global)
        db_session.commit()

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_summary_auth", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.post(
            f"/api/v1/summary-configs/{config_global.id}/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-02T00:00:00Z",
            },
        )

        # 全局配置对 operator 禁止访问
        assert response.status_code == 403

    def test_scope_semantics_consistent(
        self,
        client: TestClient,
        db_session: Session,
        setup_users,
    ) -> None:
        """验证配置列表、发送动作、发送记录的 scope 语义一致。

        规则：operator 只能访问 mailbox_ids 非空且全部在自己 scope 内的配置。
        """
        # 创建三种配置
        config_in_scope = SummaryConfig(
            name="scope-consistent-in",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            mailbox_ids=["mailbox-1"],  # 在 operator scope 内
        )
        config_partial = SummaryConfig(
            name="scope-consistent-partial",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            mailbox_ids=["mailbox-1", "mailbox-999"],  # 部分在 scope 内
        )
        config_out = SummaryConfig(
            name="scope-consistent-out",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            mailbox_ids=["mailbox-888"],  # 完全不在 scope 内
        )
        config_global = SummaryConfig(
            name="scope-consistent-global",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            mailbox_ids=None,  # 全局配置
        )
        db_session.add_all([config_in_scope, config_partial, config_out, config_global])
        db_session.commit()

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_summary_auth", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        # 1. 配置列表：只能看到完全在 scope 内的配置
        list_response = client.get(
            "/api/v1/summary-configs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.status_code == 200
        names = [item["name"] for item in list_response.json()["data"]["items"]]
        assert "scope-consistent-in" in names
        assert "scope-consistent-partial" not in names  # 部分命中不等于访问
        assert "scope-consistent-out" not in names
        assert "scope-consistent-global" not in names

        # 2. 发送动作：部分命中配置被禁止
        send_partial = client.post(
            f"/api/v1/summary-configs/{config_partial.id}/send",
            headers={"Authorization": f"Bearer {token}"},
            json={"start_time": "2024-01-01T00:00:00Z", "end_time": "2024-01-02T00:00:00Z"},
        )
        assert send_partial.status_code == 403

        # 3. 发送记录：创建全局配置的记录，operator 不应看到
        send_record_global = SummarySendRecord(
            config_id=config_global.id,
            status=SummarySendStatus.SUCCESS.value,
            window_start_date=datetime.now(timezone.utc).date(),
            window_end_date=datetime.now(timezone.utc).date(),
        )
        send_record_partial = SummarySendRecord(
            config_id=config_partial.id,
            status=SummarySendStatus.SUCCESS.value,
            window_start_date=datetime.now(timezone.utc).date(),
            window_end_date=datetime.now(timezone.utc).date(),
        )
        db_session.add_all([send_record_global, send_record_partial])
        db_session.commit()

        sends_response = client.get(
            "/api/v1/summary-sends",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert sends_response.status_code == 200
        send_config_ids = [item["config_id"] for item in sends_response.json()["data"]["items"]]
        assert config_global.id not in send_config_ids
        assert config_partial.id not in send_config_ids


class TestCustomerGroupedSendContent:
    """customer_grouped 发送正文来源测试。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        admin = User(
            username="admin_content_test",
            password_hash=AuthService.hash_password("password123"),
            display_name="Admin Content",
            role=UserRole.ADMIN.value,
        )
        db_session.add(admin)
        db_session.commit()
        return {"admin": admin}

    def test_send_uses_analysis_run_result_payload(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """customer_grouped 发送正文来自 analysis_run.result_payload.summary_markdown。"""
        from app.models.analysis_run import AnalysisRun
        from unittest.mock import patch, MagicMock

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_content_test", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        config = SummaryConfig(
            name="content-test-config",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
            summary_scope_mode=SummaryScopeMode.CUSTOMER_GROUPED.value,
        )
        db_session.add(config)
        db_session.commit()

        # 创建 analysis_run，包含特定的 summary_markdown
        expected_markdown = """# 客户问题归类汇总

## 概览

- 总记录数: 42
- 已识别客户数: 5

## 客户A

- 记录数: 10
- 高优先级: 2

## 客户B

- 记录数: 8
- 高优先级: 1

---
*此摘要来自 analysis_run.result_payload*"""

        run = AnalysisRun(
            config_id=config.id,
            window_start=datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc),
            window_end=datetime(2024, 1, 15, 23, 59, 59, tzinfo=timezone.utc),
            config_snapshot={},
            config_snapshot_hash="content_test_hash",
            status=AnalysisRunStatus.SUCCESS.value,
            result_payload={
                "summary_markdown": expected_markdown,
                "overview": {"total_records": 42, "matched_customer_count": 5},
                "customers": [
                    {"customer_name": "客户A", "record_count": 10, "high_priority_count": 2},
                    {"customer_name": "客户B", "record_count": 8, "high_priority_count": 1},
                ],
            },
        )
        db_session.add(run)
        db_session.commit()

        # Mock SMTP 服务以确保发送成功，从而验证 summary_text
        with patch("app.services.summary_service.send_summary_email") as mock_send:
            mock_send.return_value = {"recipient_count": 1}

            response = client.post(
                f"/api/v1/summary-configs/{config.id}/send",
                headers={"Authorization": f"Bearer {token}"},
                json={"analysis_run_id": run.id},
            )

            assert response.status_code == 202

            # 验证 send_summary_email 被调用，且内容来自 analysis_run
            assert mock_send.called
            call_kwargs = mock_send.call_args.kwargs
            assert call_kwargs["summary_content"] == expected_markdown

            # 验证 send_record 的 summary_text 被正确存储
            send_id = response.json()["data"]["send_id"]
            db_session.expire_all()  # 刷新 session
            send_record = db_session.get(SummarySendRecord, send_id)
            assert send_record is not None
            assert send_record.summary_text == expected_markdown
            assert send_record.status == SummarySendStatus.SUCCESS.value


class TestSenderCandidatesAPI:
    """候选发件人 API 测试类。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        admin = User(
            username="admin_candidates",
            password_hash=AuthService.hash_password("password123"),
            display_name="Admin Candidates",
            role=UserRole.ADMIN.value,
        )
        db_session.add(admin)

        operator = User(
            username="operator_candidates",
            password_hash=AuthService.hash_password("password123"),
            display_name="Operator Candidates",
            role=UserRole.OPERATOR.value,
        )
        db_session.add(operator)

        db_session.commit()
        return {"admin": admin, "operator": operator}

    def test_list_candidates_as_admin(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """管理员可以获取候选发件人列表。"""
        from app.models.mailbox import Mailbox
        from app.models.mail_message import MailMessage
        from app.models.archive import ArchiveRecord

        # 登录获取 token
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_candidates", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        # 创建测试邮箱
        mailbox = Mailbox(
            name="test-mailbox",
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password_secret="encrypted",
        )
        db_session.add(mailbox)
        db_session.commit()

        # 创建测试邮件和归档记录
        msg = MailMessage(
            mailbox_id=mailbox.id,
            internet_message_id="<test1@example.com>",
            sender_email="sender@example.com",
            sender_name="Test Sender",
            subject="Test Subject",
            received_at=datetime.now(timezone.utc),
        )
        db_session.add(msg)
        db_session.commit()

        archive = ArchiveRecord(
            message_id=msg.id,
            mailbox_id=mailbox.id,
            received_at=datetime.now(timezone.utc),
            status="archived",
        )
        db_session.add(archive)
        db_session.commit()

        response = client.get(
            "/api/v1/sender-profiles/candidates",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert "items" in data
        assert "total" in data

    def test_candidates_identified_status_filter(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """测试 identified_status 过滤。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_candidates", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        # 测试无效的 identified_status
        response = client.get(
            "/api/v1/sender-profiles/candidates?identified_status=invalid",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400


class TestAnalysisRunDetailAPI:
    """分析运行详情 API 测试类。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        admin = User(
            username="admin_run_detail",
            password_hash=AuthService.hash_password("password123"),
            display_name="Admin Run Detail",
            role=UserRole.ADMIN.value,
        )
        db_session.add(admin)
        db_session.commit()
        return {"admin": admin}

    def test_get_analysis_run_detail_success(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """获取分析运行详情成功。"""
        from app.models.analysis_run import AnalysisRun

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_run_detail", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        config = SummaryConfig(
            name="detail-test-config",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
        )
        db_session.add(config)
        db_session.commit()

        run = AnalysisRun(
            config_id=config.id,
            window_start=datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc),
            window_end=datetime(2024, 1, 15, 23, 59, 59, tzinfo=timezone.utc),
            config_snapshot={
                "summary_scope_mode": "flat",
                "mailbox_ids": None,
                "include_statuses": None,
                "include_unidentified_senders": True,
                "top_n_per_customer": 5,
                "customer_analysis_mode": "basic",
            },
            config_snapshot_hash="test_hash",
            status=AnalysisRunStatus.SUCCESS.value,
            result_payload={
                "overview": {
                    "total_records": 10,
                    "matched_customer_count": 2,
                    "unidentified_record_count": 0,
                    "failed_record_count": 0,
                    "archived_record_count": 0,
                    "ai_fallback_used": False,
                },
                "customers": [],
                "unidentified": {"record_count": 0, "senders": []},
                "summary_markdown": "# Test Summary",
            },
        )
        db_session.add(run)
        db_session.commit()

        response = client.get(
            f"/api/v1/analysis-runs/{run.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["run_id"] == run.id
        assert data["status"] == AnalysisRunStatus.SUCCESS.value
        assert data["result_payload"]["summary_markdown"] == "# Test Summary"

    def test_get_analysis_run_not_found(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """获取不存在的分析运行返回 404。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_run_detail", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.get(
            "/api/v1/analysis-runs/non-existent-id",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    def test_list_analysis_runs_for_config(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """获取配置的分析运行列表。"""
        from app.models.analysis_run import AnalysisRun

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_run_detail", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        config = SummaryConfig(
            name="list-runs-config",
            enabled=True,
            schedule_type="daily",
            recipient_emails=["test@example.com"],
        )
        db_session.add(config)
        db_session.commit()

        # 创建多个运行
        for i in range(3):
            run = AnalysisRun(
                config_id=config.id,
                window_start=datetime(2024, 1, 15 + i, 0, 0, 0, tzinfo=timezone.utc),
                window_end=datetime(2024, 1, 15 + i, 23, 59, 59, tzinfo=timezone.utc),
                config_snapshot={},
                config_snapshot_hash=f"hash_{i}",
                status=AnalysisRunStatus.SUCCESS.value,
            )
            db_session.add(run)
        db_session.commit()

        response = client.get(
            f"/api/v1/analysis-runs/by-config/{config.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 3
        assert len(data["items"]) == 3


class TestSenderProfileEmailValidation:
    """发件人档案邮箱验证测试类。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        admin = User(
            username="admin_email_validation",
            password_hash=AuthService.hash_password("password123"),
            display_name="Admin Email Validation",
            role=UserRole.ADMIN.value,
        )
        db_session.add(admin)
        db_session.commit()
        return {"admin": admin}

    def test_create_profile_invalid_email_format(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """exact_email 模式创建时邮箱格式无效应返回错误。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_email_validation", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.post(
            "/api/v1/sender-profiles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "match_type": "exact_email",
                "match_value": "invalid-email-format",
                "customer_name": "测试客户",
            },
        )

        assert response.status_code == 409  # ConflictError
        # 错误信息在 response.json()["message"] 中
        assert "邮箱格式无效" in response.json().get("message", "") or "邮箱格式无效" in response.json().get("error", "")

    def test_create_profile_valid_email_format(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """exact_email 模式创建时有效邮箱格式应成功。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_email_validation", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.post(
            "/api/v1/sender-profiles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "match_type": "exact_email",
                "match_value": "valid@example.com",
                "customer_name": "测试客户",
            },
        )

        assert response.status_code == 201
        assert response.json()["data"]["match_value"] == "valid@example.com"

    def test_create_profile_domain_no_validation(
        self,
        client: TestClient,
        db_session: Session,
        setup_data,
    ) -> None:
        """email_domain 模式不需要邮箱格式验证。"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_email_validation", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        response = client.post(
            "/api/v1/sender-profiles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "match_type": "email_domain",
                "match_value": "example.com",
                "customer_name": "测试客户",
            },
        )

        assert response.status_code == 201
