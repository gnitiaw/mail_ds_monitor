from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "back_end"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.models.enums import FailureQueueStatus, MailboxProtocol, MailboxStatus, RuleStatus, UserRole
from app.models.failure_capture import FailureCaptureRule
from app.models.failure_queue import FailureMailQueue
from app.models.mailbox import Mailbox
from app.models.user import User
from app.services.auth_service import AuthService


def ensure_mailbox(db) -> Mailbox:
    mailbox = db.query(Mailbox).filter(Mailbox.username == "pilot@example.com").first()
    if mailbox:
        return mailbox

    mailbox = Mailbox(
        name="试点邮箱",
        protocol=MailboxProtocol.IMAP.value,
        host="imap.example.com",
        port=993,
        username="pilot@example.com",
        password_secret="encrypted_password",
        folder="INBOX",
        status=MailboxStatus.ENABLED.value,
    )
    db.add(mailbox)
    db.flush()
    return mailbox


def ensure_admin(db) -> User:
    user = db.query(User).filter(User.username == "admin").first()
    if user:
        return user

    user = User(
        username="admin",
        password_hash=AuthService.hash_password("admin123"),
        display_name="试点管理员",
        role=UserRole.ADMIN.value,
        mailbox_scope_ids=None,
    )
    db.add(user)
    db.flush()
    return user


def ensure_operator(db, mailbox_id: str) -> User:
    user = db.query(User).filter(User.username == "operator").first()
    if user:
        user.mailbox_scope_ids = [mailbox_id]
        db.flush()
        return user

    user = User(
        username="operator",
        password_hash=AuthService.hash_password("operator123"),
        display_name="试点专员",
        role=UserRole.OPERATOR.value,
        mailbox_scope_ids=[mailbox_id],
    )
    db.add(user)
    db.flush()
    return user


def ensure_rule(db, mailbox_id: str) -> FailureCaptureRule:
    rule = (
        db.query(FailureCaptureRule)
        .filter(FailureCaptureRule.failure_rule_key == "batch_task_failed")
        .first()
    )
    if rule:
        rule.status = RuleStatus.ENABLED.value
        rule.mailbox_ids = [mailbox_id]
        db.flush()
        return rule

    rule = FailureCaptureRule(
        rule_name="A类客户批量任务失败规则",
        failure_rule_key="batch_task_failed",
        status=RuleStatus.ENABLED.value,
        customer_scope_type="explicit_list",
        customer_match_config={"customers": ["示例客户A"]},
        mailbox_ids=[mailbox_id],
        sender_patterns=["system@example.com"],
        subject_patterns=["执行失败", "失败通知"],
        body_patterns=["错误", "异常"],
        priority=100,
    )
    db.add(rule)
    db.flush()
    return rule


def ensure_queue_item(db, mailbox_id: str) -> FailureMailQueue:
    item = (
        db.query(FailureMailQueue)
        .filter(FailureMailQueue.failure_rule_key == "batch_task_failed")
        .first()
    )
    if item:
        return item

    item = FailureMailQueue(
        mailbox_id=mailbox_id,
        source_message_id="<pilot-failure-001@example.com>",
        provider_uid="pilot-uid-001",
        failure_rule_key="batch_task_failed",
        customer_name="示例客户A",
        task_identifier="TASK-20260323-001",
        subject="批量任务执行失败通知",
        sender="system@example.com",
        received_at=datetime.now(timezone.utc),
        status=FailureQueueStatus.NEW.value,
        body_text="检测到错误，任务执行异常，请尽快处理。",
        matched_snapshot={
            "matched_fields": {
                "subject_keywords": ["执行失败"],
                "sender_patterns": ["system@example.com"],
            },
            "extracted_fields": {
                "customer_name": "示例客户A",
                "task_identifier": "TASK-20260323-001",
            },
        },
    )
    db.add(item)
    db.flush()
    return item


def main() -> None:
    db = SessionLocal()
    try:
        mailbox = ensure_mailbox(db)
        ensure_admin(db)
        ensure_operator(db, mailbox.id)
        ensure_rule(db, mailbox.id)
        queue_item = ensure_queue_item(db, mailbox.id)
        db.commit()

        print("seed success")
        print("admin: admin / admin123")
        print("operator: operator / operator123")
        print(f"mailbox_id: {mailbox.id}")
        print(f"queue_id: {queue_item.id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
