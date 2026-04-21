from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import admin_required, db_session, operator_or_admin
from app.core.exceptions import ConflictError, NotFoundError, ParamError
from app.models.enums import ReportRunStatus, SourceRunStatus
from app.models.service_report import ServiceReportConfig, ServiceReportRun, ServiceReportSourceRun
from app.models.user import User
from app.schemas.common import success
from app.schemas.service_report import (
    ExportArtifactResponse,
    ExportRequest,
    ExportResponse,
    ManualNoteUpdateRequest,
    ManualNoteUpdateResponse,
    SectionResponse,
    ServiceReportConfigCreateRequest,
    ServiceReportConfigListResponse,
    ServiceReportConfigResponse,
    ServiceReportRunCreateRequest,
    ServiceReportRunCreateResponse,
    ServiceReportRunDetailResponse,
    ServiceReportRunListItemResponse,
    ServiceReportRunListResponse,
    ServiceReportSourceRunCreateForm,
    ServiceReportSourceRunResponse,
    SourceResultResponse,
)
from app.services.service_report_service import ServiceReportService

configs_router = APIRouter(prefix="/service-report-configs")
runs_router = APIRouter(prefix="/service-report-runs")


def _get_config(db: Session, config_id: str) -> ServiceReportConfig:
    config = db.get(ServiceReportConfig, config_id)
    if config is None:
        raise NotFoundError("service report config not found")
    return config


def _get_source_run(db: Session, source_run_id: str) -> ServiceReportSourceRun:
    source_run = db.get(ServiceReportSourceRun, source_run_id)
    if source_run is None:
        raise NotFoundError("service report source run not found")
    return source_run


def _get_report_run(db: Session, run_id: str) -> ServiceReportRun:
    run = db.get(ServiceReportRun, run_id)
    if run is None:
        raise NotFoundError("service report run not found")
    return run


