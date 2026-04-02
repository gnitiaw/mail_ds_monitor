from fastapi import APIRouter

from app.api.v1.routes import (
    analysis_runs,
    archives,
    auth,
    capture_runs,
    failure_queue,
    failure_rules,
    mail_messages,
    mailboxes,
    sender_profiles,
    summary,
    system,
    task_logs,
)

router = APIRouter()
router.include_router(system.router, tags=["system"])
router.include_router(auth.router, tags=["auth"])
router.include_router(mailboxes.router, tags=["mailboxes"])
router.include_router(mail_messages.router, tags=["mail-messages"])
router.include_router(task_logs.router, tags=["task-logs"])
router.include_router(archives.router, tags=["archives"])
router.include_router(summary.router, tags=["summary-configs"])
router.include_router(summary.sends_router, tags=["summary-sends"])
router.include_router(analysis_runs.summary_configs_router, prefix="/summary-configs", tags=["summary-configs"])
router.include_router(analysis_runs.router, tags=["analysis-runs"])
router.include_router(sender_profiles.router, tags=["sender-profiles"])
router.include_router(failure_queue.router, tags=["failure-queue"])
router.include_router(failure_rules.router, tags=["failure-rules"])
router.include_router(capture_runs.router, tags=["capture-runs"])
