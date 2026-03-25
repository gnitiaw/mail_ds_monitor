"""汇总邮件发送服务。"""

import logging
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis_run import AnalysisRun
from app.models.archive import ArchiveRecord
from app.models.enums import SummaryScopeMode, SummarySendStatus
from app.models.summary import SummaryConfig, SummarySendRecord
from app.services.llm_service import LLMClientSync, LLMError
from app.services.smtp_service import send_summary_email, SMTPError

logger = logging.getLogger(__name__)


def execute_summary_send(
    db: Session,
    config: SummaryConfig,
    send_record: SummarySendRecord,
    start_time: datetime,
    end_time: datetime,
) -> None:
    """执行汇总邮件发送。

    Args:
        db: 数据库会话
        config: 汇总配置
        send_record: 发送记录
        start_time: 统计开始时间
        end_time: 统计结束时间
    """
    try:
        # customer_grouped 模式：直接复用 analysis_run 结果
        if config.summary_scope_mode == SummaryScopeMode.CUSTOMER_GROUPED.value:
            if send_record.analysis_run_id:
                analysis_run = db.get(AnalysisRun, send_record.analysis_run_id)
                if analysis_run and analysis_run.result_payload:
                    summary_content = analysis_run.result_payload.get("summary_markdown", "")
                    if not summary_content:
                        # 如果没有 markdown，用基础格式化
                        summary_content = _format_result_payload(analysis_run.result_payload)

                    date_str = start_time.strftime("%Y-%m-%d")
                    subject = f"[邮件监控] {config.name} - {date_str} 客户问题归类汇总"

                    result = send_summary_email(
                        to_emails=config.recipient_emails,
                        subject=subject,
                        summary_content=summary_content,
                    )

                    send_record.status = SummarySendStatus.SUCCESS.value
                    send_record.subject = subject
                    send_record.recipient_emails = config.recipient_emails
                    send_record.recipient_count = result["recipient_count"]
                    send_record.summary_text = summary_content
                    send_record.sent_at = datetime.now(timezone.utc)
                    send_record.model_name = analysis_run.model_name
                    db.commit()
                    logger.info(f"customer_grouped summary sent using analysis_run {analysis_run.id}")
                    return

        # flat 模式或无 analysis_run：使用旧的基于时间窗口的逻辑
        stmt = select(ArchiveRecord).where(
            and_(
                ArchiveRecord.received_at >= start_time,
                ArchiveRecord.received_at <= end_time,
            )
        )

        # 筛选邮箱范围
        if config.mailbox_ids:
            stmt = stmt.where(ArchiveRecord.mailbox_id.in_(config.mailbox_ids))

        # 筛选状态
        if config.include_statuses:
            stmt = stmt.where(ArchiveRecord.status.in_(config.include_statuses))

        records = list(db.scalars(stmt).all())

        # 检查是否有数据
        if not records:
            if config.empty_result_policy == "skip":
                logger.info(f"No records found, skipping send for config {config.id}")
                send_record.status = SummarySendStatus.SUCCESS.value
                send_record.subject = "[邮件监控] 今日无新增邮件"
                send_record.sent_at = datetime.now(timezone.utc)
                db.commit()
                return

        # 生成汇总内容
        summary_content = _generate_summary_content(records, config)

        # 生成邮件主题
        date_str = start_time.strftime("%Y-%m-%d")
        subject = f"[邮件监控] {config.name} - {date_str} 汇总"

        # 发送邮件
        result = send_summary_email(
            to_emails=config.recipient_emails,
            subject=subject,
            summary_content=summary_content,
        )

        # 更新发送记录
        send_record.status = SummarySendStatus.SUCCESS.value
        send_record.subject = subject
        send_record.recipient_emails = config.recipient_emails
        send_record.recipient_count = result["recipient_count"]
        send_record.summary_text = summary_content
        send_record.sent_at = datetime.now(timezone.utc)
        send_record.model_name = settings.llm_model if config.summary_mode == "ai" else None
        send_record.prompt_version = settings.llm_summary_prompt_version if config.summary_mode == "ai" else None

        db.commit()
        logger.info(f"Summary email sent successfully for config {config.id}")

    except SMTPError as e:
        logger.error(f"SMTP error sending summary for config {config.id}: {e}")
        send_record.status = SummarySendStatus.FAILED.value
        send_record.error_message = str(e)
        db.commit()

    except Exception as e:
        logger.exception(f"Unexpected error sending summary for config {config.id}")
        send_record.status = SummarySendStatus.FAILED.value
        send_record.error_message = f"Unexpected error: {e}"
        db.commit()


