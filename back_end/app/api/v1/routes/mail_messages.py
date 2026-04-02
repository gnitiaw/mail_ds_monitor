"""邮件拉取与原始邮件查询路由。

注意：拉取接口挂载在 /mailboxes 路径下，需要在 mailboxes.py 中引用。
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import check_mailbox_scope, db_session, operator_or_admin
from app.core.datetime_utils import assume_utc
from app.core.exceptions import ConflictError, NotFoundError
from app.models.mail_message import MailMessage
from app.models.user import User
from app.schemas.common import success
from app.schemas.mail_message import (
    BatchRetryRequest,
    MailPullRequest,
    MailPullResponse,
    RawMailDetailResponse,
    RawMailListItem,
    RawMailListResponse,
)
from app.schemas.task_log import TaskLogAcceptedResponse
from app.services.extraction_retry_service import MAX_EXTRACTION_RETRIES, create_retry_task
from app.services.mail_pull_service import MailPullService
from app.services.mailbox_service import get_mailbox_by_id

router = APIRouter(prefix="/mail-messages")


@router.get("")
def list_mail_messages(
    db: Annotated[Session, Depends(db_session)],
    mailbox_id: Annotated[str | None, Query()] = None,
    keyword: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """获取原始邮件列表。"""
    stmt = select(MailMessage)

    if mailbox_id:
        stmt = stmt.where(MailMessage.mailbox_id == mailbox_id)
    if keyword:
        keyword_pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                MailMessage.subject.ilike(keyword_pattern),
                MailMessage.sender_email.ilike(keyword_pattern),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(db.scalar(count_stmt) or 0)

    stmt = stmt.order_by(
        MailMessage.received_at.is_(None),
        MailMessage.received_at.desc(),
        MailMessage.created_at.desc(),
    )
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt).all())

    response_items = [
        RawMailListItem(
            message_id=item.id,
            mailbox_id=item.mailbox_id,
            internet_message_id=item.internet_message_id,
            provider_uid=item.provider_uid,
            folder=item.folder,
            subject=item.subject,
            sender=item.sender_email,
            received_at=assume_utc(item.received_at),
            parse_status=item.parse_status,
            extraction_status=item.extraction_status,
            parse_error=item.parse_error,
            extraction_error=item.extraction_error,
            retry_count=item.retry_count,
            max_retries=MAX_EXTRACTION_RETRIES,
            has_attachments=item.has_attachments,
            pulled_at=item.pulled_at,
        ).model_dump()
        for item in items
    ]

    data = RawMailListResponse(
        items=response_items,
        page=page,
        page_size=page_size,
        total=total,
    )
    return success(data.model_dump())


@router.post("/batch-retry-extraction", status_code=status.HTTP_202_ACCEPTED)
def batch_retry_extraction(
    request: BatchRetryRequest,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
) -> dict[str, Any]:
    """批量重试邮件提取。"""
    message_ids = request.message_ids
    messages = list(db.scalars(select(MailMessage).where(MailMessage.id.in_(message_ids))).all())
    mailbox_ids = sorted({message.mailbox_id for message in messages})
    check_mailbox_scope(current_user, mailbox_ids)

    task_log, reused = create_retry_task(
        db,
        current_user=current_user,
        message_ids=message_ids,
    )

    from app.core.scheduler import add_extraction_retry_job, init_scheduler

    init_scheduler()
    if not reused:
        add_extraction_retry_job(task_log.id)

    return success(
        TaskLogAcceptedResponse(
            job_id=task_log.id,
            status=task_log.status,
            reused_existing_job=reused,
            requested_count=len(message_ids),
            max_retries=MAX_EXTRACTION_RETRIES,
        ).model_dump()
    )


@router.get("/{message_id}")
def get_mail_message_detail(
    message_id: str,
    db: Annotated[Session, Depends(db_session)],
) -> dict[str, Any]:
    """获取原始邮件详情。"""
    message = db.get(MailMessage, message_id)
    if message is None:
        raise NotFoundError("原始邮件不存在")

    data = RawMailDetailResponse(
        message_id=message.id,
        mailbox_id=message.mailbox_id,
        internet_message_id=message.internet_message_id,
        provider_uid=message.provider_uid,
        folder=message.folder,
        subject=message.subject,
        sender_name=message.sender_name,
        sender_email=message.sender_email,
        recipients_to=message.recipients_to,
        recipients_cc=message.recipients_cc,
        recipients_bcc=message.recipients_bcc,
        reply_to=message.reply_to,
        flags=message.flags,
        has_attachments=message.has_attachments,
        parse_status=message.parse_status,
        extraction_status=message.extraction_status,
        parse_error=message.parse_error,
        extraction_error=message.extraction_error,
        retry_count=message.retry_count,
        max_retries=MAX_EXTRACTION_RETRIES,
        last_retry_at=message.last_retry_at,
        received_at=assume_utc(message.received_at),
        pulled_at=message.pulled_at,
        body_text=message.body_text,
        body_html=message.body_html,
    )
    return success(data.model_dump())


@router.post("/{message_id}/retry-extraction", status_code=status.HTTP_202_ACCEPTED)
def retry_single_extraction(
    message_id: str,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
) -> dict[str, Any]:
    """重试单条邮件的提取。"""
    message = db.get(MailMessage, message_id)
    if message is None:
        raise NotFoundError("邮件不存在")
    check_mailbox_scope(current_user, [message.mailbox_id])

    task_log, reused = create_retry_task(
        db,
        current_user=current_user,
        message_ids=[message_id],
    )

    from app.core.scheduler import add_extraction_retry_job, init_scheduler

    init_scheduler()
    if not reused:
        add_extraction_retry_job(task_log.id)

    return success(
        TaskLogAcceptedResponse(
            job_id=task_log.id,
            status=task_log.status,
            reused_existing_job=reused,
            requested_count=1,
            max_retries=MAX_EXTRACTION_RETRIES,
        ).model_dump()
    )


def register_pull_route(main_mailbox_router: APIRouter) -> None:
    """注册拉取路由到邮箱路由器。"""

    @main_mailbox_router.post(
        "/{mailbox_id}/pull",
        status_code=status.HTTP_202_ACCEPTED,
    )
    def trigger_mail_pull(
        mailbox_id: str,
        payload: MailPullRequest,
        db: Annotated[Session, Depends(db_session)],
    ) -> dict[str, Any]:
        """手动触发邮箱拉取。"""
        mailbox = get_mailbox_by_id(db, mailbox_id)
        if mailbox is None:
            raise NotFoundError("邮箱配置不存在")

        if mailbox.status != "enabled":
            raise ConflictError("邮箱已禁用")

        job_id = MailPullService.trigger_mail_pull(
            db=db,
            mailbox=mailbox,
            force_full_sync=payload.force_full_sync,
        )

        response_data = MailPullResponse(
            job_id=job_id,
            mailbox_id=mailbox_id,
            status="pending",
        )
        return success(response_data.model_dump())
