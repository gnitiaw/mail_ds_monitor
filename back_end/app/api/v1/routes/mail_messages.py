"""邮件拉取任务路由。

注意：拉取接口挂载在 /mailboxes 路径下，需要在 mailboxes.py 中引用。
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.common import success
from app.schemas.mail_message import MailPullRequest, MailPullResponse
from app.services.imap_service import pull_emails_for_mailbox
from app.services.mailbox_service import get_mailbox_by_id

# 不设置前缀，由调用方决定
router = APIRouter()


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
        """手动触发邮箱拉取。

        按契约要求，始终返回 pending 状态。
        实际执行结果通过任务记录或日志体现。
        """
        mailbox = get_mailbox_by_id(db, mailbox_id)
        if mailbox is None:
            raise NotFoundError("邮箱配置不存在")

        if mailbox.status != "enabled":
            raise ConflictError("邮箱已禁用")

        # 生成任务 ID
        job_id = str(uuid.uuid4())

        # 执行拉取（同步执行，后续可改为异步任务）
        # 注意：执行结果通过 mailbox.last_pull_status 和 last_pull_error 记录
        # 接口始终返回 pending，符合契约要求
        pull_emails_for_mailbox(
            db, mailbox, force_full_sync=payload.force_full_sync
        )

        response_data = MailPullResponse(
            job_id=job_id,
            mailbox_id=mailbox_id,
            status="pending",  # 按契约要求始终返回 pending
        )
        return success(response_data.model_dump())
