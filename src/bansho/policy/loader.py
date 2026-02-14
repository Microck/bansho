from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from bansho.policy.models import Policy

DEFAULT_POLICY_PATH = Path("config/policies.yaml")


class PolicyLoadError(RuntimeError):
    pass


def load_policy(path: str | Path = DEFAULT_POLICY_PATH) -> Policy:
    policy_path = Path(path)

    try:
        raw_policy = policy_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PolicyLoadError(f"Policy file not found: {policy_path}") from exc
    except OSError as exc:
        raise PolicyLoadError(f"Unable to read policy file: {policy_path}") from exc

    try:
        loaded_data = yaml.safe_load(raw_policy)
    except yaml.YAMLError as exc:
        raise PolicyLoadError(f"Policy file is not valid YAML: {policy_path}") from exc

    if not isinstance(loaded_data, dict):
        raise PolicyLoadError("Policy file must contain a top-level mapping.")

    return _validate_policy(loaded_data, policy_path)


def _validate_policy(loaded_data: dict[str, Any], policy_path: Path) -> Policy:
    try:
        return Policy.model_validate(loaded_data)
    except ValidationError as exc:
        raise PolicyLoadError(f"Policy file failed schema validation: {policy_path}") from exc


__all__ = ["DEFAULT_POLICY_PATH", "PolicyLoadError", "load_policy"]
