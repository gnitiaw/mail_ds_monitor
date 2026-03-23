from app.models.archive import ArchiveRecord
from app.models.failure_capture import FailureCaptureRule
from app.models.failure_queue import FailureMailQueue
from app.models.mail_message import MailMessage
from app.models.mailbox import Mailbox
from app.models.summary import SummaryConfig, SummarySendRecord
from app.models.task_log import TaskLog
from app.models.user import User

__all__ = [
    "ArchiveRecord",
    "FailureCaptureRule",
    "FailureMailQueue",
    "MailMessage",
    "Mailbox",
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
