"""失败邮件队列表。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, event, ForeignKey, Index, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import FailureQueueStatus
from app.models.mixins import PrimaryKeyMixin, TimestampMixin


class FailureMailQueue(PrimaryKeyMixin, TimestampMixin, Base):
    """失败邮件队列表 - 独立于 archive_records。"""

    __tablename__ = "failure_mail_queue"
    __table_args__ = (
        # 幂等防重（数据库级）：
        # 契约要求 mailbox_id + internet_message_id/provider_uid + failure_rule_key
        # 方案：dedup_message_key 列统一幂等维度，由 before_insert 事件设置
        # - 优先使用 source_message_id（格式：MSG:<value>）
        # - 为空时回退到 provider_uid（格式：UID:<value>）
        UniqueConstraint(
            "mailbox_id", "dedup_message_key", "failure_rule_key",
            name="uq_failure_queue_dedup"
        ),
        Index("ix_failure_queue_status_received", "status", "received_at"),
        Index("ix_failure_queue_mailbox_received", "mailbox_id", "received_at"),
        Index("ix_failure_queue_rule_key", "failure_rule_key"),
    )

    # 来源信息
    mailbox_id: Mapped[str] = mapped_column(String(36), ForeignKey("mailboxes.id"), nullable=False)
    source_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_uid: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 幂等防重键：由 before_insert 事件自动设置
    # 格式：MSG:<source_message_id> 或 UID:<provider_uid>
    dedup_message_key: Mapped[str | None] = mapped_column(String(261), nullable=True)

    # 命中规则
    failure_rule_key: Mapped[str] = mapped_column(String(64), nullable=False)

    # 提取字段
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sender: Mapped[str | None] = mapped_column(String(255), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 邮件正文
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 状态机
    status: Mapped[str] = mapped_column(
        String(32), default=FailureQueueStatus.NEW.value, nullable=False
    )

    # 命中快照 - 保留命中时的规则和提取结果
    matched_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # 时间戳
    first_captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 状态流转时间与操作人
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # 关联
    mailbox: Mapped["Mailbox"] = relationship(back_populates="failure_queue_items")


@event.listens_for(FailureMailQueue, "before_insert")
def set_dedup_message_key(mapper, connection, target):
    """在插入前自动设置 dedup_message_key。

    幂等防重逻辑：
    - 优先使用 source_message_id（格式：MSG:<value>）
    - 为空时回退到 provider_uid（格式：UID:<value>）
    """
    if target.source_message_id:
        target.dedup_message_key = f"MSG:{target.source_message_id}"
    elif target.provider_uid:
        target.dedup_message_key = f"UID:{target.provider_uid}"
    else:
        target.dedup_message_key = None


# 在 Mailbox 模型中添加反向关系 (需要在 mailbox.py 中添加)
# failure_queue_items: Mapped[list["FailureMailQueue"]] = relationship(back_populates="mailbox")
