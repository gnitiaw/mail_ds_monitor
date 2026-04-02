"""Task log helpers."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import TaskStatus
from app.models.task_log import TaskLog


def build_task_key(prefix: str, payload: dict) -> str:
    """Build a stable task key from a normalized payload."""
    normalized = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def get_active_task_by_key(
    db: Session,
    *,
    task_type: str,
    task_key: str,
) -> TaskLog | None:
    """Return an active task if one already exists for the key."""
    return db.scalar(
        select(TaskLog).where(
            TaskLog.task_type == task_type,
            TaskLog.task_key == task_key,
            TaskLog.status.in_([TaskStatus.PENDING.value, TaskStatus.RUNNING.value]),
        )
    )


def create_task_log(
    db: Session,
    *,
    task_type: str,
    task_key: str | None,
    related_mailbox_id: str | None = None,
    related_message_id: str | None = None,
    payload: dict | None = None,
    task_id: str | None = None,
) -> TaskLog:
    """Create a pending task log and persist it."""
    task_log = TaskLog(
        id=task_id or str(uuid.uuid4()),
        task_type=task_type,
        task_key=task_key,
        status=TaskStatus.PENDING.value,
        related_mailbox_id=related_mailbox_id,
        related_message_id=related_message_id,
        payload=payload,
    )
    db.add(task_log)
    db.commit()
    db.refresh(task_log)
    return task_log


def mark_task_running(db: Session, task_log: TaskLog) -> None:
    """Mark task as running."""
    task_log.status = TaskStatus.RUNNING.value
    task_log.started_at = datetime.now(timezone.utc)
    db.commit()


def mark_task_success(db: Session, task_log: TaskLog, *, result: dict | None = None) -> None:
    """Mark task as successful."""
    task_log.status = TaskStatus.SUCCESS.value
    task_log.finished_at = datetime.now(timezone.utc)
    task_log.result = result
    task_log.error_message = None
    db.commit()


def mark_task_failed(
    db: Session,
    task_log: TaskLog,
    *,
    error_message: str,
    result: dict | None = None,
) -> None:
    """Mark task as failed."""
    task_log.status = TaskStatus.FAILED.value
    task_log.finished_at = datetime.now(timezone.utc)
    task_log.error_message = error_message
    if result is not None:
        task_log.result = result
    db.commit()
