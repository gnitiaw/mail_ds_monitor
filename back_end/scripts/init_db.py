"""数据库表初始化脚本。

用法：
    uv run python scripts/init_db.py
"""

from app.db.base import Base
from app.db.session import engine
from app.models import load_all_models


def main() -> None:
    """创建所有数据库表。"""
    print("Loading models...")
    load_all_models()

    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    print("Done! All tables created.")


if __name__ == "__main__":
    main()
