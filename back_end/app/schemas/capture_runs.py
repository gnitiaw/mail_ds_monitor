"""捕获任务运行 schemas。"""

from pydantic import BaseModel, Field


class ReplayRequest(BaseModel):
    """手动补跑请求。"""

    mailbox_ids: list[str] = Field(..., min_length=1)
    lookback_minutes: int = Field(default=120, ge=1, le=1440)


class ReplayResponse(BaseModel):
    """手动补跑响应。"""

    run_id: str
    status: str
    mailbox_ids: list[str]
