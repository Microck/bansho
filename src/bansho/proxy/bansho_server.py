from __future__ import annotations

import os
import sys
from time import perf_counter
from typing import Any

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError

from bansho.audit.logger import AuditLogger
from bansho.audit.models import AuditEvent
from bansho.config import Settings
from bansho.middleware import AuthContext, authenticate_request
from bansho.middleware.authz import AuthorizationDecision, authorize_tool
from bansho.middleware.rate_limit import RateLimitDecision, enforce_rate_limit
from bansho.policy.loader import DEFAULT_POLICY_PATH, load_policy
from bansho.policy.models import Policy
from bansho.proxy.upstream import UpstreamConnector

_FORBIDDEN_ERROR = types.ErrorData(code=403, message="Forbidden")
_INTERNAL_ERROR_MESSAGE = "Internal Server Error"
_UPSTREAM_FAILURE_MESSAGE = "Upstream request failed"
_NOT_EVALUATED_REASON = "not_evaluated"


def create_bansho_server(
    connector: UpstreamConnector,
    *,
    policy: Policy,
    audit_logger: AuditLogger | None = None,
) -> Server[Any, Any]:
    server = Server("bansho")
    resolved_audit_logger = audit_logger or AuditLogger()

    async def handle_list_tools(req: types.ListToolsRequest) -> types.ServerResult:
        auth_context = await _authenticate(server)
        listed_tools = await connector.list_tools(req.params)
        filtered_tools = [
            tool
            for tool in listed_tools.tools
            if authorize_tool(policy, auth_context, tool.name).allowed
        ]
        return types.ServerResult(listed_tools.model_copy(update={"tools": filtered_tools}))

    async def handle_call_tool(req: types.CallToolRequest) -> types.ServerResult:
        tool_name = req.params.name
        started_at = perf_counter()

        auth_context: AuthContext | None = None
        status_code = 500
        decision = _default_decision_payload()
        response_json: dict[str, Any] = _safe_error_payload(
            code=500, message=_INTERNAL_ERROR_MESSAGE
        )
        upstream_called = False

        try:
            auth_context = await _authenticate(server)
            decision["auth"] = {
                "allowed": True,
                "api_key_id": auth_context.api_key_id,
                "role": auth_context.role,
            }

            authz_decision = authorize_tool(policy, auth_context, tool_name)
            decision["authz"] = _authz_decision_payload(authz_decision)
            if not authz_decision.allowed:
                status_code = _normalize_status_code(_FORBIDDEN_ERROR.code, default=403)
                response_json = _safe_mcp_error_payload(_FORBIDDEN_ERROR)
                raise McpError(_FORBIDDEN_ERROR)

            rate_decision = await enforce_rate_limit(policy, auth_context, tool_name)
            decision["rate"] = _rate_limit_decision_payload(rate_decision)

            upstream_called = True
            upstream_result = await connector.call_tool(
                name=tool_name, arguments=req.params.arguments
            )
            status_code = 200
            response_json = upstream_result.model_dump(mode="json", exclude_none=True)
            return types.ServerResult(upstream_result)
        except McpError as exc:
            status_code = _normalize_status_code(exc.error.code, default=500)
            response_json = _safe_mcp_error_payload(exc.error)

            if status_code == 401:
                decision["auth"] = {
                    "allowed": False,
                    "reason": "unauthorized",
                }
            elif status_code == 429:
                decision["rate"] = {
                    "allowed": False,
                    "reason": "too_many_requests",
                }

            raise
        except Exception as exc:
            status_code = 502 if upstream_called else 500
            response_json = _safe_exception_payload(status_code=status_code, exc=exc)
            raise
        finally:
            latency_ms = max(int((perf_counter() - started_at) * 1000), 0)
            await _write_audit_event(
                audit_logger=resolved_audit_logger,
                event=AuditEvent(
                    api_key_id=auth_context.api_key_id if auth_context is not None else None,
                    role=auth_context.role if auth_context is not None else "unknown",
                    method="tools/call",
                    tool_name=tool_name,
                    request_json=_request_payload(req),
                    response_json=response_json,
                    status_code=status_code,
                    latency_ms=latency_ms,
                    decision=decision,
                ),
            )

    async def handle_list_resources(req: types.ListResourcesRequest) -> types.ServerResult:
        return types.ServerResult(await connector.list_resources(req.params))

    async def handle_read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
        return types.ServerResult(await connector.read_resource(req.params.uri))

    async def handle_list_prompts(req: types.ListPromptsRequest) -> types.ServerResult:
        return types.ServerResult(await connector.list_prompts(req.params))

    async def handle_get_prompt(req: types.GetPromptRequest) -> types.ServerResult:
        return types.ServerResult(
            await connector.get_prompt(name=req.params.name, arguments=req.params.arguments)
        )

    server.request_handlers[types.ListToolsRequest] = handle_list_tools
    server.request_handlers[types.CallToolRequest] = handle_call_tool
    server.request_handlers[types.ListResourcesRequest] = handle_list_resources
    server.request_handlers[types.ReadResourceRequest] = handle_read_resource
    server.request_handlers[types.ListPromptsRequest] = handle_list_prompts
    server.request_handlers[types.GetPromptRequest] = handle_get_prompt

    return server


