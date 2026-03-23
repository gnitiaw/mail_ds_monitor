"""失败邮件队列 schemas。"""

from datetime import datetime

from pydantic import BaseModel, Field


class MatchedSnapshot(BaseModel):
    """命中快照。"""

    matched_fields: dict | None = None
    extracted_fields: dict | None = None


class FailureQueueItem(BaseModel):
    """失败队列列表项。"""

    queue_id: str
    mailbox_id: str
    source_message_id: str | None = None
    failure_rule_key: str
    customer_name: str | None = None
    task_identifier: str | None = None
    subject: str | None = None
    sender: str | None = None
    received_at: datetime | None = None
    status: str
    first_captured_at: datetime
    last_seen_at: datetime


class FailureQueueListResponse(BaseModel):
    """失败队列列表响应。"""

    items: list[FailureQueueItem]
    page: int
    page_size: int
    total: int


class FailureQueueDetail(BaseModel):
    """失败队列详情。"""

    queue_id: str
    mailbox_id: str
    source_message_id: str | None = None
    provider_uid: str | None = None
    failure_rule_key: str
    customer_name: str | None = None
    task_identifier: str | None = None
    subject: str | None = None
    sender: str | None = None
    received_at: datetime | None = None
    status: str
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    matched_snapshot: MatchedSnapshot | None = None


class StatusUpdateRequest(BaseModel):
    """状态更新请求。"""

    status: str = Field(..., pattern="^(acknowledged|resolved)$")


class StatusUpdateResponse(BaseModel):
    """状态更新响应。"""

    queue_id: str
    status: str
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    updated_at: datetime
