"""归档字段映射正确性测试。"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.archive import ArchiveRecord
from app.models.enums import ExtractionStatus, ProcessingStatus
from app.models.mail_message import MailMessage
from app.models.mailbox import Mailbox


class TestArchiveFieldMapping:
    """归档字段映射正确性测试类。"""

    @pytest.fixture
    def setup_data(self, db_session: Session):
        """设置测试数据。"""
        # 创建邮箱
        mailbox = Mailbox(
            name="归档测试邮箱",
            protocol="imap",
            host="imap.example.com",
            port=993,
            username="archive@example.com",
            password_secret="encrypted_password",
            folder="INBOX",
            status="enabled",
        )
        db_session.add(mailbox)
        db_session.flush()

        # 创建邮件消息
        mail_message = MailMessage(
            mailbox_id=mailbox.id,
            internet_message_id="<test123@example.com>",
            provider_uid="123",
            folder="INBOX",
            subject="测试邮件主题",
            sender_email="sender@example.com",
            recipients_to=["receiver@example.com"],
            body_text="这是测试邮件正文",
            has_attachments=False,
            parse_status=ProcessingStatus.PARSED.value,
            extraction_status=ExtractionStatus.SUCCESS.value,
            parse_error=None,
            received_at=datetime.now(timezone.utc),
        )
        db_session.add(mail_message)
        db_session.flush()

        # 创建归档记录
        archive = ArchiveRecord(
            mailbox_id=mailbox.id,
            message_id=mail_message.id,
            status=ProcessingStatus.ARCHIVED.value,
            summary="这是 AI 生成的摘要",
            business_type="通知",
            priority="medium",
            risk_tags=["常规"],
            confidence=Decimal("0.92"),
            received_at=datetime.now(timezone.utc),
        )
        db_session.add(archive)
        db_session.commit()

        return {
            "mailbox": mailbox,
            "mail_message": mail_message,
            "archive": archive,
        }

    def test_archive_list_field_mapping(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试归档列表字段映射正确性。"""
        response = client.get("/api/v1/archives")

        assert response.status_code == 200
        json_data = response.json()

        # 验证统一响应结构
        assert json_data["code"] == 0
        assert "data" in json_data

        items = json_data["data"]["items"]
        assert len(items) > 0

        # 找到测试记录
        archive = setup_data["archive"]
        test_item = next(
            (item for item in items if item["archive_id"] == archive.id),
            None
        )
        assert test_item is not None

        # 验证字段映射
        assert test_item["subject"] == "测试邮件主题"
        assert test_item["sender"] == "sender@example.com"
        assert test_item["status"] == "archived"

        # 验证 extraction_status 来自真实数据（不是硬编码的 "success"）
        assert test_item["extraction_status"] == "success"

        # 验证 confidence 是正确的数值
        assert test_item["confidence"] == 0.92

    def test_archive_detail_field_mapping(
        self, client: TestClient, db_session: Session, setup_data
    ):
        """测试归档详情字段映射正确性。"""
        archive = setup_data["archive"]

        response = client.get(f"/api/v1/archives/{archive.id}")

        assert response.status_code == 200
        json_data = response.json()

        # 验证统一响应结构
        assert json_data["code"] == 0
        assert "data" in json_data

        detail = json_data["data"]

        # 验证基本字段
        assert detail["archive_id"] == archive.id
        assert detail["subject"] == "测试邮件主题"
        assert detail["sender"] == "sender@example.com"
        assert detail["recipients"] == ["receiver@example.com"]
        assert detail["body_text"] == "这是测试邮件正文"

        # 验证 extraction_status 来自真实数据
        assert detail["extraction_status"] == "success"

        # 验证 parse_error 对应解析错误（这里应该是 null，因为解析成功）
        assert detail["parse_error"] is None

    def test_archive_not_found_error_response(
        self, client: TestClient, db_session: Session
    ):
        """测试归档不存在的错误响应结构。"""
        response = client.get("/api/v1/archives/nonexistent-id")

        assert response.status_code == 404

        # 验证统一错误响应结构
        json_data = response.json()
        assert "code" in json_data
        assert "message" in json_data
        assert "data" in json_data
        assert json_data["code"] == 40401
        assert "detail" not in json_data

    def test_archive_extraction_status_failed(
        self, client: TestClient, db_session: Session
    ):
        """测试提取失败时的 extraction_status。"""
        # 创建邮箱
        mailbox = Mailbox(
            name="失败测试邮箱",
            protocol="imap",
            host="imap.example.com",
            port=993,
            username="failed@example.com",
            password_secret="encrypted_password",
            folder="INBOX",
            status="enabled",
        )
        db_session.add(mailbox)
        db_session.flush()

        # 创建邮件消息，设置提取失败
        mail_message = MailMessage(
            mailbox_id=mailbox.id,
            internet_message_id="<failed@example.com>",
            provider_uid="456",
            subject="提取失败邮件",
            sender_email="sender@example.com",
            parse_status=ProcessingStatus.PARSED.value,
            extraction_status=ExtractionStatus.FAILED.value,
            extraction_error="LLM 调用超时",
            received_at=datetime.now(timezone.utc),
        )
        db_session.add(mail_message)
        db_session.flush()

        # 创建归档记录
        archive = ArchiveRecord(
            mailbox_id=mailbox.id,
            message_id=mail_message.id,
            status=ProcessingStatus.FAILED.value,
            extraction_error="LLM 调用超时",
            received_at=datetime.now(timezone.utc),
        )
        db_session.add(archive)
        db_session.commit()

        # 请求详情
        response = client.get(f"/api/v1/archives/{archive.id}")

        assert response.status_code == 200
        json_data = response.json()
        detail = json_data["data"]

        # 验证 extraction_status 是 failed（来自真实数据）
        assert detail["extraction_status"] == "failed"

    def test_archive_parse_error_mapping(
        self, client: TestClient, db_session: Session
    ):
        """测试 parse_error 字段映射正确性。"""
        # 创建邮箱
        mailbox = Mailbox(
            name="解析错误测试邮箱",
            protocol="imap",
            host="imap.example.com",
            port=993,
            username="parse_error@example.com",
            password_secret="encrypted_password",
            folder="INBOX",
            status="enabled",
        )
        db_session.add(mailbox)
        db_session.flush()

        # 创建邮件消息，设置解析错误
        mail_message = MailMessage(
            mailbox_id=mailbox.id,
            internet_message_id="<parse_error@example.com>",
            provider_uid="789",
            subject="解析错误邮件",
            sender_email="sender@example.com",
            parse_status=ProcessingStatus.FAILED.value,
            parse_error="编码转换失败: unknown encoding",
            extraction_status=ExtractionStatus.PENDING.value,
            received_at=datetime.now(timezone.utc),
        )
        db_session.add(mail_message)
        db_session.flush()

        # 创建归档记录
        archive = ArchiveRecord(
            mailbox_id=mailbox.id,
            message_id=mail_message.id,
            status=ProcessingStatus.PENDING.value,
            received_at=datetime.now(timezone.utc),
        )
        db_session.add(archive)
        db_session.commit()

        # 请求详情
        response = client.get(f"/api/v1/archives/{archive.id}")

        assert response.status_code == 200
        json_data = response.json()
        detail = json_data["data"]

        # 验证 parse_error 是解析错误（不是 extraction_error）
        assert detail["parse_error"] == "编码转换失败: unknown encoding"

        # 验证 extraction_status 是 pending
        assert detail["extraction_status"] == "pending"
