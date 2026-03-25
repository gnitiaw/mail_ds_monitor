"""AI 提取服务，将邮件内容提取为结构化归档记录。"""

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.archive import ArchiveRecord
from app.models.enums import ExtractionStatus, ProcessingStatus
from app.models.mail_message import MailMessage

from .llm_service import LLMClientSync, LLMError

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """提取错误。"""


def extract_and_archive(
    db: Session,
    mail_message: MailMessage,
) -> ArchiveRecord:
    """从邮件消息中提取结构化信息并创建归档记录。

    Args:
        db: 数据库会话
        mail_message: 邮件消息记录

    Returns:
        创建的归档记录
    """
    # 检查是否已有归档记录
    existing_archive = db.scalar(
        select(ArchiveRecord).where(ArchiveRecord.message_id == mail_message.id)
    )
    if existing_archive:
        logger.info(f"Archive record already exists for message {mail_message.id}")
        return existing_archive

    # 准备提取内容
    subject = mail_message.subject or ""
    sender = mail_message.sender_email or ""
    body = mail_message.body_text or mail_message.body_html or ""

    # 创建归档记录（初始状态）
    archive = ArchiveRecord(
        mailbox_id=mail_message.mailbox_id,
        message_id=mail_message.id,
        status=ProcessingStatus.PENDING.value,
        received_at=mail_message.received_at,
    )
    db.add(archive)
    db.flush()  # 获取 ID

    try:
        # 调用 LLM 提取
        if not settings.llm_enabled:
            logger.warning(f"LLM disabled, skipping extraction for message {mail_message.id}")
            archive.status = ProcessingStatus.ARCHIVED.value
            archive.extraction_error = "LLM extraction disabled"
            db.commit()
            return archive

        client = LLMClientSync()
        result: dict[str, Any] = client.extract_from_email(subject, sender, body)

        # 更新归档记录
        archive.summary = result.get("summary")
        archive.business_type = result.get("business_type")
        archive.priority = result.get("priority")
        archive.risk_tags = result.get("risk_tags")
        archive.action_items = result.get("action_items")
        archive.entities = result.get("entities")
        archive.extracted_fields = result
        archive.model_name = settings.llm_model
        archive.prompt_version = settings.llm_extraction_prompt_version

        # 计算置信度（简单实现：基于提取字段完整性）
        confidence = _calculate_confidence(result)
        archive.confidence = Decimal(str(confidence))

        archive.status = ProcessingStatus.ARCHIVED.value

        # 更新邮件消息状态
        mail_message.extraction_status = ExtractionStatus.SUCCESS.value
        mail_message.extraction_error = None

        db.commit()
        logger.info(f"Successfully extracted archive for message {mail_message.id}")

    except LLMError as e:
        logger.error(f"LLM extraction failed for message {mail_message.id}: {e}")
        archive.status = ProcessingStatus.FAILED.value
        archive.extraction_error = str(e)
        mail_message.extraction_status = ExtractionStatus.FAILED.value
        mail_message.extraction_error = str(e)
        db.commit()

    except Exception as e:
        logger.exception(f"Unexpected error extracting message {mail_message.id}")
        archive.status = ProcessingStatus.FAILED.value
        archive.extraction_error = f"Unexpected error: {e}"
        mail_message.extraction_status = ExtractionStatus.FAILED.value
        mail_message.extraction_error = str(e)
        db.commit()

    return archive


def _calculate_confidence(result: dict[str, Any]) -> float:
    """计算提取结果的置信度。"""
    score = 0.0
    total = 0.0

    # 检查必要字段
    important_fields = ["summary", "business_type", "priority"]
    for field in important_fields:
        total += 1.0
        if result.get(field):
            score += 1.0

    # 检查可选字段
    optional_fields = ["risk_tags", "action_items", "entities"]
    for field in optional_fields:
        total += 0.5
        value = result.get(field)
        if value:
            if isinstance(value, list) and len(value) > 0:
                score += 0.5
            elif isinstance(value, dict) and len(value) > 0:
                score += 0.5

    return min(score / total, 1.0) if total > 0 else 0.0


def extract_pending_messages(
    db: Session,
    limit: int = 50,
    mailbox_id: str | None = None,
) -> tuple[int, int, int]:
    """提取所有待处理的邮件消息。

    Args:
        db: 数据库会话
        limit: 最大处理数量

    Returns:
        (成功数, 失败数, 跳过数)
    """
    success_count = 0
    failed_count = 0
    skipped_count = 0

    # 查询待提取的邮件
    stmt = (
        select(MailMessage)
        .where(MailMessage.extraction_status == ExtractionStatus.PENDING.value)
        .where(MailMessage.parse_status == ProcessingStatus.PARSED.value)
    )
    if mailbox_id:
        stmt = stmt.where(MailMessage.mailbox_id == mailbox_id)
    stmt = stmt.limit(limit)

    messages = list(db.scalars(stmt).all())

    for message in messages:
        try:
            archive = extract_and_archive(db, message)
            if archive.status == ProcessingStatus.ARCHIVED.value:
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            logger.exception(f"Failed to extract message {message.id}")
            failed_count += 1

    return success_count, failed_count, skipped_count
