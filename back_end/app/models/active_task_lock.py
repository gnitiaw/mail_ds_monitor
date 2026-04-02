from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActiveTaskLock(Base):
    """Active task lock used to deduplicate in-flight task creation."""

    __tablename__ = "active_task_locks"
    __table_args__ = (
        UniqueConstraint("task_type", "task_key", name="uq_active_task_locks_task_type_key"),
    )

    task_log_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("task_logs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    task_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
