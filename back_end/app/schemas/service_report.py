from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserOptionResponse(BaseModel):
    id: str
    display_name: str
    role: str


class UserOptionsListResponse(BaseModel):
    items: list[UserOptionResponse]


class ServiceReportConfigCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    project_name: str = Field(min_length=1, max_length=120)
    report_type: str = Field(pattern="^(monthly|quarterly|annual)$")
    period_rule: str = Field(pattern="^(natural_month|natural_quarter|natural_year|custom)$")
    template_key: str = Field(
        pattern="^(ops_service_monthly_v1|ops_service_quarterly_v1|ops_service_annual_v1)$"
    )
    project_owner_user_id: str = Field(min_length=1, max_length=36)
    template_owner_user_id: str = Field(min_length=1, max_length=36)
    metric_owner_user_id: str = Field(min_length=1, max_length=36)
    enabled: bool = Field(default=True)
    recipient_emails: list[str] = Field(min_length=1)
    source_bindings: list[dict] = Field(min_length=4)

    @field_validator("source_bindings")
    @classmethod
    def validate_source_bindings(cls, value: list[dict]) -> list[dict]:
        required = {"inspection", "vulnerability", "worklog", "zentao_bug"}
        actual = {item.get("source_type") for item in value}
        if required - actual:
            raise ValueError("source_bindings must include inspection/vulnerability/worklog/zentao_bug")
        return value


class ServiceReportConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    config_id: str
    name: str
    project_name: str
    report_type: str
    period_rule: str
    template_key: str
    project_owner_user_id: str
    template_owner_user_id: str
    metric_owner_user_id: str
    enabled: bool
    recipient_emails: list[str]
    source_bindings: list[dict]
    created_at: datetime
    updated_at: datetime


class ServiceReportConfigListResponse(BaseModel):
    items: list[ServiceReportConfigResponse]
    page: int
    page_size: int
    total: int


class SourceResultResponse(BaseModel):
    source_type: str
    status: str
    record_count: int = 0
    valid_row_count: int = 0
    invalid_row_count: int = 0
    error_message: str | None = None


class ServiceReportSourceRunResponse(BaseModel):
    source_run_id: str
    config_id: str
    status: str
    window_start: datetime
    window_end: datetime
    included_sources: list[str]
    source_results: list[SourceResultResponse]
    created_at: datetime


class ServiceReportSourceRunCreateForm(BaseModel):
    window_start: datetime
    window_end: datetime


class SectionResponse(BaseModel):
    key: str
    title: str
    data_status: str
    blocking_reason: str | None = None
    content_markdown: str


class ExportArtifactResponse(BaseModel):
    format: str
    file_name: str
    download_url: str
    generated_at: datetime


class ServiceReportRunCreateRequest(BaseModel):
    window_start: datetime
    window_end: datetime
    source_run_id: str
    force_regenerate: bool = False


class ServiceReportRunCreateResponse(BaseModel):
    run_id: str
    config_id: str
    source_run_id: str
    status: str
    completeness_status: str
    window_start: datetime
    window_end: datetime
    report_type: str
    template_key: str
    created_at: datetime


class ServiceReportRunListItemResponse(BaseModel):
    run_id: str
    config_id: str
    config_name: str
    project_name: str
    report_type: str
    status: str
    completeness_status: str
    window_start: datetime
    window_end: datetime
    source_run_id: str
    export_formats: list[str]
    created_at: datetime
    finished_at: datetime | None = None


class ServiceReportRunListResponse(BaseModel):
    items: list[ServiceReportRunListItemResponse]
    total: int
    page: int
    page_size: int


class ServiceReportRunDetailResponse(BaseModel):
    run_id: str
    config_id: str
    config_snapshot: dict
    source_run_id: str
    status: str
    completeness_status: str
    window_start: datetime
    window_end: datetime
    source_snapshot_summary: dict
    report_payload: dict
    manual_note: str | None = None
    export_artifacts: list[ExportArtifactResponse]
    evidence_refs: list[dict]
    error_message: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class ManualNoteUpdateRequest(BaseModel):
    manual_note: str | None = Field(default=None, max_length=2000)


class ManualNoteUpdateResponse(BaseModel):
    run_id: str
    manual_note: str | None = None


class ExportRequest(BaseModel):
    format: str = Field(pattern="^(markdown|html)$")
    overwrite: bool = False


class ExportResponse(BaseModel):
    run_id: str
    format: str
    file_name: str
    download_url: str
    generated_at: datetime
