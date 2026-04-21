"""服务报告接口测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.user import User
from app.services.auth_service import AuthService


class TestServiceReportAPI:
    """服务报告接口测试。"""

    def _create_user(
        self,
        db_session: Session,
        username: str,
        display_name: str,
        role: str,
    ) -> User:
        user = User(
            username=username,
            password_hash=AuthService.hash_password("password123"),
            display_name=display_name,
            role=role,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def _get_token(self, client: TestClient, username: str) -> str:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "password123"},
        )
        assert response.status_code == 200
        return response.json()["data"]["access_token"]

    def _config_payload(self, owner_ids: dict[str, str], **overrides) -> dict:
        payload = {
            "name": "试点项目月报配置",
            "project_name": "Alpha 项目",
            "report_type": "monthly",
            "period_rule": "natural_month",
            "template_key": "ops_service_monthly_v1",
            "project_owner_user_id": owner_ids["project_owner_user_id"],
            "template_owner_user_id": owner_ids["template_owner_user_id"],
            "metric_owner_user_id": owner_ids["metric_owner_user_id"],
            "enabled": True,
            "recipient_emails": ["ops@example.com"],
            "source_bindings": [
                {"source_type": "inspection", "ingest_mode": "file_import"},
                {"source_type": "vulnerability", "ingest_mode": "file_import"},
                {"source_type": "worklog", "ingest_mode": "file_import"},
                {"source_type": "zentao_bug", "ingest_mode": "file_import"},
            ],
        }
        payload.update(overrides)
        return payload

    def _valid_files(self) -> dict:
        return {
            "inspection_file": (
                "inspection.csv",
                (
                    "inspection_date,system_name,status,issue_count,summary\n"
                    "2026-04-01,app-server,正常,1,月度巡检发现 1 个问题\n"
                ).encode("utf-8"),
                "text/csv",
            ),
            "vulnerability_file": (
                "vulnerability.csv",
                (
                    "vulnerability_id,severity,status,fixed_at,system_name,summary\n"
                    "V-1001,high,fixed,2026-04-02,app-server,修复高危漏洞\n"
                ).encode("utf-8"),
                "text/csv",
            ),
            "worklog_file": (
                "worklog.csv",
                (
                    "work_date,category,summary,hours,result\n"
                    "2026-04-03,巡检,处理巡检问题,2,已完成\n"
                ).encode("utf-8"),
                "text/csv",
            ),
            "zentao_bug_file": (
                "zentao_bug.csv",
                (
                    "bug_id,severity,status,title,closed_at\n"
                    "BUG-1,medium,closed,登录偶发报错,2026-04-05\n"
                ).encode("utf-8"),
                "text/csv",
            ),
        }

    def _create_config(self, client: TestClient, token: str, payload: dict) -> dict:
        response = client.post(
            "/api/v1/service-report-configs",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        return response.json()["data"]

    def test_list_user_options(self, client: TestClient, db_session: Session):
        admin = self._create_user(db_session, "admin_service_report", "管理员", UserRole.ADMIN.value)
        self._create_user(db_session, "owner_a", "项目负责人", UserRole.OPERATOR.value)
        self._create_user(db_session, "owner_b", "模板负责人", UserRole.OPERATOR.value)

        token = self._get_token(client, admin.username)
        response = client.get(
            "/api/v1/users/options",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["items"]) == 3
        assert {item["display_name"] for item in data["items"]} == {"管理员", "项目负责人", "模板负责人"}

    def test_create_config_enforces_single_project(self, client: TestClient, db_session: Session):
        admin = self._create_user(db_session, "admin_single_project", "管理员", UserRole.ADMIN.value)
        project_owner = self._create_user(db_session, "project_owner", "项目负责人", UserRole.OPERATOR.value)
        template_owner = self._create_user(db_session, "template_owner", "模板负责人", UserRole.OPERATOR.value)
        metric_owner = self._create_user(db_session, "metric_owner", "口径负责人", UserRole.OPERATOR.value)
        token = self._get_token(client, admin.username)

        owner_ids = {
            "project_owner_user_id": project_owner.id,
            "template_owner_user_id": template_owner.id,
            "metric_owner_user_id": metric_owner.id,
        }
        self._create_config(client, token, self._config_payload(owner_ids))

        response = client.post(
            "/api/v1/service-report-configs",
            json=self._config_payload(
                owner_ids,
                name="另一个项目配置",
                project_name="Beta 项目",
                report_type="quarterly",
                period_rule="natural_quarter",
                template_key="ops_service_quarterly_v1",
            ),
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409
        data = response.json()
        assert data["code"] == 40902

    def test_create_config_requires_owner_fields(self, client: TestClient, db_session: Session):
        admin = self._create_user(db_session, "admin_owner_required", "管理员", UserRole.ADMIN.value)
        token = self._get_token(client, admin.username)

        response = client.post(
            "/api/v1/service-report-configs",
            json={
                "name": "缺少 owner 配置",
                "project_name": "Alpha 项目",
                "report_type": "monthly",
                "period_rule": "natural_month",
                "template_key": "ops_service_monthly_v1",
                "enabled": True,
                "recipient_emails": ["ops@example.com"],
                "source_bindings": [
                    {"source_type": "inspection", "ingest_mode": "file_import"},
                    {"source_type": "vulnerability", "ingest_mode": "file_import"},
                    {"source_type": "worklog", "ingest_mode": "file_import"},
                    {"source_type": "zentao_bug", "ingest_mode": "file_import"},
                ],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == 40001

    def test_list_configs_supports_pagination(self, client: TestClient, db_session: Session):
        admin = self._create_user(db_session, "admin_config_paging", "管理员", UserRole.ADMIN.value)
        project_owner = self._create_user(db_session, "project_owner_paging", "项目负责人", UserRole.OPERATOR.value)
        template_owner = self._create_user(db_session, "template_owner_paging", "模板负责人", UserRole.OPERATOR.value)
        metric_owner = self._create_user(db_session, "metric_owner_paging", "口径负责人", UserRole.OPERATOR.value)
        token = self._get_token(client, admin.username)
        owner_ids = {
            "project_owner_user_id": project_owner.id,
            "template_owner_user_id": template_owner.id,
            "metric_owner_user_id": metric_owner.id,
        }

        self._create_config(client, token, self._config_payload(owner_ids, name="月报配置"))
        self._create_config(
            client,
            token,
            self._config_payload(
                owner_ids,
                name="季报配置",
                report_type="quarterly",
                period_rule="natural_quarter",
                template_key="ops_service_quarterly_v1",
            ),
        )

        response = client.get(
            "/api/v1/service-report-configs",
            params={"page": 2, "page_size": 1},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["page"] == 2
        assert data["page_size"] == 1
        assert data["total"] == 2
        assert len(data["items"]) == 1

    def test_source_runs_reject_json_body(self, client: TestClient, db_session: Session):
        admin = self._create_user(db_session, "admin_json_source_run", "管理员", UserRole.ADMIN.value)
        project_owner = self._create_user(db_session, "project_owner_json", "项目负责人", UserRole.OPERATOR.value)
        template_owner = self._create_user(db_session, "template_owner_json", "模板负责人", UserRole.OPERATOR.value)
        metric_owner = self._create_user(db_session, "metric_owner_json", "口径负责人", UserRole.OPERATOR.value)
        token = self._get_token(client, admin.username)
        config = self._create_config(
            client,
            token,
            self._config_payload(
                {
                    "project_owner_user_id": project_owner.id,
                    "template_owner_user_id": template_owner.id,
                    "metric_owner_user_id": metric_owner.id,
                },
                name="JSON source-run 配置",
            ),
        )

        response = client.post(
            f"/api/v1/service-report-configs/{config['config_id']}/source-runs",
            json={
                "window_start": "2026-04-01T00:00:00Z",
                "window_end": "2026-04-30T23:59:59Z",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422

    def test_generate_ready_report_and_export(self, client: TestClient, db_session: Session):
        admin = self._create_user(db_session, "admin_ready_report", "管理员", UserRole.ADMIN.value)
        project_owner = self._create_user(db_session, "project_owner_ready", "项目负责人", UserRole.OPERATOR.value)
        template_owner = self._create_user(db_session, "template_owner_ready", "模板负责人", UserRole.OPERATOR.value)
        metric_owner = self._create_user(db_session, "metric_owner_ready", "口径负责人", UserRole.OPERATOR.value)
        token = self._get_token(client, admin.username)
        config = self._create_config(
            client,
            token,
            self._config_payload(
                {
                    "project_owner_user_id": project_owner.id,
                    "template_owner_user_id": template_owner.id,
                    "metric_owner_user_id": metric_owner.id,
                }
            ),
        )

        source_run_response = client.post(
            f"/api/v1/service-report-configs/{config['config_id']}/source-runs",
            data={
                "window_start": "2026-04-01T00:00:00Z",
                "window_end": "2026-04-30T23:59:59Z",
            },
            files=self._valid_files(),
            headers={"Authorization": f"Bearer {token}"},
        )

        assert source_run_response.status_code == 201
        source_run = source_run_response.json()["data"]
        assert source_run["status"] == "success"

        run_response = client.post(
            f"/api/v1/service-report-configs/{config['config_id']}/report-runs",
            json={
                "window_start": "2026-04-01T00:00:00Z",
                "window_end": "2026-04-30T23:59:59Z",
                "source_run_id": source_run["source_run_id"],
                "force_regenerate": False,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert run_response.status_code == 201
        run = run_response.json()["data"]
        assert run["completeness_status"] == "ready"

        detail_response = client.get(
            f"/api/v1/service-report-runs/{run['run_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()["data"]
        assert detail["completeness_status"] == "ready"
        assert len(detail["report_payload"]["sections"]) == 6
        assert "原始邮件正文" not in str(detail)

        note_response = client.patch(
            f"/api/v1/service-report-runs/{run['run_id']}/manual-note",
            json={"manual_note": "本期重点为高危漏洞已完成修复。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert note_response.status_code == 200
        assert note_response.json()["data"]["manual_note"] == "本期重点为高危漏洞已完成修复。"

        export_response = client.post(
            f"/api/v1/service-report-runs/{run['run_id']}/export",
            json={"format": "markdown", "overwrite": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert export_response.status_code == 200
        download_response = client.get(
            f"/api/v1/service-report-runs/{run['run_id']}/export",
            params={"format": "markdown"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert download_response.status_code == 200
        assert "仅供内部复核" not in download_response.text
        assert "人工补充说明" in download_response.text

    def test_generate_partial_report_allows_internal_export(self, client: TestClient, db_session: Session):
        admin = self._create_user(db_session, "admin_partial_report", "管理员", UserRole.ADMIN.value)
        project_owner = self._create_user(db_session, "project_owner_partial", "项目负责人", UserRole.OPERATOR.value)
        template_owner = self._create_user(db_session, "template_owner_partial", "模板负责人", UserRole.OPERATOR.value)
        metric_owner = self._create_user(db_session, "metric_owner_partial", "口径负责人", UserRole.OPERATOR.value)
        token = self._get_token(client, admin.username)
        config = self._create_config(
            client,
            token,
            self._config_payload(
                {
                    "project_owner_user_id": project_owner.id,
                    "template_owner_user_id": template_owner.id,
                    "metric_owner_user_id": metric_owner.id,
                },
                name="试点项目季报配置",
                report_type="quarterly",
                period_rule="natural_quarter",
                template_key="ops_service_quarterly_v1",
            ),
        )

        files = self._valid_files()
        files["worklog_file"] = (
            "worklog.csv",
            (
                "work_date,category,summary,hours,result\n"
                "2026-04-03,巡检,处理巡检问题,2,已完成\n"
                "2026-04-04,变更,,1,待复核\n"
            ).encode("utf-8"),
            "text/csv",
        )

        source_run_response = client.post(
            f"/api/v1/service-report-configs/{config['config_id']}/source-runs",
            data={
                "window_start": "2026-04-01T00:00:00Z",
                "window_end": "2026-06-30T23:59:59Z",
            },
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert source_run_response.status_code == 201
        source_run = source_run_response.json()["data"]
        statuses = {item["source_type"]: item["status"] for item in source_run["source_results"]}
        assert statuses["worklog"] == "partial_success"

        run_response = client.post(
            f"/api/v1/service-report-configs/{config['config_id']}/report-runs",
            json={
                "window_start": "2026-04-01T00:00:00Z",
                "window_end": "2026-06-30T23:59:59Z",
                "source_run_id": source_run["source_run_id"],
                "force_regenerate": False,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert run_response.status_code == 201
        run = run_response.json()["data"]
        assert run["completeness_status"] == "partial"

        export_response = client.post(
            f"/api/v1/service-report-runs/{run['run_id']}/export",
            json={"format": "markdown", "overwrite": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert export_response.status_code == 200

        download_response = client.get(
            f"/api/v1/service-report-runs/{run['run_id']}/export",
            params={"format": "markdown"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert download_response.status_code == 200
        assert "仅供内部复核" in download_response.text

    def test_generate_blocked_report_cannot_export(self, client: TestClient, db_session: Session):
        admin = self._create_user(db_session, "admin_blocked_report", "管理员", UserRole.ADMIN.value)
        project_owner = self._create_user(db_session, "project_owner_blocked", "项目负责人", UserRole.OPERATOR.value)
        template_owner = self._create_user(db_session, "template_owner_blocked", "模板负责人", UserRole.OPERATOR.value)
        metric_owner = self._create_user(db_session, "metric_owner_blocked", "口径负责人", UserRole.OPERATOR.value)
        token = self._get_token(client, admin.username)
        config = self._create_config(
            client,
            token,
            self._config_payload(
                {
                    "project_owner_user_id": project_owner.id,
                    "template_owner_user_id": template_owner.id,
                    "metric_owner_user_id": metric_owner.id,
                },
                name="试点项目年报配置",
                report_type="annual",
                period_rule="natural_year",
                template_key="ops_service_annual_v1",
            ),
        )

        files = self._valid_files()
        del files["zentao_bug_file"]

        source_run_response = client.post(
            f"/api/v1/service-report-configs/{config['config_id']}/source-runs",
            data={
                "window_start": "2026-01-01T00:00:00Z",
                "window_end": "2026-12-31T23:59:59Z",
            },
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert source_run_response.status_code == 201
        source_run = source_run_response.json()["data"]
        statuses = {item["source_type"]: item["status"] for item in source_run["source_results"]}
        assert statuses["zentao_bug"] == "failed"

        run_response = client.post(
            f"/api/v1/service-report-configs/{config['config_id']}/report-runs",
            json={
                "window_start": "2026-01-01T00:00:00Z",
                "window_end": "2026-12-31T23:59:59Z",
                "source_run_id": source_run["source_run_id"],
                "force_regenerate": False,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert run_response.status_code == 201
        run = run_response.json()["data"]
        assert run["completeness_status"] == "blocked"

        export_response = client.post(
            f"/api/v1/service-report-runs/{run['run_id']}/export",
            json={"format": "markdown", "overwrite": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert export_response.status_code == 409
        data = export_response.json()
        assert data["code"] == 40903
