"""发件人配置相关 Schema。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SenderProfileCreateRequest(BaseModel):
    """创建发件人档案请求。"""

    match_type: str = Field(
        pattern="^(exact_email|email_domain)$",
        description="匹配类型: exact_email=精确邮箱, email_domain=域名匹配",
    )
    match_value: str = Field(
        min_length=1,
        max_length=255,
        description="匹配值: exact_email 时是邮箱地址, email_domain 时是域名",
    )
    customer_name: str = Field(
        min_length=1,
        max_length=128,
        description="客户名称",
    )
    customer_code: str | None = Field(
        default=None,
        max_length=64,
        description="客户编码（可选）",
    )
    sender_label: str | None = Field(
        default=None,
        max_length=128,
        description="发件人标签，业务上给该发件人归类的展示名称",
    )
    sender_type: str = Field(
        default="unknown",
        pattern="^(customer|vendor|internal|system|unknown)$",
        description="发件人类型",
    )
    status: str = Field(
        default="enabled",
        pattern="^(enabled|disabled)$",
        description="状态: disabled 后不再参与客户归类匹配",
    )
    notes: str | None = Field(
        default=None,
        description="备注",
    )


class SenderProfileUpdateRequest(BaseModel):
    """更新发件人档案请求。"""

    customer_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
    )
    customer_code: str | None = Field(
        default=None,
        max_length=64,
    )
    sender_label: str | None = Field(
        default=None,
        max_length=128,
    )
    sender_type: str | None = Field(
        default=None,
        pattern="^(customer|vendor|internal|system|unknown)$",
    )
    status: str | None = Field(
        default=None,
        pattern="^(enabled|disabled)$",
    )
    notes: str | None = Field(
        default=None,
    )


class SenderProfileResponse(BaseModel):
    """发件人档案响应。"""

    model_config = ConfigDict(from_attributes=True)

    profile_id: str = Field(description="发件人档案 ID")
    match_type: str
    match_value: str
    customer_name: str
    customer_code: str | None
    sender_label: str | None
    sender_type: str
    status: str
    notes: str | None
    last_seen_at: datetime | None = Field(
        default=None,
        description="最近一次匹配到的时间",
    )
    linked_message_count: int = Field(
        default=0,
        description="当前档案命中的历史邮件数量",
    )
    created_at: datetime
    updated_at: datetime


class SenderProfileListResponse(BaseModel):
    """发件人档案列表响应。"""

    items: list[SenderProfileResponse]
    total: int
    page: int
    page_size: int


class SenderCandidateResponse(BaseModel):
    """候选发件人响应。"""

    sender_email: str = Field(description="发件人邮箱，作为候选发件人主标识")
    sender_name_sample: str | None = Field(
        default=None,
        description="最近一次解析到的发件人名称样例",
    )
    email_domain: str | None = Field(
        default=None,
        description="发件人邮箱域名",
    )
    message_count: int = Field(description="时间窗口内原始邮件数量")
    archive_count: int = Field(description="时间窗口内已进入归档的数据数量")
    last_seen_at: datetime | None = Field(
        default=None,
        description="最近出现时间",
    )
    latest_subject: str | None = Field(
        default=None,
        description="最近一封邮件的主题",
    )
    identified_profile_id: str | None = Field(
        default=None,
        description="若已建档，则返回对应发件人档案 ID",
    )
    identified_status: str = Field(
        description="识别状态: identified=已建档, unidentified=未建档",
    )
    customer_name: str | None = Field(
        default=None,
        description="若已建档，则返回对应的客户名称",
    )


class SenderCandidateListResponse(BaseModel):
    """候选发件人列表响应。"""

    items: list[SenderCandidateResponse]
    total: int
    page: int
    page_size: int
