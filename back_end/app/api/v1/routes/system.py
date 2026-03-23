from fastapi import APIRouter

from app.core.config import settings
from app.schemas.system import AppMetaResponse, HealthCheckResponse

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.app_env,
        timezone=settings.app_timezone,
    )


@router.get("/meta", response_model=AppMetaResponse)
def app_meta() -> AppMetaResponse:
    return AppMetaResponse(
        app_name=settings.app_name,
        api_prefix=settings.api_prefix,
        timezone=settings.app_timezone,
        mysql_database=settings.mysql_database,
        llm_enabled=settings.llm_enabled,
        summary_enabled=settings.summary_enabled,
        summary_schedule_type=settings.summary_schedule_type,
        smtp_from_email=settings.smtp_from_email,
        mail_parse_attachments=settings.mail_parse_attachments,
    )
