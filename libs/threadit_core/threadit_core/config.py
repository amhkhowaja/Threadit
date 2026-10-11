from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="THREADIT_", env_file=".env", extra="ignore")

    environment: str = Field(default="dev")
    log_level: str = Field(default="INFO")

    aws_region: str = Field(default="us-east-1")
    # Floci endpoint in dev (http://localhost:4566); unset/None in prod (real AWS).
    aws_endpoint_url: str | None = Field(default=None)

    table_name: str = Field(default="threadit")

    # Cognito (claims trusted from the API Gateway authorizer in P1).
    cognito_issuer: str | None = Field(default=None)
    cognito_audience: str | None = Field(default=None)

    # Contract size caps (I6).
    max_title_len: int = Field(default=300)
    max_body_len: int = Field(default=40_000)
    max_text_len: int = Field(default=10_000)
    default_page_limit: int = Field(default=20)
    max_page_limit: int = Field(default=100)

    # Threading (D3).
    max_comment_depth: int = Field(default=8)

    # Idempotency sentinel TTL (I8).
    idempotency_ttl_seconds: int = Field(default=86_400)


def load_settings() -> Settings:
    return Settings()
