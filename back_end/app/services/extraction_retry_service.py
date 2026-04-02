"""Async extraction retry task service."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import NotFoundError
from app.models.archive import ArchiveRecord
from app.models.enums import ExtractionStatus, ProcessingStatus, TaskStatus, TaskType
from app.models.mail_message import MailMessage
from app.models.task_log import TaskLog
from app.models.user import User
from app.services.extraction_service import extract_and_archive
from app.services.task_log_service import (
    build_task_key,
    create_task_log,
    get_active_task_by_key,
    mark_task_failed,
    mark_task_running,
    mark_task_success,
)

logger = logging.getLogger(__name__)

MAX_EXTRACTION_RETRIES = 3


def _normalize_message_ids(message_ids: list[str]) -> list[str]:
    """Deduplicate while preserving input order."""
    seen: set[str] = set()
    normalized: list[str] = []
    for message_id in message_ids:
        if message_id not in seen:
            normalized.append(message_id)
            seen.add(message_id)
    return normalized


def create_retry_task(
    db: Session,
    *,
    current_user: User,
    message_ids: list[str],
) -> tuple[TaskLog, bool]:
    """Create or reuse an extraction retry task."""
    normalized_ids = _normalize_message_ids(message_ids)
    messages = list(db.scalars(select(MailMessage).where(MailMessage.id.in_(normalized_ids))).all())
    message_map = {message.id: message for message in messages}

    if len(normalized_ids) == 1 and normalized_ids[0] not in message_map:
        raise NotFoundError("邮件不存在")
    if not messages:
        raise NotFoundError("邮件不存在")

    mailbox_ids = sorted({message.mailbox_id for message in messages})
    task_key = build_task_key(
        "extraction_retry",
        {
            "requested_by": current_user.id,
            "message_ids": sorted(normalized_ids),
        },
    )

    existing = get_active_task_by_key(
        db,
        task_type=TaskType.AI_EXTRACTION.value,
        task_key=task_key,
    )
    if existing:
        return existing, True

    task_log = create_task_log(
        db,
        task_type=TaskType.AI_EXTRACTION.value,
        task_key=task_key,
        related_mailbox_id=mailbox_ids[0] if len(mailbox_ids) == 1 else None,
        related_message_id=normalized_ids[0] if len(normalized_ids) == 1 and normalized_ids[0] in message_map else None,
        payload={
            "message_ids": normalized_ids,
            "mailbox_ids": mailbox_ids,
            "requested_by": current_user.id,
            "max_retries": MAX_EXTRACTION_RETRIES,
        },
    )
    return task_log, False


def execute_extraction_retry_async(database_uri: str, job_id: str) -> None:
    """Execute an extraction retry task in the background."""
    engine = create_engine(database_uri)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)
    db = SessionLocal()
    result: dict | None = None

    try:
        task_log = db.get(TaskLog, job_id)
        if not task_log:
            logger.error("Extraction retry task log not found: %s", job_id)
            return

        if task_log.status not in (TaskStatus.PENDING.value, TaskStatus.RUNNING.value):
            logger.info("Skip extraction retry task %s because status=%s", job_id, task_log.status)
            return

        mark_task_running(db, task_log)

        payload = task_log.payload or {}
        requested_ids: list[str] = payload.get("message_ids", [])

        messages = list(db.scalars(select(MailMessage).where(MailMessage.id.in_(requested_ids))).all())
        message_map = {message.id: message for message in messages}

        result = {
            "total_requested": len(requested_ids),
            "succeeded_count": 0,
            "failed_count": 0,
            "already_max_retries": 0,
            "not_failed_status": 0,
            "not_found": 0,
            "max_retries": MAX_EXTRACTION_RETRIES,
            "details": [],
        }

        for message_id in requested_ids:
            message = message_map.get(message_id)
            if message is None:
                result["not_found"] += 1
                result["details"].append(
                    {
                        "message_id": message_id,
                        "status": "not_found",
                        "retry_count": 0,
                        "max_retries": MAX_EXTRACTION_RETRIES,
                    }
                )
                continue

            prior_retry_count = message.retry_count
            retry_started_at = datetime.now(timezone.utc)

            if message.extraction_status != ExtractionStatus.FAILED.value:
                result["not_failed_status"] += 1
                result["details"].append(
                    {
                        "message_id": message.id,
                        "status": "not_failed_status",
                        "retry_count": message.retry_count,
                        "max_retries": MAX_EXTRACTION_RETRIES,
                    }
                )
                continue

            if message.retry_count >= MAX_EXTRACTION_RETRIES:
                result["already_max_retries"] += 1
                result["details"].append(
                    {
                        "message_id": message.id,
                        "status": "max_retries_reached",
                        "retry_count": message.retry_count,
                        "max_retries": MAX_EXTRACTION_RETRIES,
                    }
                )
                continue

            try:
                message.extraction_status = ExtractionStatus.PENDING.value
                message.extraction_error = None
                message.retry_count = prior_retry_count + 1
                message.last_retry_at = retry_started_at

                extract_and_archive(db, message)

                if message.extraction_status == ExtractionStatus.SUCCESS.value:
                    result["succeeded_count"] += 1
                else:
                    result["failed_count"] += 1

                db.commit()
                result["details"].append(
                    {
                        "message_id": message.id,
                        "status": message.extraction_status,
                        "retry_count": message.retry_count,
                        "max_retries": MAX_EXTRACTION_RETRIES,
                    }
                )
            except Exception as exc:
                logger.exception("Extraction retry task failed for message=%s", message_id)
                db.rollback()

                failed_message = db.get(MailMessage, message_id)
                if failed_message:
                    failed_message.extraction_status = ExtractionStatus.FAILED.value
                    failed_message.extraction_error = str(exc)
                    failed_message.retry_count = prior_retry_count + 1
                    failed_message.last_retry_at = retry_started_at

                    archive = db.scalar(select(ArchiveRecord).where(ArchiveRecord.message_id == message_id))
                    if archive:
                        archive.status = ProcessingStatus.FAILED.value
                        archive.extraction_error = str(exc)

                    db.commit()

                result["failed_count"] += 1
                result["details"].append(
                    {
                        "message_id": message_id,
                        "status": "failed",
                        "retry_count": prior_retry_count + 1,
                        "max_retries": MAX_EXTRACTION_RETRIES,
                        "error_message": str(exc),
                    }
                )

        task_log = db.get(TaskLog, job_id)
        if task_log:
            mark_task_success(db, task_log, result=result)

    except Exception as exc:
        logger.exception("Extraction retry task crashed job=%s", job_id)
        db.rollback()
        task_log = db.get(TaskLog, job_id)
        if task_log:
            mark_task_failed(db, task_log, error_message=str(exc), result=result)
    finally:
        db.close()
        engine.dispose()
