from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="mail-ds-monitor", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_timezone: str = Field(default="Asia/Shanghai", alias="APP_TIMEZONE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")

    secret_key: str = Field(default="replace-with-a-long-random-string", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    mysql_host: str = Field(default="127.0.0.1", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_database: str = Field(default="mail_ds_monitor", alias="MYSQL_DATABASE")
    mysql_user: str = Field(default="mail_ds_user", alias="MYSQL_USER")
    mysql_password: str = Field(default="replace-with-db-password", alias="MYSQL_PASSWORD")
    mysql_charset: str = Field(default="utf8mb4", alias="MYSQL_CHARSET")
    db_echo: bool = Field(default=False, alias="DB_ECHO")
    db_pool_pre_ping: bool = Field(default=True, alias="DB_POOL_PRE_PING")
    db_auto_create_tables: bool = Field(default=False, alias="DB_AUTO_CREATE_TABLES")

    cors_allow_origins_raw: str = Field(default="", alias="CORS_ALLOW_ORIGINS")

    mail_pull_enabled: bool = Field(default=True, alias="MAIL_PULL_ENABLED")
    mail_pull_default_folder: str = Field(default="INBOX", alias="MAIL_PULL_DEFAULT_FOLDER")
    mail_pull_batch_size: int = Field(default=50, alias="MAIL_PULL_BATCH_SIZE")
    mail_pull_timeout_seconds: int = Field(default=60, alias="MAIL_PULL_TIMEOUT_SECONDS")
    mail_pull_retry_times: int = Field(default=2, alias="MAIL_PULL_RETRY_TIMES")
    mail_parse_attachments: bool = Field(default=False, alias="MAIL_PARSE_ATTACHMENTS")

    llm_enabled: bool = Field(default=True, alias="LLM_ENABLED")
    llm_provider: str = Field(default="openai_compatible", alias="LLM_PROVIDER")
    llm_base_url: str = Field(default="https://api.example.com/v1", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="replace-with-llm-api-key", alias="LLM_API_KEY")
    llm_model: str = Field(default="replace-with-model-name", alias="LLM_MODEL")
    llm_timeout_seconds: int = Field(default=60, alias="LLM_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=2, alias="LLM_MAX_RETRIES")
    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=4096, alias="LLM_MAX_TOKENS")
    llm_extraction_prompt_version: str = Field(default="v1", alias="LLM_EXTRACTION_PROMPT_VERSION")
    llm_summary_prompt_version: str = Field(default="v1", alias="LLM_SUMMARY_PROMPT_VERSION")

    summary_enabled: bool = Field(default=True, alias="SUMMARY_ENABLED")
    summary_schedule_type: str = Field(default="daily", alias="SUMMARY_SCHEDULE_TYPE")
    summary_daily_send_time: str = Field(default="09:00", alias="SUMMARY_DAILY_SEND_TIME")
    summary_timezone: str = Field(default="Asia/Shanghai", alias="SUMMARY_TIMEZONE")
    summary_empty_result_policy: str = Field(default="skip", alias="SUMMARY_EMPTY_RESULT_POLICY")
    summary_use_ai: bool = Field(default=True, alias="SUMMARY_USE_AI")

    smtp_host: str = Field(default="smtp.example.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str = Field(default="replace-with-smtp-username", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="replace-with-smtp-password", alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    smtp_use_ssl: bool = Field(default=False, alias="SMTP_USE_SSL")
    smtp_from_email: str = Field(default="no-reply@example.com", alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="Mail DS Monitor", alias="SMTP_FROM_NAME")
    smtp_timeout_seconds: int = Field(default=30, alias="SMTP_TIMEOUT_SECONDS")

    enable_audit_log: bool = Field(default=True, alias="ENABLE_AUDIT_LOG")
    enable_task_log: bool = Field(default=True, alias="ENABLE_TASK_LOG")

    # 失败邮件捕获自动轮询配置
    capture_poll_enabled: bool = Field(default=False, alias="CAPTURE_POLL_ENABLED")
    capture_poll_interval_minutes: int = Field(default=30, alias="CAPTURE_POLL_INTERVAL_MINUTES")
    capture_poll_lookback_minutes: int = Field(default=30, alias="CAPTURE_POLL_LOOKBACK_MINUTES")

    @field_validator("summary_schedule_type")
    @classmethod
    def validate_summary_schedule_type(cls, value: str) -> str:
        allowed = {"daily"}
        if value not in allowed:
            raise ValueError(f"SUMMARY_SCHEDULE_TYPE must be one of {sorted(allowed)}")
        return value

    @field_validator("summary_empty_result_policy")
    @classmethod
    def validate_summary_empty_result_policy(cls, value: str) -> str:
        allowed = {"skip", "send_empty"}
        if value not in allowed:
            raise ValueError(f"SUMMARY_EMPTY_RESULT_POLICY must be one of {sorted(allowed)}")
        return value

    @field_validator("summary_daily_send_time")
    @classmethod
    def validate_summary_daily_send_time(cls, value: str) -> str:
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError("SUMMARY_DAILY_SEND_TIME must use HH:MM format")

        hour, minute = parts
        if not (hour.isdigit() and minute.isdigit()):
            raise ValueError("SUMMARY_DAILY_SEND_TIME must use HH:MM format")

        if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
            raise ValueError("SUMMARY_DAILY_SEND_TIME must use a valid 24-hour time")
        return value

    @computed_field
    @property
    def cors_allow_origins(self) -> list[str]:
        if not self.cors_allow_origins_raw:
            return []
        return [item.strip() for item in self.cors_allow_origins_raw.split(",") if item.strip()]

    @computed_field
    @property
    def sqlalchemy_database_uri(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset={self.mysql_charset}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