def _format_result_payload(result_payload: dict) -> str:
    """格式化 analysis_run 结果为可读文本。"""
    lines = ["# 客户问题归类汇总", ""]

    overview = result_payload.get("overview", {})
    if overview:
        lines.extend([
            "## 概览",
            "",
            f"- 总记录数: {overview.get('total_records', 0)}",
            f"- 已识别客户数: {overview.get('matched_customer_count', 0)}",
            f"- 未识别记录数: {overview.get('unidentified_record_count', 0)}",
            "",
        ])

    customers = result_payload.get("customers", [])
    for customer in customers:
        lines.extend([
            f"## {customer.get('customer_name', '未知客户')}",
            "",
            f"- 记录数: {customer.get('record_count', 0)}",
            f"- 高优先级: {customer.get('high_priority_count', 0)}",
            "",
        ])

    lines.extend([
        "---",
        "*此摘要由系统自动生成*",
    ])

    return "\n".join(lines)


def _generate_summary_content(
    records: list[ArchiveRecord],
    config: SummaryConfig,
) -> str:
    """生成汇总邮件内容。"""
    if not records:
        return """# 邮件监控汇总

今日无新增邮件。

---
*此邮件由系统自动发送*
"""

    # 基础统计
    total_count = len(records)
    high_priority = sum(1 for r in records if r.priority == "high")
    medium_priority = sum(1 for r in records if r.priority == "medium")
    low_priority = sum(1 for r in records if r.priority == "low")

    # 使用 AI 生成汇总
    if config.summary_mode == "ai" and settings.llm_enabled:
        try:
            return _generate_ai_summary(records)
        except LLMError as e:
            logger.error(f"AI summary generation failed: {e}")
            # 降级为基础汇总

    # 基础汇总
    return _generate_basic_summary(records, total_count, high_priority, medium_priority, low_priority)


def _generate_ai_summary(records: list[ArchiveRecord]) -> str:
    """使用 AI 生成汇总内容。"""
    # 准备记录数据
    records_data = []
    for r in records:
        records_data.append({
            "subject": r.message.subject if r.message else None,
            "sender": r.message.sender_email if r.message else None,
            "summary": r.summary,
            "priority": r.priority,
            "risk_tags": r.risk_tags,
        })

    client = LLMClientSync()
    return client.generate_summary(records_data)


def _generate_basic_summary(
    records: list[ArchiveRecord],
    total_count: int,
    high_priority: int,
    medium_priority: int,
    low_priority: int,
) -> str:
    """生成基础汇总内容。"""
    lines = [
        "# 邮件监控汇总",
        "",
        "## 统计概览",
        "",
        f"- 总邮件数: {total_count}",
        f"- 高优先级: {high_priority}",
        f"- 中优先级: {medium_priority}",
        f"- 低优先级: {low_priority}",
        "",
        "## 邮件列表",
        "",
    ]

    # 按优先级排序
    sorted_records = sorted(
        records,
        key=lambda r: {"high": 0, "medium": 1, "low": 2}.get(r.priority or "low", 3),
    )

    for record in sorted_records:
        subject = record.message.subject if record.message else "(无主题)"
        sender = record.message.sender_email if record.message else "(未知发件人)"
        priority = record.priority or "low"
        summary = record.summary or "(无摘要)"

        lines.append(f"### {subject}")
        lines.append("")
        lines.append(f"- **发件人**: {sender}")
        lines.append(f"- **优先级**: {priority}")
        lines.append(f"- **摘要**: {summary}")

        if record.risk_tags:
            lines.append(f"- **风险标签**: {', '.join(record.risk_tags)}")

        lines.append("")

    lines.extend([
        "---",
        "*此邮件由系统自动发送*",
    ])

    return "\n".join(lines)
