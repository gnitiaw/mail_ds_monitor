"""Task log query routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import check_mailbox_scope, db_session, operator_or_admin
from app.core.exceptions import NotFoundError
from app.models.task_log import TaskLog
from app.models.user import User
from app.schemas.common import success
from app.schemas.task_log import TaskLogDetailResponse

router = APIRouter(prefix="/task-logs")


@router.get("/{job_id}")
def get_task_log_detail(
    job_id: str,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
) -> dict[str, Any]:
    """Get a task log with mailbox-scope authorization."""
    task_log = db.get(TaskLog, job_id)
    if task_log is None:
        raise NotFoundError("任务不存在")

    payload = task_log.payload or {}
    mailbox_ids = payload.get("mailbox_ids")
    if not mailbox_ids and task_log.related_mailbox_id:
        mailbox_ids = [task_log.related_mailbox_id]
    check_mailbox_scope(current_user, mailbox_ids)

    data = TaskLogDetailResponse(
        job_id=task_log.id,
        task_type=task_log.task_type,
        status=task_log.status,
        task_key=task_log.task_key,
        related_mailbox_id=task_log.related_mailbox_id,
        related_message_id=task_log.related_message_id,
        payload=task_log.payload,
        result=task_log.result,
        error_message=task_log.error_message,
        started_at=task_log.started_at,
        finished_at=task_log.finished_at,
        executed_at=task_log.executed_at,
    )
    return success(data.model_dump())
