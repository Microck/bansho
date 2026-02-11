from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    sentinel_listen_host: str = "127.0.0.1"
    sentinel_listen_port: int = 9000

    upstream_transport: str = "stdio"  # stdio|http
    upstream_cmd: str = ""
    upstream_url: str = ""

    postgres_dsn: str = "postgresql://sentinel:sentinel@127.0.0.1:5432/mcp_sentinel"
    redis_url: str = "redis://127.0.0.1:6379/0"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }
