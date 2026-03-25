"""IMAP 拉取服务测试。"""

from app.services.imap_service import _decode_header_value
from app.models.mailbox import Mailbox
from app.services.imap_service import IMAPClient


class _FakeIMAPClient:
    def __init__(self, raw_email: bytes):
        self.raw_email = raw_email
        self.search_called = False
        self.uid_search_calls: list[str] = []

    def select(self, folder: str):
        return "OK", [b"1"]

    def search(self, charset, criteria):
        self.search_called = True
        return "OK", [b"1"]

    def uid(self, command, *args):
        if command == "search":
            criteria = args[1]
            self.uid_search_calls.append(criteria)
            return "OK", [b"9462"]

        if command == "fetch":
            uid = args[0]
            return "OK", [(f"1 (UID {uid.decode()} RFC822 {{{len(self.raw_email)}}}".encode(), self.raw_email)]

        raise AssertionError(f"Unexpected uid command: {command}")


def test_fetch_messages_full_sync_uses_uid_search():
    """全量同步应使用 uid search，避免序号和 uid fetch 混用。"""
    raw_email = (
        b"From: sender@example.com\r\n"
        b"To: receiver@example.com\r\n"
        b"Subject: Pull Test\r\n"
        b"Message-ID: <pull-test@example.com>\r\n"
        b"Date: Tue, 24 Mar 2026 11:30:00 +0800\r\n"
        b"Content-Type: text/plain; charset=UTF-8\r\n"
        b"\r\n"
        b"hello world"
    )
    mailbox = Mailbox(
        name="imap-test",
        protocol="imap",
        host="imap.example.com",
        port=993,
        username="imap@example.com",
        password_secret="encrypted",
        folder="INBOX",
        status="enabled",
    )
    client = IMAPClient(mailbox)
    fake_client = _FakeIMAPClient(raw_email)
    client._client = fake_client

    messages = client.fetch_messages(folder="INBOX", limit=10, since_uid=None)

    assert fake_client.search_called is False
    assert fake_client.uid_search_calls == ["ALL"]
    assert len(messages) == 1
    assert messages[0]["provider_uid"] == "9462"
    assert messages[0]["internet_message_id"] == "<pull-test@example.com>"
    assert messages[0]["subject"] == "Pull Test"


def test_decode_header_value_handles_encoded_subject():
    """中文邮件主题应被正确解码，而不是原样显示 MIME 编码串。"""
    encoded = "=?UTF-8?B?5p+l6K+i5a6i5oi355S75YOP55u45YWz5pWw5o2uXzExMjA=?="

    decoded = _decode_header_value(encoded)

    assert decoded == "查询客户画像相关数据_1120"
