from __future__ import annotations

from dataclasses import dataclass

from mcp_sentinel.middleware.auth import AuthContext
from mcp_sentinel.policy.models import TOOL_WILDCARD, Policy


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    role: str
    tool_name: str
    reason: str
    matched_rule: str


def authorize_tool(policy: Policy, auth_ctx: AuthContext, tool_name: str) -> AuthorizationDecision:
    normalized_role = auth_ctx.role.strip().lower()
    normalized_tool = tool_name.strip()

    if not normalized_tool:
        return AuthorizationDecision(
            allowed=False,
            role=normalized_role,
            tool_name=normalized_tool,
            reason="empty_tool_name",
            matched_rule="deny:empty_tool_name",
        )

    role_policy = policy.roles.for_role(normalized_role)
    if role_policy is None:
        return AuthorizationDecision(
            allowed=False,
            role=normalized_role,
            tool_name=normalized_tool,
            reason="unknown_role",
            matched_rule="deny:unknown_role",
        )

    if role_policy.allows(normalized_tool):
        matched_tool = TOOL_WILDCARD if TOOL_WILDCARD in role_policy.allow else normalized_tool
        return AuthorizationDecision(
            allowed=True,
            role=normalized_role,
            tool_name=normalized_tool,
            reason="allowed",
            matched_rule=f"roles.{normalized_role}.allow:{matched_tool}",
        )

    if normalized_tool not in _known_tools(policy):
        return AuthorizationDecision(
            allowed=False,
            role=normalized_role,
            tool_name=normalized_tool,
            reason="unknown_tool",
            matched_rule="deny:unknown_tool",
        )

    return AuthorizationDecision(
        allowed=False,
        role=normalized_role,
        tool_name=normalized_tool,
        reason="tool_not_allowed_for_role",
        matched_rule=f"roles.{normalized_role}.allow",
    )


def _known_tools(policy: Policy) -> set[str]:
    known: set[str] = set()

    for role_policy in (policy.roles.admin, policy.roles.user, policy.roles.readonly):
        for allowed_tool in role_policy.allow:
            if allowed_tool != TOOL_WILDCARD:
                known.add(allowed_tool)

    return known


__all__ = ["AuthorizationDecision", "authorize_tool"]
