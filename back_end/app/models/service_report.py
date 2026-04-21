from __future__ import annotations

from datetime import datetime

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


MYSQL_COLLATION = "utf8mb4_unicode_ci"
MYSQL_ID_TYPE = String(36).with_variant(String(36, collation=MYSQL_COLLATION), "mysql")
MYSQL_NAME_TYPE = String(120).with_variant(String(120, collation=MYSQL_COLLATION), "mysql")
MYSQL_SHORT_TYPE = String(32).with_variant(String(32, collation=MYSQL_COLLATION), "mysql")
MYSQL_TEMPLATE_TYPE = String(64).with_variant(String(64, collation=MYSQL_COLLATION), "mysql")


class ServiceReportConfig(TimestampMixin, Base):
    """服务报告配置。"""

    __tablename__ = "service_report_configs"
    __table_args__ = (
        Index("ix_service_report_configs_project_name", "project_name"),
        Index("ix_service_report_configs_report_type", "report_type"),
        Index("ix_service_report_configs_enabled", "enabled"),
        {"mysql_charset": "utf8mb4", "mysql_collate": MYSQL_COLLATION},
    )

    id: Mapped[str] = mapped_column(
        MYSQL_ID_TYPE,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(MYSQL_NAME_TYPE, nullable=False, unique=True)
    project_name: Mapped[str] = mapped_column(MYSQL_NAME_TYPE, nullable=False)
    report_type: Mapped[str] = mapped_column(MYSQL_SHORT_TYPE, nullable=False)
    period_rule: Mapped[str] = mapped_column(MYSQL_SHORT_TYPE, nullable=False)
    template_key: Mapped[str] = mapped_column(MYSQL_TEMPLATE_TYPE, nullable=False)
    project_owner_user_id: Mapped[str] = mapped_column(
        MYSQL_ID_TYPE, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    template_owner_user_id: Mapped[str] = mapped_column(
        MYSQL_ID_TYPE, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    metric_owner_user_id: Mapped[str] = mapped_column(
        MYSQL_ID_TYPE, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    recipient_emails: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    source_bindings: Mapped[list[dict]] = mapped_column(JSON, nullable=False)


class ServiceReportSourceRun(TimestampMixin, Base):
    """服务报告源数据汇总记录。"""

    __tablename__ = "service_report_source_runs"
    __table_args__ = (
        Index("ix_service_report_source_runs_config_id", "config_id"),
        Index("ix_service_report_source_runs_status", "status"),
        {"mysql_charset": "utf8mb4", "mysql_collate": MYSQL_COLLATION},
    )

    id: Mapped[str] = mapped_column(
        MYSQL_ID_TYPE,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    config_id: Mapped[str] = mapped_column(
        MYSQL_ID_TYPE, ForeignKey("service_report_configs.id", ondelete="CASCADE"), nullable=False
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(MYSQL_SHORT_TYPE, nullable=False, default="pending")
    included_sources: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    source_results: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    snapshot_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ServiceReportRun(TimestampMixin, Base):
    """服务报告生成记录。"""

    __tablename__ = "service_report_runs"
    __table_args__ = (
        Index("ix_service_report_runs_config_id", "config_id"),
        Index("ix_service_report_runs_status", "status"),
        Index("ix_service_report_runs_completeness_status", "completeness_status"),
        {"mysql_charset": "utf8mb4", "mysql_collate": MYSQL_COLLATION},
    )

    id: Mapped[str] = mapped_column(
        MYSQL_ID_TYPE,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    config_id: Mapped[str] = mapped_column(
        MYSQL_ID_TYPE, ForeignKey("service_report_configs.id", ondelete="CASCADE"), nullable=False
    )
    source_run_id: Mapped[str] = mapped_column(
        MYSQL_ID_TYPE, ForeignKey("service_report_source_runs.id", ondelete="CASCADE"), nullable=False
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(MYSQL_SHORT_TYPE, nullable=False, default="pending")
    completeness_status: Mapped[str] = mapped_column(MYSQL_SHORT_TYPE, nullable=False, default="blocked")
    config_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_snapshot_summary: Mapped[dict] = mapped_column(JSON, nullable=False)
    report_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    manual_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    export_artifacts: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    evidence_refs: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
