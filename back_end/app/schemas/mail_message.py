"""邮件拉取相关 Schema。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.services.extraction_retry_service import MAX_EXTRACTION_RETRIES


class MailPullRequest(BaseModel):
    """手动触发拉取请求。"""
    force_full_sync: bool = Field(default=False, description="是否强制全量同步")


class MailPullResponse(BaseModel):
    """拉取任务响应"""
    job_id: str = Field(description="拉取任务 ID")
    mailbox_id: str = Field(description="邮箱配置 ID")
    status: str = Field(description="任务状态")


class MailMessageResponse(BaseModel):
    """邮件消息响应（用于归档列表）"""
    model_config = ConfigDict(from_attributes=True)

    archive_id: str = Field(description="归档记录 ID")
    mailbox_id: str
    message_id: str = Field(description="邮件唯一标识")
    subject: str | None
    sender: str | None = Field(description="发件人邮箱")
    received_at: datetime | None
    status: str = Field(description="归档状态")
    tags: list[str] | None = Field(description="规则命中标签")
    summary: str | None = Field(description="AI 生成的摘要")
    extraction_status: str = Field(description="AI 提取状态")
    confidence: float | None = Field(description="AI 提取置信度")


class ArchiveListResponse(BaseModel):
    """归档列表分页响应"""
    items: list[MailMessageResponse]
    page: int
    page_size: int
    total: int


class ArchiveDetailResponse(BaseModel):
    """归档详情响应"""
    model_config = ConfigDict(from_attributes=True)

    archive_id: str = Field(description="归档记录 ID")
    mailbox_id: str
    message_id: str = Field(description="邮件唯一标识")
    subject: str | None
    sender: str | None = Field(description="发件人邮箱")
    recipients: list[str] | None = Field(description="收件人列表")
    received_at: datetime | None
    body_text: str | None = Field(description="纯文本正文")
    body_html: str | None = Field(description="HTML 正文")
    extracted_fields: dict | None = Field(description="结构化提取结果")
    tags: list[str] | None = Field(description="规则命中标签")
    status: str = Field(description="归档状态")
    extraction_status: str = Field(description="AI 提取状态")
    confidence: float | None = Field(description="AI 提取置信度")
    model_name: str | None = Field(description="大模型名称")
    prompt_version: str | None = Field(description="Prompt 版本")
    parse_error: str | None = Field(description="解析失败原因")


class RawMailListItem(BaseModel):
    """原始邮件列表项"""
    model_config = ConfigDict(from_attributes=True)

    message_id: str = Field(description="原始邮件记录 ID")
    mailbox_id: str
    internet_message_id: str | None
    provider_uid: str | None
    folder: str
    subject: str | None
    sender: str | None = Field(description="发件人邮箱")
    received_at: datetime | None
    parse_status: str
    extraction_status: str
    parse_error: str | None = Field(description="解析错误信息")
    extraction_error: str | None = Field(description="提取错误信息")
    retry_count: int = Field(default=0, description="重试次数")
    max_retries: int = Field(default=MAX_EXTRACTION_RETRIES, description="最大允许重试次数")
    has_attachments: bool
    pulled_at: datetime


class RawMailListResponse(BaseModel):
    """原始邮件列表分页响应"""
    items: list[RawMailListItem]
    page: int
    page_size: int
    total: int


class BatchRetryRequest(BaseModel):
    """批量重试请求"""
    message_ids: list[str] = Field(..., min_length=1, max_length=50, description="消息 ID 列表")


class RawMailDetailResponse(BaseModel):
    """原始邮件详情响应"""
    model_config = ConfigDict(from_attributes=True)

    message_id: str
    mailbox_id: str
    internet_message_id: str | None
    provider_uid: str | None
    folder: str
    subject: str | None
    sender_name: str | None
    sender_email: str | None
    recipients_to: list[str] | None
    recipients_cc: list[str] | None
    recipients_bcc: list[str] | None
    reply_to: list[str] | None
    flags: list[str] | None
    has_attachments: bool
    parse_status: str
    extraction_status: str
    parse_error: str | None
    extraction_error: str | None
    retry_count: int = Field(default=0, description="重试次数")
    max_retries: int = Field(default=MAX_EXTRACTION_RETRIES, description="最大允许重试次数")
    last_retry_at: datetime | None
    received_at: datetime | None
    pulled_at: datetime
    body_text: str | None
    body_html: str | None
