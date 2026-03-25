"""发件人匹配服务。

匹配优先级：exact_email > email_domain
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.sender_profile import SenderProfile

logger = logging.getLogger(__name__)


def match_sender(
    db: Session,
    sender_email: str | None,
) -> SenderProfile | None:
    """根据发件人邮箱匹配发件人档案。

    匹配优先级：
    1. 精确邮箱匹配 (exact_email)
    2. 域名匹配 (email_domain)

    Args:
        db: 数据库会话
        sender_email: 发件人邮箱地址

    Returns:
        匹配到的发件人档案，未匹配则返回 None
    """
    if not sender_email:
        return None

    email_lower = sender_email.lower().strip()

    # 1. 精确邮箱匹配
    exact_match = db.query(SenderProfile).filter(
        SenderProfile.match_type == "exact_email",
        SenderProfile.match_value == email_lower,
        SenderProfile.status == "enabled",
    ).first()

    if exact_match:
        logger.debug(f"Exact email match found for {sender_email}: {exact_match.customer_name}")
        return exact_match

    # 2. 域名匹配
    if "@" not in email_lower:
        return None

    domain = email_lower.split("@")[-1]

    domain_match = db.query(SenderProfile).filter(
        SenderProfile.match_type == "email_domain",
        SenderProfile.match_value == domain,
        SenderProfile.status == "enabled",
    ).first()

    if domain_match:
        logger.debug(f"Domain match found for {sender_email}: {domain_match.customer_name}")
        return domain_match

    return None


def match_senders_batch(
    db: Session,
    sender_emails: list[str | None],
) -> dict[str, SenderProfile | None]:
    """批量匹配发件人邮箱。

    Args:
        db: 数据库会话
        sender_emails: 发件人邮箱地址列表

    Returns:
        邮箱到档案的映射字典，未匹配的邮箱值为 None
    """
    # 去重并过滤空值
    unique_emails = {e.lower().strip() for e in sender_emails if e}

    if not unique_emails:
        return {}

    # 加载所有启用的发件人档案
    all_profiles = db.query(SenderProfile).filter(
        SenderProfile.status == "enabled",
    ).all()

    # 构建索引
    exact_map: dict[str, SenderProfile] = {}
    domain_map: dict[str, SenderProfile] = {}

    for profile in all_profiles:
        if profile.match_type == "exact_email":
            exact_map[profile.match_value.lower()] = profile
        elif profile.match_type == "email_domain":
            domain_map[profile.match_value.lower()] = profile

    # 匹配
    result: dict[str, SenderProfile | None] = {}

    for email in unique_emails:
        # 精确匹配
        if email in exact_map:
            result[email] = exact_map[email]
            continue

        # 域名匹配
        if "@" in email:
            domain = email.split("@")[-1]
            if domain in domain_map:
                result[email] = domain_map[domain]
                continue

        result[email] = None

    return result


def get_sender_identification_status(
    db: Session,
    sender_email: str | None,
) -> dict[str, Any]:
    """获取发件人识别状态。

    Args:
        db: 数据库会话
        sender_email: 发件人邮箱地址

    Returns:
        包含识别状态和档案信息的字典
    """
    if not sender_email:
        return {
            "identified_status": "unidentified",
            "profile_id": None,
            "customer_name": None,
        }

    profile = match_sender(db, sender_email)

    if profile:
        return {
            "identified_status": "identified",
            "profile_id": profile.id,
            "customer_name": profile.customer_name,
        }

    return {
        "identified_status": "unidentified",
        "profile_id": None,
        "customer_name": None,
    }
