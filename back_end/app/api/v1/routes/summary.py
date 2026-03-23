"""汇总配置相关路由。"""

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.exceptions import ConflictError, NotFoundError, ParamError
from app.models.enums import SummarySendStatus
from app.models.summary import SummaryConfig, SummarySendRecord
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


@router.get("")
def list_summary_configs(
    db: Annotated[Session, Depends(db_session)],
) -> dict[str, Any]:
    """获取汇总邮件配置列表。"""
    stmt = select(SummaryConfig).order_by(SummaryConfig.created_at.desc())
    items = list(db.scalars(stmt).all())

    data = SummaryConfigListResponse(
        items=[SummaryConfigResponse.model_validate(item) for item in items],
        total=len(items),
    )
    return success(data.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED)
def create_summary_config(
    payload: SummaryConfigCreateRequest,
    db: Annotated[Session, Depends(db_session)],
) -> dict[str, Any]:
    """创建汇总邮件配置。"""
    # 检查同名配置
    existing = db.scalar(select(SummaryConfig).where(SummaryConfig.name == payload.name))
    if existing:
        raise ConflictError("汇总配置名称已存在")

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
) -> dict[str, Any]:
    """手动发送汇总邮件。

    按契约要求，始终返回 pending 状态。
    实际执行结果通过发送记录查询。
    """
    config = db.get(SummaryConfig, config_id)
    if config is None:
        raise NotFoundError("汇总配置不存在")

    if not config.enabled:
        raise ConflictError("汇总配置已禁用")

    # 解析时间范围
    try:
        start_dt = datetime.fromisoformat(payload.start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(payload.end_time.replace("Z", "+00:00"))
    except ValueError as e:
        raise ParamError(f"时间格式错误: {e}")

    # 创建发送记录
    send_record = SummarySendRecord(
        config_id=config_id,
        status=SummarySendStatus.PENDING.value,
        window_start_date=start_dt.date(),
        window_end_date=end_dt.date(),
    )
    db.add(send_record)
    db.commit()
    db.refresh(send_record)

    # 执行发送（同步执行，后续可改为异步任务）
    # 注意：执行结果通过 send_record.status 和 error_message 记录
    # 接口始终返回 pending，符合契约要求
    execute_summary_send(db, config, send_record, start_dt, end_dt)

    response_data = ManualSendResponse(
        send_id=send_record.id,
        status="pending",  # 按契约要求始终返回 pending
    )
    return success(response_data.model_dump())


# 发送记录路由
sends_router = APIRouter(prefix="/summary-sends")


@sends_router.get("")
def list_summary_sends(
    db: Annotated[Session, Depends(db_session)],
    config_id: Annotated[str | None, Query()] = None,
    status_value: Annotated[str | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """查询汇总邮件发送记录。"""
    stmt = select(SummarySendRecord)

    if config_id:
        stmt = stmt.where(SummarySendRecord.config_id == config_id)
    if status_value:
        stmt = stmt.where(SummarySendRecord.status == status_value)

    # 统计总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(db.scalar(count_stmt) or 0)

    # 排序分页
    stmt = stmt.order_by(SummarySendRecord.executed_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt).all())

    data = SummarySendListResponse(
        items=[
            SummarySendRecordResponse(
                send_id=item.id,
                config_id=item.config_id,
                subject=item.subject,
                recipient_count=item.recipient_count,
                status=item.status,
                sent_at=item.sent_at,
                error_message=item.error_message,
            ).model_dump()
            for item in items
        ],
        page=page,
        page_size=page_size,
        total=total,
    )
    return success(data.model_dump())
