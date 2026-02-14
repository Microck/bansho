from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from bansho.policy.loader import PolicyLoadError, load_policy


def _write_policy(path: Path, body: str) -> Path:
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_load_policy_loads_valid_yaml_file(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path / "policy.yaml",
        """
        roles:
          admin:
            allow:
              - "*"
          user:
            allow:
              - "tools/list"
          readonly:
            allow: []
        rate_limits:
          per_api_key:
            requests: 120
            window_seconds: 60
          per_tool:
            default:
              requests: 30
              window_seconds: 60
            overrides:
              tools/call:
                requests: 10
                window_seconds: 60
        """,
    )

    policy = load_policy(policy_path)

    assert policy.is_tool_allowed("admin", "any-tool")
    assert policy.is_tool_allowed("user", "tools/list")
    assert not policy.is_tool_allowed("readonly", "tools/list")
    assert policy.rate_limits.per_tool.for_tool("tools/call").requests == 10


def test_load_policy_raises_for_invalid_schema(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path / "invalid-policy.yaml",
        """
        roles: []
        rate_limits:
          per_api_key:
            requests: 120
            window_seconds: 60
          per_tool:
            default:
              requests: 30
              window_seconds: 60
        """,
    )

    with pytest.raises(PolicyLoadError):
        load_policy(policy_path)


def test_load_policy_raises_for_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing-policy.yaml"

    with pytest.raises(PolicyLoadError):
        load_policy(missing_path)
