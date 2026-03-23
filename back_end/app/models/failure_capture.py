"""失败邮件捕获相关模型。"""

from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import CustomerScopeType, RuleStatus
from app.models.mixins import PrimaryKeyMixin, TimestampMixin


class FailureCaptureRule(PrimaryKeyMixin, TimestampMixin, Base):
    """失败邮件识别规则配置表。"""

    __tablename__ = "failure_capture_rules"

    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    failure_rule_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default=RuleStatus.ENABLED.value, nullable=False)
    # 客户范围定义方式
    customer_scope_type: Mapped[str] = mapped_column(
        String(32), default=CustomerScopeType.EXPLICIT_LIST.value, nullable=False
    )
    # 客户匹配配置，结构由 customer_scope_type 决定
    customer_match_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 规则适用的试点邮箱范围
    mailbox_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 匹配模式
    sender_patterns: Mapped[list | None] = mapped_column(JSON, nullable=True)
    subject_patterns: Mapped[list | None] = mapped_column(JSON, nullable=True)
    body_patterns: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 优先级，数值越大优先级越高
    priority: Mapped[int] = mapped_column(default=100, nullable=False)
