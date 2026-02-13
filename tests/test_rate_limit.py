from __future__ import annotations

from collections.abc import Sequence

import pytest

from mcp_sentinel.ratelimit import limiter as limiter_module


@pytest.fixture
def fake_redis_eval(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, int], list[tuple[str, str, int]]]:
    counters: dict[str, int] = {}
    invocations: list[tuple[str, str, int]] = []

    async def fake_eval(
        script: str,
        keys: Sequence[str] | None = None,
        args: Sequence[str | bytes | int | float] | None = None,
    ) -> int:
        key_list = list(keys or [])
        arg_list = list(args or [])
        assert len(key_list) == 1
        assert len(arg_list) == 1

        key = key_list[0]
        ttl = int(arg_list[0])
        counters[key] = counters.get(key, 0) + 1
        invocations.append((script, key, ttl))
        return counters[key]

    monkeypatch.setattr(limiter_module, "redis_eval", fake_eval)
    return counters, invocations


@pytest.mark.anyio
async def test_limiter_uses_expected_key_patterns_and_atomic_script(
    fake_redis_eval: tuple[dict[str, int], list[tuple[str, str, int]]],
) -> None:
    counters, invocations = fake_redis_eval

    per_key_result = await limiter_module.check_api_key_limit(
        api_key_id="key-123",
        requests=2,
        window_seconds=10,
        now_s=21,
    )
    per_tool_result = await limiter_module.check_tool_limit(
        api_key_id="key-123",
        tool_name="public.echo",
        requests=2,
        window_seconds=10,
        now_s=21,
    )

    assert per_key_result.allowed is True
    assert per_key_result.remaining == 1
    assert per_key_result.reset_s == 9

    assert per_tool_result.allowed is True
    assert per_tool_result.remaining == 1
    assert per_tool_result.reset_s == 9

    assert counters == {
        "rl:key-123:2": 1,
        "rl:key-123:public.echo:2": 1,
    }

    assert len(invocations) == 2
    assert "INCR" in invocations[0][0]
    assert "EXPIRE" in invocations[0][0]
    assert invocations[0][2] == 9


@pytest.mark.anyio
async def test_limiter_resets_when_window_changes(
    fake_redis_eval: tuple[dict[str, int], list[tuple[str, str, int]]],
) -> None:
    _, invocations = fake_redis_eval

    within_window = await limiter_module.check_api_key_limit(
        api_key_id="key-abc",
        requests=1,
        window_seconds=10,
        now_s=9,
    )
    exceeded_window = await limiter_module.check_api_key_limit(
        api_key_id="key-abc",
        requests=1,
        window_seconds=10,
        now_s=9,
    )
    new_window = await limiter_module.check_api_key_limit(
        api_key_id="key-abc",
        requests=1,
        window_seconds=10,
        now_s=10,
    )

    assert within_window.allowed is True
    assert within_window.remaining == 0
    assert within_window.reset_s == 1

    assert exceeded_window.allowed is False
    assert exceeded_window.remaining == 0
    assert exceeded_window.reset_s == 1

    assert new_window.allowed is True
    assert new_window.remaining == 0
    assert new_window.reset_s == 10

    assert invocations[0][1] == "rl:key-abc:0"
    assert invocations[1][1] == "rl:key-abc:0"
    assert invocations[2][1] == "rl:key-abc:1"
