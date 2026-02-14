from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, cast
from urllib.parse import parse_qs, urlencode, urlparse

from anyio.from_thread import BlockingPortal, start_blocking_portal

from mcp_sentinel.auth.api_keys import resolve_api_key
from mcp_sentinel.config import Settings
from mcp_sentinel.storage.postgres import close_postgres_pool, ensure_schema, get_postgres_pool

DEFAULT_EVENT_LIMIT = 50
MAX_EVENT_LIMIT = 200


@dataclass(frozen=True, slots=True)
class DashboardAuthContext:
    api_key_id: str
    role: str


class DashboardUnauthorizedError(Exception):
    pass


class DashboardForbiddenError(Exception):
    pass


class DashboardHTTPServer(HTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
        *,
        portal: BlockingPortal,
    ) -> None:
        self.portal = portal
        super().__init__(server_address, request_handler_class)


class DashboardRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/", "/dashboard", "/api/events"}:
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"error": {"code": 404, "message": "Not Found"}},
            )
            return

        query_params = parse_qs(parsed.query)

        try:
            auth_context = self._authenticate(query_params)
            filters = _extract_filters(query_params)
            dashboard_server = cast(DashboardHTTPServer, self.server)
            events = dashboard_server.portal.call(
                _fetch_recent_events,
                filters.limit,
                filters.api_key_id,
                filters.tool_name,
            )
        except DashboardUnauthorizedError:
            self._send_json(
                HTTPStatus.UNAUTHORIZED,
                {"error": {"code": 401, "message": "Unauthorized"}},
            )
            return
        except DashboardForbiddenError:
            self._send_json(
                HTTPStatus.FORBIDDEN,
                {"error": {"code": 403, "message": "Forbidden"}},
            )
            return
        except ValueError as exc:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": {"code": 400, "message": str(exc)}},
            )
            return
        except Exception:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": {"code": 500, "message": "Dashboard query failed"}},
            )
            return

        if parsed.path in {"/", "/dashboard"}:
            html = _render_dashboard_html(events=events, filters=filters, auth_context=auth_context)
            self._send_html(HTTPStatus.OK, html)
            return

        if parsed.path == "/api/events":
            self._send_json(
                HTTPStatus.OK,
                {
                    "count": len(events),
                    "filters": {
                        "api_key_id": filters.api_key_id,
                        "tool_name": filters.tool_name,
                        "limit": filters.limit,
                    },
                    "events": events,
                },
            )
            return

        self._send_json(
            HTTPStatus.NOT_FOUND,
            {"error": {"code": 404, "message": "Not Found"}},
        )

    def _authenticate(self, query_params: dict[str, list[str]]) -> DashboardAuthContext:
        presented_api_key = _extract_presented_api_key(self.headers, query_params)
        dashboard_server = cast(DashboardHTTPServer, self.server)
        return dashboard_server.portal.call(_authenticate_admin_api_key, presented_api_key)

    def _send_html(self, status: HTTPStatus, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


@dataclass(frozen=True, slots=True)
class DashboardFilters:
    api_key_id: str | None
    tool_name: str | None
    limit: int


async def _authenticate_admin_api_key(presented_api_key: str | None) -> DashboardAuthContext:
    normalized_api_key = _normalize_string(presented_api_key)
    if normalized_api_key is None:
        raise DashboardUnauthorizedError

    resolved = await resolve_api_key(normalized_api_key)
    if resolved is None:
        raise DashboardUnauthorizedError

    api_key_id = _normalize_string(resolved.get("api_key_id"))
    role = _normalize_string(resolved.get("role"))
    if api_key_id is None or role is None:
        raise DashboardUnauthorizedError

    if role.lower() != "admin":
        raise DashboardForbiddenError

    return DashboardAuthContext(api_key_id=api_key_id, role=role)


async def _fetch_recent_events(
    limit: int,
    api_key_id: str | None,
    tool_name: str | None,
) -> list[dict[str, Any]]:
    pool = await get_postgres_pool()

    conditions: list[str] = []
    values: list[object] = []

    if api_key_id is not None:
        conditions.append(f"api_key_id::text = ${len(values) + 1}")
        values.append(api_key_id)

    if tool_name is not None:
        conditions.append(f"tool_name = ${len(values) + 1}")
        values.append(tool_name)

    limit_placeholder = f"${len(values) + 1}"
    values.append(limit)

    where_clause = ""
    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)

    sql = (
        "SELECT "
        "ts, "
        "api_key_id::text AS api_key_id, "
        "role, "
        "method, "
        "tool_name, "
        "status_code, "
        "latency_ms, "
        "decision, "
        "request_json, "
        "response_json "
        "FROM audit_events"
        f"{where_clause} "
        "ORDER BY ts DESC "
        f"LIMIT {limit_placeholder};"
    )

    async with pool.acquire() as connection:
        rows = await connection.fetch(sql, *values)

    return [
        {
            "ts": _serialize_timestamp(row.get("ts")),
            "api_key_id": _normalize_string(row.get("api_key_id")),
            "role": _normalize_string(row.get("role")) or "unknown",
            "method": _normalize_string(row.get("method")) or "unknown",
            "tool_name": _normalize_string(row.get("tool_name")) or "unknown",
            "status_code": int(row.get("status_code") or 0),
            "latency_ms": int(row.get("latency_ms") or 0),
            "decision": _coerce_json_value(row.get("decision")),
            "request_json": _coerce_json_value(row.get("request_json")),
            "response_json": _coerce_json_value(row.get("response_json")),
        }
        for row in rows
    ]


