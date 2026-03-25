"""分析运行相关路由。"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import check_mailbox_scope, db_session, operator_or_admin
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ParamError
from app.models.analysis_run import AnalysisRun
from app.models.enums import AnalysisRunStatus
from app.models.summary import SummaryConfig
from app.schemas.analysis_run import (
    AnalysisRunCreateRequest,
    AnalysisRunCreateResponse,
    AnalysisRunDetailResponse,
    AnalysisRunListResponse,
    AnalysisRunSummaryResponse,
    ConfigSnapshotResponse,
    ResultPayloadResponse,
)
from app.schemas.common import success
from app.services.customer_analysis_service import (
    create_analysis_run,
    start_analysis_background,
)
from app.models.user import User

router = APIRouter(prefix="/analysis-runs")


@router.post("/by-config/{config_id}", status_code=status.HTTP_201_CREATED)
def create_for_config(
    config_id: str,
    payload: AnalysisRunCreateRequest,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
) -> dict[str, Any]:
    """创建配置作用域分析运行。

    admin 和 operator 都可以触发。
    operator 只能访问其 mailbox_scope_ids 范围内的配置。
    """
    config = db.get(SummaryConfig, config_id)
    if not config:
        raise NotFoundError("汇总配置不存在")

    if not config.enabled:
        raise ConflictError("汇总配置已禁用")

    # 检查邮箱范围权限
    check_mailbox_scope(current_user, config.mailbox_ids)

    try:
        run, reused = create_analysis_run(
            db=db,
            config=config,
            window_start=payload.window_start,
            window_end=payload.window_end,
            force_rerun=payload.force_rerun or False,
        )

        # 如果是新创建的运行，启动后台任务
        if not reused:
            start_analysis_background(db, run, config)

    except ValueError as e:
        raise ConflictError(str(e))

    data = AnalysisRunCreateResponse(
        run_id=run.id,
        status=run.status,
        reused_existing_run=reused,
    )
    return success(data.model_dump())


@router.get("/by-config/{config_id}")
def list_for_config(
    config_id: str,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
    status_value: Annotated[str | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """获取配置作用域分析运行列表。

    admin 和 operator 都可以访问。
    operator 只能访问其 mailbox_scope_ids 范围内的配置。
    """
    config = db.get(SummaryConfig, config_id)
    if not config:
        raise NotFoundError("汇总配置不存在")

    # 检查邮箱范围权限
    check_mailbox_scope(current_user, config.mailbox_ids)

    # 验证状态参数
    if status_value and status_value not in (
        "pending", "running", "success", "failed", "canceled"
    ):
        raise ParamError("无效的状态值")

    # 构建查询
    stmt = select(AnalysisRun).where(AnalysisRun.config_id == config_id)

    if status_value:
        stmt = stmt.where(AnalysisRun.status == status_value)

    # 统计总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(db.scalar(count_stmt) or 0)

    # 排序分页
    stmt = stmt.order_by(AnalysisRun.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    runs = list(db.scalars(stmt).all())

    items = []
    for run in runs:
        items.append(AnalysisRunSummaryResponse(
            run_id=run.id,
            config_id=run.config_id,
            status=run.status,
            window_start=run.window_start,
            window_end=run.window_end,
            summary_scope_mode=run.config_snapshot.get("summary_scope_mode", "flat"),
            customer_analysis_mode=run.config_snapshot.get("customer_analysis_mode", "basic"),
            ai_fallback_used=run.degraded,
            created_at=run.created_at,
            finished_at=run.finished_at,
            error_message=run.error_message,
        ))

    data = AnalysisRunListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
    return success(data.model_dump())


@router.get("/{run_id}")
def get_run(
    run_id: str,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
) -> dict[str, Any]:
    """获取分析运行详情。

    admin 和 operator 都可以访问。
    operator 只能访问其 mailbox_scope_ids 范围内的配置产生的运行。
    """
    run = db.get(AnalysisRun, run_id)
    if not run:
        raise NotFoundError("分析运行不存在")

    # 通过配置检查邮箱范围权限
    config = db.get(SummaryConfig, run.config_id)
    if config:
        check_mailbox_scope(current_user, config.mailbox_ids)

    # 构建配置快照响应
    config_snapshot = ConfigSnapshotResponse(
        summary_scope_mode=run.config_snapshot.get("summary_scope_mode", "flat"),
        mailbox_ids=run.config_snapshot.get("mailbox_ids"),
        include_statuses=run.config_snapshot.get("include_statuses"),
        include_unidentified_senders=run.config_snapshot.get("include_unidentified_senders", True),
        top_n_per_customer=run.config_snapshot.get("top_n_per_customer", 5),
        customer_analysis_mode=run.config_snapshot.get("customer_analysis_mode", "basic"),
    )

    # 构建结果负载响应
    result_payload = None
    if run.result_payload:
        result_payload = ResultPayloadResponse(**run.result_payload)

    data = AnalysisRunDetailResponse(
        run_id=run.id,
        config_id=run.config_id,
        status=run.status,
        window_start=run.window_start,
        window_end=run.window_end,
        config_snapshot=config_snapshot,
        result_payload=result_payload,
        error_message=run.error_message,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )
    return success(data.model_dump())


# 注册到 summary-configs 的嵌套路由
summary_configs_router = APIRouter()


@summary_configs_router.post("/{config_id}/analysis-runs", status_code=status.HTTP_201_CREATED)
def create_analysis_run_for_config(
    config_id: str,
    payload: AnalysisRunCreateRequest,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
) -> dict[str, Any]:
    """创建配置作用域分析运行。

    路由别名，指向 /analysis-runs/by-config/{config_id}
    """
    return create_for_config(config_id, payload, db, current_user)


@summary_configs_router.get("/{config_id}/analysis-runs")
def list_analysis_runs_for_config(
    config_id: str,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
    status_value: Annotated[str | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """获取配置作用域分析运行列表。

    路由别名，指向 /analysis-runs/by-config/{config_id}
    """
    return list_for_config(config_id, db, current_user, status_value, page, page_size)
