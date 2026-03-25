"""汇总邮件配置相关 Schema。"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SummaryConfigCreateRequest(BaseModel):
    """创建汇总邮件配置请求。"""

    name: str = Field(min_length=1, max_length=120)
    enabled: bool = Field(default=True)
    schedule_type: str = Field(default="daily", pattern="^daily$")
    recipient_emails: list[str] = Field(min_length=1, description="收件人邮箱列表")
    mailbox_ids: list[str] | None = Field(default=None, description="汇总邮箱范围，空表示全部")
    include_statuses: list[str] | None = Field(default=None, description="包含的归档状态")
    send_time: str = Field(default="09:00", pattern="^[0-2][0-9]:[0-5][0-9]$")
    summary_mode: str = Field(default="ai", pattern="^ai$")
    empty_result_policy: str = Field(default="skip", pattern="^(skip|send_empty)$")
    # 客户归类摘要扩展字段
    summary_scope_mode: str = Field(
        default="flat",
        pattern="^(flat|customer_grouped)$",
        description="汇总范围模式: flat=普通汇总, customer_grouped=按客户归类",
    )
    include_unidentified_senders: bool = Field(
        default=True,
        description="customer_grouped 模式下是否纳入未识别发件人分组",
    )
    top_n_per_customer: int = Field(
        default=5,
        ge=1,
        le=50,
        description="每个客户在摘要中展示的样例邮件数量上限",
    )
    customer_analysis_mode: str = Field(
        default="basic",
        pattern="^(basic|ai)$",
        description="客户分析模式: basic=规则汇总, ai=AI 摘要增强",
    )


class SummaryConfigResponse(BaseModel):
    """汇总配置响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    enabled: bool
    schedule_type: str
    recipient_emails: list[str]
    mailbox_ids: list[str] | None
    send_time: str
    summary_scope_mode: str
    include_unidentified_senders: bool
    top_n_per_customer: int
    customer_analysis_mode: str


class SummaryConfigListResponse(BaseModel):
    """汇总配置列表响应。"""

    items: list[SummaryConfigResponse]
    total: int


class ManualSendRequest(BaseModel):
    """手动发送汇总邮件请求。"""

    analysis_run_id: str | None = Field(
        default=None,
        description="customer_grouped 模式下必填，引用 success 状态的分析运行",
    )
    start_time: str | None = Field(
        default=None,
        description="仅旧 flat 模式兼容路径可用，汇总统计开始时间 ISO8601",
    )
    end_time: str | None = Field(
        default=None,
        description="仅旧 flat 模式兼容路径可用，汇总统计结束时间 ISO8601",
    )


class ManualSendResponse(BaseModel):
    """手动发送响应。"""

    send_id: str = Field(description="发送任务 ID")
    status: str = Field(description="发送状态")


class SummarySendRecordResponse(BaseModel):
    """汇总发送记录响应。"""

    model_config = ConfigDict(from_attributes=True)

    send_id: str = Field(description="发送记录 ID")
    config_id: str
    analysis_run_id: str | None = Field(
        default=None,
        description="若本次发送来自 customer_grouped 模式，则指向使用的分析运行",
    )
    subject: str | None
    recipient_count: int
    status: str
    sent_at: datetime | None
    error_message: str | None


class SummarySendListResponse(BaseModel):
    """汇总发送记录列表响应。"""

    items: list[SummarySendRecordResponse]
    page: int
    page_size: int
    total: int
