from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "sentry-workflow"
    environment: str = "development"

    mongodb_uri: str
    mongodb_database: str = "sentry_workflow"

    redis_url: str = "redis://localhost:6379"

    sentry_base_url: str = "https://sentry.io"
    sentry_auth_token: str | None = None
    sentry_org_slug: str | None = None
    sentry_webhook_secret: str | None = None

    slack_base_url: str = "https://slack.com/api"
    slack_bot_token: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
