"""IMAP 邮件拉取服务。"""

import email
import imaplib
import logging
from datetime import datetime, timezone
from email.header import decode_header
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_password
from app.models.enums import ExtractionStatus, ProcessingStatus
from app.models.mail_message import MailMessage
from app.models.mailbox import Mailbox

logger = logging.getLogger(__name__)


def _mark_pull_failure(
    db: Session,
    mailbox: Mailbox,
    status: str,
    error_message: str,
) -> None:
    """回滚当前事务并记录邮箱拉取失败状态。"""
    db.rollback()
    mailbox.last_pull_status = status
    mailbox.last_pull_error = error_message
    db.commit()


class IMAPConnectionError(Exception):
    """IMAP 连接错误。"""


class IMAPAuthenticationError(Exception):
    """IMAP 认证错误。"""


class IMAPFetchError(Exception):
    """IMAP 拉取错误。"""


def _decode_header_value(value: str | bytes | None) -> str:
    """解码邮件头字段。"""
    if value is None:
        return ""

    raw_value = (
        value.decode("utf-8", errors="replace")
        if isinstance(value, bytes)
        else value
    )
    decoded_parts = decode_header(raw_value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def _extract_email_addresses(header_value: str | None) -> list[str]:
    """从邮件头提取邮箱地址列表。"""
    if not header_value:
        return []
    addresses = []
    for part in header_value.split(","):
        part = part.strip()
        if "<" in part and ">" in part:
            # 提取 <email@domain.com> 中的邮箱
            start = part.index("<") + 1
            end = part.index(">")
            addresses.append(part[start:end])
        elif "@" in part:
            addresses.append(part)
    return addresses


def _parse_message(msg: email.message.Message) -> dict[str, Any]:
    """解析邮件消息为字典。"""
    # 解析邮件头
    subject = _decode_header_value(msg.get("Subject"))
    sender = msg.get("From", "")
    sender_name = ""
    sender_email = ""

    if sender:
        decoded_sender = _decode_header_value(sender)
        if "<" in decoded_sender and ">" in decoded_sender:
            start = decoded_sender.index("<")
            end = decoded_sender.index(">")
            sender_email = decoded_sender[start + 1 : end]
            sender_name = decoded_sender[:start].strip().strip('"').strip("'")
        else:
            sender_email = decoded_sender

    # 解析收件人
    recipients_to = _extract_email_addresses(msg.get("To"))
    recipients_cc = _extract_email_addresses(msg.get("Cc"))
    recipients_bcc = _extract_email_addresses(msg.get("Bcc"))
    reply_to = _extract_email_addresses(msg.get("Reply-To"))

    # 解析日期
    received_at = None
    date_str = msg.get("Date")
    if date_str:
        try:
            # 尝试解析邮件日期
            parsed_date = email.utils.parsedate_to_datetime(date_str)
            received_at = parsed_date.astimezone(timezone.utc)
        except (ValueError, TypeError):
            pass

    # 解析正文
    body_text = None
    body_html = None
    has_attachments = False

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            # 检查附件
            if "attachment" in content_disposition:
                has_attachments = True
                continue

            # 跳过非文本部分
            if content_type not in ("text/plain", "text/html"):
                continue

            try:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="replace")

                    if content_type == "text/plain" and body_text is None:
                        body_text = text
                    elif content_type == "text/html" and body_html is None:
                        body_html = text
            except Exception as e:
                logger.warning(f"Failed to parse email part: {e}")
    else:
        content_type = msg.get_content_type()
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")

                if content_type == "text/plain":
                    body_text = text
                elif content_type == "text/html":
                    body_html = text
        except Exception as e:
            logger.warning(f"Failed to parse single-part email: {e}")

    # 提取 Message-ID
    internet_message_id = msg.get("Message-ID", "")

    # 提取 Flags
    flags: list[str] = []

    return {
        "internet_message_id": internet_message_id or None,
        "subject": subject or None,
        "sender_name": sender_name or None,
        "sender_email": sender_email or None,
        "recipients_to": recipients_to or None,
        "recipients_cc": recipients_cc or None,
        "recipients_bcc": recipients_bcc or None,
        "reply_to": reply_to or None,
        "body_text": body_text,
        "body_html": body_html,
        "has_attachments": has_attachments,
        "received_at": received_at,
        "flags": flags or None,
    }


