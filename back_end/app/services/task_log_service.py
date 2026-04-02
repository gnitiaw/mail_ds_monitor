"""Task log helpers."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.active_task_lock import ActiveTaskLock
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
    active_lock = db.scalar(
        select(ActiveTaskLock).where(
            ActiveTaskLock.task_type == task_type,
            ActiveTaskLock.task_key == task_key,
        )
    )
    if active_lock is None:
        return None

    task_log = db.get(TaskLog, active_lock.task_log_id)
    if task_log is None or task_log.status not in (TaskStatus.PENDING.value, TaskStatus.RUNNING.value):
        db.delete(active_lock)
        db.commit()
        return None

    return task_log


def cleanup_stale_task_lock(
    db: Session,
    *,
    task_type: str,
    task_key: str,
) -> bool:
    """Remove a stale task lock that no longer points to an active task."""
    active_lock = db.scalar(
        select(ActiveTaskLock).where(
            ActiveTaskLock.task_type == task_type,
            ActiveTaskLock.task_key == task_key,
        )
    )
    if active_lock is None:
        return False

    task_log = db.get(TaskLog, active_lock.task_log_id)
    if task_log is not None and task_log.status in (TaskStatus.PENDING.value, TaskStatus.RUNNING.value):
        return False

    db.delete(active_lock)
    db.commit()
    return True


def acquire_task_lock(
    db: Session,
    *,
    task_type: str,
    task_key: str,
    task_log_id: str,
) -> None:
    """Persist an active task lock for the given task."""
    db.add(
        ActiveTaskLock(
            task_log_id=task_log_id,
            task_type=task_type,
            task_key=task_key,
        )
    )
    db.flush()


def release_task_lock(
    db: Session,
    *,
    task_log_id: str,
) -> bool:
    """Release the lock held by a task if it still exists."""
    active_lock = db.get(ActiveTaskLock, task_log_id)
    if active_lock is None:
        return False

    db.delete(active_lock)
    db.flush()
    return True


def create_task_log(
    db: Session,
    *,
    task_type: str,
    task_key: str | None,
    related_mailbox_id: str | None = None,
    related_message_id: str | None = None,
    payload: dict | None = None,
    task_id: str | None = None,
    commit: bool = True,
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
    if commit:
        db.commit()
        db.refresh(task_log)
    else:
        db.flush()
    return task_log


def mark_task_running(db: Session, task_log: TaskLog, *, commit: bool = True) -> None:
    """Mark task as running."""
    task_log.status = TaskStatus.RUNNING.value
    task_log.started_at = datetime.now(timezone.utc)
    if commit:
        db.commit()


def mark_task_success(
    db: Session,
    task_log: TaskLog,
    *,
    result: dict | None = None,
    release_lock: bool = False,
    commit: bool = True,
) -> None:
    """Mark task as successful."""
    task_log.status = TaskStatus.SUCCESS.value
    task_log.finished_at = datetime.now(timezone.utc)
    task_log.result = result
    task_log.error_message = None
    if release_lock:
        release_task_lock(db, task_log_id=task_log.id)
    if commit:
        db.commit()


def mark_task_failed(
    db: Session,
    task_log: TaskLog,
    *,
    error_message: str,
    result: dict | None = None,
    release_lock: bool = False,
    commit: bool = True,
) -> None:
    """Mark task as failed."""
    task_log.status = TaskStatus.FAILED.value
    task_log.finished_at = datetime.now(timezone.utc)
    task_log.error_message = error_message
    if result is not None:
        task_log.result = result
    if release_lock:
        release_task_lock(db, task_log_id=task_log.id)
    if commit:
        db.commit()
