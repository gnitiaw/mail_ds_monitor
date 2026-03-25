"""捕获调度服务 - 自动轮询和手动补跑。"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import CaptureTaskType, FailureQueueStatus, RuleStatus, TaskStatus, TaskType
from app.models.failure_capture import FailureCaptureRule
from app.models.failure_queue import FailureMailQueue
from app.models.mailbox import Mailbox
from app.models.mail_message import MailMessage
from app.models.task_log import TaskLog
from app.services.imap_service import pull_emails_for_mailbox

logger = logging.getLogger(__name__)


class CaptureSchedulerService:
    """捕获调度服务。"""

    # 运行中任务锁 (生产环境应使用 Redis)
    _running_tasks: dict[str, threading.Lock] = {}
    _lock = threading.Lock()

    @classmethod
    def _get_task_lock(cls, task_key: str) -> bool:
        """获取任务锁。"""
        with cls._lock:
            if task_key in cls._running_tasks:
                return False
            cls._running_tasks[task_key] = threading.Lock()
            return True

    @classmethod
    def _release_task_lock(cls, task_key: str) -> None:
        """释放任务锁。"""
        with cls._lock:
            cls._running_tasks.pop(task_key, None)

    @classmethod
    def trigger_manual_replay(
        cls,
        db: Session,
        mailbox_ids: list[str],
        lookback_minutes: int,
        triggered_by: str,
    ) -> dict:
        """触发手动补跑。

        按契约要求：立即返回 pending 状态，后台执行实际捕获。
        """
        # 生成任务 key 用于去重
        task_key = f"replay:{','.join(sorted(mailbox_ids))}:{lookback_minutes}"

        # 检查是否有进行中的任务
        if not cls._get_task_lock(task_key):
            return {"already_running": True, "run_id": None, "status": None}

        # 创建任务记录 (复用 TaskLog)
        run_id = str(uuid.uuid4())
        task_log = TaskLog(
            id=run_id,
            task_type=TaskType.MAIL_PULL.value,
            task_key=task_key,
            status=TaskStatus.PENDING.value,
            related_mailbox_id=mailbox_ids[0] if len(mailbox_ids) == 1 else None,
            payload={
                "capture_task_type": CaptureTaskType.MANUAL_REPLAY.value,
                "mailbox_ids": mailbox_ids,
                "lookback_minutes": lookback_minutes,
                "triggered_by": triggered_by,
            },
        )
        db.add(task_log)
        db.commit()

        # 后台执行捕获任务
        thread = threading.Thread(
            target=cls._execute_capture_background,
            args=(run_id, task_key, mailbox_ids, lookback_minutes),
            daemon=True,
        )
        thread.start()

        # 立即返回 pending 状态（符合契约）
        return {
            "already_running": False,
            "run_id": run_id,
            "status": TaskStatus.PENDING.value,
        }

    @classmethod
    def _execute_capture_background(
        cls,
        run_id: str,
        task_key: str,
        mailbox_ids: list[str],
        lookback_minutes: int,
    ) -> None:
        """后台执行捕获任务。"""
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            task_log = db.get(TaskLog, run_id)
            if not task_log:
                logger.error(f"Task log not found: {run_id}")
                return

            task_log.status = TaskStatus.RUNNING.value
            task_log.started_at = datetime.now(timezone.utc)
            db.commit()

            result = cls._execute_capture(db, mailbox_ids, lookback_minutes)

            task_log.status = TaskStatus.SUCCESS.value
            task_log.finished_at = datetime.now(timezone.utc)
            task_log.result = result
            db.commit()

            logger.info(f"Capture task {run_id} completed: {result}")

        except Exception as e:
            logger.exception(f"Capture task {run_id} failed: {e}")
            try:
                task_log = db.get(TaskLog, run_id)
                if task_log:
                    task_log.status = TaskStatus.FAILED.value
                    task_log.finished_at = datetime.now(timezone.utc)
                    task_log.error_message = str(e)
                    db.commit()
            except Exception:
                pass

        finally:
            cls._release_task_lock(task_key)
            db.close()

    @classmethod
    def _execute_capture(
        cls,
        db: Session,
        mailbox_ids: list[str],
        lookback_minutes: int,
    ) -> dict:
        """执行捕获任务（从邮箱拉取邮件并匹配规则）。"""
        scanned_count = 0
        matched_count = 0
        deduped_count = 0
        error_mailboxes = []

        # 获取启用的规则
        rules = list(db.scalars(
            select(FailureCaptureRule)
            .where(FailureCaptureRule.status == RuleStatus.ENABLED.value)
            .order_by(FailureCaptureRule.priority.desc())
        ).all())

        for mailbox_id in mailbox_ids:
            mailbox = db.get(Mailbox, mailbox_id)
            if not mailbox or mailbox.status != "enabled":
                error_mailboxes.append({"mailbox_id": mailbox_id, "error": "Mailbox not found or disabled"})
                continue

            try:
                # 从邮箱拉取邮件
                new_count, existing_count, error = pull_emails_for_mailbox(
                    db=db,
                    mailbox=mailbox,
                    force_full_sync=False,
                )

                if error:
                    error_mailboxes.append({"mailbox_id": mailbox_id, "error": error})
                    continue

                # 获取 lookback 时间窗口内的邮件
                since_time = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
                messages = list(db.scalars(
                    select(MailMessage)
                    .where(
                        MailMessage.mailbox_id == mailbox_id,
                        MailMessage.received_at >= since_time,
                    )
                    .order_by(MailMessage.received_at.desc())
                ).all())

                scanned_count += len(messages)

                # 对每封邮件执行规则匹配
                for msg in messages:
                    matched = cls._process_mail_against_rules(
                        db=db,
                        mailbox_id=mailbox_id,
                        message=msg,
                        rules=rules,
                    )
                    if matched is None:
                        pass  # 未命中
                    elif matched.get("deduped"):
                        deduped_count += 1
                    else:
                        matched_count += 1

                db.commit()

            except Exception as e:
                logger.exception(f"Failed to process mailbox {mailbox_id}: {e}")
                error_mailboxes.append({"mailbox_id": mailbox_id, "error": str(e)})
                # 单个邮箱失败不影响其他邮箱
                continue

        return {
            "scanned_count": scanned_count,
            "matched_count": matched_count,
            "deduped_count": deduped_count,
            "error_mailboxes": error_mailboxes,
        }

    @classmethod
    def scan_existing_messages(
        cls,
        db: Session,
        mailbox_ids: list[str],
        lookback_minutes: int,
    ) -> dict:
        """仅扫描已拉取的现有邮件，不重复执行 IMAP 拉取。"""
        scanned_count = 0
        matched_count = 0
        deduped_count = 0
        error_mailboxes = []

        rules = list(db.scalars(
            select(FailureCaptureRule)
            .where(FailureCaptureRule.status == RuleStatus.ENABLED.value)
            .order_by(FailureCaptureRule.priority.desc())
        ).all())

        since_time = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)

        for mailbox_id in mailbox_ids:
            mailbox = db.get(Mailbox, mailbox_id)
            if not mailbox or mailbox.status != "enabled":
                error_mailboxes.append({"mailbox_id": mailbox_id, "error": "Mailbox not found or disabled"})
                continue

            try:
                messages = list(db.scalars(
                    select(MailMessage)
                    .where(
                        MailMessage.mailbox_id == mailbox_id,
                        MailMessage.received_at >= since_time,
                    )
                    .order_by(MailMessage.received_at.desc())
                ).all())

                scanned_count += len(messages)

                for msg in messages:
                    matched = cls._process_mail_against_rules(
                        db=db,
                        mailbox_id=mailbox_id,
                        message=msg,
                        rules=rules,
                    )
                    if matched is None:
                        continue
                    if matched.get("deduped"):
                        deduped_count += 1
                    else:
                        matched_count += 1

                db.commit()
            except Exception as e:
                logger.exception(f"Failed to scan existing messages for mailbox {mailbox_id}: {e}")
                error_mailboxes.append({"mailbox_id": mailbox_id, "error": str(e)})

        return {
            "scanned_count": scanned_count,
            "matched_count": matched_count,
            "deduped_count": deduped_count,
            "error_mailboxes": error_mailboxes,
        }

    @classmethod
    def _process_mail_against_rules(
        cls,
        db: Session,
        mailbox_id: str,
        message: MailMessage,
        rules: list[FailureCaptureRule],
    ) -> dict | None:
        """对单封邮件执行规则匹配和入队。"""
        # 过滤适用于该邮箱的规则
        applicable_rules = []
        for rule in rules:
            if rule.mailbox_ids is None or mailbox_id in rule.mailbox_ids:
                applicable_rules.append(rule)

        if not applicable_rules:
            return None

        # 按优先级匹配
        for rule in applicable_rules:
            matched = cls._match_rule(
                rule=rule,
                subject=message.subject,
                sender=message.sender_email,
                body_text=message.body_text,
            )
            if matched:
                return cls._enqueue_if_not_exists(
                    db=db,
                    mailbox_id=mailbox_id,
                    source_message_id=message.internet_message_id,
                    provider_uid=message.provider_uid,
                    rule=rule,
                    subject=message.subject,
                    sender=message.sender_email,
                    body_text=message.body_text,
                    received_at=message.received_at,
                )

        return None

    @classmethod
    def _match_rule(
        cls,
        rule: FailureCaptureRule,
        subject: str | None,
        sender: str | None,
        body_text: str | None,
    ) -> bool:
        """检查邮件是否匹配规则。"""
        # 发件人匹配（全部匹配才通过）
        if rule.sender_patterns:
            if not sender:
                return False
            matched = any(pattern.lower() in sender.lower() for pattern in rule.sender_patterns)
            if not matched:
                return False

        # 主题匹配（全部匹配才通过）
        if rule.subject_patterns:
            if not subject:
                return False
            matched = any(pattern.lower() in subject.lower() for pattern in rule.subject_patterns)
            if not matched:
                return False

        # 正文匹配（至少匹配一个）
        if rule.body_patterns:
            if not body_text:
                return False
            matched = any(pattern.lower() in body_text.lower() for pattern in rule.body_patterns)
            if not matched:
                return False

        return True

    @classmethod
    def _enqueue_if_not_exists(
        cls,
        db: Session,
        mailbox_id: str,
        source_message_id: str | None,
        provider_uid: str | None,
        rule: FailureCaptureRule,
        subject: str | None,
        sender: str | None,
        body_text: str | None,
        received_at: datetime | None,
    ) -> dict:
        """入队（幂等防重）。

        契约要求幂等维度：mailbox_id + internet_message_id/provider_uid + failure_rule_key
        - 优先使用 source_message_id (internet_message_id)
        - 如果为空，回退到 provider_uid
        """
        # 查重：契约要求的核心幂等维度
        existing = None

        if source_message_id:
            # 优先使用 source_message_id
            existing = db.scalar(
                select(FailureMailQueue).where(
                    FailureMailQueue.mailbox_id == mailbox_id,
                    FailureMailQueue.source_message_id == source_message_id,
                    FailureMailQueue.failure_rule_key == rule.failure_rule_key,
                )
            )
        elif provider_uid:
            # 回退到 provider_uid
            existing = db.scalar(
                select(FailureMailQueue).where(
                    FailureMailQueue.mailbox_id == mailbox_id,
                    FailureMailQueue.provider_uid == provider_uid,
                    FailureMailQueue.failure_rule_key == rule.failure_rule_key,
                )
            )

        if existing:
            # 更新 last_seen_at
            existing.last_seen_at = datetime.now(timezone.utc)
            db.flush()
            return {"deduped": True, "queue_id": existing.id}

        # 提取字段
        customer_name = cls._extract_customer_name(rule, subject, body_text)
        task_identifier = cls._extract_task_identifier(subject, body_text)

        # 创建新记录
        queue_item = FailureMailQueue(
            mailbox_id=mailbox_id,
            source_message_id=source_message_id,
            provider_uid=provider_uid,
            failure_rule_key=rule.failure_rule_key,
            customer_name=customer_name,
            task_identifier=task_identifier,
            subject=subject,
            sender=sender,
            body_text=body_text,
            received_at=received_at,
            status=FailureQueueStatus.NEW.value,
            matched_snapshot={
                "rule_id": rule.id,
                "rule_name": rule.rule_name,
                "matched_fields": {
                    "subject_keywords": rule.subject_patterns,
                    "sender_patterns": rule.sender_patterns,
                },
                "extracted_fields": {
                    "customer_name": customer_name,
                    "task_identifier": task_identifier,
                },
            },
        )

        db.add(queue_item)
        db.flush()

        # 触发短窗口聚合提醒（占位实现）
        cls._trigger_short_window_alert(db, queue_item)

        return {"deduped": False, "queue_id": queue_item.id}

    @classmethod
    def _extract_customer_name(
        cls,
        rule: FailureCaptureRule,
        subject: str | None,
        body_text: str | None,
    ) -> str | None:
        """提取客户名称。"""
        if rule.customer_match_config and rule.customer_scope_type == "explicit_list":
            customers = rule.customer_match_config.get("customers", [])
            text = f"{subject or ''} {body_text or ''}"
            for customer in customers:
                if customer.lower() in text.lower():
                    return customer
        return None

    @classmethod
    def _extract_task_identifier(
        cls,
        subject: str | None,
        body_text: str | None,
    ) -> str | None:
        """提取任务标识。"""
        import re
        text = f"{subject or ''} {body_text or ''}"
        # 查找 TASK-XXXXXXXX-XXX 格式
        match = re.search(r"TASK-\d{8}-\d+", text)
        if match:
            return match.group()
        return None

    @classmethod
    def _trigger_short_window_alert(cls, db: Session, queue_item: FailureMailQueue) -> None:
        """短窗口聚合提醒（占位实现）。

        TODO: 实现完整的短窗口聚合逻辑
        - 收集短窗口内（如 5 分钟）新增的失败邮件
        - 聚合后发送提醒邮件给监督人
        """
        logger.info(f"Short window alert placeholder: new failure queue item {queue_item.id}")

    @classmethod
    def run_auto_poll(cls, db: Session) -> dict:
        """执行自动轮询。

        定时任务入口，扫描所有启用的试点邮箱并执行捕获。
        """
        # 获取所有启用的试点邮箱
        mailboxes = list(db.scalars(
            select(Mailbox).where(Mailbox.status == "enabled")
        ).all())

        if not mailboxes:
            return {"status": "skipped", "reason": "no enabled mailboxes"}

        mailbox_ids = [m.id for m in mailboxes]

        # 使用默认 lookback 时间
        lookback_minutes = getattr(settings, 'capture_poll_lookback_minutes', 30)

        task_key = f"poll:auto:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"

        if not cls._get_task_lock(task_key):
            return {"status": "skipped", "reason": "already_running"}

        run_id = str(uuid.uuid4())
        task_log = TaskLog(
            id=run_id,
            task_type=TaskType.MAIL_PULL.value,
            task_key=task_key,
            status=TaskStatus.PENDING.value,
            payload={
                "capture_task_type": CaptureTaskType.POLL.value,
                "mailbox_ids": mailbox_ids,
                "lookback_minutes": lookback_minutes,
            },
        )
        db.add(task_log)
        db.commit()

        # 后台执行
        thread = threading.Thread(
            target=cls._execute_capture_background,
            args=(run_id, task_key, mailbox_ids, lookback_minutes),
            daemon=True,
        )
        thread.start()

        return {
            "status": "started",
            "run_id": run_id,
            "mailbox_count": len(mailbox_ids),
        }
