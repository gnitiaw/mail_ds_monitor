"""分析运行相关 Schema。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConfigSnapshotResponse(BaseModel):
    """配置快照响应。"""

    summary_scope_mode: str
    mailbox_ids: list[str] | None
    include_statuses: list[str] | None
    include_unidentified_senders: bool
    top_n_per_customer: int
    customer_analysis_mode: str


class IssueCategoryResponse(BaseModel):
    """问题分类响应。"""

    category: str = Field(description="问题类别")
    count: int = Field(description="该类别下的记录数")
    sample_subjects: list[str] = Field(description="样例邮件主题")


class TopRecordResponse(BaseModel):
    """样例记录响应。"""

    archive_id: str
    message_id: str
    sender_email: str | None
    subject: str | None
    summary: str | None
    priority: str | None
    risk_tags: list[str] | None
    received_at: datetime | None


class CustomerAnalysisResultResponse(BaseModel):
    """客户分析结果响应。"""

    customer_name: str
    sender_count: int = Field(description="该客户下的发件人数量")
    record_count: int = Field(description="该客户下的记录数量")
    high_priority_count: int = Field(description="高优先级记录数量")
    issue_categories: list[IssueCategoryResponse] = Field(description="问题分类列表")
    top_records: list[TopRecordResponse] = Field(description="样例记录")


class UnidentifiedSenderResponse(BaseModel):
    """未识别发件人响应。"""

    sender_email: str | None
    record_count: int
    sample_subjects: list[str]


class UnidentifiedGroupResponse(BaseModel):
    """未识别发件人分组响应。"""

    record_count: int
    senders: list[UnidentifiedSenderResponse]


class OverviewResponse(BaseModel):
    """分析概览响应。"""

    total_records: int
    matched_customer_count: int
    unidentified_record_count: int
    failed_record_count: int
    archived_record_count: int
    ai_fallback_used: bool = Field(description="是否触发 AI 降级")


class ResultPayloadResponse(BaseModel):
    """分析结果负载响应。"""

    overview: OverviewResponse
    customers: list[CustomerAnalysisResultResponse]
    unidentified: UnidentifiedGroupResponse
    summary_markdown: str = Field(description="Markdown 格式的摘要")


class AnalysisRunCreateRequest(BaseModel):
    """创建分析运行请求。"""

    window_start: datetime = Field(description="分析窗口开始时间")
    window_end: datetime = Field(description="分析窗口结束时间")
    force_rerun: bool | None = Field(
        default=False,
        description="true 时允许跳过活动 run 复用策略，新建新一轮分析",
    )


class AnalysisRunCreateResponse(BaseModel):
    """创建分析运行响应。"""

    run_id: str
    status: str
    reused_existing_run: bool = Field(
        description="true 表示命中幂等键，直接复用已有活动 run",
    )


class AnalysisRunSummaryResponse(BaseModel):
    """分析运行摘要响应（列表用）。"""

    model_config = ConfigDict(from_attributes=True)

    run_id: str = Field(description="分析运行 ID")
    config_id: str
    status: str
    window_start: datetime = Field(description="分析窗口开始时间")
    window_end: datetime = Field(description="分析窗口结束时间")
    summary_scope_mode: str
    customer_analysis_mode: str
    ai_fallback_used: bool = Field(
        default=False,
        description="是否触发 AI 降级",
    )
    created_at: datetime
    finished_at: datetime | None
    error_message: str | None


class AnalysisRunListResponse(BaseModel):
    """分析运行列表响应。"""

    items: list[AnalysisRunSummaryResponse]
    total: int
    page: int
    page_size: int


class AnalysisRunDetailResponse(BaseModel):
    """分析运行详情响应。"""

    model_config = ConfigDict(from_attributes=True)

    run_id: str
    config_id: str
    status: str
    window_start: datetime
    window_end: datetime
    config_snapshot: ConfigSnapshotResponse
    result_payload: ResultPayloadResponse | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
