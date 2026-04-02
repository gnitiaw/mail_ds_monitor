"""Scheduling helpers for extraction retry tasks."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.task_log import TaskLog
from app.services.task_log_service import mark_task_failed


def schedule_retry_task(db: Session, task_log: TaskLog, *, reused: bool) -> None:
    """Schedule a retry task or mark it failed if scheduling cannot start."""
    from app.core.scheduler import add_extraction_retry_job, init_scheduler

    init_scheduler()
    if reused:
        return

    try:
        add_extraction_retry_job(task_log.id)
    except Exception as exc:
        failed_task = db.get(TaskLog, task_log.id)
        if failed_task is not None:
            mark_task_failed(
                db,
                failed_task,
                error_message=f"任务调度失败: {exc}",
                release_lock=True,
            )
        raise