def _extract_filters(query_params: dict[str, list[str]]) -> DashboardFilters:
    api_key_id = _normalize_string(_first(query_params.get("api_key_id")))
    tool_name = _normalize_string(_first(query_params.get("tool_name")))
    limit = _parse_limit(_first(query_params.get("limit")))
    return DashboardFilters(api_key_id=api_key_id, tool_name=tool_name, limit=limit)


def _extract_presented_api_key(
    headers: Any,
    query_params: dict[str, list[str]],
) -> str | None:
    authorization = _normalize_string(headers.get("Authorization"))
    if authorization is not None:
        parts = authorization.split(maxsplit=1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            bearer_token = _normalize_string(parts[1])
            if bearer_token is not None:
                return bearer_token

    header_api_key = _normalize_string(headers.get("X-API-Key"))
    if header_api_key is not None:
        return header_api_key

    query_api_key = _normalize_string(_first(query_params.get("api_key")))
    return query_api_key


def _parse_limit(limit_value: str | None) -> int:
    if limit_value is None:
        return DEFAULT_EVENT_LIMIT

    try:
        parsed_limit = int(limit_value)
    except ValueError as exc:
        msg = "limit must be an integer"
        raise ValueError(msg) from exc

    if parsed_limit < 1 or parsed_limit > MAX_EVENT_LIMIT:
        msg = f"limit must be between 1 and {MAX_EVENT_LIMIT}"
        raise ValueError(msg)

    return parsed_limit


def _serialize_timestamp(value: object) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC).isoformat()
        return value.isoformat()
    return ""


def _coerce_json_value(value: object) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _first(values: list[str] | None) -> str | None:
    if not values:
        return None
    return values[0]


