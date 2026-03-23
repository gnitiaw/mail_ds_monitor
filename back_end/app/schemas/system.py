from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    timezone: str


class AppMetaResponse(BaseModel):
    app_name: str
    api_prefix: str
    timezone: str
    mysql_database: str
    llm_enabled: bool
    summary_enabled: bool
    summary_schedule_type: str
    smtp_from_email: str
    mail_parse_attachments: bool
