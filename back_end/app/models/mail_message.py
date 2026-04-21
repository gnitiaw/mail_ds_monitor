from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.mysql import JSON, MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ExtractionStatus, ProcessingStatus
from app.models.mixins import PrimaryKeyMixin, TimestampMixin


class MailMessage(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mail_messages"
    __table_args__ = (
        UniqueConstraint("mailbox_id", "internet_message_id", name="uq_mail_messages_mailbox_message_id"),
        UniqueConstraint("mailbox_id", "provider_uid", name="uq_mail_messages_mailbox_provider_uid"),
        Index("ix_mail_messages_mailbox_received_at", "mailbox_id", "received_at"),
        Index("ix_mail_messages_extraction_status", "extraction_status"),
    )

    mailbox_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("mailboxes.id", ondelete="CASCADE"),
        nullable=False,
    )
    internet_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_uid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    folder: Mapped[str] = mapped_column(String(255), default="INBOX", nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sender_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipients_to: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    recipients_cc: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    recipients_bcc: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    reply_to: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    headers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    flags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    body_text: Mapped[str | None] = mapped_column(
        Text().with_variant(MEDIUMTEXT, "mysql"),
        nullable=True,
    )
    body_html: Mapped[str | None] = mapped_column(
        Text().with_variant(MEDIUMTEXT, "mysql"),
        nullable=True,
    )
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parse_status: Mapped[str] = mapped_column(
        String(32),
        default=ProcessingStatus.PENDING.value,
        nullable=False,
    )
    extraction_status: Mapped[str] = mapped_column(
        String(32),
        default=ExtractionStatus.PENDING.value,
        nullable=False,
    )
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pulled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    mailbox: Mapped["Mailbox"] = relationship(back_populates="messages")
    archive: Mapped["ArchiveRecord | None"] = relationship(back_populates="message", uselist=False)
