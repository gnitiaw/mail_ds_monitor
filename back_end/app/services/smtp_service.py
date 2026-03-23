"""SMTP 发信服务。"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class SMTPError(Exception):
    """SMTP 发信错误。"""


class SMTPConnectionError(SMTPError):
    """SMTP 连接错误。"""


class SMTPAuthenticationError(SMTPError):
    """SMTP 认证错误。"""


class SMTPSendError(SMTPError):
    """SMTP 发送错误。"""


def send_email(
    to_emails: list[str],
    subject: str,
    body_text: str | None = None,
    body_html: str | None = None,
    cc_emails: list[str] | None = None,
    bcc_emails: list[str] | None = None,
) -> dict[str, Any]:
    """发送邮件。

    Args:
        to_emails: 收件人列表
        subject: 邮件主题
        body_text: 纯文本正文
        body_html: HTML 正文
        cc_emails: 抄送列表
        bcc_emails: 密送列表

    Returns:
        发送结果字典
    """
    if not to_emails:
        raise SMTPSendError("No recipients specified")

    # 创建邮件
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = ", ".join(to_emails)

    if cc_emails:
        msg["Cc"] = ", ".join(cc_emails)

    # 添加正文
    if body_text:
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        msg.attach(MIMEText(body_html, "html", "utf-8"))

    # 合并所有收件人
    all_recipients = list(to_emails)
    if cc_emails:
        all_recipients.extend(cc_emails)
    if bcc_emails:
        all_recipients.extend(bcc_emails)

    smtp_client: smtplib.SMTP | smtplib.SMTP_SSL | None = None

    try:
        # 连接 SMTP 服务器
        if settings.smtp_use_ssl:
            smtp_client = smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            )
        else:
            smtp_client = smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            )
            if settings.smtp_use_tls:
                smtp_client.starttls()

        # 认证
        if settings.smtp_username and settings.smtp_password:
            smtp_client.login(settings.smtp_username, settings.smtp_password)

        # 发送
        smtp_client.sendmail(
            settings.smtp_from_email,
            all_recipients,
            msg.as_string(),
        )

        logger.info(f"Email sent successfully to {len(all_recipients)} recipients")

        return {
            "success": True,
            "recipient_count": len(all_recipients),
            "error": None,
        }

    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"SMTP authentication failed: {e}"
        logger.error(error_msg)
        raise SMTPAuthenticationError(error_msg) from e

    except smtplib.SMTPConnectError as e:
        error_msg = f"SMTP connection failed: {e}"
        logger.error(error_msg)
        raise SMTPConnectionError(error_msg) from e

    except smtplib.SMTPException as e:
        error_msg = f"SMTP send failed: {e}"
        logger.error(error_msg)
        raise SMTPSendError(error_msg) from e

    except Exception as e:
        error_msg = f"Unexpected SMTP error: {e}"
        logger.exception(error_msg)
        raise SMTPError(error_msg) from e

    finally:
        if smtp_client:
            try:
                smtp_client.quit()
            except Exception:
                pass


def send_summary_email(
    to_emails: list[str],
    subject: str,
    summary_content: str,
) -> dict[str, Any]:
    """发送汇总邮件。

    Args:
        to_emails: 收件人列表
        subject: 邮件主题
        summary_content: 汇总内容（Markdown 格式）

    Returns:
        发送结果字典
    """
    # 将 Markdown 转换为简单的 HTML
    html_content = _markdown_to_html(summary_content)

    return send_email(
        to_emails=to_emails,
        subject=subject,
        body_text=summary_content,
        body_html=html_content,
    )


def _markdown_to_html(markdown_text: str) -> str:
    """将 Markdown 转换为简单的 HTML。"""
    import re

    html = markdown_text

    # 标题
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    # 粗体
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)

    # 斜体
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # 列表
    html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    html = re.sub(r"(<li>.*</li>\n?)+", r"<ul>\g<0></ul>", html)

    # 段落
    html = re.sub(r"\n\n", r"</p><p>", html)

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; }}
        h1, h2, h3 {{ margin-top: 1em; }}
        ul {{ padding-left: 1.5em; }}
        li {{ margin-bottom: 0.5em; }}
    </style>
</head>
<body>
<p>{html}</p>
</body>
</html>"""
