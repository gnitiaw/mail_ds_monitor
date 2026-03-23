"""失败邮件识别规则 schemas。"""

from datetime import datetime

from pydantic import BaseModel, Field


class FailureRuleItem(BaseModel):
    """规则列表项。"""

    rule_id: str
    rule_name: str
    failure_rule_key: str
    status: str
    customer_scope_type: str
    mailbox_ids: list[str] | None = None
    updated_at: datetime


class FailureRuleListResponse(BaseModel):
    """规则列表响应。"""

    items: list[FailureRuleItem]
    total: int


class CustomerMatchConfig(BaseModel):
    """客户匹配配置。"""

    customers: list[str] | None = None
    domain_mapping: dict | None = None


class FailureRuleCreateRequest(BaseModel):
    """创建规则请求。"""

    rule_name: str = Field(..., min_length=1, max_length=128)
    failure_rule_key: str = Field(..., min_length=1, max_length=64)
    status: str = Field(default="enabled", pattern="^(enabled|disabled)$")
    customer_scope_type: str = Field(default="explicit_list", pattern="^(explicit_list|domain_mapping)$")
    customer_match_config: CustomerMatchConfig | None = None
    mailbox_ids: list[str] | None = None
    sender_patterns: list[str] | None = None
    subject_patterns: list[str] | None = None
    body_patterns: list[str] | None = None
    priority: int = Field(default=100, ge=0, le=1000)


class FailureRuleCreateResponse(BaseModel):
    """创建规则响应。"""

    rule_id: str
    rule_name: str
    status: str
    updated_at: datetime


class FailureRuleUpdateRequest(BaseModel):
    """更新规则请求。"""

    rule_name: str | None = Field(None, min_length=1, max_length=128)
    status: str | None = Field(None, pattern="^(enabled|disabled)$")
    customer_scope_type: str | None = Field(None, pattern="^(explicit_list|domain_mapping)$")
    customer_match_config: CustomerMatchConfig | None = None
    mailbox_ids: list[str] | None = None
    sender_patterns: list[str] | None = None
    subject_patterns: list[str] | None = None
    body_patterns: list[str] | None = None
    priority: int | None = Field(None, ge=0, le=1000)


class FailureRuleUpdateResponse(BaseModel):
    """更新规则响应。"""

    rule_id: str
    status: str
    updated_at: datetime
