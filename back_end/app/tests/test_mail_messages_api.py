"""原始邮件查询接口测试。"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import ExtractionStatus, ProcessingStatus
from app.models.mail_message import MailMessage
from app.models.mailbox import Mailbox


def _is_utc_timestamp(value: str) -> bool:
    return value.endswith("Z") or value.endswith("+00:00")


def _seed_mailbox_with_messages(db_session: Session) -> tuple[Mailbox, MailMessage, MailMessage]:
    mailbox = Mailbox(
        name="原始邮件测试邮箱",
        protocol="imap",
        host="imap.example.com",
        port=993,
        username="raw@example.com",
        password_secret="encrypted",
        folder="INBOX",
        status="enabled",
    )
    db_session.add(mailbox)
    db_session.flush()

    first = MailMessage(
        mailbox_id=mailbox.id,
        internet_message_id="<raw-1@example.com>",
        provider_uid="1001",
        folder="INBOX",
        subject="scheduler success",
        sender_email="sender1@example.com",
        body_text="body 1",
        parse_status=ProcessingStatus.PARSED.value,
        extraction_status=ExtractionStatus.PENDING.value,
        received_at=datetime.now(timezone.utc),
    )
    second = MailMessage(
        mailbox_id=mailbox.id,
        internet_message_id="<raw-2@example.com>",
        provider_uid="1002",
        folder="INBOX",
        subject="batch task failed",
        sender_email="alert@example.com",
        body_text="body 2",
        parse_status=ProcessingStatus.PARSED.value,
        extraction_status=ExtractionStatus.FAILED.value,
        received_at=datetime.now(timezone.utc),
    )
    db_session.add_all([first, second])
    db_session.commit()
    return mailbox, first, second


class TestMailMessagesAPI:
    def test_list_mail_messages(self, client: TestClient, db_session: Session):
        mailbox, first, second = _seed_mailbox_with_messages(db_session)

        response = client.get(f"/api/v1/mail-messages?mailbox_id={mailbox.id}")

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["total"] == 2
        ids = {item["message_id"] for item in payload["items"]}
        assert first.id in ids
        assert second.id in ids

    def test_list_mail_messages_keyword(self, client: TestClient, db_session: Session):
        mailbox, _, second = _seed_mailbox_with_messages(db_session)

        response = client.get(
            f"/api/v1/mail-messages?mailbox_id={mailbox.id}&keyword=failed"
        )

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["total"] == 1
        assert payload["items"][0]["message_id"] == second.id

    def test_get_mail_message_detail(self, client: TestClient, db_session: Session):
        _, first, _ = _seed_mailbox_with_messages(db_session)

        response = client.get(f"/api/v1/mail-messages/{first.id}")

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["message_id"] == first.id
        assert payload["internet_message_id"] == "<raw-1@example.com>"
        assert payload["sender_email"] == "sender1@example.com"
        assert payload["body_text"] == "body 1"
        assert _is_utc_timestamp(payload["received_at"])

    def test_list_mail_messages_returns_utc_offset_for_naive_datetime(
        self,
        client: TestClient,
        db_session: Session,
    ):
        mailbox, _, _ = _seed_mailbox_with_messages(db_session)

        response = client.get(f"/api/v1/mail-messages?mailbox_id={mailbox.id}")

        assert response.status_code == 200
        payload = response.json()["data"]
        assert _is_utc_timestamp(payload["items"][0]["received_at"])

    def test_get_mail_message_detail_not_found(self, client: TestClient):
        response = client.get("/api/v1/mail-messages/nonexistent-id")

        assert response.status_code == 404
        payload = response.json()
        assert payload["code"] == 40401
