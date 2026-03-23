from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TaskStatus, TaskType
from app.models.mixins import PrimaryKeyMixin, TimestampMixin


class TaskLog(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "task_logs"
    __table_args__ = (
        Index("ix_task_logs_task_type_status", "task_type", "status"),
        Index("ix_task_logs_related_mailbox_id", "related_mailbox_id"),
    )

    task_type: Mapped[str] = mapped_column(String(64), default=TaskType.MAIL_PULL.value, nullable=False)
    task_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=TaskStatus.PENDING.value, nullable=False)
    related_mailbox_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("mailboxes.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_message_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("mail_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    mailbox: Mapped["Mailbox | None"] = relationship(back_populates="task_logs")
