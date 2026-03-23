"""捕获任务运行路由。"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.models.enums import UserRole
from app.schemas.common import success
from app.schemas.capture_runs import ReplayRequest, ReplayResponse
from app.services.auth_service import AuthService
from app.services.capture_scheduler_service import CaptureSchedulerService

router = APIRouter(prefix="/failure-capture-runs", tags=["capture-runs"])


def _get_user_and_scope(db: Session, authorization: str):
    """验证用户并返回邮箱访问范围。"""
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("未登录")

    token = authorization[7:]
    user = AuthService.get_current_user(db, token)
    if not user:
        raise UnauthorizedError("未登录")

    mailbox_scope_ids = user.mailbox_scope_ids
    if user.role == UserRole.ADMIN.value:
        mailbox_scope_ids = None  # admin 不限制

    return user, mailbox_scope_ids


@router.post("/replay")
def trigger_manual_replay(
    request: ReplayRequest,
    authorization: str = Header(...),
    db: Session = Depends(db_session),
) -> dict:
    """手动补跑失败邮件捕获任务。"""
    user, mailbox_scope_ids = _get_user_and_scope(db, authorization)

    # 检查邮箱范围权限
    if mailbox_scope_ids:
        for mailbox_id in request.mailbox_ids:
            if mailbox_id not in mailbox_scope_ids:
                raise ForbiddenError("无权限访问该邮箱范围")

    # 触发手动补跑
    result = CaptureSchedulerService.trigger_manual_replay(
        db=db,
        mailbox_ids=request.mailbox_ids,
        lookback_minutes=request.lookback_minutes,
        triggered_by=user.id,
    )

    if result.get("already_running"):
        raise ConflictError("当前已有进行中的补跑任务")

    return success(
        ReplayResponse(
            run_id=result["run_id"],
            status=result["status"],
            mailbox_ids=request.mailbox_ids,
        ).model_dump()
    )
