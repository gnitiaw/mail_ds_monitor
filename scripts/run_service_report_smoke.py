"""服务报告 V1 冒烟联调脚本。

使用当前 worktree 的 back_end/.env 连接真实数据库，
并通过 FastAPI TestClient 完整跑一遍：
配置 -> 上传 -> 生成 -> 手工补充 -> 导出

输出目录：
    scripts/service-report-smoke-output/<timestamp>/
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import delete, select


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "back_end"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.core.scheduler as scheduler_module  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import create_application  # noqa: E402
from app.models.service_report import ServiceReportConfig, ServiceReportRun, ServiceReportSourceRun  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402


SAMPLES_DIR = ROOT_DIR / "scripts" / "service-report-samples"
OUTPUT_ROOT = ROOT_DIR / "scripts" / "service-report-smoke-output"
PROJECT_NAME = "Smoke Service Report Project"


def _disable_scheduler() -> None:
    scheduler_module.init_scheduler = lambda: None
    scheduler_module.recover_stuck_runs = lambda: None
    scheduler_module.shutdown_scheduler = lambda wait=True: None


def _ensure_user(username: str, display_name: str, role: str) -> User:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == username))
        if user:
            user.display_name = display_name
            user.role = role
            user.is_active = True
            db.commit()
            db.refresh(user)
            return user

        user = User(
            username=username,
            password_hash=AuthService.hash_password("password123"),
            display_name=display_name,
            role=role,
            is_active=True,
            mailbox_scope_ids=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _cleanup_existing(project_name: str) -> None:
    db = SessionLocal()
    try:
        configs = list(db.scalars(select(ServiceReportConfig).where(ServiceReportConfig.project_name == project_name)).all())
        config_ids = [item.id for item in configs]
        if config_ids:
            db.execute(delete(ServiceReportRun).where(ServiceReportRun.config_id.in_(config_ids)))
            db.execute(delete(ServiceReportSourceRun).where(ServiceReportSourceRun.config_id.in_(config_ids)))
            db.execute(delete(ServiceReportConfig).where(ServiceReportConfig.id.in_(config_ids)))
            db.commit()
    finally:
        db.close()


def _login(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "password123"},
    )
    response.raise_for_status()
    return response.json()["data"]["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_config(client: TestClient, token: str, name: str, report_type: str, owner_ids: dict[str, str]) -> dict[str, Any]:
    mapping = {
        "monthly": ("natural_month", "ops_service_monthly_v1"),
        "quarterly": ("natural_quarter", "ops_service_quarterly_v1"),
        "annual": ("natural_year", "ops_service_annual_v1"),
    }
    period_rule, template_key = mapping[report_type]
    response = client.post(
        "/api/v1/service-report-configs",
        json={
            "name": name,
            "project_name": PROJECT_NAME,
            "report_type": report_type,
            "period_rule": period_rule,
            "template_key": template_key,
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
        },
        headers=_headers(token),
    )
    response.raise_for_status()
    payload = response.json()
    if payload["code"] != 0:
        raise RuntimeError(payload)
    return payload["data"]


def _source_files(worklog_name: str, include_zentao: bool = True) -> dict[str, tuple[str, bytes, str]]:
    files: dict[str, tuple[str, bytes, str]] = {
        "inspection_file": ("inspection.csv", (SAMPLES_DIR / "inspection.csv").read_bytes(), "text/csv"),
        "vulnerability_file": ("vulnerability.csv", (SAMPLES_DIR / "vulnerability.csv").read_bytes(), "text/csv"),
        "worklog_file": (worklog_name, (SAMPLES_DIR / worklog_name).read_bytes(), "text/csv"),
    }
    if include_zentao:
        files["zentao_bug_file"] = ("zentao_bug.csv", (SAMPLES_DIR / "zentao_bug.csv").read_bytes(), "text/csv")
    return files


def _create_source_run(
    client: TestClient,
    token: str,
    config_id: str,
    window_start: str,
    window_end: str,
    worklog_name: str,
    include_zentao: bool = True,
) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/service-report-configs/{config_id}/source-runs",
        data={"window_start": window_start, "window_end": window_end},
        files=_source_files(worklog_name, include_zentao),
        headers=_headers(token),
    )
    response.raise_for_status()
    payload = response.json()
    if payload["code"] != 0:
        raise RuntimeError(payload)
    return payload["data"]


def _create_report_run(
    client: TestClient,
    token: str,
    config_id: str,
    source_run_id: str,
    window_start: str,
    window_end: str,
) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/service-report-configs/{config_id}/report-runs",
        json={
            "window_start": window_start,
            "window_end": window_end,
            "source_run_id": source_run_id,
            "force_regenerate": False,
        },
        headers=_headers(token),
    )
    response.raise_for_status()
    payload = response.json()
    if payload["code"] != 0:
        raise RuntimeError(payload)
    return payload["data"]


def _get_run_detail(client: TestClient, token: str, run_id: str) -> dict[str, Any]:
    response = client.get(f"/api/v1/service-report-runs/{run_id}", headers=_headers(token))
    response.raise_for_status()
    payload = response.json()
    if payload["code"] != 0:
        raise RuntimeError(payload)
    return payload["data"]


def _save_manual_note(client: TestClient, token: str, run_id: str, note: str) -> None:
    response = client.patch(
        f"/api/v1/service-report-runs/{run_id}/manual-note",
        json={"manual_note": note},
        headers=_headers(token),
    )
    response.raise_for_status()
    payload = response.json()
    if payload["code"] != 0:
        raise RuntimeError(payload)


def _export_artifact(
    client: TestClient,
    token: str,
    run_id: str,
    export_format: str,
    output_dir: Path,
) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/service-report-runs/{run_id}/export",
        json={"format": export_format, "overwrite": True},
        headers=_headers(token),
    )
    response.raise_for_status()
    payload = response.json()
    if payload["code"] != 0:
        raise RuntimeError(payload)
    artifact = payload["data"]

    download = client.get(
        f"/api/v1/service-report-runs/{run_id}/export",
        params={"format": export_format},
        headers=_headers(token),
    )
    download.raise_for_status()
    target = output_dir / artifact["file_name"]
    target.write_bytes(download.content)
    artifact["saved_path"] = str(target)
    return artifact


def _expect_blocked_export(client: TestClient, token: str, run_id: str) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/service-report-runs/{run_id}/export",
        json={"format": "markdown", "overwrite": True},
        headers=_headers(token),
    )
    if response.status_code != 409:
        raise RuntimeError(f"expected 409, got {response.status_code}: {response.text}")
    payload = response.json()
    if payload["code"] != 40903:
        raise RuntimeError(payload)
    return payload


def main() -> None:
    _disable_scheduler()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    run_dir = OUTPUT_ROOT / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=True)

    _cleanup_existing(PROJECT_NAME)

    admin = _ensure_user("service_report_admin", "服务报告管理员", "admin")
    project_owner = _ensure_user("service_report_owner_project", "服务报告项目Owner", "operator")
    template_owner = _ensure_user("service_report_owner_template", "服务报告模板Owner", "operator")
    metric_owner = _ensure_user("service_report_owner_metric", "服务报告口径Owner", "operator")
    owner_ids = {
        "project_owner_user_id": project_owner.id,
        "template_owner_user_id": template_owner.id,
        "metric_owner_user_id": metric_owner.id,
    }

    app = create_application()
    result: dict[str, Any] = {
        "project_name": PROJECT_NAME,
        "output_dir": str(run_dir),
        "users": {
            "admin": admin.username,
            "project_owner": project_owner.username,
            "template_owner": template_owner.username,
            "metric_owner": metric_owner.username,
        },
        "scenarios": {},
    }

    with TestClient(app) as client:
        token = _login(client, admin.username)

        monthly = _create_config(client, token, "Smoke 服务报告月报配置", "monthly", owner_ids)
        ready_source = _create_source_run(
            client,
            token,
            monthly["config_id"],
            "2026-04-01T00:00:00Z",
            "2026-04-30T23:59:59Z",
            "worklog.csv",
        )
        ready_run = _create_report_run(
            client,
            token,
            monthly["config_id"],
            ready_source["source_run_id"],
            "2026-04-01T00:00:00Z",
            "2026-04-30T23:59:59Z",
        )
        _save_manual_note(client, token, ready_run["run_id"], "冒烟联调：月报 ready 场景通过。")
        ready_detail = _get_run_detail(client, token, ready_run["run_id"])
        ready_markdown = _export_artifact(client, token, ready_run["run_id"], "markdown", run_dir)
        ready_html = _export_artifact(client, token, ready_run["run_id"], "html", run_dir)
        result["scenarios"]["ready"] = {
            "config_id": monthly["config_id"],
            "source_run_id": ready_source["source_run_id"],
            "run_id": ready_run["run_id"],
            "completeness_status": ready_detail["completeness_status"],
            "source_statuses": {item["source_type"]: item["status"] for item in ready_source["source_results"]},
            "exports": [ready_markdown, ready_html],
        }

        quarterly = _create_config(client, token, "Smoke 服务报告季报配置", "quarterly", owner_ids)
        partial_source = _create_source_run(
            client,
            token,
            quarterly["config_id"],
            "2026-04-01T00:00:00Z",
            "2026-06-30T23:59:59Z",
            "worklog-partial.csv",
        )
        partial_run = _create_report_run(
            client,
            token,
            quarterly["config_id"],
            partial_source["source_run_id"],
            "2026-04-01T00:00:00Z",
            "2026-06-30T23:59:59Z",
        )
        partial_detail = _get_run_detail(client, token, partial_run["run_id"])
        partial_markdown = _export_artifact(client, token, partial_run["run_id"], "markdown", run_dir)
        result["scenarios"]["partial"] = {
            "config_id": quarterly["config_id"],
            "source_run_id": partial_source["source_run_id"],
            "run_id": partial_run["run_id"],
            "completeness_status": partial_detail["completeness_status"],
            "source_statuses": {item["source_type"]: item["status"] for item in partial_source["source_results"]},
            "export": partial_markdown,
        }

        annual = _create_config(client, token, "Smoke 服务报告年报配置", "annual", owner_ids)
        blocked_source = _create_source_run(
            client,
            token,
            annual["config_id"],
            "2026-01-01T00:00:00Z",
            "2026-12-31T23:59:59Z",
            "worklog.csv",
            include_zentao=False,
        )
        blocked_run = _create_report_run(
            client,
            token,
            annual["config_id"],
            blocked_source["source_run_id"],
            "2026-01-01T00:00:00Z",
            "2026-12-31T23:59:59Z",
        )
        blocked_detail = _get_run_detail(client, token, blocked_run["run_id"])
        blocked_export = _expect_blocked_export(client, token, blocked_run["run_id"])
        result["scenarios"]["blocked"] = {
            "config_id": annual["config_id"],
            "source_run_id": blocked_source["source_run_id"],
            "run_id": blocked_run["run_id"],
            "completeness_status": blocked_detail["completeness_status"],
            "source_statuses": {item["source_type"]: item["status"] for item in blocked_source["source_results"]},
            "export_error": blocked_export,
        }

    (run_dir / "smoke-results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
