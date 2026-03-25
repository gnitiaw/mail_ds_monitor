"""邮箱拉取后台任务服务。"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.enums import TaskStatus, TaskType
from app.models.mailbox import Mailbox
from app.models.task_log import TaskLog
from app.services.imap_service import pull_emails_for_mailbox

logger = logging.getLogger(__name__)


class MailPullService:
    """邮箱拉取后台任务服务。"""

    @classmethod
    def trigger_mail_pull(
        cls,
        db: Session,
        mailbox: Mailbox,
        force_full_sync: bool,
    ) -> str:
        """创建拉取任务并后台执行。"""
        job_id = str(uuid.uuid4())
        mailbox.last_pull_status = TaskStatus.PENDING.value
        mailbox.last_pull_error = None

        task_log = TaskLog(
            id=job_id,
            task_type=TaskType.MAIL_PULL.value,
            task_key=f"mail_pull:{mailbox.id}",
            status=TaskStatus.PENDING.value,
            related_mailbox_id=mailbox.id,
            payload={
                "force_full_sync": force_full_sync,
            },
        )
        db.add(task_log)
        db.commit()

        cls._start_background_pull(job_id=job_id, mailbox_id=mailbox.id, force_full_sync=force_full_sync)
        return job_id

    @classmethod
    def _start_background_pull(
        cls,
        job_id: str,
        mailbox_id: str,
        force_full_sync: bool,
    ) -> None:
        """启动后台线程。"""
        thread = threading.Thread(
            target=cls._execute_pull_background,
            args=(job_id, mailbox_id, force_full_sync),
            daemon=True,
        )
        thread.start()

    @classmethod
    def _execute_pull_background(
        cls,
        job_id: str,
        mailbox_id: str,
        force_full_sync: bool,
    ) -> None:
        """后台执行 IMAP 拉取。"""
        db = SessionLocal()
        try:
            task_log = db.get(TaskLog, job_id)
            mailbox = db.get(Mailbox, mailbox_id)
            if not task_log or not mailbox:
                logger.error("Mail pull background task missing job=%s mailbox=%s", job_id, mailbox_id)
                return

            task_log.status = TaskStatus.RUNNING.value
            task_log.started_at = datetime.now(timezone.utc)
            db.commit()

            new_count, existing_count, error_message = pull_emails_for_mailbox(
                db=db,
                mailbox=mailbox,
                force_full_sync=force_full_sync,
            )

            task_log.finished_at = datetime.now(timezone.utc)
            task_log.result = {
                "new_count": new_count,
                "existing_count": existing_count,
            }

            if error_message:
                task_log.status = TaskStatus.FAILED.value
                task_log.error_message = error_message
            else:
                task_log.status = TaskStatus.SUCCESS.value

            db.commit()
        except Exception as exc:
            logger.exception("Mail pull background task failed job=%s mailbox=%s", job_id, mailbox_id)
            try:
                db.rollback()
                task_log = db.get(TaskLog, job_id)
                mailbox = db.get(Mailbox, mailbox_id)
                if task_log:
                    task_log.status = TaskStatus.FAILED.value
                    task_log.finished_at = datetime.now(timezone.utc)
                    task_log.error_message = str(exc)
                if mailbox:
                    mailbox.last_pull_status = TaskStatus.FAILED.value
                    mailbox.last_pull_error = str(exc)
                db.commit()
            except Exception:
                logger.exception("Failed to persist mail pull task failure job=%s", job_id)
        finally:
            db.close()
