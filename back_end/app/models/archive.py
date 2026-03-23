from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import PrimaryKeyMixin, TimestampMixin


class ArchiveRecord(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "archive_records"
    __table_args__ = (
        Index("ix_archive_records_mailbox_id_status", "mailbox_id", "status"),
        Index("ix_archive_records_received_at", "received_at"),
    )

    mailbox_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("mailboxes.id", ondelete="CASCADE"),
        nullable=False,
    )
    message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("mail_messages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="archived", nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    action_items: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    entities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extracted_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    mailbox: Mapped["Mailbox"] = relationship(back_populates="archives")
    message: Mapped["MailMessage"] = relationship(back_populates="archive")
