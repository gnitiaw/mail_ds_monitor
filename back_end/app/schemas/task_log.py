"""Task log schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class TaskLogAcceptedResponse(BaseModel):
    """Accepted async task response."""

    job_id: str = Field(description="后台任务 ID")
    status: str = Field(description="任务当前状态")
    reused_existing_job: bool = Field(description="是否复用了已有进行中的任务")
    requested_count: int = Field(description="本次请求涉及的消息数量")
    max_retries: int = Field(description="最大允许重试次数")


class TaskLogDetailResponse(BaseModel):
    """Task log detail response."""

    job_id: str
    task_type: str
    status: str
    task_key: str | None
    related_mailbox_id: str | None
    related_message_id: str | None
    payload: dict | None
    result: dict | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    executed_at: datetime
