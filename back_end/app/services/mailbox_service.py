from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import encrypt_password
from app.models.enums import MailboxProtocol
from app.models.mailbox import Mailbox
from app.schemas.mailbox import MailboxCreateRequest, MailboxUpdateRequest


class MailboxConflictError(Exception):
    """Raised when mailbox configuration conflicts with existing data."""


class MailboxNotFoundError(Exception):
    """Raised when mailbox configuration does not exist."""


def list_mailboxes(
    db: Session,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Mailbox], int]:
    """查询邮箱配置列表。"""
    stmt = select(Mailbox)
    count_stmt = select(func.count()).select_from(Mailbox)
    if status:
        stmt = stmt.where(Mailbox.status == status)
        count_stmt = count_stmt.where(Mailbox.status == status)

    stmt = stmt.order_by(Mailbox.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt).all())
    total = int(db.scalar(count_stmt) or 0)
    return items, total


def create_mailbox(db: Session, payload: MailboxCreateRequest) -> Mailbox:
    """创建邮箱配置，密码加密存储。"""
    # 检查冲突：同名或同账号
    conflict_stmt = select(Mailbox).where(
        (Mailbox.name == payload.name)
        | ((Mailbox.username == payload.username) & (Mailbox.host == payload.host) & (Mailbox.port == payload.port))
    )
    existing = db.scalar(conflict_stmt)
    if existing:
        raise MailboxConflictError("Mailbox name or account configuration already exists")

    # 加密密码
    encrypted_password = encrypt_password(payload.password)

    mailbox = Mailbox(
        name=payload.name,
        protocol=MailboxProtocol.IMAP.value,
        host=payload.host,
        port=payload.port,
        username=payload.username,
        password_secret=encrypted_password,
        folder=payload.folder,
        status=payload.status,
    )
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)
    return mailbox


def update_mailbox(db: Session, mailbox_id: str, payload: MailboxUpdateRequest) -> Mailbox:
    """更新邮箱配置，如有密码则加密存储。"""
    mailbox = db.get(Mailbox, mailbox_id)
    if mailbox is None:
        raise MailboxNotFoundError("Mailbox configuration not found")

    data = payload.model_dump(exclude_unset=True)

    # 检查名称冲突
    if "name" in data and data["name"] != mailbox.name:
        existing = db.scalar(select(Mailbox).where(Mailbox.name == data["name"], Mailbox.id != mailbox_id))
        if existing:
            raise MailboxConflictError("Mailbox name already exists")

    # 密码加密
    if "password" in data:
        data["password_secret"] = encrypt_password(data.pop("password"))
    else:
        data.pop("password", None)

    for field, value in data.items():
        setattr(mailbox, field, value)

    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)
    return mailbox


def get_mailbox_by_id(db: Session, mailbox_id: str) -> Mailbox | None:
    """根据 ID 获取邮箱配置。"""
    return db.get(Mailbox, mailbox_id)
