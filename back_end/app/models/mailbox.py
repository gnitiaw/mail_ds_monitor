from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MailboxProtocol, MailboxStatus
from app.models.mixins import PrimaryKeyMixin, TimestampMixin


class Mailbox(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mailboxes"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    protocol: Mapped[str] = mapped_column(
        String(32),
        default=MailboxProtocol.IMAP.value,
        nullable=False,
    )
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password_secret: Mapped[str] = mapped_column(String(512), nullable=False)
    folder: Mapped[str] = mapped_column(String(255), default="INBOX", nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default=MailboxStatus.ENABLED.value,
        nullable=False,
    )
    last_pull_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_pull_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_pull_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    messages: Mapped[list["MailMessage"]] = relationship(
        back_populates="mailbox",
        cascade="all, delete-orphan",
    )
    archives: Mapped[list["ArchiveRecord"]] = relationship(
        back_populates="mailbox",
        cascade="all, delete-orphan",
    )
    summary_configs: Mapped[list["SummaryConfig"]] = relationship(back_populates="mailbox")
    task_logs: Mapped[list["TaskLog"]] = relationship(back_populates="mailbox")
    failure_queue_items: Mapped[list["FailureMailQueue"]] = relationship(
        back_populates="mailbox",
        cascade="all, delete-orphan",
    )
