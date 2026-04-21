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


# === 发件人管理与客户问题归类分析 ===


class SenderMatchType(StrEnum):
    """发件人匹配类型。"""
    EXACT_EMAIL = "exact_email"
    EMAIL_DOMAIN = "email_domain"


class SenderType(StrEnum):
    """发件人类型。"""
    CUSTOMER = "customer"
    VENDOR = "vendor"
    INTERNAL = "internal"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class SenderProfileStatus(StrEnum):
    """发件人配置状态。"""
    ENABLED = "enabled"
    DISABLED = "disabled"


class SenderIdentificationStatus(StrEnum):
    """发件人识别状态。"""
    IDENTIFIED = "identified"
    UNIDENTIFIED = "unidentified"


class SummaryScopeMode(StrEnum):
    """汇总范围模式。"""
    FLAT = "flat"
    CUSTOMER_GROUPED = "customer_grouped"


class CustomerAnalysisMode(StrEnum):
    """客户分析模式。"""
    BASIC = "basic"
    AI = "ai"


class AnalysisRunStatus(StrEnum):
    """分析运行状态。"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"


class ReportType(StrEnum):
    """服务报告类型。"""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class PeriodRule(StrEnum):
    """报告周期规则。"""

    NATURAL_MONTH = "natural_month"
    NATURAL_QUARTER = "natural_quarter"
    NATURAL_YEAR = "natural_year"
    CUSTOM = "custom"


class SourceType(StrEnum):
    """服务报告数据源类型。"""

    INSPECTION = "inspection"
    VULNERABILITY = "vulnerability"
    WORKLOG = "worklog"
    ZENTAO_BUG = "zentao_bug"


class SourceIngestMode(StrEnum):
    """数据源接入模式。"""

    API_PULL = "api_pull"
    FILE_IMPORT = "file_import"
    MANUAL_ENTRY = "manual_entry"


class SourceRunStatus(StrEnum):
    """数据汇总执行状态。"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class ReportRunStatus(StrEnum):
    """报告生成执行状态。"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"


class CompletenessStatus(StrEnum):
    """报告可交付状态。"""

    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class SectionDataStatus(StrEnum):
    """章节数据状态。"""

    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"
