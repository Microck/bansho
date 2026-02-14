from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RoleName = Literal["admin", "user", "readonly"]
TOOL_WILDCARD = "*"


class RoleToolPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow: list[str] = Field(default_factory=list)

    @field_validator("allow")
    @classmethod
    def validate_allow_list(cls, tools: list[str]) -> list[str]:
        normalized: list[str] = []
        for tool in tools:
            tool_name = tool.strip()
            if not tool_name:
                msg = "tool names in role allow lists must be non-empty"
                raise ValueError(msg)

            if tool_name == TOOL_WILDCARD:
                return [TOOL_WILDCARD]

            if tool_name not in normalized:
                normalized.append(tool_name)

        return normalized

    def allows(self, tool_name: str) -> bool:
        normalized_tool = tool_name.strip()
        if not normalized_tool:
            return False
        return TOOL_WILDCARD in self.allow or normalized_tool in self.allow


class RolesPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    admin: RoleToolPolicy = Field(default_factory=lambda: RoleToolPolicy(allow=[TOOL_WILDCARD]))
    user: RoleToolPolicy = Field(default_factory=RoleToolPolicy)
    readonly: RoleToolPolicy = Field(default_factory=RoleToolPolicy)

    def for_role(self, role: str) -> RoleToolPolicy | None:
        normalized_role = role.strip().lower()
        if normalized_role == "admin":
            return self.admin
        if normalized_role == "user":
            return self.user
        if normalized_role == "readonly":
            return self.readonly
        return None


class RateLimitWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requests: int = Field(default=60, gt=0)
    window_seconds: int = Field(default=60, gt=0)


class ToolRateLimitPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default: RateLimitWindow = Field(
        default_factory=lambda: RateLimitWindow(requests=30, window_seconds=60)
    )
    overrides: dict[str, RateLimitWindow] = Field(default_factory=dict)

    @field_validator("overrides")
    @classmethod
    def validate_tool_override_names(
        cls,
        overrides: dict[str, RateLimitWindow],
    ) -> dict[str, RateLimitWindow]:
        normalized: dict[str, RateLimitWindow] = {}
        for tool_name, limit in overrides.items():
            clean_name = tool_name.strip()
            if not clean_name:
                msg = "tool override names must be non-empty"
                raise ValueError(msg)
            normalized[clean_name] = limit
        return normalized

    def for_tool(self, tool_name: str) -> RateLimitWindow:
        normalized_tool = tool_name.strip()
        if not normalized_tool:
            return self.default
        return self.overrides.get(normalized_tool, self.default)


class RateLimitsPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    per_api_key: RateLimitWindow = Field(
        default_factory=lambda: RateLimitWindow(requests=120, window_seconds=60)
    )
    per_tool: ToolRateLimitPolicy = Field(default_factory=ToolRateLimitPolicy)


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roles: RolesPolicy = Field(default_factory=RolesPolicy)
    rate_limits: RateLimitsPolicy = Field(default_factory=RateLimitsPolicy)

    def is_tool_allowed(self, role: str, tool_name: str) -> bool:
        role_policy = self.roles.for_role(role)
        if role_policy is None:
            return False
        return role_policy.allows(tool_name)


__all__ = [
    "Policy",
    "RateLimitsPolicy",
    "RateLimitWindow",
    "RoleName",
    "RolesPolicy",
    "RoleToolPolicy",
    "TOOL_WILDCARD",
    "ToolRateLimitPolicy",
]
