from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models import load_all_models


def init_db() -> None:
    load_all_models()
    Base.metadata.create_all(bind=engine)


def init_db_if_enabled() -> None:
    if settings.db_auto_create_tables:
        init_db()
