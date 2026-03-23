"""失败邮件识别规则路由。"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.models.enums import RuleStatus, UserRole
from app.models.failure_capture import FailureCaptureRule
from app.schemas.common import success
from app.schemas.failure_rules import (
    CustomerMatchConfig,
    FailureRuleCreateRequest,
    FailureRuleCreateResponse,
    FailureRuleItem,
    FailureRuleListResponse,
    FailureRuleUpdateRequest,
    FailureRuleUpdateResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/failure-rules", tags=["failure-rules"])


def _require_admin(db: Session, authorization: str):
    """验证管理员权限。"""
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("未登录")

    token = authorization[7:]
    user = AuthService.get_current_user(db, token)
    if not user:
        raise UnauthorizedError("未登录")

    if user.role != UserRole.ADMIN.value:
        raise ForbiddenError("无权限")

    return user


@router.get("")
def list_failure_rules(
    authorization: str = Header(...),
    status: str | None = Query(None, pattern="^(enabled|disabled)$"),
    db: Session = Depends(db_session),
) -> dict:
    """获取失败邮件识别规则列表（仅 admin）。"""
    _require_admin(db, authorization)

    stmt = select(FailureCaptureRule)

    if status:
        stmt = stmt.where(FailureCaptureRule.status == status)

    stmt = stmt.order_by(FailureCaptureRule.priority.desc(), FailureCaptureRule.created_at.desc())
    items = list(db.scalars(stmt).all())

    response_items = [
        FailureRuleItem(
            rule_id=item.id,
            rule_name=item.rule_name,
            failure_rule_key=item.failure_rule_key,
            status=item.status,
            customer_scope_type=item.customer_scope_type,
            mailbox_ids=item.mailbox_ids,
            updated_at=item.updated_at,
        ).model_dump()
        for item in items
    ]

    return success(
        FailureRuleListResponse(
            items=response_items,
            total=len(items),
        ).model_dump()
    )


@router.post("", status_code=201)
def create_failure_rule(
    request: FailureRuleCreateRequest,
    authorization: str = Header(...),
    db: Session = Depends(db_session),
) -> dict:
    """创建失败邮件识别规则（仅 admin）。"""
    _require_admin(db, authorization)

    # 检查 failure_rule_key 是否已存在
    existing = db.scalar(
        select(FailureCaptureRule).where(FailureCaptureRule.failure_rule_key == request.failure_rule_key)
    )
    if existing:
        raise ConflictError("规则配置冲突：failure_rule_key 已存在")

    rule = FailureCaptureRule(
        rule_name=request.rule_name,
        failure_rule_key=request.failure_rule_key,
        status=request.status,
        customer_scope_type=request.customer_scope_type,
        customer_match_config=request.customer_match_config.model_dump() if request.customer_match_config else None,
        mailbox_ids=request.mailbox_ids,
        sender_patterns=request.sender_patterns,
        subject_patterns=request.subject_patterns,
        body_patterns=request.body_patterns,
        priority=request.priority,
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    return success(
        FailureRuleCreateResponse(
            rule_id=rule.id,
            rule_name=rule.rule_name,
            status=rule.status,
            updated_at=rule.updated_at,
        ).model_dump()
    )


@router.put("/{rule_id}")
def update_failure_rule(
    rule_id: str,
    request: FailureRuleUpdateRequest,
    authorization: str = Header(...),
    db: Session = Depends(db_session),
) -> dict:
    """更新失败邮件识别规则（仅 admin）。"""
    _require_admin(db, authorization)

    rule = db.scalar(
        select(FailureCaptureRule).where(FailureCaptureRule.id == rule_id)
    )

    if not rule:
        raise NotFoundError("规则不存在")

    # 更新字段
    if request.rule_name is not None:
        rule.rule_name = request.rule_name
    if request.status is not None:
        rule.status = request.status
    if request.customer_scope_type is not None:
        rule.customer_scope_type = request.customer_scope_type
    if request.customer_match_config is not None:
        rule.customer_match_config = request.customer_match_config.model_dump()
    if request.mailbox_ids is not None:
        rule.mailbox_ids = request.mailbox_ids
    if request.sender_patterns is not None:
        rule.sender_patterns = request.sender_patterns
    if request.subject_patterns is not None:
        rule.subject_patterns = request.subject_patterns
    if request.body_patterns is not None:
        rule.body_patterns = request.body_patterns
    if request.priority is not None:
        rule.priority = request.priority

    db.commit()
    db.refresh(rule)

    return success(
        FailureRuleUpdateResponse(
            rule_id=rule.id,
            status=rule.status,
            updated_at=rule.updated_at,
        ).model_dump()
    )
