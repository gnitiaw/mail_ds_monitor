"""后台任务调度器配置。

使用 APScheduler 管理后台任务，确保任务持久化和崩溃恢复。
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from app.core.config import settings

logger = logging.getLogger(__name__)

# 任务存储配置：使用现有数据库
jobstores = {
    "default": SQLAlchemyJobStore(url=settings.sqlalchemy_database_uri)
}

# 执行器配置：线程池
executors = {
    "default": ThreadPoolExecutor(max_workers=4)
}

# 任务默认配置
job_defaults = {
    "coalesce": True,  # 合并错过的任务
    "max_instances": 1,  # 同一任务最多同时运行 1 个实例
    "misfire_grace_time": 300,  # 错过触发时间后 5 分钟内仍可执行
}

# 创建调度器实例
scheduler = BackgroundScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone="UTC",
)


def init_scheduler() -> None:
    """初始化并启动调度器。"""
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started with SQLAlchemy job store")


def shutdown_scheduler(wait: bool = True) -> None:
    """关闭调度器。

    Args:
        wait: 是否等待正在执行的任务完成
    """
    if scheduler.running:
        scheduler.shutdown(wait=wait)
        logger.info("APScheduler shutdown complete")


def add_analysis_job(run_id: str, config_id: str) -> None:
    """添加分析任务到调度器。

    Args:
        run_id: 分析运行 ID
        config_id: 汇总配置 ID
    """
    from app.services.customer_analysis_service import execute_analysis_async

    # 使用 run_id 作为 job_id，确保唯一性
    job_id = f"analysis_run_{run_id}"

    scheduler.add_job(
        execute_analysis_async,
        id=job_id,
        args=[settings.sqlalchemy_database_uri, run_id, config_id],
        replace_existing=True,
        # 任务执行完成后自动删除，避免 JobLookupError
        misfire_grace_time=3600,  # 1小时内仍可执行
    )
    logger.info(f"Scheduled analysis job: {job_id}")


def recover_stuck_runs() -> None:
    """恢复卡在 running 状态的分析任务。

    启动时检查所有 running 状态的任务，如果对应的 job 不存在或已完成，
    则将任务标记为 failed。
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.analysis_run import AnalysisRun
    from app.models.enums import AnalysisRunStatus

    engine = create_engine(settings.sqlalchemy_database_uri)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 查找所有 running 状态的任务
        stuck_runs = db.query(AnalysisRun).filter(
            AnalysisRun.status == AnalysisRunStatus.RUNNING.value,
        ).all()

        for run in stuck_runs:
            job_id = f"analysis_run_{run.id}"
            job = scheduler.get_job(job_id)

            if job is None:
                # job 不存在，说明可能已丢失
                logger.warning(f"Recovering stuck analysis run: {run.id}")
                run.status = AnalysisRunStatus.FAILED.value
                run.error_message = "Task lost due to server restart"
                run.finished_at = datetime.now(timezone.utc)

        db.commit()
        logger.info(f"Recovered {len(stuck_runs)} stuck analysis runs")

    except Exception as e:
        logger.exception(f"Failed to recover stuck runs: {e}")
        db.rollback()
    finally:
        db.close()
