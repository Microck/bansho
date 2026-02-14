from __future__ import annotations

import json
from types import TracebackType
from typing import Any, cast
from uuid import UUID

import pytest

import bansho.audit.logger as audit_logger_module
from bansho.audit.logger import AuditLogger
from bansho.audit.models import AuditEvent


class FakeConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def execute(self, query: str, *args: Any) -> str:
        self.calls.append((query, args))
        return "INSERT 0 1"


class FakeAcquireContext:
    def __init__(self, connection: FakeConnection) -> None:
        self._connection = connection

    async def __aenter__(self) -> FakeConnection:
        return self._connection

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        _ = (exc_type, exc, traceback)
        return False


class FakePool:
    def __init__(self, connection: FakeConnection) -> None:
        self._connection = connection

    def acquire(self) -> FakeAcquireContext:
        return FakeAcquireContext(self._connection)


@pytest.mark.anyio
async def test_audit_logger_inserts_redacted_event_payload() -> None:
    connection = FakeConnection()
    logger = AuditLogger(pool=cast(Any, FakePool(connection)))

    event = AuditEvent(
        api_key_id="00000000-0000-0000-0000-000000000123",
        role="user",
        method="tools/call",
        tool_name="public.echo",
        request_json={
            "api_key": "bansho-secret-key",
            "arguments": {"text": "hello"},
        },
        response_json={"result": "ok"},
        status_code=200,
        latency_ms=15,
        decision={
            "auth": {"allowed": True},
            "authz": {"allowed": True},
            "rate": {"allowed": True},
        },
    )

    await logger.log_event(event)

    assert len(connection.calls) == 1
    sql, args = connection.calls[0]
    assert "INSERT INTO audit_events" in sql
    assert isinstance(args[0], UUID)
    assert args[2] == UUID("00000000-0000-0000-0000-000000000123")
    assert args[3] == "user"
    assert args[4] == "TOOLS/CALL"

    request_payload = json.loads(cast(str, args[6]))
    decision_payload = json.loads(cast(str, args[10]))

    assert request_payload["api_key"] == "[REDACTED]"
    assert request_payload["arguments"]["text"] == "hello"
    assert decision_payload["auth"]["allowed"] is True
    assert decision_payload["rate"]["allowed"] is True


@pytest.mark.anyio
async def test_audit_logger_uses_shared_postgres_pool_when_not_injected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection()
    fake_pool = FakePool(connection)

    async def fake_get_postgres_pool() -> Any:
        return fake_pool

    monkeypatch.setattr(audit_logger_module, "get_postgres_pool", fake_get_postgres_pool)

    logger = AuditLogger()
    event = AuditEvent(
        api_key_id="not-a-uuid",
        role="readonly",
        method="tools/list",
        tool_name="public.echo",
        request_json={"query": "all"},
        response_json={"tools": ["public.echo"]},
        status_code=200,
        latency_ms=5,
        decision={"auth": {"allowed": True}},
    )

    await logger.log_event(event)

    assert len(connection.calls) == 1
    _, args = connection.calls[0]
    assert args[2] is None
    assert args[3] == "readonly"