class IMAPClient:
    """IMAP 客户端。"""

    def __init__(self, mailbox: Mailbox):
        self.mailbox = mailbox
        self._client: imaplib.IMAP4_SSL | imaplib.IMAP4 | None = None

    def connect(self) -> None:
        """连接 IMAP 服务器。"""
        try:
            password = decrypt_password(self.mailbox.password_secret)

            # 根据端口选择连接方式
            if self.mailbox.port == 993:
                self._client = imaplib.IMAP4_SSL(
                    self.mailbox.host,
                    self.mailbox.port,
                    timeout=settings.mail_pull_timeout_seconds,
                )
            else:
                self._client = imaplib.IMAP4(
                    self.mailbox.host,
                    self.mailbox.port,
                    timeout=settings.mail_pull_timeout_seconds,
                )
                # 非 SSL 端口尝试 STARTTLS
                if self.mailbox.port == 143:
                    self._client.starttls()

            self._client.login(self.mailbox.username, password)
            logger.info(f"IMAP connected to {self.mailbox.host}:{self.mailbox.port}")

        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP authentication failed: {e}")
            raise IMAPAuthenticationError(f"Authentication failed: {e}") from e
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            raise IMAPConnectionError(f"Connection failed: {e}") from e

    def disconnect(self) -> None:
        """断开连接。"""
        if self._client:
            try:
                self._client.logout()
            except Exception:
                pass
            self._client = None

    def fetch_messages(
        self,
        folder: str | None = None,
        limit: int | None = None,
        since_uid: int | None = None,
    ) -> list[dict[str, Any]]:
        """拉取邮件消息。

        Args:
            folder: 邮箱目录，默认使用配置的目录
            limit: 最大拉取数量
            since_uid: 从指定 UID 之后开始拉取（增量同步）

        Returns:
            解析后的邮件消息列表
        """
        if not self._client:
            raise IMAPConnectionError("Not connected")

        folder = folder or self.mailbox.folder
        messages: list[dict[str, Any]] = []

        try:
            # 选择邮箱目录
            status, _ = self._client.select(folder)
            if status != "OK":
                raise IMAPFetchError(f"Failed to select folder: {folder}")

            # 统一使用 UID 搜索，避免序号结果和 uid fetch 混用导致全量拉取为空。
            if since_uid:
                # 增量同步：从指定 UID 之后
                search_criteria = f"UID {since_uid + 1}:*"
                status, data = self._client.uid("search", None, search_criteria)
            else:
                # 全量同步
                status, data = self._client.uid("search", None, "ALL")

            if status != "OK":
                raise IMAPFetchError("Failed to search messages")

            message_uids = data[0].split()
            if not message_uids:
                return messages

            # 限制数量
            if limit and len(message_uids) > limit:
                message_uids = message_uids[-limit:]

            # 拉取邮件
            for uid in message_uids:
                try:
                    status, msg_data = self._client.uid("fetch", uid, "(RFC822 FLAGS)")
                    if status != "OK" or not msg_data or not msg_data[0]:
                        continue

                    raw_email = msg_data[0][1]
                    email_message = email.message_from_bytes(raw_email)

                    # 解析邮件
                    parsed = _parse_message(email_message)
                    parsed["provider_uid"] = uid.decode() if isinstance(uid, bytes) else str(uid)
                    parsed["folder"] = folder

                    # 提取 Flags
                    flags_str = msg_data[0][0] if isinstance(msg_data[0], tuple) else ""
                    if isinstance(flags_str, bytes):
                        flags_str = flags_str.decode()
                    parsed["flags"] = [f.strip() for f in flags_str.replace("\\", "").split() if f.strip()] or None

                    messages.append(parsed)

                except Exception as e:
                    logger.warning(f"Failed to fetch message UID {uid}: {e}")
                    continue

            return messages

        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP fetch failed: {e}")
            raise IMAPFetchError(f"Fetch failed: {e}") from e

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False


