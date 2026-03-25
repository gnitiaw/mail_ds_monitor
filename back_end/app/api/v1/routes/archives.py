"""归档查询相关路由。"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import db_session
from app.core.datetime_utils import assume_utc
from app.core.exceptions import NotFoundError
from app.models.archive import ArchiveRecord
from app.schemas.common import success
from app.schemas.mail_message import ArchiveDetailResponse, ArchiveListResponse, MailMessageResponse

router = APIRouter(prefix="/archives")


@router.get("")
def list_archives(
    db: Annotated[Session, Depends(db_session)],
    mailbox_id: Annotated[str | None, Query()] = None,
    status_value: Annotated[str | None, Query(alias="status")] = None,
    start_time: Annotated[str | None, Query()] = None,
    end_time: Annotated[str | None, Query()] = None,
    keyword: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """获取归档列表。"""
    stmt = select(ArchiveRecord).options(joinedload(ArchiveRecord.message))

    # 筛选条件
    if mailbox_id:
        stmt = stmt.where(ArchiveRecord.mailbox_id == mailbox_id)
    if status_value:
        stmt = stmt.where(ArchiveRecord.status == status_value)

    # 时间范围
    if start_time:
        stmt = stmt.where(ArchiveRecord.received_at >= start_time)
    if end_time:
        stmt = stmt.where(ArchiveRecord.received_at <= end_time)

    # 关键词搜索
    if keyword:
        keyword_pattern = f"%{keyword}%"
        stmt = stmt.where((ArchiveRecord.summary.ilike(keyword_pattern)))

    # 统计总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(db.scalar(count_stmt) or 0)

    # 排序和分页
    stmt = stmt.order_by(
        ArchiveRecord.received_at.is_(None),
        ArchiveRecord.received_at.desc(),
    )
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt).unique().all())

    # 转换响应
    response_items = []
    for archive in items:
        sender = None
        subject = None
        extraction_status = "pending"
        confidence = None

        if archive.message:
            sender = archive.message.sender_email
            subject = archive.message.subject
            # extraction_status 来自邮件消息的真实状态
            extraction_status = archive.message.extraction_status or "pending"

        # confidence 来自归档记录
        if archive.confidence is not None:
            confidence = float(archive.confidence)

        response_items.append(
            MailMessageResponse(
                archive_id=archive.id,
                mailbox_id=archive.mailbox_id,
                message_id=archive.message_id,
                subject=subject,
                sender=sender,
                received_at=assume_utc(archive.received_at),
                status=archive.status,
                tags=archive.risk_tags,
                summary=archive.summary,
                extraction_status=extraction_status,
                confidence=confidence,
            ).model_dump()
        )

    data = ArchiveListResponse(
        items=response_items,
        page=page,
        page_size=page_size,
        total=total,
    )
    return success(data.model_dump())


@router.get("/{archive_id}")
def get_archive_detail(
    archive_id: str,
    db: Annotated[Session, Depends(db_session)],
) -> dict[str, Any]:
    """获取归档详情。"""
    archive = db.scalar(
        select(ArchiveRecord)
        .options(joinedload(ArchiveRecord.message))
        .where(ArchiveRecord.id == archive_id)
    )

    if archive is None:
        raise NotFoundError("归档记录不存在")

    message = archive.message
    recipients = None
    body_text = None
    body_html = None
    sender = None
    subject = None
    extraction_status = "pending"
    parse_error = None
    confidence = None

    if message:
        recipients = (message.recipients_to or []) + (message.recipients_cc or [])
        body_text = message.body_text
        body_html = message.body_html
        sender = message.sender_email
        subject = message.subject
        # extraction_status 来自邮件消息的真实状态
        extraction_status = message.extraction_status or "pending"
        # parse_error 来自邮件消息的解析错误（不是 extraction_error）
        parse_error = message.parse_error

    # confidence 来自归档记录
    if archive.confidence is not None:
        confidence = float(archive.confidence)

    response_data = ArchiveDetailResponse(
        archive_id=archive.id,
        mailbox_id=archive.mailbox_id,
        message_id=archive.message_id,
        subject=subject,
        sender=sender,
        recipients=recipients,
        received_at=assume_utc(archive.received_at),
        body_text=body_text,
        body_html=body_html,
        extracted_fields=archive.extracted_fields,
        tags=archive.risk_tags,
        status=archive.status,
        extraction_status=extraction_status,
        confidence=confidence,
        model_name=archive.model_name,
        prompt_version=archive.prompt_version,
        parse_error=parse_error,
    )
    return success(response_data.model_dump())
