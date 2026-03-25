"""发件人配置服务。"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select, union_all
from sqlalchemy.orm import Session

from app.models.archive import ArchiveRecord
from app.models.mail_message import MailMessage
from app.models.sender_profile import SenderProfile
from app.models.enums import SenderProfileStatus

logger = logging.getLogger(__name__)


def get_sender_candidates(
    db: Session,
    mailbox_id: str | None = None,
    identified_status: str | None = None,
    keyword: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """获取候选发件人列表。

    从 archive_records 和未归档的 mail_messages 中聚合近期出现过的发件人邮箱。

    Args:
        db: 数据库会话
        mailbox_id: 可选，按单个邮箱过滤
        identified_status: 按是否已建档筛选 (identified/unidentified)
        keyword: 按发件人邮箱、域名、样例名称模糊搜索
        date_from: 候选发件人统计起始时间
        date_to: 候选发件人统计结束时间
        page: 页码
        page_size: 每页数量

    Returns:
        (候选发件人列表, 总数)
    """
    # 默认时间窗口：最近 30 天
    if not date_from:
        date_from = datetime.now(timezone.utc) - timedelta(days=30)
    if not date_to:
        date_to = datetime.now(timezone.utc)

    # 查询1: 从 archive_records 获取已归档的发件人
    archived_stmt = (
        select(
            MailMessage.sender_email,
            MailMessage.sender_name,
            ArchiveRecord.received_at.label("seen_at"),
            ArchiveRecord.mailbox_id,
        )
        .select_from(ArchiveRecord)
        .join(MailMessage, ArchiveRecord.message_id == MailMessage.id)
        .where(
            and_(
                ArchiveRecord.received_at >= date_from,
                ArchiveRecord.received_at <= date_to,
                MailMessage.sender_email.isnot(None),
            )
        )
    )
    if mailbox_id:
        archived_stmt = archived_stmt.where(ArchiveRecord.mailbox_id == mailbox_id)

    # 查询2: 从 mail_messages 获取未归档的发件人（通过 received_at 时间过滤）
    # 排除已在 archive_records 中的邮件
    unarchived_stmt = (
        select(
            MailMessage.sender_email,
            MailMessage.sender_name,
            MailMessage.received_at.label("seen_at"),
            MailMessage.mailbox_id,
        )
        .select_from(MailMessage)
        .outerjoin(ArchiveRecord, MailMessage.id == ArchiveRecord.message_id)
        .where(
            and_(
                MailMessage.received_at >= date_from,
                MailMessage.received_at <= date_to,
                MailMessage.sender_email.isnot(None),
                ArchiveRecord.id.is_(None),  # 未归档的邮件
            )
        )
    )
    if mailbox_id:
        unarchived_stmt = unarchived_stmt.where(MailMessage.mailbox_id == mailbox_id)

    # 合并两个查询
    combined_stmt = union_all(archived_stmt, unarchived_stmt)

    # 关键词搜索需要在合并后应用
    if keyword:
        search_pattern = f"%{keyword}%"
        # 使用子查询过滤
        from sqlalchemy import text
        combined_stmt = select(combined_stmt.c).where(
            or_(
                combined_stmt.c.sender_email.ilike(search_pattern),
                combined_stmt.c.sender_name.ilike(search_pattern),
            )
        )

    # 执行合并查询
    results = db.execute(combined_stmt).all()

    # 在内存中聚合
    sender_data: dict[str, dict] = defaultdict(lambda: {
        "sender_name_sample": None,
        "seen_count": 0,
        "last_seen_at": None,
        "archive_count": 0,
    })

    for row in results:
        email = row.sender_email
        if not email:
            continue

        email_lower = email.lower()
        data = sender_data[email_lower]

        # 更新名称样本
        if not data["sender_name_sample"] and row.sender_name:
            data["sender_name_sample"] = row.sender_name

        # 更新计数
        data["seen_count"] += 1

        # 更新最后出现时间
        seen_at = row.seen_at
        if seen_at:
            if not data["last_seen_at"] or seen_at > data["last_seen_at"]:
                data["last_seen_at"] = seen_at

    # 加载所有启用的发件人档案用于匹配
    all_profiles = db.query(SenderProfile).filter(
        SenderProfile.status == SenderProfileStatus.ENABLED.value,
    ).all()

    # 构建邮箱到档案的映射
    profile_map: dict[str, SenderProfile] = {}
    domain_profiles: dict[str, SenderProfile] = {}

    for profile in all_profiles:
        if profile.match_type == "exact_email":
            profile_map[profile.match_value.lower()] = profile
        elif profile.match_type == "email_domain":
            domain_profiles[profile.match_value.lower()] = profile

    # 批量获取所有候选发件人的最新邮件主题（修复 N+1 查询）
    sender_email_list = list(sender_data.keys())
    latest_subject_map: dict[str, str | None] = {}

    if sender_email_list:
        # 使用子查询获取每个发件人的最新归档记录
        from sqlalchemy import func
        from sqlalchemy.orm import aliased

        # 查询每个 sender_email 对应的最大 received_at
        latest_subquery = (
            db.query(
                MailMessage.sender_email,
                func.max(ArchiveRecord.received_at).label("max_received_at"),
            )
            .join(ArchiveRecord, MailMessage.id == ArchiveRecord.message_id)
            .filter(MailMessage.sender_email.in_(sender_email_list))
            .group_by(MailMessage.sender_email)
            .subquery()
        )

        # 关联获取对应的 subject
        latest_records = (
            db.query(MailMessage.sender_email, MailMessage.subject)
            .join(ArchiveRecord, MailMessage.id == ArchiveRecord.message_id)
            .join(
                latest_subquery,
                and_(
                    MailMessage.sender_email == latest_subquery.c.sender_email,
                    ArchiveRecord.received_at == latest_subquery.c.max_received_at,
                ),
            )
            .all()
        )

        for row in latest_records:
            latest_subject_map[row.sender_email.lower()] = row.subject

    # 构建候选列表
    candidates = []

    for sender_email, data in sender_data.items():
        # 匹配档案
        profile = None
        if sender_email in profile_map:
            profile = profile_map[sender_email]
        elif "@" in sender_email:
            domain = sender_email.split("@")[-1]
            if domain in domain_profiles:
                profile = domain_profiles[domain]

        # 根据识别状态过滤
        if identified_status == "identified" and not profile:
            continue
        if identified_status == "unidentified" and profile:
            continue

        # 从批量查询结果中获取最新邮件主题
        latest_subject = latest_subject_map.get(sender_email)

        # 提取域名
        email_domain = None
        if "@" in sender_email:
            email_domain = sender_email.split("@")[-1]

        candidates.append({
            "sender_email": sender_email,
            "sender_name_sample": data["sender_name_sample"],
            "email_domain": email_domain,
            "message_count": data["seen_count"],
            "archive_count": data["archive_count"],
            "last_seen_at": data["last_seen_at"],
            "latest_subject": latest_subject,
            "identified_profile_id": profile.id if profile else None,
            "identified_status": "identified" if profile else "unidentified",
            "customer_name": profile.customer_name if profile else None,
        })

    # 排序：按最近出现时间倒序
    candidates.sort(key=lambda x: x["last_seen_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    # 分页
    total = len(candidates)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = candidates[start:end]

    return paginated, total


def list_sender_profiles(
    db: Session,
    keyword: str | None = None,
    status: str | None = None,
    match_type: str | None = None,
    customer_name: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[SenderProfile], int]:
    """获取发件人档案列表。

    Args:
        db: 数据库会话
        keyword: 按客户名称、发件人标签、匹配值模糊搜索
        status: 按状态筛选
        match_type: 按匹配类型筛选
        customer_name: 按客户名称筛选
        page: 页码
        page_size: 每页数量

    Returns:
        (发件人档案列表, 总数)
    """
    query = db.query(SenderProfile)

    # 状态过滤
    if status:
        query = query.filter(SenderProfile.status == status)

    # 匹配类型过滤
    if match_type:
        query = query.filter(SenderProfile.match_type == match_type)

    # 客户名称过滤
    if customer_name:
        query = query.filter(SenderProfile.customer_name.ilike(f"%{customer_name}%"))

    # 关键词搜索
    if keyword:
        search_pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                SenderProfile.customer_name.ilike(search_pattern),
                SenderProfile.sender_label.ilike(search_pattern),
                SenderProfile.match_value.ilike(search_pattern),
            )
        )

    # 统计总数
    total = query.count()

    # 分页
    profiles = query.order_by(SenderProfile.updated_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return profiles, total


def create_sender_profile(
    db: Session,
    match_type: str,
    match_value: str,
    customer_name: str,
    customer_code: str | None = None,
    sender_label: str | None = None,
    sender_type: str = "unknown",
    status: str = "enabled",
    notes: str | None = None,
) -> SenderProfile:
    """创建发件人档案。

    Args:
        db: 数据库会话
        match_type: 匹配类型
        match_value: 匹配值
        customer_name: 客户名称
        customer_code: 客户编码
        sender_label: 发件人标签
        sender_type: 发件人类型
        status: 状态
        notes: 备注

    Returns:
        创建的发件人档案

    Raises:
        ValueError: 如果已存在相同的 match_type + match_value
    """
    # 邮箱格式验证（仅对 exact_email 模式）
    if match_type == "exact_email":
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, match_value):
            raise ValueError(f"邮箱格式无效: {match_value}")

    # 检查冲突
    existing = db.query(SenderProfile).filter(
        SenderProfile.match_type == match_type,
        SenderProfile.match_value == match_value.lower().strip(),
    ).first()

    if existing:
        raise ValueError(f"发件人档案冲突，匹配规则已存在: {match_type}={match_value}")

    profile = SenderProfile(
        match_type=match_type,
        match_value=match_value.lower().strip(),
        customer_name=customer_name,
        customer_code=customer_code,
        sender_label=sender_label,
        sender_type=sender_type,
        status=status,
        notes=notes,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    logger.info(f"Created sender profile: {profile.id}, {match_type}={match_value}, customer={customer_name}")

    return profile


def update_sender_profile(
    db: Session,
    profile_id: str,
    customer_name: str | None = None,
    customer_code: str | None = None,
    sender_label: str | None = None,
    sender_type: str | None = None,
    status: str | None = None,
    notes: str | None = None,
) -> SenderProfile | None:
    """更新发件人档案。

    Args:
        db: 数据库会话
        profile_id: 发件人档案 ID
        customer_name: 客户名称
        customer_code: 客户编码
        sender_label: 发件人标签
        sender_type: 发件人类型
        status: 状态
        notes: 备注

    Returns:
        更新后的发件人档案，不存在则返回 None
    """
    profile = db.query(SenderProfile).filter(SenderProfile.id == profile_id).first()

    if not profile:
        return None

    if customer_name is not None:
        profile.customer_name = customer_name
    if customer_code is not None:
        profile.customer_code = customer_code
    if sender_label is not None:
        profile.sender_label = sender_label
    if sender_type is not None:
        profile.sender_type = sender_type
    if status is not None:
        profile.status = status
    if notes is not None:
        profile.notes = notes

    db.commit()
    db.refresh(profile)

    logger.info(f"Updated sender profile: {profile_id}")

    return profile


def get_sender_profile(
    db: Session,
    profile_id: str,
) -> SenderProfile | None:
    """获取单个发件人档案。

    Args:
        db: 数据库会话
        profile_id: 发件人档案 ID

    Returns:
        发件人档案，不存在则返回 None
    """
    return db.query(SenderProfile).filter(SenderProfile.id == profile_id).first()


def get_profile_linked_message_count(
    db: Session,
    profile: SenderProfile,
) -> int:
    """获取档案命中的历史邮件数量。

    Args:
        db: 数据库会话
        profile: 发件人档案

    Returns:
        命中的邮件数量
    """
    from app.models.mail_message import MailMessage
    from sqlalchemy.orm import joinedload

    if profile.match_type == "exact_email":
        return db.query(ArchiveRecord).join(
            MailMessage, ArchiveRecord.message_id == MailMessage.id
        ).filter(
            MailMessage.sender_email == profile.match_value,
        ).count()
    elif profile.match_type == "email_domain":
        return db.query(ArchiveRecord).join(
            MailMessage, ArchiveRecord.message_id == MailMessage.id
        ).filter(
            MailMessage.sender_email.ilike(f"%@{profile.match_value}"),
        ).count()

    return 0