def pull_emails_for_mailbox(
    db: Session,
    mailbox: Mailbox,
    force_full_sync: bool = False,
) -> tuple[int, int, str | None]:
    """为指定邮箱拉取邮件。

    Args:
        db: 数据库会话
        mailbox: 邮箱配置
        force_full_sync: 是否强制全量同步

    Returns:
        (新邮件数, 已存在邮件数, 错误信息)
    """
    new_count = 0
    existing_count = 0
    error_message = None

    try:
        # 获取上次同步的最大 UID（增量同步）
        since_uid = None
        if not force_full_sync:
            last_msg = db.scalar(
                select(MailMessage)
                .where(MailMessage.mailbox_id == mailbox.id)
                .order_by(MailMessage.provider_uid.desc())
                .limit(1)
            )
            if last_msg and last_msg.provider_uid:
                try:
                    since_uid = int(last_msg.provider_uid)
                except ValueError:
                    pass

        with IMAPClient(mailbox) as client:
            messages = client.fetch_messages(
                folder=mailbox.folder,
                limit=settings.mail_pull_batch_size,
                since_uid=since_uid,
            )

            for msg_data in messages:
                # 幂等检查
                existing = db.scalar(
                    select(MailMessage).where(
                        (MailMessage.mailbox_id == mailbox.id)
                        & (
                            (MailMessage.internet_message_id == msg_data.get("internet_message_id"))
                            | (MailMessage.provider_uid == msg_data.get("provider_uid"))
                        )
                    )
                )

                if existing:
                    existing_count += 1
                    continue

                # 创建新邮件记录
                mail_message = MailMessage(
                    mailbox_id=mailbox.id,
                    internet_message_id=msg_data.get("internet_message_id"),
                    provider_uid=msg_data.get("provider_uid"),
                    folder=msg_data.get("folder", mailbox.folder),
                    subject=msg_data.get("subject"),
                    sender_name=msg_data.get("sender_name"),
                    sender_email=msg_data.get("sender_email"),
                    recipients_to=msg_data.get("recipients_to"),
                    recipients_cc=msg_data.get("recipients_cc"),
                    recipients_bcc=msg_data.get("recipients_bcc"),
                    reply_to=msg_data.get("reply_to"),
                    body_text=msg_data.get("body_text"),
                    body_html=msg_data.get("body_html"),
                    has_attachments=msg_data.get("has_attachments", False),
                    flags=msg_data.get("flags"),
                    parse_status=ProcessingStatus.PARSED.value,
                    extraction_status=ExtractionStatus.PENDING.value,
                    received_at=msg_data.get("received_at"),
                )
                db.add(mail_message)
                new_count += 1

            db.commit()

        # 更新邮箱最后拉取状态
        mailbox.last_pull_at = datetime.now(timezone.utc)
        mailbox.last_pull_status = "success"
        mailbox.last_pull_error = None
        db.commit()

        logger.info(f"Pulled {new_count} new messages, {existing_count} existing for mailbox {mailbox.id}")

    except IMAPConnectionError as e:
        error_message = f"Connection error: {e}"
        logger.error(f"IMAP connection error for mailbox {mailbox.id}: {e}")
        _mark_pull_failure(db, mailbox, "connection_error", error_message)
    except IMAPAuthenticationError as e:
        error_message = f"Authentication error: {e}"
        logger.error(f"IMAP authentication error for mailbox {mailbox.id}: {e}")
        _mark_pull_failure(db, mailbox, "auth_error", error_message)
    except IMAPFetchError as e:
        error_message = f"Fetch error: {e}"
        logger.error(f"IMAP fetch error for mailbox {mailbox.id}: {e}")
        _mark_pull_failure(db, mailbox, "fetch_error", error_message)
    except Exception as e:
        error_message = f"Unknown error: {e}"
        logger.exception(f"Unknown error pulling emails for mailbox {mailbox.id}")
        _mark_pull_failure(db, mailbox, "error", error_message)

    return new_count, existing_count, error_message