def _normalize_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _render_dashboard_html(
    *,
    events: list[dict[str, Any]],
    filters: DashboardFilters,
    auth_context: DashboardAuthContext,
) -> str:
    filters_query = {
        "limit": str(filters.limit),
    }
    if filters.api_key_id is not None:
        filters_query["api_key_id"] = filters.api_key_id
    if filters.tool_name is not None:
        filters_query["tool_name"] = filters.tool_name
    api_href = f"/api/events?{urlencode(filters_query)}"

    rows_html = "\n".join(_render_event_row(event) for event in events)
    if not rows_html:
        rows_html = "<tr><td colspan='8'>No audit events found for the current filters.</td></tr>"

    api_key_value = escape(filters.api_key_id or "")
    tool_name_value = escape(filters.tool_name or "")

    return (
        "<!doctype html>"
        "<html lang='en'>"
        "<head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>MCP Sentinel Audit Dashboard</title>"
        "<style>"
        "body{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;"
        "margin:24px;background:#f5f7fb;color:#111827;}"
        "h1{margin:0 0 12px 0;font-size:24px;}"
        "p{margin:0 0 16px 0;}"
        "form{display:flex;flex-wrap:wrap;gap:12px;margin:0 0 16px 0;padding:12px;"
        "background:#ffffff;border:1px solid #d1d5db;border-radius:8px;}"
        "label{display:flex;flex-direction:column;font-size:12px;gap:6px;}"
        "input{padding:8px;border:1px solid #9ca3af;border-radius:6px;min-width:220px;}"
        "button{padding:8px 12px;border:1px solid #374151;background:#111827;color:#fff;"
        "border-radius:6px;cursor:pointer;}"
        "a{color:#1d4ed8;text-decoration:none;}"
        "table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #d1d5db;}"
        "th,td{padding:8px;vertical-align:top;border-bottom:1px solid #e5e7eb;text-align:left;}"
        "th{background:#f3f4f6;font-size:12px;text-transform:uppercase;letter-spacing:0.04em;}"
        "code{font-size:12px;white-space:pre-wrap;word-break:break-word;}"
        "</style>"
        "</head>"
        "<body>"
        "<h1>MCP Sentinel Audit Dashboard</h1>"
        f"<p>Authenticated as admin key ID: <strong>{escape(auth_context.api_key_id)}</strong></p>"
        "<form method='get' action='/dashboard'>"
        "<label>API Key ID"
        f"<input type='text' name='api_key_id' value='{api_key_value}'></label>"
        "<label>Tool Name"
        f"<input type='text' name='tool_name' value='{tool_name_value}'></label>"
        "<label>Limit"
        f"<input type='number' min='1' max='{MAX_EVENT_LIMIT}' name='limit'"
        f" value='{filters.limit}'></label>"
        "<button type='submit'>Apply filters</button>"
        f"<a href='{escape(api_href)}'>JSON API</a>"
        "</form>"
        "<table>"
        "<thead><tr>"
        "<th>Timestamp</th><th>API Key ID</th><th>Role</th><th>Method</th>"
        "<th>Tool</th><th>Status</th><th>Latency (ms)</th><th>Decision</th>"
        "</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table>"
        "</body></html>"
    )


def _render_event_row(event: dict[str, Any]) -> str:
    decision_json = escape(json.dumps(event.get("decision"), ensure_ascii=True))
    return (
        "<tr>"
        f"<td>{escape(str(event.get('ts', '')))}</td>"
        f"<td>{escape(str(event.get('api_key_id') or ''))}</td>"
        f"<td>{escape(str(event.get('role') or ''))}</td>"
        f"<td>{escape(str(event.get('method') or ''))}</td>"
        f"<td>{escape(str(event.get('tool_name') or ''))}</td>"
        f"<td>{escape(str(event.get('status_code') or ''))}</td>"
        f"<td>{escape(str(event.get('latency_ms') or ''))}</td>"
        f"<td><code>{decision_json}</code></td>"
        "</tr>"
    )


def run_dashboard_server(settings: Settings | None = None) -> None:
    resolved_settings = settings or Settings()
    bind_addr = (resolved_settings.dashboard_host, resolved_settings.dashboard_port)

    with start_blocking_portal() as portal:
        portal.call(ensure_schema)
        server = DashboardHTTPServer(
            bind_addr,
            DashboardRequestHandler,
            portal=portal,
        )

        try:
            server.serve_forever()
        finally:
            server.server_close()
            portal.call(close_postgres_pool)


__all__ = ["run_dashboard_server"]