async def _authenticate(server: Server[Any, Any]) -> AuthContext:
    return await authenticate_request(_request_context(server))


def _request_context(server: Server[Any, Any]) -> Any | None:
    try:
        return server.request_context
    except LookupError:
        return None


def _default_decision_payload() -> dict[str, Any]:
    return {
        "auth": {
            "allowed": False,
            "reason": _NOT_EVALUATED_REASON,
        },
        "authz": {
            "allowed": False,
            "reason": _NOT_EVALUATED_REASON,
        },
        "rate": {
            "allowed": False,
            "reason": _NOT_EVALUATED_REASON,
        },
    }


def _authz_decision_payload(decision: AuthorizationDecision) -> dict[str, Any]:
    return {
        "allowed": decision.allowed,
        "role": decision.role,
        "reason": decision.reason,
        "matched_rule": decision.matched_rule,
    }


def _rate_limit_decision_payload(decision: RateLimitDecision) -> dict[str, Any]:
    return {
        "allowed": True,
        "reason": "within_limits",
        "tool_name": decision.tool_name,
        "per_api_key": {
            "allowed": decision.per_api_key.allowed,
            "remaining": decision.per_api_key.remaining,
            "reset_s": decision.per_api_key.reset_s,
        },
        "per_tool": {
            "allowed": decision.per_tool.allowed,
            "remaining": decision.per_tool.remaining,
            "reset_s": decision.per_tool.reset_s,
        },
    }


def _request_payload(req: types.CallToolRequest) -> dict[str, Any]:
    return {
        "name": req.params.name,
        "arguments": req.params.arguments or {},
    }


def _safe_mcp_error_payload(error: types.ErrorData) -> dict[str, Any]:
    return _safe_error_payload(
        code=_normalize_status_code(error.code, default=500),
        message=error.message,
    )


def _safe_exception_payload(*, status_code: int, exc: Exception) -> dict[str, Any]:
    message = _UPSTREAM_FAILURE_MESSAGE if status_code == 502 else _INTERNAL_ERROR_MESSAGE
    return {
        "error": {
            "code": status_code,
            "message": message,
            "type": type(exc).__name__,
        }
    }


def _safe_error_payload(*, code: int, message: str) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
        }
    }


def _normalize_status_code(code: object, *, default: int) -> int:
    if isinstance(code, int) and 0 <= code <= 999:
        return code
    return default


async def _write_audit_event(*, audit_logger: AuditLogger, event: AuditEvent) -> None:
    try:
        await audit_logger.log_event(event)
    except Exception as exc:
        print(
            "audit_log_failed"
            f" method={event.method}"
            f" tool={event.tool_name}"
            f" status={event.status_code}"
            f" error_type={type(exc).__name__}",
            file=sys.stderr,
            flush=True,
        )


def _upstream_target(settings: Settings) -> str:
    if settings.upstream_transport == "stdio":
        return settings.upstream_cmd
    return settings.upstream_url


async def run_stdio_proxy(settings: Settings | None = None) -> None:
    resolved_settings = settings or Settings()
    connector = UpstreamConnector(resolved_settings)
    policy_path = os.environ.get("BANSHO_POLICY_PATH", str(DEFAULT_POLICY_PATH))
    policy = load_policy(policy_path)

    try:
        upstream_init = await connector.initialize()
        server = create_bansho_server(connector, policy=policy)

        initialization_options = InitializationOptions(
            server_name=upstream_init.serverInfo.name,
            server_version=upstream_init.serverInfo.version,
            capabilities=upstream_init.capabilities,
            instructions=upstream_init.instructions,
        )

        print(
            "bansho_proxy_start"
            f" listen_addr={resolved_settings.bansho_listen_host}"
            f":{resolved_settings.bansho_listen_port}"
            f" upstream_transport={resolved_settings.upstream_transport}"
            f" upstream_target={_upstream_target(resolved_settings)}",
            f" policy_path={policy_path}",
            file=sys.stderr,
            flush=True,
        )

        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, initialization_options)
    finally:
        await connector.aclose()
