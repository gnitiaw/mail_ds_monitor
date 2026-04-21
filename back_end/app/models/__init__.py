from app.models.active_task_lock import ActiveTaskLock
from app.models.analysis_run import AnalysisRun
from app.models.archive import ArchiveRecord
from app.models.failure_capture import FailureCaptureRule
from app.models.failure_queue import FailureMailQueue
from app.models.mail_message import MailMessage
from app.models.mailbox import Mailbox
from app.models.sender_profile import SenderProfile
from app.models.service_report import (
    ServiceReportConfig,
    ServiceReportRun,
    ServiceReportSourceRun,
)
from app.models.summary import SummaryConfig, SummarySendRecord
from app.models.task_log import TaskLog
from app.models.user import User

__all__ = [
    "AnalysisRun",
    "ActiveTaskLock",
    "ArchiveRecord",
    "FailureCaptureRule",
    "FailureMailQueue",
    "MailMessage",
    "Mailbox",
    "SenderProfile",
    "ServiceReportConfig",
    "ServiceReportRun",
    "ServiceReportSourceRun",
    "SummaryConfig",
    "SummarySendRecord",
    "TaskLog",
    "User",
    "load_all_models",
]


def load_all_models() -> None:
    """Ensure model metadata is imported before create_all.

    This function imports all models to ensure their metadata is registered
    with SQLAlchemy's Base.metadata before calling create_all().
    """
    # Models are already imported above, this function just needs to exist
    # to explicitly trigger the imports when called
    pass
