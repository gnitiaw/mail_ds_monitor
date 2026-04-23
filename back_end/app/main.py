import logging
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.init_db import init_db_if_enabled

logger = logging.getLogger(__name__)

# 全局定时器引用，用于优雅关闭
_poll_timer: threading.Timer | None = None


def _schedule_auto_poll() -> None:
    """调度下一次自动轮询。"""
    global _poll_timer

    if not settings.capture_poll_enabled:
        return

    def run_poll():
        from app.db.session import SessionLocal
        from app.services.capture_scheduler_service import CaptureSchedulerService

        db = SessionLocal()
        try:
            logger.info("Auto poll triggered")
            result = CaptureSchedulerService.run_auto_poll(db)
            logger.info(f"Auto poll result: {result}")
        except Exception as e:
            logger.exception(f"Auto poll failed: {e}")
        finally:
            db.close()

        # 调度下一次轮询
        _schedule_auto_poll()

    _poll_timer = threading.Timer(
        settings.capture_poll_interval_minutes * 60,
        run_poll,
    )
    _poll_timer.daemon = True
    _poll_timer.start()
    logger.info(
        f"Auto poll scheduled in {settings.capture_poll_interval_minutes} minutes"
    )


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
    )

    # 注册统一异常处理器
    register_exception_handlers(app)

    if settings.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.on_event("startup")
    def on_startup() -> None:
        # DB connection health check
        from sqlalchemy import text
        from app.db.session import engine

        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection OK")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            logger.error("Check your .env — MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD")
            raise

        init_db_if_enabled()

        # 初始化 APScheduler 并恢复卡住的任务
        from app.core.scheduler import init_scheduler, recover_stuck_runs

        init_scheduler()
        recover_stuck_runs()

        # 注册自动轮询定时任务
        if settings.capture_poll_enabled:
            logger.info("Capture auto-poll enabled, starting scheduler")
            _schedule_auto_poll()
        else:
            logger.info("Capture auto-poll disabled")

    @app.on_event("shutdown")
    def on_shutdown() -> None:
        global _poll_timer
        if _poll_timer:
            _poll_timer.cancel()
            logger.info("Auto poll timer cancelled")

        # 关闭 APScheduler
        from app.core.scheduler import shutdown_scheduler

        shutdown_scheduler(wait=True)

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_application()
