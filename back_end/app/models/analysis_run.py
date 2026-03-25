"""分析运行模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AnalysisRunStatus
from app.models.mixins import PrimaryKeyMixin, TimestampMixin


class AnalysisRun(PrimaryKeyMixin, TimestampMixin, Base):
    """分析运行表 - 记录每次客户问题归类分析的执行状态和结果。"""

    __tablename__ = "analysis_runs"
    __table_args__ = (
        # 幂等约束: config_id + window_start + window_end + config_snapshot_hash
        UniqueConstraint(
            "config_id",
            "window_start",
            "window_end",
            "config_snapshot_hash",
            name="uq_analysis_runs_window_hash",
        ),
        Index("ix_analysis_runs_config_id", "config_id"),
        Index("ix_analysis_runs_status", "status"),
        Index("ix_analysis_runs_config_status", "config_id", "status"),
    )

    # 关联配置
    config_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("summary_configs.id", ondelete="CASCADE"),
        nullable=False,
    )

    # 时间窗口（完整 datetime，保留时分秒精度）
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # 配置快照（用于复盘）
    config_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    config_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # 状态机: pending -> running -> success | failed | canceled
    status: Mapped[str] = mapped_column(
        String(32),
        default=AnalysisRunStatus.PENDING.value,
        nullable=False,
    )

    # 结果存储 (JSON 格式的完整分析结果)
    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # 执行信息
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 模型信息
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    analysis_mode_used: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # AI 降级标记
    degraded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 关联
    config: Mapped["SummaryConfig"] = relationship(back_populates="analysis_runs")
    send_records: Mapped[list["SummarySendRecord"]] = relationship(
        back_populates="analysis_run"
    )
