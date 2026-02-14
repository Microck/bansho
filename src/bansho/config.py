from __future__ import annotations

from typing import Literal, cast

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

UpstreamTransport = Literal["stdio", "http"]


class Settings(BaseSettings):
    bansho_listen_host: str = Field(default="127.0.0.1", validation_alias="BANSHO_LISTEN_HOST")
    bansho_listen_port: int = Field(default=9000, validation_alias="BANSHO_LISTEN_PORT")
    dashboard_host: str = Field(default="127.0.0.1", validation_alias="DASHBOARD_HOST")
    dashboard_port: int = Field(default=9100, validation_alias="DASHBOARD_PORT")

    upstream_transport: UpstreamTransport = Field(
        default="stdio", validation_alias="UPSTREAM_TRANSPORT"
    )
    upstream_cmd: str = Field(default="", validation_alias="UPSTREAM_CMD")
    upstream_url: str = Field(default="", validation_alias="UPSTREAM_URL")

    postgres_dsn: PostgresDsn = Field(
        default=cast(PostgresDsn, "postgresql://bansho:bansho@127.0.0.1:5433/bansho"),
        validation_alias="POSTGRES_DSN",
    )
    redis_url: RedisDsn = Field(
        default=cast(RedisDsn, "redis://127.0.0.1:6379/0"),
        validation_alias="REDIS_URL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )
