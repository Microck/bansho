from __future__ import annotations

import json
from datetime import UTC, datetime
from math import isfinite
from typing import Any, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | dict[str, Any] | list[Any]

MAX_JSON_BYTES = 4_096
MAX_JSON_DEPTH = 6
MAX_JSON_ITEMS = 40
MAX_JSON_KEY_CHARS = 64
MAX_JSON_STRING_CHARS = 512
REDACTED_VALUE = "[REDACTED]"
TRUNCATED_VALUE = "[TRUNCATED]"

_SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "password",
    "secret",
    "token",
    "x-api-key",
}


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    api_key_id: str | None = None
    role: str = "unknown"
    method: str
    tool_name: str
    request_json: JsonValue = Field(default_factory=dict)
    response_json: JsonValue = Field(default_factory=dict)
    status_code: int = Field(ge=0, le=999)
    latency_ms: int = Field(ge=0)
    decision: JsonValue = Field(default_factory=dict)

    @field_validator("api_key_id", mode="before")
    @classmethod
    def _normalize_api_key_id(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = _normalize_text(value)
        return normalized if normalized else None

    @field_validator("role", mode="before")
    @classmethod
    def _normalize_role(cls, value: Any) -> str:
        normalized = _normalize_text(value)
        if normalized:
            return normalized
        return "unknown"

    @field_validator("method", mode="before")
    @classmethod
    def _normalize_method(cls, value: Any) -> str:
        normalized = _normalize_text(value)
        if not normalized:
            msg = "method must be a non-empty string"
            raise ValueError(msg)
        return normalized.upper()

    @field_validator("tool_name", mode="before")
    @classmethod
    def _normalize_tool_name(cls, value: Any) -> str:
        normalized = _normalize_text(value)
        if not normalized:
            msg = "tool_name must be a non-empty string"
            raise ValueError(msg)
        return normalized

    @field_validator("request_json", "response_json", "decision", mode="before")
    @classmethod
    def _bound_payloads(cls, value: Any) -> JsonValue:
        return _bound_json_payload(value)

    def as_insert_values(
        self,
    ) -> tuple[
        datetime,
        str | None,
        str,
        str,
        str,
        str,
        str,
        int,
        int,
        str,
    ]:
        return (
            self.ts,
            self.api_key_id,
            self.role,
            self.method,
            self.tool_name,
            _serialize_json(self.request_json),
            _serialize_json(self.response_json),
            self.status_code,
            self.latency_ms,
            _serialize_json(self.decision),
        )


def _bound_json_payload(value: Any) -> JsonValue:
    sanitized = _sanitize_json_value(value, depth=0)
    encoded = _serialize_json(sanitized)
    encoded_size = len(encoded.encode("utf-8"))

    if encoded_size <= MAX_JSON_BYTES:
        return sanitized

    preview_chars = max(1, min(MAX_JSON_STRING_CHARS, MAX_JSON_BYTES // 2))
    return {
        "truncated": True,
        "original_bytes": encoded_size,
        "preview": _truncate_text(encoded, max_chars=preview_chars),
    }


def _sanitize_json_value(value: Any, *, depth: int) -> JsonValue:
    if depth >= MAX_JSON_DEPTH:
        return TRUNCATED_VALUE

    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if isfinite(value):
            return value
        return _truncate_text(str(value), max_chars=MAX_JSON_STRING_CHARS)

    if isinstance(value, str):
        return _truncate_text(value, max_chars=MAX_JSON_STRING_CHARS)

    if isinstance(value, bytes):
        return _truncate_text(
            value.decode("utf-8", errors="replace"), max_chars=MAX_JSON_STRING_CHARS
        )

    if isinstance(value, dict):
        sanitized_dict: dict[str, JsonValue] = {}
        items = list(value.items())
        for index, (key, item_value) in enumerate(items):
            if index >= MAX_JSON_ITEMS:
                sanitized_dict["_truncated_items"] = f"{len(items) - MAX_JSON_ITEMS} omitted"
                break

            key_text = _truncate_text(str(key), max_chars=MAX_JSON_KEY_CHARS)
            if key_text.lower() in _SENSITIVE_KEYS:
                sanitized_dict[key_text] = REDACTED_VALUE
                continue

            sanitized_dict[key_text] = _sanitize_json_value(item_value, depth=depth + 1)

        return sanitized_dict

    if isinstance(value, list | tuple | set):
        sanitized_list: list[JsonValue] = []
        for index, item in enumerate(value):
            if index >= MAX_JSON_ITEMS:
                sanitized_list.append(TRUNCATED_VALUE)
                break
            sanitized_list.append(_sanitize_json_value(item, depth=depth + 1))

        return sanitized_list

    return _truncate_text(repr(value), max_chars=MAX_JSON_STRING_CHARS)


def _normalize_text(value: Any) -> str:
    normalized = str(value).strip()
    return _truncate_text(normalized, max_chars=MAX_JSON_STRING_CHARS)


def _truncate_text(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    marker = "..."
    if max_chars <= len(marker):
        return marker[:max_chars]
    return f"{text[: max_chars - len(marker)]}{marker}"


def _serialize_json(value: JsonValue) -> str:
    try:
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        fallback = _truncate_text(repr(value), max_chars=MAX_JSON_STRING_CHARS)
        return json.dumps(
            {
                "unserializable": True,
                "preview": fallback,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )


__all__ = [
    "AuditEvent",
    "JsonValue",
    "MAX_JSON_BYTES",
]
