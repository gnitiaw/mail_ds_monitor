from enum import StrEnum


class MailboxProtocol(StrEnum):
    IMAP = "imap"


class MailboxStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class ProcessingStatus(StrEnum):
    PENDING = "pending"
    PARSED = "parsed"
    ARCHIVED = "archived"
    FAILED = "failed"


class ExtractionStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class SummaryScheduleType(StrEnum):
    DAILY = "daily"


class SummarySendStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class SummaryMode(StrEnum):
    AI = "ai"


class EmptyResultPolicy(StrEnum):
    SKIP = "skip"
    SEND_EMPTY = "send_empty"


class TaskType(StrEnum):
    MAIL_PULL = "mail_pull"
    AI_EXTRACTION = "ai_extraction"
    SUMMARY_SEND = "summary_send"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


# === A类客户关键失败邮件捕获层试点 ===


class UserRole(StrEnum):
    """用户角色。"""
    ADMIN = "admin"
    OPERATOR = "operator"


class FailureQueueStatus(StrEnum):
    """失败邮件队列状态。"""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class CaptureRunStatus(StrEnum):
    """捕获任务运行状态。"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class RuleStatus(StrEnum):
    """规则状态。"""
    ENABLED = "enabled"
    DISABLED = "disabled"


class CustomerScopeType(StrEnum):
    """客户范围定义方式。"""
    EXPLICIT_LIST = "explicit_list"
    DOMAIN_MAPPING = "domain_mapping"


class CaptureTaskType(StrEnum):
    """捕获任务类型。"""
    POLL = "poll"
    MANUAL_REPLAY = "manual_replay"
