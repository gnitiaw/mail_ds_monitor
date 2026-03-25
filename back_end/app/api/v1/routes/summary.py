"""Summary config routes."""

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import admin_required, db_session, operator_or_admin
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ParamError
from app.models.analysis_run import AnalysisRun
from app.models.enums import AnalysisRunStatus, SummarySendStatus, SummaryScopeMode
from app.models.summary import SummaryConfig, SummarySendRecord
from app.models.user import User
from app.schemas.common import success
from app.schemas.summary import (
    ManualSendRequest,
    ManualSendResponse,
    SummaryConfigCreateRequest,
    SummaryConfigListResponse,
    SummaryConfigResponse,
    SummarySendListResponse,
    SummarySendRecordResponse,
)
from app.services.summary_service import execute_summary_send

router = APIRouter(prefix="/summary-configs")
sends_router = APIRouter(prefix="/summary-sends")


def _operator_can_access_config(
    current_user: User,
    config: SummaryConfig,
) -> bool:
    """Check if operator can access the config.

    Rules (consistent across list/send/send-records):
    - Admin can access everything
    - Operator can ONLY access configs with explicit mailbox_ids
    - Operator's scope must contain ALL mailboxes in the config
    - Global configs (mailbox_ids=None/empty) are FORBIDDEN for operators

    This prevents operators from triggering full-mailbox summaries.
    """
    if current_user.role == "admin":
        return True

    if current_user.role != "operator":
        return False

    user_scope = current_user.mailbox_scope_ids or []

    # Operator with no scope cannot access anything
    if not user_scope:
        return False

    # Global config (no mailbox_ids) is FORBIDDEN for operators
    # This prevents "summary all mailboxes" privilege escalation
    if not config.mailbox_ids:
        return False

    # All mailboxes in config must be in operator's scope
    for mailbox_id in config.mailbox_ids:
        if mailbox_id not in user_scope:
            return False

    return True


def _check_config_access(
    current_user: User,
    config: SummaryConfig,
) -> None:
    """Check if user has permission to access the config.

    Raises:
        ForbiddenError: If user has no permission to access the config
    """
    if not _operator_can_access_config(current_user, config):
        raise ForbiddenError("no permission to access this config")


@router.get("")
def list_summary_configs(
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
) -> dict[str, Any]:
    """List summary configs. Operator sees only configs in their scope."""
    stmt = select(SummaryConfig).order_by(SummaryConfig.created_at.desc())
    all_items = list(db.scalars(stmt).all())

    items = [cfg for cfg in all_items if _operator_can_access_config(current_user, cfg)]

    data = SummaryConfigListResponse(
        items=[SummaryConfigResponse.model_validate(item) for item in items],
        total=len(items),
    )
    return success(data.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED)
def create_summary_config(
    payload: SummaryConfigCreateRequest,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(admin_required)],
) -> dict[str, Any]:
    """Create summary config. Admin only."""
    existing = db.scalar(select(SummaryConfig).where(SummaryConfig.name == payload.name))
    if existing:
        raise ConflictError("config name already exists")

    config = SummaryConfig(
        name=payload.name,
        enabled=payload.enabled,
        schedule_type=payload.schedule_type,
        recipient_emails=payload.recipient_emails,
        mailbox_ids=payload.mailbox_ids,
        include_statuses=payload.include_statuses,
        send_time=payload.send_time,
        summary_mode=payload.summary_mode,
        empty_result_policy=payload.empty_result_policy,
        summary_scope_mode=payload.summary_scope_mode,
        include_unidentified_senders=payload.include_unidentified_senders,
        top_n_per_customer=payload.top_n_per_customer,
        customer_analysis_mode=payload.customer_analysis_mode,
    )
    db.add(config)
    db.commit()
    db.refresh(config)

    data = SummaryConfigResponse.model_validate(config)
    return success(data.model_dump())


@router.post("/{config_id}/send", status_code=status.HTTP_202_ACCEPTED)
def trigger_manual_send(
    config_id: str,
    payload: ManualSendRequest,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
) -> dict[str, Any]:
    """Trigger manual summary send.

    customer_grouped mode requires analysis_run_id.
    flat mode uses start_time/end_time.
    """
    config = db.get(SummaryConfig, config_id)
    if config is None:
        raise NotFoundError("config not found")

    if not config.enabled:
        raise ConflictError("config is disabled")

    # Check permission - uses unified scope logic
    _check_config_access(current_user, config)

    if config.summary_scope_mode == SummaryScopeMode.CUSTOMER_GROUPED.value:
        if not payload.analysis_run_id:
            raise ParamError("customer_grouped mode requires analysis_run_id")

        analysis_run = db.get(AnalysisRun, payload.analysis_run_id)
        if not analysis_run:
            raise NotFoundError("analysis run not found")

        if analysis_run.config_id != config_id:
            raise ParamError("analysis run does not belong to this config")

        if analysis_run.status != AnalysisRunStatus.SUCCESS.value:
            raise ConflictError("can only send success status analysis runs")

        # Use new datetime fields
        start_dt = analysis_run.window_start
        end_dt = analysis_run.window_end

        send_record = SummarySendRecord(
            config_id=config_id,
            analysis_run_id=payload.analysis_run_id,
            status=SummarySendStatus.PENDING.value,
            window_start_date=start_dt.date(),
            window_end_date=end_dt.date(),
        )
    else:
        if not payload.start_time or not payload.end_time:
            raise ParamError("flat mode requires start_time and end_time")

        try:
            start_dt = datetime.fromisoformat(payload.start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(payload.end_time.replace("Z", "+00:00"))
        except ValueError as e:
            raise ParamError(f"invalid time format: {e}")

        send_record = SummarySendRecord(
            config_id=config_id,
            analysis_run_id=None,
            status=SummarySendStatus.PENDING.value,
            window_start_date=start_dt.date(),
            window_end_date=end_dt.date(),
        )

    db.add(send_record)
    db.commit()
    db.refresh(send_record)

    execute_summary_send(db, config, send_record, start_dt, end_dt)

    response_data = ManualSendResponse(
        send_id=send_record.id,
        status="pending",
    )
    return success(response_data.model_dump())


@sends_router.get("")
def list_summary_sends(
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
    config_id: Annotated[str | None, Query()] = None,
    status_value: Annotated[str | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """List summary send records. Operator sees only records in their scope."""
    stmt = select(SummarySendRecord)

    if config_id:
        stmt = stmt.where(SummarySendRecord.config_id == config_id)
    if status_value:
        stmt = stmt.where(SummarySendRecord.status == status_value)

    stmt = stmt.order_by(SummarySendRecord.executed_at.desc())
    all_items = list(db.scalars(stmt).all())

    # Filter by scope using unified logic
    filtered_items = []
    for item in all_items:
        config = db.get(SummaryConfig, item.config_id)
        if config and _operator_can_access_config(current_user, config):
            filtered_items.append(item)

    total = len(filtered_items)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_items = filtered_items[start:end]

    data = SummarySendListResponse(
        items=[
            SummarySendRecordResponse(
                send_id=item.id,
                config_id=item.config_id,
                analysis_run_id=item.analysis_run_id,
                subject=item.subject,
                recipient_count=item.recipient_count,
                status=item.status,
                sent_at=item.sent_at,
                error_message=item.error_message,
            ).model_dump()
            for item in paginated_items
        ],
        page=page,
        page_size=page_size,
        total=total,
    )
    return success(data.model_dump())
