"""发件人配置模型。"""

from __future__ import annotations

from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import SenderMatchType, SenderProfileStatus, SenderType
from app.models.mixins import PrimaryKeyMixin, TimestampMixin


class SenderProfile(PrimaryKeyMixin, TimestampMixin, Base):
    """发件人配置表 - 用于识别和归类邮件发件人。"""

    __tablename__ = "sender_profiles"
    __table_args__ = (
        # 幂等约束: match_type + match_value 唯一（启用状态）
        UniqueConstraint("match_type", "match_value", name="uq_sender_profiles_match"),
        Index("ix_sender_profiles_status", "status"),
        Index("ix_sender_profiles_customer_name", "customer_name"),
        Index("ix_sender_profiles_match_type_value", "match_type", "match_value"),
    )

    # 匹配规则
    match_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    match_value: Mapped[str] = mapped_column(String(255), nullable=False)

    # 客户信息
    customer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    customer_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # 发件人标签
    sender_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sender_type: Mapped[str] = mapped_column(
        String(32),
        default=SenderType.UNKNOWN.value,
        nullable=False,
    )

    # 状态
    status: Mapped[str] = mapped_column(
        String(32),
        default=SenderProfileStatus.ENABLED.value,
        nullable=False,
    )

    # 备注
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
