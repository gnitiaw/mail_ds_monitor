from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MailboxBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(gt=0, le=65535)
    username: str = Field(min_length=1, max_length=255)
    folder: str = Field(default="INBOX", min_length=1, max_length=255)
    status: str = Field(default="enabled", pattern="^(enabled|disabled)$")


class MailboxCreateRequest(MailboxBase):
    """创建邮箱配置请求体，字段对齐契约。"""

    password: str = Field(min_length=1, max_length=512, description="邮箱密码，服务端加密存储")


class MailboxUpdateRequest(BaseModel):
    """更新邮箱配置请求体，字段对齐契约。"""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, gt=0, le=65535)
    password: str | None = Field(default=None, min_length=1, max_length=512, description="邮箱密码，服务端加密存储")
    folder: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, pattern="^(enabled|disabled)$")


class MailboxResponse(BaseModel):
    """邮箱配置响应，字段对齐契约。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    protocol: str
    host: str
    port: int
    username: str
    status: str
    created_at: datetime
    updated_at: datetime


class MailboxListResponse(BaseModel):
    """邮箱列表分页响应。"""

    items: list[MailboxResponse]
    page: int
    page_size: int
    total: int


class MailboxProcessRequest(BaseModel):
    """邮箱已拉取邮件处理请求。"""

    lookback_minutes: int = Field(default=1440, ge=1, le=10080)
    limit: int = Field(default=50, ge=1, le=500)


class MailboxProcessResponse(BaseModel):
    """邮箱已拉取邮件处理响应。"""

    mailbox_id: str
    archive_success_count: int
    archive_failed_count: int
    archive_skipped_count: int
    failure_scanned_count: int
    failure_matched_count: int
    failure_deduped_count: int
