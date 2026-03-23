"""测试配置。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import db_session as db_session_dep
from app.db.base import Base
from app.main import create_application
from app.models import load_all_models


@pytest.fixture(scope="function")
def engine():
    """创建测试数据库引擎（每个测试独立的内存 SQLite）。"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # 确保模型已加载
    load_all_models()
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    yield engine
    # 清理
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(engine) -> Session:
    """创建测试数据库会话。"""
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """创建测试客户端，覆写数据库依赖。"""
    app = create_application()

    # 正确覆写 db_session 依赖
    def override_db_session():
        try:
            yield db_session
        finally:
            pass  # 由 db_session fixture 管理生命周期

    app.dependency_overrides[db_session_dep] = override_db_session

    with TestClient(app) as test_client:
        yield test_client

    # 清理覆写
    app.dependency_overrides.clear()
