"""客户归类分析服务。

支持两种分析模式：
- basic: 基础规则汇总
- ai: AI 摘要增强（带降级策略）
"""

import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis_run import AnalysisRun
from app.models.archive import ArchiveRecord
from app.models.enums import AnalysisRunStatus, CustomerAnalysisMode
from app.models.sender_profile import SenderProfile
from app.models.summary import SummaryConfig
from app.services.llm_service import LLMClientSync, LLMError
from app.services.sender_matching_service import match_senders_batch

logger = logging.getLogger(__name__)


def create_analysis_run(
    db: Session,
    config: SummaryConfig,
    window_start: datetime,
    window_end: datetime,
    force_rerun: bool = False,
) -> tuple[AnalysisRun, bool]:
    """创建分析运行记录。

    Args:
        db: 数据库会话
        config: 汇总配置
        window_start: 分析窗口开始时间
        window_end: 分析窗口结束时间
        force_rerun: 是否强制重新运行

    Returns:
        (分析运行记录, 是否复用现有运行)

    Raises:
        ValueError: 如果当前已有活动分析任务
    """
    # 构建配置快照
    config_snapshot = {
        "summary_scope_mode": config.summary_scope_mode,
        "mailbox_ids": config.mailbox_ids,
        "include_statuses": config.include_statuses,
        "include_unidentified_senders": config.include_unidentified_senders,
        "top_n_per_customer": config.top_n_per_customer,
        "customer_analysis_mode": config.customer_analysis_mode,
    }

    # 计算配置快照哈希
    config_snapshot_hash = _compute_config_hash(config_snapshot)

    # 检查是否有可复用的活动运行（基于完整 datetime 窗口）
    if not force_rerun:
        existing_run = db.query(AnalysisRun).filter(
            AnalysisRun.config_id == config.id,
            AnalysisRun.window_start == window_start,
            AnalysisRun.window_end == window_end,
            AnalysisRun.config_snapshot_hash == config_snapshot_hash,
            AnalysisRun.status.in_([
                AnalysisRunStatus.PENDING.value,
                AnalysisRunStatus.RUNNING.value,
            ]),
        ).first()

        if existing_run:
            logger.info(f"Reusing existing analysis run: {existing_run.id}")
            return existing_run, True

    # 检查是否有活动中的运行（防止重复）
    active_run = db.query(AnalysisRun).filter(
        AnalysisRun.config_id == config.id,
        AnalysisRun.status.in_([
            AnalysisRunStatus.PENDING.value,
            AnalysisRunStatus.RUNNING.value,
        ]),
    ).first()

    if active_run:
        raise ValueError("当前已有活动分析任务")

    # 创建新的分析运行
    run = AnalysisRun(
        config_id=config.id,
        window_start=window_start,
        window_end=window_end,
        config_snapshot=config_snapshot,
        config_snapshot_hash=config_snapshot_hash,
        status=AnalysisRunStatus.PENDING.value,
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    logger.info(f"Created analysis run: {run.id}")

    return run, False


def execute_analysis(
    db: Session,
    run: AnalysisRun,
    config: SummaryConfig,
) -> None:
    """执行分析任务。

    Args:
        db: 数据库会话
        run: 分析运行记录
        config: 汇总配置
    """
    try:
        # 更新状态为运行中
        run.status = AnalysisRunStatus.RUNNING.value
        run.started_at = datetime.now(timezone.utc)
        run.analysis_mode_used = config.customer_analysis_mode
        run.model_name = settings.llm_model if config.customer_analysis_mode == CustomerAnalysisMode.AI.value else None
        db.commit()

        # 执行分析
        result = _execute_customer_grouped_analysis(db, config, run)

        # 更新结果
        run.result_payload = result
        run.status = AnalysisRunStatus.SUCCESS.value
        run.finished_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Analysis run completed: {run.id}")

    except Exception as e:
        logger.exception(f"Analysis run failed: {run.id}")
        try:
            run.status = AnalysisRunStatus.FAILED.value
            run.error_message = str(e)
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as commit_error:
            logger.exception(f"Failed to commit failure status for run {run.id}: {commit_error}")
            try:
                db.rollback()
            except Exception:
                pass


def execute_analysis_async(
    db_url: str,
    run_id: str,
    config_id: str,
) -> None:
    """异步执行分析任务（用于后台线程）。

    Args:
        db_url: 数据库连接 URL
        run_id: 分析运行 ID
        config_id: 汇总配置 ID
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        config = db.query(SummaryConfig).filter(SummaryConfig.id == config_id).first()

        if run and config:
            execute_analysis(db, run, config)
    finally:
        db.close()


def start_analysis_background(
    db: Session,
    run: AnalysisRun,
    config: SummaryConfig,
) -> None:
    """启动后台分析任务。

    使用 APScheduler 调度，确保任务持久化和崩溃恢复。

    Args:
        db: 数据库会话
        run: 分析运行记录
        config: 汇总配置
    """
    from app.core.scheduler import add_analysis_job, init_scheduler

    # 确保调度器已启动
    init_scheduler()

    # 添加任务到调度器
    add_analysis_job(run.id, config.id)


def _execute_customer_grouped_analysis(
    db: Session,
    config: SummaryConfig,
    run: AnalysisRun,
) -> dict:
    """执行按客户归类分析。

    Args:
        db: 数据库会话
        config: 汇总配置
        run: 分析运行记录

    Returns:
        分析结果字典
    """
    # 直接使用存储的 datetime 窗口
    window_start = run.window_start
    window_end = run.window_end

    # 查询归档记录
    stmt = select(ArchiveRecord).where(
        and_(
            ArchiveRecord.received_at >= window_start,
            ArchiveRecord.received_at <= window_end,
        )
    )

    # 筛选邮箱范围
    if config.mailbox_ids:
        stmt = stmt.where(ArchiveRecord.mailbox_id.in_(config.mailbox_ids))

    # 筛选状态
    if config.include_statuses:
        stmt = stmt.where(ArchiveRecord.status.in_(config.include_statuses))

    records = list(db.scalars(stmt).all())

    # 批量匹配发件人 - sender_email 在 MailMessage 上
    sender_emails = [r.message.sender_email for r in records if r.message and r.message.sender_email]
    sender_map = match_senders_batch(db, sender_emails)

    # 按客户分组
    customer_groups: dict[str, list[ArchiveRecord]] = defaultdict(list)
    unidentified_records: list[ArchiveRecord] = []

    for record in records:
        sender_email = record.message.sender_email if record.message else None
        if sender_email:
            profile = sender_map.get(sender_email.lower())
            if profile:
                customer_groups[profile.customer_name].append(record)
            else:
                unidentified_records.append(record)
        else:
            unidentified_records.append(record)

    # 构建分析结果
    overview = {
        "total_records": len(records),
        "matched_customer_count": len(customer_groups),
        "unidentified_record_count": len(unidentified_records),
        "failed_record_count": sum(1 for r in records if r.status == "failed"),
        "archived_record_count": sum(1 for r in records if r.status == "archived"),
        "ai_fallback_used": False,
    }

    # 分析各客户
    customers = []
    for customer_name, customer_records in customer_groups.items():
        customer_result = _analyze_customer_group(customer_name, customer_records, config.top_n_per_customer)
        customers.append(customer_result)

    # 按记录数排序
    customers.sort(key=lambda x: x["record_count"], reverse=True)

    # 未识别发件人（根据配置决定是否包含）
    include_unidentified = config.include_unidentified_senders
    if include_unidentified:
        unidentified = _build_unidentified_group(unidentified_records)
    else:
        # 不包含时返回空结构
        unidentified = {"record_count": 0, "senders": []}

    # AI 增强摘要（带降级）
    summary_markdown = ""
    # 传递 unidentified 用于摘要生成，但如果不包含则传空结构
    summary_unidentified = unidentified if include_unidentified else {"record_count": 0, "senders": []}

    if config.customer_analysis_mode == CustomerAnalysisMode.AI.value and settings.llm_enabled:
        try:
            summary_markdown = _generate_ai_customer_summary(overview, customers, summary_unidentified)
        except LLMError as e:
            logger.error(f"AI customer summary failed, falling back to basic: {e}")
            run.degraded = True
            overview["ai_fallback_used"] = True
            summary_markdown = _generate_basic_customer_summary(overview, customers, summary_unidentified)
    else:
        summary_markdown = _generate_basic_customer_summary(overview, customers, summary_unidentified)

    return {
        "overview": overview,
        "customers": customers,
        "unidentified": unidentified,
        "summary_markdown": summary_markdown,
    }


def _analyze_customer_group(
    customer_name: str,
    records: list[ArchiveRecord],
    top_n: int,
) -> dict:
    """分析单个客户组。

    Args:
        customer_name: 客户名称
        records: 该客户的记录列表
        top_n: 返回的样例数量

    Returns:
        客户分析结果
    """
    # 统计
    record_count = len(records)
    high_priority_count = sum(1 for r in records if r.priority == "high")

    # 发件人统计
    sender_emails = set(r.message.sender_email for r in records if r.message and r.message.sender_email)
    sender_count = len(sender_emails)

    # 问题分类统计
    category_counts: dict[str, int] = defaultdict(int)
    category_subjects: dict[str, list[str]] = defaultdict(list)

    for record in records:
        if record.business_type:
            category_counts[record.business_type] += 1
            if len(category_subjects[record.business_type]) < 3:
                subject = record.message.subject if record.message else None
                if subject:
                    category_subjects[record.business_type].append(subject)

    issue_categories = [
        {
            "category": cat,
            "count": count,
            "sample_subjects": category_subjects[cat],
        }
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # 样例记录（按优先级和接收时间排序）
    sorted_records = sorted(
        records,
        key=lambda r: (
            {"high": 0, "medium": 1, "low": 2}.get(r.priority or "low", 3),
            -(r.received_at.timestamp() if r.received_at else 0),
        ),
    )

    top_records = []
    for record in sorted_records[:top_n]:
        top_records.append({
            "archive_id": record.id,
            "message_id": record.message_id,
            "sender_email": record.message.sender_email if record.message else None,
            "subject": record.message.subject if record.message else None,
            "summary": record.summary,
            "priority": record.priority,
            "risk_tags": record.risk_tags,
            "received_at": record.received_at.isoformat() if record.received_at else None,
        })

    return {
        "customer_name": customer_name,
        "sender_count": sender_count,
        "record_count": record_count,
        "high_priority_count": high_priority_count,
        "issue_categories": issue_categories,
        "top_records": top_records,
    }


def _build_unidentified_group(records: list[ArchiveRecord]) -> dict:
    """构建未识别发件人分组。

    Args:
        records: 未识别的记录列表

    Returns:
        未识别发件人分组结果
    """
    sender_counts: dict[str, int] = defaultdict(int)
    sender_subjects: dict[str, list[str]] = defaultdict(list)

    for record in records:
        email = record.message.sender_email if record.message else None
        email = email or "(未知)"
        sender_counts[email] += 1
        if len(sender_subjects[email]) < 3:
            subject = record.message.subject if record.message else None
            if subject:
                sender_subjects[email].append(subject)

    senders = [
        {
            "sender_email": email,
            "record_count": count,
            "sample_subjects": sender_subjects[email],
        }
        for email, count in sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "record_count": len(records),
        "senders": senders,
    }


def _generate_basic_customer_summary(
    overview: dict,
    customers: list[dict],
    unidentified: dict,
) -> str:
    """生成基础客户归类摘要。

    Args:
        overview: 概览统计
        customers: 客户分析结果列表
        unidentified: 未识别发件人分组

    Returns:
        Markdown 格式的摘要
    """
    lines = [
        "# 客户问题归类摘要",
        "",
        "## 概览",
        "",
        f"- 总记录数: {overview['total_records']}",
        f"- 已识别客户数: {overview['matched_customer_count']}",
        f"- 未识别记录数: {overview['unidentified_record_count']}",
        f"- 高优先级记录: {overview.get('high_priority_count', 'N/A')}",
    ]

    if overview.get("ai_fallback_used"):
        lines.append("")
        lines.append("> ⚠️ AI 分析降级为基础汇总")

    # 各客户详情
    for customer in customers:
        lines.extend([
            "",
            f"## {customer['customer_name']}",
            "",
            f"- 记录数: {customer['record_count']}",
            f"- 发件人数: {customer['sender_count']}",
            f"- 高优先级: {customer['high_priority_count']}",
        ])

        if customer["issue_categories"]:
            lines.append("")
            lines.append("### 问题分类")
            lines.append("")
            for cat in customer["issue_categories"]:
                lines.append(f"- **{cat['category']}**: {cat['count']} 条")

        if customer["top_records"]:
            lines.append("")
            lines.append("### 样例邮件")
            lines.append("")
            for record in customer["top_records"][:3]:
                subject = record.get("subject") or "(无主题)"
                lines.append(f"- {subject}")

    # 未识别发件人
    if unidentified["record_count"] > 0:
        lines.extend([
            "",
            "## 未识别发件人",
            "",
            f"- 未识别记录数: {unidentified['record_count']}",
        ])

        for sender in unidentified["senders"][:5]:
            lines.append(f"- {sender['sender_email']}: {sender['record_count']} 条")

    lines.extend([
        "",
        "---",
        "*此摘要由系统自动生成*",
    ])

    return "\n".join(lines)


def _generate_ai_customer_summary(
    overview: dict,
    customers: list[dict],
    unidentified: dict,
) -> str:
    """使用 AI 生成客户归类摘要。

    Args:
        overview: 概览统计
        customers: 客户分析结果列表
        unidentified: 未识别发件人分组

    Returns:
        Markdown 格式的 AI 生成摘要
    """
    client = LLMClientSync()

    # 准备提示词
    prompt_data = {
        "overview": overview,
        "customers": [
            {
                "name": c["customer_name"],
                "record_count": c["record_count"],
                "high_priority_count": c["high_priority_count"],
                "categories": [cat["category"] for cat in c["issue_categories"]],
            }
            for c in customers
        ],
        "unidentified_count": unidentified["record_count"],
    }

    return client.generate_customer_analysis_summary(prompt_data)


def _compute_config_hash(config_snapshot: dict) -> str:
    """计算配置快照的哈希值。

    Args:
        config_snapshot: 配置快照字典

    Returns:
        SHA256 哈希值
    """
    # 规范化 JSON
    json_str = json.dumps(config_snapshot, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode()).hexdigest()
