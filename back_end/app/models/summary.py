from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    CustomerAnalysisMode,
    EmptyResultPolicy,
    SummaryMode,
    SummaryScheduleType,
    SummaryScopeMode,
    SummarySendStatus,
)
from app.models.mixins import PrimaryKeyMixin, TimestampMixin


class SummaryConfig(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "summary_configs"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    schedule_type: Mapped[str] = mapped_column(
        String(32),
        default=SummaryScheduleType.DAILY.value,
        nullable=False,
    )
    mailbox_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("mailboxes.id", ondelete="SET NULL"),
        nullable=True,
    )
    mailbox_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    recipient_emails: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    include_statuses: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    send_time: Mapped[str] = mapped_column(String(5), default="09:00", nullable=False)
    summary_mode: Mapped[str] = mapped_column(
        String(32),
        default=SummaryMode.AI.value,
        nullable=False,
    )
    empty_result_policy: Mapped[str] = mapped_column(
        String(32),
        default=EmptyResultPolicy.SKIP.value,
        nullable=False,
    )
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # 客户归类摘要扩展字段
    summary_scope_mode: Mapped[str] = mapped_column(
        String(32),
        default=SummaryScopeMode.FLAT.value,
        nullable=False,
    )
    include_unidentified_senders: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    top_n_per_customer: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
    )
    customer_analysis_mode: Mapped[str] = mapped_column(
        String(32),
        default=CustomerAnalysisMode.BASIC.value,
        nullable=False,
    )

    mailbox: Mapped["Mailbox | None"] = relationship(back_populates="summary_configs")
    send_records: Mapped[list["SummarySendRecord"]] = relationship(
        back_populates="config",
        cascade="all, delete-orphan",
    )
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(
        back_populates="config",
        cascade="all, delete-orphan",
    )


class SummarySendRecord(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "summary_send_records"
    __table_args__ = (
        Index("ix_summary_send_records_config_id_status", "config_id", "status"),
        Index("ix_summary_send_records_window", "window_start_date", "window_end_date"),
    )

    config_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("summary_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    analysis_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=SummarySendStatus.PENDING.value,
        nullable=False,
    )
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipient_emails: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    recipient_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    window_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    window_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    config: Mapped["SummaryConfig"] = relationship(back_populates="send_records")
    analysis_run: Mapped["AnalysisRun | None"] = relationship(
        back_populates="send_records"
    )
