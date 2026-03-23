"""邮箱配置路由。"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.common import success
from app.schemas.mailbox import (
    MailboxCreateRequest,
    MailboxListResponse,
    MailboxResponse,
    MailboxUpdateRequest,
)
from app.services.mailbox_service import (
    MailboxConflictError,
    MailboxNotFoundError,
    create_mailbox,
    list_mailboxes,
    update_mailbox,
)

router = APIRouter(prefix="/mailboxes")


@router.get("")
def get_mailboxes(
    db: Annotated[Session, Depends(db_session)],
    status_value: Annotated[str | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """获取邮箱列表。"""
    items, total = list_mailboxes(db, status=status_value, page=page, page_size=page_size)
    data = MailboxListResponse(
        items=[MailboxResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )
    return success(data.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED)
def post_mailbox(
    payload: MailboxCreateRequest,
    db: Annotated[Session, Depends(db_session)],
) -> dict[str, Any]:
    """创建邮箱配置。"""
    try:
        mailbox = create_mailbox(db, payload)
    except MailboxConflictError as exc:
        raise ConflictError(str(exc))

    data = MailboxResponse.model_validate(mailbox)
    return success(data.model_dump())


@router.put("/{mailbox_id}")
def put_mailbox(
    mailbox_id: str,
    payload: MailboxUpdateRequest,
    db: Annotated[Session, Depends(db_session)],
) -> dict[str, Any]:
    """更新邮箱配置。"""
    try:
        mailbox = update_mailbox(db, mailbox_id, payload)
    except MailboxNotFoundError as exc:
        raise NotFoundError(str(exc))
    except MailboxConflictError as exc:
        raise ConflictError(str(exc))

    data = MailboxResponse.model_validate(mailbox)
    return success(data.model_dump())


# 导入并注册拉取路由
from app.api.v1.routes.mail_messages import register_pull_route

register_pull_route(router)
