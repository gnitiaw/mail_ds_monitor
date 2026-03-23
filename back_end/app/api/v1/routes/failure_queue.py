"""失败邮件队列路由。"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.exceptions import ForbiddenError, NotFoundError, ParamError, UnauthorizedError
from app.models.enums import FailureQueueStatus, UserRole
from app.models.failure_queue import FailureMailQueue
from app.schemas.common import success
from app.schemas.failure_queue import (
    FailureQueueDetail,
    FailureQueueItem,
    FailureQueueListResponse,
    MatchedSnapshot,
    StatusUpdateRequest,
    StatusUpdateResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/failure-queue", tags=["failure-queue"])


def _get_user_and_scope(db: Session, authorization: str) -> tuple[dict, list[str] | None]:
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


@router.get("")
def list_failure_queue(
    authorization: str = Header(...),
    status: str | None = Query(None, pattern="^(new|acknowledged|resolved)$"),
    mailbox_id: str | None = Query(None),
    keyword: str | None = Query(None),
    start_time: str | None = Query(None),
    end_time: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(db_session),
) -> dict:
    """获取失败邮件队列列表。"""
    user, mailbox_scope_ids = _get_user_and_scope(db, authorization)

    # 检查邮箱范围权限（显式指定越权 mailbox_id 返回 403）
    if mailbox_id and mailbox_scope_ids is not None and mailbox_id not in mailbox_scope_ids:
        raise ForbiddenError("无权限访问该邮箱范围")

    stmt = select(FailureMailQueue)

    # 邮箱范围过滤（operator 有空列表时应返回空结果）
    if mailbox_scope_ids is not None:
        stmt = stmt.where(FailureMailQueue.mailbox_id.in_(mailbox_scope_ids))

    if mailbox_id:
        stmt = stmt.where(FailureMailQueue.mailbox_id == mailbox_id)

    # 状态过滤
    if status:
        stmt = stmt.where(FailureMailQueue.status == status)

    # 时间范围
    if start_time:
        stmt = stmt.where(FailureMailQueue.received_at >= start_time)
    if end_time:
        stmt = stmt.where(FailureMailQueue.received_at <= end_time)

    # 关键词搜索
    if keyword:
        keyword_pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                FailureMailQueue.subject.ilike(keyword_pattern),
                FailureMailQueue.customer_name.ilike(keyword_pattern),
                FailureMailQueue.task_identifier.ilike(keyword_pattern),
            )
        )

    # 统计总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(db.scalar(count_stmt) or 0)

    # 排序和分页
    stmt = stmt.order_by(FailureMailQueue.received_at.desc().nullslast())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt).all())

    # 转换响应
    response_items = [
        FailureQueueItem(
            queue_id=item.id,
            mailbox_id=item.mailbox_id,
            source_message_id=item.source_message_id,
            failure_rule_key=item.failure_rule_key,
            customer_name=item.customer_name,
            task_identifier=item.task_identifier,
            subject=item.subject,
            sender=item.sender,
            received_at=item.received_at,
            status=item.status,
            first_captured_at=item.first_captured_at,
            last_seen_at=item.last_seen_at,
        ).model_dump()
        for item in items
    ]

    data = FailureQueueListResponse(
        items=response_items,
        page=page,
        page_size=page_size,
        total=total,
    )
    return success(data.model_dump())


@router.get("/{queue_id}")
def get_failure_queue_detail(
    queue_id: str,
    authorization: str = Header(...),
    db: Session = Depends(db_session),
) -> dict:
    """获取失败邮件队列详情。"""
    user, mailbox_scope_ids = _get_user_and_scope(db, authorization)

    item = db.scalar(
        select(FailureMailQueue).where(FailureMailQueue.id == queue_id)
    )

    if not item:
        raise NotFoundError("失败邮件队列记录不存在")

    # 检查邮箱范围权限（mailbox_scope_ids 为 None 表示 admin，为列表表示 operator）
    if mailbox_scope_ids is not None and item.mailbox_id not in mailbox_scope_ids:
        raise ForbiddenError("无权限访问该邮箱范围")

    # 构建命中快照
    matched_snapshot = None
    if item.matched_snapshot:
        matched_snapshot = MatchedSnapshot(
            matched_fields=item.matched_snapshot.get("matched_fields"),
            extracted_fields=item.matched_snapshot.get("extracted_fields"),
        )

    detail = FailureQueueDetail(
        queue_id=item.id,
        mailbox_id=item.mailbox_id,
        source_message_id=item.source_message_id,
        provider_uid=item.provider_uid,
        failure_rule_key=item.failure_rule_key,
        customer_name=item.customer_name,
        task_identifier=item.task_identifier,
        subject=item.subject,
        sender=item.sender,
        received_at=item.received_at,
        status=item.status,
        acknowledged_at=item.acknowledged_at,
        acknowledged_by=item.acknowledged_by,
        resolved_at=item.resolved_at,
        resolved_by=item.resolved_by,
        body_text=item.body_text,
        body_html=item.body_html,
        matched_snapshot=matched_snapshot,
    )

    return success(detail.model_dump())


@router.patch("/{queue_id}/status")
def update_failure_queue_status(
    queue_id: str,
    request: StatusUpdateRequest,
    authorization: str = Header(...),
    db: Session = Depends(db_session),
) -> dict:
    """更新失败邮件队列状态。"""
    user, mailbox_scope_ids = _get_user_and_scope(db, authorization)

    item = db.scalar(
        select(FailureMailQueue).where(FailureMailQueue.id == queue_id)
    )

    if not item:
        raise NotFoundError("失败邮件队列记录不存在")

    # 检查邮箱范围权限（mailbox_scope_ids 为 None 表示 admin，为列表表示 operator）
    if mailbox_scope_ids is not None and item.mailbox_id not in mailbox_scope_ids:
        raise ForbiddenError("无权限访问该邮箱范围")

    # 状态机校验
    current_status = item.status
    target_status = request.status

    # 合法状态流转: new -> acknowledged -> resolved
    valid_transitions = {
        FailureQueueStatus.NEW.value: [FailureQueueStatus.ACKNOWLEDGED.value],
        FailureQueueStatus.ACKNOWLEDGED.value: [FailureQueueStatus.RESOLVED.value],
        FailureQueueStatus.RESOLVED.value: [],  # 已解决不能回退
    }

    # 幂等：同一目标状态重复提交返回一致结果
    if current_status == target_status:
        pass  # 允许幂等
    elif target_status not in valid_transitions.get(current_status, []):
        from app.core.exceptions import ConflictError
        raise ConflictError("状态流转冲突")

    # 更新状态
    now = datetime.now(timezone.utc)
    item.status = target_status

    if target_status == FailureQueueStatus.ACKNOWLEDGED.value:
        if not item.acknowledged_at:
            item.acknowledged_at = now
            item.acknowledged_by = user.id

    if target_status == FailureQueueStatus.RESOLVED.value:
        if not item.resolved_at:
            item.resolved_at = now
            item.resolved_by = user.id

    db.commit()
    db.refresh(item)

    response = StatusUpdateResponse(
        queue_id=item.id,
        status=item.status,
        acknowledged_at=item.acknowledged_at,
        acknowledged_by=item.acknowledged_by,
        resolved_at=item.resolved_at,
        resolved_by=item.resolved_by,
        updated_at=item.updated_at,
    )

    return success(response.model_dump())
