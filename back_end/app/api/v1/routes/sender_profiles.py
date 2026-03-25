"""发件人配置相关路由。"""

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import admin_required, db_session, filter_mailbox_scope, operator_or_admin
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ParamError
from app.models.user import User
from app.schemas.common import success
from app.schemas.sender_profile import (
    SenderCandidateListResponse,
    SenderCandidateResponse,
    SenderProfileCreateRequest,
    SenderProfileListResponse,
    SenderProfileResponse,
    SenderProfileUpdateRequest,
)
from app.services.sender_profile_service import (
    create_sender_profile,
    get_profile_linked_message_count,
    get_sender_candidates,
    list_sender_profiles,
    update_sender_profile,
)

router = APIRouter(prefix="/sender-profiles")


@router.get("/candidates")
def get_candidates(
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
    mailbox_id: Annotated[str | None, Query()] = None,
    identified_status: Annotated[str | None, Query()] = None,
    keyword: Annotated[str | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """获取候选发件人列表。

    admin 和 operator 都可以访问。
    operator 只能看到其 mailbox_scope_ids 范围内的数据。
    """
    # 验证 identified_status
    if identified_status and identified_status not in ("identified", "unidentified"):
        raise ParamError("identified_status 必须为 identified 或 unidentified")

    # 应用邮箱范围过滤
    effective_mailbox_ids = filter_mailbox_scope(current_user, [mailbox_id] if mailbox_id else None)
    effective_mailbox_id = effective_mailbox_ids[0] if effective_mailbox_ids else None

    candidates, total = get_sender_candidates(
        db=db,
        mailbox_id=effective_mailbox_id,
        identified_status=identified_status,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )

    data = SenderCandidateListResponse(
        items=[SenderCandidateResponse(**c) for c in candidates],
        total=total,
        page=page,
        page_size=page_size,
    )
    return success(data.model_dump())


@router.get("")
def list_profiles(
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
    keyword: Annotated[str | None, Query()] = None,
    status_value: Annotated[str | None, Query(alias="status")] = None,
    match_type: Annotated[str | None, Query()] = None,
    customer_name: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """获取发件人档案列表。

    admin 和 operator 都可以访问（只读）。
    """
    # 验证参数
    if status_value and status_value not in ("enabled", "disabled"):
        raise ParamError("status 必须为 enabled 或 disabled")
    if match_type and match_type not in ("exact_email", "email_domain"):
        raise ParamError("match_type 必须为 exact_email 或 email_domain")

    profiles, total = list_sender_profiles(
        db=db,
        keyword=keyword,
        status=status_value,
        match_type=match_type,
        customer_name=customer_name,
        page=page,
        page_size=page_size,
    )

    items = []
    for profile in profiles:
        # 获取关联邮件数量
        linked_count = get_profile_linked_message_count(db, profile)

        items.append(SenderProfileResponse(
            profile_id=profile.id,
            match_type=profile.match_type,
            match_value=profile.match_value,
            customer_name=profile.customer_name,
            customer_code=profile.customer_code,
            sender_label=profile.sender_label,
            sender_type=profile.sender_type,
            status=profile.status,
            notes=profile.notes,
            last_seen_at=None,  # TODO: 实现最近匹配时间查询
            linked_message_count=linked_count,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        ))

    data = SenderProfileListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
    return success(data.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: SenderProfileCreateRequest,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(admin_required)],
) -> dict[str, Any]:
    """创建发件人档案。

    仅 admin 可以创建。
    """
    try:
        profile = create_sender_profile(
            db=db,
            match_type=payload.match_type,
            match_value=payload.match_value,
            customer_name=payload.customer_name,
            customer_code=payload.customer_code,
            sender_label=payload.sender_label,
            sender_type=payload.sender_type,
            status=payload.status,
            notes=payload.notes,
        )
    except ValueError as e:
        raise ConflictError(str(e))

    data = SenderProfileResponse(
        profile_id=profile.id,
        match_type=profile.match_type,
        match_value=profile.match_value,
        customer_name=profile.customer_name,
        customer_code=profile.customer_code,
        sender_label=profile.sender_label,
        sender_type=profile.sender_type,
        status=profile.status,
        notes=profile.notes,
        last_seen_at=None,
        linked_message_count=0,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
    return success(data.model_dump())


@router.put("/{profile_id}")
def update_profile(
    profile_id: str,
    payload: SenderProfileUpdateRequest,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(admin_required)],
) -> dict[str, Any]:
    """更新发件人档案。

    仅 admin 可以更新。
    """
    profile = update_sender_profile(
        db=db,
        profile_id=profile_id,
        customer_name=payload.customer_name,
        customer_code=payload.customer_code,
        sender_label=payload.sender_label,
        sender_type=payload.sender_type,
        status=payload.status,
        notes=payload.notes,
    )

    if not profile:
        raise NotFoundError("发件人档案不存在")

    linked_count = get_profile_linked_message_count(db, profile)

    data = SenderProfileResponse(
        profile_id=profile.id,
        match_type=profile.match_type,
        match_value=profile.match_value,
        customer_name=profile.customer_name,
        customer_code=profile.customer_code,
        sender_label=profile.sender_label,
        sender_type=profile.sender_type,
        status=profile.status,
        notes=profile.notes,
        last_seen_at=None,
        linked_message_count=linked_count,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
    return success(data.model_dump())
