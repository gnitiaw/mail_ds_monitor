"""将 mail_messages 正文字段扩容到 MEDIUMTEXT。"""

from __future__ import annotations

from sqlalchemy import text

from app.db.session import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                ALTER TABLE mail_messages
                MODIFY COLUMN body_text MEDIUMTEXT NULL,
                MODIFY COLUMN body_html MEDIUMTEXT NULL
                """
            )
        )
        db.commit()
        print("mail_messages body_text/body_html migrated to MEDIUMTEXT")
    finally:
        db.close()


if __name__ == "__main__":
    main()