def _config_response(config: ServiceReportConfig) -> ServiceReportConfigResponse:
    return ServiceReportConfigResponse(
        config_id=config.id,
        name=config.name,
        project_name=config.project_name,
        report_type=config.report_type,
        period_rule=config.period_rule,
        template_key=config.template_key,
        project_owner_user_id=config.project_owner_user_id,
        template_owner_user_id=config.template_owner_user_id,
        metric_owner_user_id=config.metric_owner_user_id,
        enabled=config.enabled,
        recipient_emails=config.recipient_emails,
        source_bindings=config.source_bindings,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


def _source_run_response(source_run: ServiceReportSourceRun) -> ServiceReportSourceRunResponse:
    return ServiceReportSourceRunResponse(
        source_run_id=source_run.id,
        config_id=source_run.config_id,
        status=source_run.status,
        window_start=source_run.window_start,
        window_end=source_run.window_end,
        included_sources=source_run.included_sources,
        source_results=[
            SourceResultResponse.model_validate(item)
            for item in (source_run.source_results or [])
        ],
        created_at=source_run.created_at,
    )


def _run_create_response(run: ServiceReportRun) -> ServiceReportRunCreateResponse:
    config_snapshot = run.config_snapshot or {}
    return ServiceReportRunCreateResponse(
        run_id=run.id,
        config_id=run.config_id,
        source_run_id=run.source_run_id,
        status=run.status,
        completeness_status=run.completeness_status,
        window_start=run.window_start,
        window_end=run.window_end,
        report_type=config_snapshot.get("report_type", ""),
        template_key=config_snapshot.get("template_key", ""),
        created_at=run.created_at,
    )


def _run_detail_response(run: ServiceReportRun) -> ServiceReportRunDetailResponse:
    return ServiceReportRunDetailResponse(
        run_id=run.id,
        config_id=run.config_id,
        config_snapshot=run.config_snapshot,
        source_run_id=run.source_run_id,
        status=run.status,
        completeness_status=run.completeness_status,
        window_start=run.window_start,
        window_end=run.window_end,
        source_snapshot_summary=run.source_snapshot_summary,
        report_payload={
            "summary_markdown": (run.report_payload or {}).get("summary_markdown", ""),
            "sections": [
                SectionResponse.model_validate(item).model_dump()
                for item in (run.report_payload or {}).get("sections", [])
            ],
        },
        manual_note=run.manual_note,
        export_artifacts=[
            ExportArtifactResponse.model_validate(item)
            for item in (run.export_artifacts or [])
        ],
        evidence_refs=run.evidence_refs or [],
        error_message=run.error_message,
        created_at=run.created_at,
        finished_at=run.finished_at,
    )


@configs_router.get("")
def list_service_report_configs(
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
    report_type: Annotated[str | None, Query()] = None,
    enabled: Annotated[bool | None, Query()] = None,
    keyword: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    items, total = ServiceReportService.list_configs(db, report_type, enabled, keyword, page, page_size)
    data = ServiceReportConfigListResponse(
        items=[_config_response(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )
    return success(data.model_dump())


@configs_router.post("", status_code=status.HTTP_201_CREATED)
def create_service_report_config(
    payload: ServiceReportConfigCreateRequest,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(admin_required)],
) -> dict[str, Any]:
    config = ServiceReportService.create_config(db, payload)
    return success(_config_response(config).model_dump())


@configs_router.post("/{config_id}/source-runs", status_code=status.HTTP_201_CREATED)
async def create_service_report_source_run(
    config_id: str,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
    window_start: Annotated[str, Form()],
    window_end: Annotated[str, Form()],
    inspection_file: Annotated[UploadFile | None, File()] = None,
    vulnerability_file: Annotated[UploadFile | None, File()] = None,
    worklog_file: Annotated[UploadFile | None, File()] = None,
    zentao_bug_file: Annotated[UploadFile | None, File()] = None,
) -> dict[str, Any]:
    config = _get_config(db, config_id)
    if not config.enabled:
        raise ConflictError("service report config is disabled")

    try:
        parsed_form = ServiceReportSourceRunCreateForm.model_validate(
            {"window_start": window_start, "window_end": window_end}
        )
    except ValidationError as exc:
        raise ParamError(f"invalid datetime format: {exc}") from exc

    source_run = await ServiceReportService.create_source_run(
        db=db,
        config=config,
        window_start=parsed_form.window_start,
        window_end=parsed_form.window_end,
        files={
            "inspection": inspection_file,
            "vulnerability": vulnerability_file,
            "worklog": worklog_file,
            "zentao_bug": zentao_bug_file,
        },
    )
    return success(_source_run_response(source_run).model_dump())


@configs_router.post("/{config_id}/report-runs", status_code=status.HTTP_201_CREATED)
def create_service_report_run(
    config_id: str,
    payload: ServiceReportRunCreateRequest,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
) -> dict[str, Any]:
    config = _get_config(db, config_id)
    if not config.enabled:
        raise ConflictError("service report config is disabled")

    source_run = _get_source_run(db, payload.source_run_id)
    if source_run.status not in {
        SourceRunStatus.SUCCESS.value,
        SourceRunStatus.PARTIAL_SUCCESS.value,
        SourceRunStatus.FAILED.value,
    }:
        raise ConflictError("source run is not ready")

    run = ServiceReportService.create_report_run(
        db=db,
        config=config,
        source_run=source_run,
        window_start=payload.window_start,
        window_end=payload.window_end,
        force_regenerate=payload.force_regenerate,
    )
    return success(_run_create_response(run).model_dump())


@runs_router.get("")
def list_service_report_runs(
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
    config_id: Annotated[str | None, Query()] = None,
    report_type: Annotated[str | None, Query()] = None,
    status_value: Annotated[str | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    items, total = ServiceReportService.list_runs(
        db=db,
        config_id=config_id,
        report_type=report_type,
        status=status_value,
        page=page,
        page_size=page_size,
    )
    data = ServiceReportRunListResponse(
        items=[ServiceReportRunListItemResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
    return success(data.model_dump())


@runs_router.get("/{run_id}")
def get_service_report_run_detail(
    run_id: str,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
) -> dict[str, Any]:
    run = _get_report_run(db, run_id)
    return success(_run_detail_response(run).model_dump())


@runs_router.patch("/{run_id}/manual-note")
def update_service_report_manual_note(
    run_id: str,
    payload: ManualNoteUpdateRequest,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
) -> dict[str, Any]:
    run = _get_report_run(db, run_id)
    updated = ServiceReportService.update_manual_note(db, run, payload.manual_note)
    return success(
        ManualNoteUpdateResponse(
            run_id=updated.id,
            manual_note=updated.manual_note,
        ).model_dump()
    )


@runs_router.post("/{run_id}/export")
def create_service_report_export(
    run_id: str,
    payload: ExportRequest,
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
) -> dict[str, Any]:
    run = _get_report_run(db, run_id)
    artifact = ServiceReportService.register_export(
        db=db,
        run=run,
        export_format=payload.format,
        overwrite=payload.overwrite,
    )
    return success(
        ExportResponse(
            run_id=run.id,
            format=artifact["format"],
            file_name=artifact["file_name"],
            download_url=artifact["download_url"],
            generated_at=artifact["generated_at"],
        ).model_dump()
    )


@runs_router.get("/{run_id}/export")
def download_service_report_export(
    run_id: str,
    format: Annotated[str, Query(pattern="^(markdown|html)$")],
    db: Annotated[Session, Depends(db_session)],
    current_user: Annotated[User, Depends(operator_or_admin)],
) -> Response:
    run = _get_report_run(db, run_id)
    if run.status != ReportRunStatus.SUCCESS.value:
        raise ConflictError("current report is not ready to export")

    artifacts = run.export_artifacts or []
    artifact = next((item for item in artifacts if item["format"] == format), None)
    if artifact is None:
        raise NotFoundError("export artifact not found, create export first")

    content = ServiceReportService.render_export(run, format)
    headers = {"Content-Disposition": f'attachment; filename="{artifact["file_name"]}"'}
    if format == "markdown":
        return PlainTextResponse(content=content, headers=headers)
    return HTMLResponse(content=content, headers=headers)
