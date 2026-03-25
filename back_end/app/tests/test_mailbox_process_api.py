"""邮箱后处理接口测试。"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import ExtractionStatus, ProcessingStatus, RuleStatus
from app.models.failure_capture import FailureCaptureRule
from app.models.failure_queue import FailureMailQueue
from app.models.mail_message import MailMessage
from app.models.mailbox import Mailbox


def test_process_mailbox_messages(client: TestClient, db_session: Session, monkeypatch):
    mailbox = Mailbox(
        name="处理测试邮箱",
        protocol="imap",
        host="imap.example.com",
        port=993,
        username="process@example.com",
        password_secret="encrypted",
        folder="INBOX",
        status="enabled",
    )
    db_session.add(mailbox)
    db_session.flush()

    message = MailMessage(
        mailbox_id=mailbox.id,
        internet_message_id="<process-1@example.com>",
        provider_uid="2001",
        folder="INBOX",
        subject="batch task failed",
        sender_email="alert@example.com",
        body_text="failed because upstream error",
        parse_status=ProcessingStatus.PARSED.value,
        extraction_status=ExtractionStatus.PENDING.value,
        received_at=datetime.now(timezone.utc),
    )
    db_session.add(message)

    rule = FailureCaptureRule(
        rule_name="失败规则",
        failure_rule_key="process_test_rule",
        status=RuleStatus.ENABLED.value,
        sender_patterns=["alert@example.com"],
        subject_patterns=["failed"],
        priority=100,
        mailbox_ids=[mailbox.id],
    )
    db_session.add(rule)
    db_session.commit()

    monkeypatch.setattr(settings, "llm_enabled", False)

    response = client.post(
        f"/api/v1/mailboxes/{mailbox.id}/process",
        json={"lookback_minutes": 1440, "limit": 50},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["mailbox_id"] == mailbox.id
    assert payload["archive_success_count"] == 1
    assert payload["failure_scanned_count"] >= 1
    assert payload["failure_matched_count"] == 1

    queue_items = db_session.query(FailureMailQueue).filter(FailureMailQueue.mailbox_id == mailbox.id).all()
    assert len(queue_items) == 1


def test_process_mailbox_not_found(client: TestClient):
    response = client.post(
        "/api/v1/mailboxes/nonexistent-id/process",
        json={"lookback_minutes": 60, "limit": 10},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["code"] == 40401
