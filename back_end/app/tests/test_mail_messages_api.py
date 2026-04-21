"""原始邮件重试与任务查询接口测试。"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.active_task_lock import ActiveTaskLock
from app.models.archive import ArchiveRecord
from app.models.enums import ExtractionStatus, ProcessingStatus, TaskStatus, TaskType, UserRole
from app.models.mail_message import MailMessage
from app.models.mailbox import Mailbox
from app.models.task_log import TaskLog
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.extraction_retry_service import MAX_EXTRACTION_RETRIES, execute_extraction_retry_async


def _is_utc_timestamp(value: str) -> bool:
    return value.endswith("Z") or value.endswith("+00:00")


def _create_mailbox(db_session: Session, *, name: str, username: str) -> Mailbox:
    mailbox = Mailbox(
        name=name,
        protocol="imap",
        host="imap.example.com",
        port=993,
        username=username,
        password_secret="encrypted",
        folder="INBOX",
        status="enabled",
    )
    db_session.add(mailbox)
    db_session.flush()
    return mailbox


def _create_user(
    db_session: Session,
    *,
    username: str,
    role: str,
    mailbox_scope_ids: list[str] | None = None,
) -> User:
    user = User(
        username=username,
        password_hash=AuthService.hash_password("password123"),
        display_name=username,
        role=role,
        mailbox_scope_ids=mailbox_scope_ids,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _auth_headers(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_mail_message(
    db_session: Session,
    *,
    mailbox: Mailbox,
    subject: str,
    extraction_status: str = ExtractionStatus.FAILED.value,
    parse_status: str = ProcessingStatus.PARSED.value,
    retry_count: int = 0,
    extraction_error: str | None = "temporary llm error",
    suffix: str | None = None,
) -> MailMessage:
    unique = suffix or subject.replace(" ", "-")
    message = MailMessage(
        mailbox_id=mailbox.id,
        internet_message_id=f"<{unique}@example.com>",
        provider_uid=unique,
        folder="INBOX",
        subject=subject,
        sender_email=f"{unique}@example.com",
        body_text=f"body-{unique}",
        parse_status=parse_status,
        extraction_status=extraction_status,
        extraction_error=extraction_error,
        retry_count=retry_count,
        received_at=datetime.now(timezone.utc),
    )
    db_session.add(message)
    db_session.flush()
    return message


def _create_failed_archive(db_session: Session, *, mailbox: Mailbox, message: MailMessage) -> ArchiveRecord:
    archive = ArchiveRecord(
        mailbox_id=mailbox.id,
        message_id=message.id,
        status=ProcessingStatus.FAILED.value,
        extraction_error=message.extraction_error,
        received_at=message.received_at,
    )
    db_session.add(archive)
    db_session.flush()
    return archive


class TestMailMessageReadAPI:
    def test_list_mail_messages_returns_retry_limits(self, client: TestClient, db_session: Session):
        mailbox = _create_mailbox(db_session, name="原始邮件列表测试邮箱", username="list@example.com")
        _create_mail_message(
            db_session,
            mailbox=mailbox,
            subject="failed retryable",
            retry_count=1,
        )
        db_session.commit()

        response = client.get(f"/api/v1/mail-messages?mailbox_id={mailbox.id}")

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["total"] == 1
        assert payload["items"][0]["retry_count"] == 1
        assert payload["items"][0]["max_retries"] == MAX_EXTRACTION_RETRIES
        assert _is_utc_timestamp(payload["items"][0]["received_at"])

    def test_get_mail_message_detail_returns_retry_limits(self, client: TestClient, db_session: Session):
        mailbox = _create_mailbox(db_session, name="原始邮件详情测试邮箱", username="detail@example.com")
        message = _create_mail_message(
            db_session,
            mailbox=mailbox,
            subject="detail retryable",
            retry_count=2,
        )
        db_session.commit()

        response = client.get(f"/api/v1/mail-messages/{message.id}")

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["message_id"] == message.id
        assert payload["retry_count"] == 2
        assert payload["max_retries"] == MAX_EXTRACTION_RETRIES
        assert payload["last_retry_at"] is None


class TestRetryTaskEndpoints:
    @pytest.fixture
    def setup_users(self, db_session: Session) -> dict[str, User | Mailbox]:
        mailbox = _create_mailbox(db_session, name="重试邮箱A", username="retry-a@example.com")
        other_mailbox = _create_mailbox(db_session, name="重试邮箱B", username="retry-b@example.com")
        admin = _create_user(db_session, username="admin_mail_retry", role=UserRole.ADMIN.value)
        operator = _create_user(
            db_session,
            username="operator_mail_retry",
            role=UserRole.OPERATOR.value,
            mailbox_scope_ids=[mailbox.id],
        )
        return {
            "mailbox": mailbox,
            "other_mailbox": other_mailbox,
            "admin": admin,
            "operator": operator,
        }

    def test_retry_single_extraction_rejects_invalid_authorization(
        self,
        client: TestClient,
        db_session: Session,
        setup_users: dict[str, User | Mailbox],
    ):
        message = _create_mail_message(
            db_session,
            mailbox=setup_users["mailbox"],
            subject="unauthorized single retry",
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/mail-messages/{message.id}/retry-extraction",
            headers={"Authorization": "invalid-token"},
        )

        assert response.status_code == 401
        assert response.json()["code"] == 40101

    def test_retry_single_extraction_rejects_missing_authorization_header(
        self,
        client: TestClient,
        db_session: Session,
        setup_users: dict[str, User | Mailbox],
    ):
        message = _create_mail_message(
            db_session,
            mailbox=setup_users["mailbox"],
            subject="missing auth single retry",
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/mail-messages/{message.id}/retry-extraction",
        )

        assert response.status_code == 401
        assert response.json()["code"] == 40101

    def test_retry_single_extraction_returns_pending_job(
        self,
        client: TestClient,
        db_session: Session,
        setup_users: dict[str, User | Mailbox],
        monkeypatch: pytest.MonkeyPatch,
    ):
        message = _create_mail_message(
            db_session,
            mailbox=setup_users["mailbox"],
            subject="single async retry",
        )
        _create_failed_archive(db_session, mailbox=setup_users["mailbox"], message=message)
        db_session.commit()

        scheduled: list[str] = []
        monkeypatch.setattr("app.core.scheduler.init_scheduler", lambda: None)
        monkeypatch.setattr("app.core.scheduler.add_extraction_retry_job", lambda job_id: scheduled.append(job_id))

        response = client.post(
            f"/api/v1/mail-messages/{message.id}/retry-extraction",
            headers=_auth_headers(client, "admin_mail_retry"),
        )

        assert response.status_code == 202
        payload = response.json()["data"]
        assert payload["status"] == TaskStatus.PENDING.value
        assert payload["requested_count"] == 1
        assert payload["reused_existing_job"] is False
        assert payload["max_retries"] == MAX_EXTRACTION_RETRIES
        assert scheduled == [payload["job_id"]]

        task_log = db_session.get(TaskLog, payload["job_id"])
        assert task_log is not None
        assert task_log.task_type == TaskType.AI_EXTRACTION.value
        assert task_log.status == TaskStatus.PENDING.value
        assert task_log.related_message_id == message.id
        assert task_log.payload["message_ids"] == [message.id]
        assert task_log.payload["mailbox_ids"] == [message.mailbox_id]

    def test_retry_single_extraction_marks_task_failed_when_scheduling_fails(
        self,
        client: TestClient,
        db_session: Session,
        setup_users: dict[str, User | Mailbox],
        monkeypatch: pytest.MonkeyPatch,
    ):
        message = _create_mail_message(
            db_session,
            mailbox=setup_users["mailbox"],
            subject="single schedule failure",
        )
        _create_failed_archive(db_session, mailbox=setup_users["mailbox"], message=message)
        db_session.commit()

        monkeypatch.setattr("app.core.scheduler.init_scheduler", lambda: None)

        def raise_schedule(_job_id: str):
            raise RuntimeError("scheduler offline")

        monkeypatch.setattr("app.core.scheduler.add_extraction_retry_job", raise_schedule)

        with pytest.raises(RuntimeError, match="scheduler offline"):
            client.post(
                f"/api/v1/mail-messages/{message.id}/retry-extraction",
                headers=_auth_headers(client, "admin_mail_retry"),
            )

        failed_task = db_session.scalar(
            select(TaskLog)
            .where(TaskLog.related_message_id == message.id)
            .order_by(TaskLog.executed_at.desc())
            .limit(1)
        )
        assert failed_task is not None
        assert failed_task.status == TaskStatus.FAILED.value
        assert "任务调度失败" in failed_task.error_message
        assert db_session.get(ActiveTaskLock, failed_task.id) is None

        scheduled: list[str] = []
        monkeypatch.setattr("app.core.scheduler.add_extraction_retry_job", lambda job_id: scheduled.append(job_id))

        retry_response = client.post(
            f"/api/v1/mail-messages/{message.id}/retry-extraction",
            headers=_auth_headers(client, "admin_mail_retry"),
        )

        assert retry_response.status_code == 202
        payload = retry_response.json()["data"]
        assert payload["job_id"] != failed_task.id
        assert scheduled == [payload["job_id"]]

    def test_retry_single_extraction_checks_mailbox_scope(
        self,
        client: TestClient,
        db_session: Session,
        setup_users: dict[str, User | Mailbox],
    ):
        message = _create_mail_message(
            db_session,
            mailbox=setup_users["other_mailbox"],
            subject="out of scope single retry",
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/mail-messages/{message.id}/retry-extraction",
            headers=_auth_headers(client, "operator_mail_retry"),
        )

        assert response.status_code == 403
        assert response.json()["code"] == 40301

    def test_batch_retry_reuses_existing_active_task(
        self,
        client: TestClient,
        db_session: Session,
        setup_users: dict[str, User | Mailbox],
        monkeypatch: pytest.MonkeyPatch,
    ):
        first = _create_mail_message(
            db_session,
            mailbox=setup_users["mailbox"],
            subject="batch retry one",
        )
        second = _create_mail_message(
            db_session,
            mailbox=setup_users["mailbox"],
            subject="batch retry two",
        )
        db_session.commit()

        scheduled: list[str] = []
        monkeypatch.setattr("app.core.scheduler.init_scheduler", lambda: None)
        monkeypatch.setattr("app.core.scheduler.add_extraction_retry_job", lambda job_id: scheduled.append(job_id))
        headers = _auth_headers(client, "admin_mail_retry")

        first_response = client.post(
            "/api/v1/mail-messages/batch-retry-extraction",
            json={"message_ids": [first.id, second.id]},
            headers=headers,
        )
        second_response = client.post(
            "/api/v1/mail-messages/batch-retry-extraction",
            json={"message_ids": [second.id, first.id, second.id]},
            headers=headers,
        )

        assert first_response.status_code == 202
        assert second_response.status_code == 202
        first_payload = first_response.json()["data"]
        second_payload = second_response.json()["data"]
        assert first_payload["reused_existing_job"] is False
        assert second_payload["reused_existing_job"] is True
        assert second_payload["job_id"] == first_payload["job_id"]
        assert scheduled == [first_payload["job_id"]]

    def test_batch_retry_checks_mailbox_scope(
        self,
        client: TestClient,
        db_session: Session,
        setup_users: dict[str, User | Mailbox],
    ):
        in_scope = _create_mail_message(
            db_session,
            mailbox=setup_users["mailbox"],
            subject="batch in scope",
        )
        out_of_scope = _create_mail_message(
            db_session,
            mailbox=setup_users["other_mailbox"],
            subject="batch out of scope",
        )
        db_session.commit()

        response = client.post(
            "/api/v1/mail-messages/batch-retry-extraction",
            json={"message_ids": [in_scope.id, out_of_scope.id]},
            headers=_auth_headers(client, "operator_mail_retry"),
        )

        assert response.status_code == 403
        assert response.json()["code"] == 40301

    def test_get_task_log_detail_rejects_missing_authorization_header(
        self,
        client: TestClient,
        db_session: Session,
        setup_users: dict[str, User | Mailbox],
    ):
        task_log = TaskLog(
            task_type=TaskType.AI_EXTRACTION.value,
            task_key="missing-auth-task-key",
            status=TaskStatus.PENDING.value,
            related_mailbox_id=setup_users["mailbox"].id,
            payload={"mailbox_ids": [setup_users["mailbox"].id], "message_ids": ["msg-auth"]},
        )
        db_session.add(task_log)
        db_session.commit()

        response = client.get(f"/api/v1/task-logs/{task_log.id}")

        assert response.status_code == 401
        assert response.json()["code"] == 40101

    def test_get_task_log_detail_obeys_mailbox_scope(
        self,
        client: TestClient,
        db_session: Session,
        setup_users: dict[str, User | Mailbox],
    ):
        task_log = TaskLog(
            task_type=TaskType.AI_EXTRACTION.value,
            task_key="test-task-key",
            status=TaskStatus.PENDING.value,
            related_mailbox_id=setup_users["mailbox"].id,
            payload={"mailbox_ids": [setup_users["mailbox"].id], "message_ids": ["msg-1"]},
        )
        db_session.add(task_log)
        db_session.commit()

        response = client.get(
            f"/api/v1/task-logs/{task_log.id}",
            headers=_auth_headers(client, "operator_mail_retry"),
        )

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["job_id"] == task_log.id
        assert payload["status"] == TaskStatus.PENDING.value
        assert payload["payload"]["mailbox_ids"] == [setup_users["mailbox"].id]

    def test_get_task_log_detail_rejects_out_of_scope(
        self,
        client: TestClient,
        db_session: Session,
        setup_users: dict[str, User | Mailbox],
    ):
        task_log = TaskLog(
            task_type=TaskType.AI_EXTRACTION.value,
            task_key="test-task-key-out-of-scope",
            status=TaskStatus.PENDING.value,
            related_mailbox_id=setup_users["other_mailbox"].id,
            payload={"mailbox_ids": [setup_users["other_mailbox"].id], "message_ids": ["msg-2"]},
        )
        db_session.add(task_log)
        db_session.commit()

        response = client.get(
            f"/api/v1/task-logs/{task_log.id}",
            headers=_auth_headers(client, "operator_mail_retry"),
        )

        assert response.status_code == 403
        assert response.json()["code"] == 40301

    def test_get_task_log_detail_returns_404(
        self,
        client: TestClient,
        db_session: Session,
        setup_users: dict[str, User | Mailbox],
    ):
        response = client.get(
            "/api/v1/task-logs/nonexistent-job",
            headers=_auth_headers(client, "admin_mail_retry"),
        )

        assert response.status_code == 404
        assert response.json()["code"] == 40401


class TestExtractionRetryWorker:
    def test_execute_extraction_retry_async_reuses_failed_archive_and_marks_success(
        self,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ):
        mailbox = _create_mailbox(db_session, name="worker success mailbox", username="worker-success@example.com")
        user = _create_user(db_session, username="worker_success_admin", role=UserRole.ADMIN.value)
        message = _create_mail_message(
            db_session,
            mailbox=mailbox,
            subject="worker success message",
        )
        archive = _create_failed_archive(db_session, mailbox=mailbox, message=message)
        task_log = TaskLog(
            task_type=TaskType.AI_EXTRACTION.value,
            task_key="worker-success-task",
            status=TaskStatus.PENDING.value,
            related_mailbox_id=mailbox.id,
            related_message_id=message.id,
            payload={
                "message_ids": [message.id],
                "mailbox_ids": [mailbox.id],
                "requested_by": user.id,
                "max_retries": MAX_EXTRACTION_RETRIES,
            },
        )
        db_session.add(task_log)
        db_session.commit()

        engine = db_session.get_bind()
        monkeypatch.setattr("app.services.extraction_retry_service.create_engine", lambda _: engine)
        monkeypatch.setattr(engine, "dispose", lambda: None)

        def fake_extract(_self, subject: str, sender: str, body: str):
            return {
                "summary": f"{subject}:{sender}:{body}",
                "business_type": "support",
                "priority": "high",
                "risk_tags": ["retry"],
                "action_items": ["follow_up"],
                "entities": {"customer": "ACME"},
            }

        monkeypatch.setattr(
            "app.services.extraction_service.LLMClientSync.extract_from_email",
            fake_extract,
        )

        execute_extraction_retry_async("sqlite://", task_log.id)

        db_session.refresh(message)
        db_session.refresh(archive)
        db_session.refresh(task_log)
        assert message.extraction_status == ExtractionStatus.SUCCESS.value
        assert message.retry_count == 1
        assert message.last_retry_at is not None
        assert archive.status == ProcessingStatus.ARCHIVED.value
        assert archive.summary is not None
        assert task_log.status == TaskStatus.SUCCESS.value
        assert db_session.get(ActiveTaskLock, task_log.id) is None
        assert task_log.result["succeeded_count"] == 1
        assert task_log.result["failed_count"] == 0
        assert task_log.result["details"][0]["status"] == ExtractionStatus.SUCCESS.value

    def test_execute_extraction_retry_async_records_partial_failures(
        self,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ):
        mailbox = _create_mailbox(db_session, name="worker partial mailbox", username="worker-partial@example.com")
        user = _create_user(db_session, username="worker_partial_admin", role=UserRole.ADMIN.value)
        retryable = _create_mail_message(
            db_session,
            mailbox=mailbox,
            subject="worker partial retryable",
        )
        maxed = _create_mail_message(
            db_session,
            mailbox=mailbox,
            subject="worker partial maxed",
            retry_count=MAX_EXTRACTION_RETRIES,
        )
        non_failed = _create_mail_message(
            db_session,
            mailbox=mailbox,
            subject="worker partial non failed",
            extraction_status=ExtractionStatus.SUCCESS.value,
            extraction_error=None,
        )
        _create_failed_archive(db_session, mailbox=mailbox, message=retryable)
        task_log = TaskLog(
            task_type=TaskType.AI_EXTRACTION.value,
            task_key="worker-partial-task",
            status=TaskStatus.PENDING.value,
            related_mailbox_id=mailbox.id,
            payload={
                "message_ids": [retryable.id, maxed.id, non_failed.id, "missing-id"],
                "mailbox_ids": [mailbox.id],
                "requested_by": user.id,
                "max_retries": MAX_EXTRACTION_RETRIES,
            },
        )
        db_session.add(task_log)
        db_session.commit()

        engine = db_session.get_bind()
        monkeypatch.setattr("app.services.extraction_retry_service.create_engine", lambda _: engine)
        monkeypatch.setattr(engine, "dispose", lambda: None)

        def raise_extract(_db: Session, _message: MailMessage):
            raise RuntimeError("boom")

        monkeypatch.setattr("app.services.extraction_retry_service.extract_and_archive", raise_extract)

        execute_extraction_retry_async("sqlite://", task_log.id)

        db_session.refresh(retryable)
        db_session.refresh(task_log)
        assert retryable.extraction_status == ExtractionStatus.FAILED.value
        assert retryable.retry_count == 1
        assert retryable.extraction_error == "boom"
        assert task_log.status == TaskStatus.SUCCESS.value
        assert task_log.result["failed_count"] == 1
        assert task_log.result["already_max_retries"] == 1
        assert task_log.result["not_failed_status"] == 1
        assert task_log.result["not_found"] == 1

        details = {item["message_id"]: item for item in task_log.result["details"]}
        assert details[retryable.id]["status"] == "failed"
        assert details[retryable.id]["error_message"] == "boom"
        assert details[maxed.id]["status"] == "max_retries_reached"
        assert details[non_failed.id]["status"] == "not_failed_status"
        assert details["missing-id"]["status"] == "not_found"
