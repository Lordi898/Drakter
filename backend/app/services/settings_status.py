"""Agent configuration status. Presence only: secrets are never read, stored or logged."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Final

import platformdirs

from app.services.settings_models import AgentConfigStatus, DevModeState, KeyState

_DEV_VALUES: Final = frozenset({"dev", "fake", "dev_stub"})
_PUBLIC_PROVIDERS: Final = frozenset({"hermes", "dev", "fake"})


def _from_settings(cfg: Any) -> AgentConfigStatus:
    key: KeyState = "configured" if getattr(cfg, "anthropic_api_key", None) is not None else "missing"
    agent_provider = getattr(cfg, "agent_provider", None)
    model_provider = getattr(cfg, "model_provider", None)
    dev = agent_provider in {"dev", "fake"} or model_provider == "dev_stub"
    return AgentConfigStatus(
        key=key,
        dev_mode="active" if dev else "inactive",
        provider=agent_provider if isinstance(agent_provider, str) else None,
        model=getattr(cfg, "model_name", None),
    )


def _from_environment() -> AgentConfigStatus:
    env_file = Path(platformdirs.user_config_dir("drakter")) / ".env"
    env_exists = env_file.exists()

    key: KeyState
    if os.environ.get("ANTHROPIC_API_KEY"):
        key = "configured"
    else:
        key = "unknown" if env_exists else "missing"

    agent = os.environ.get("DRAKTER_AGENT_PROVIDER") or None
    model = os.environ.get("DRAKTER_MODEL_PROVIDER") or None
    dev_mode: DevModeState
    if (agent in _DEV_VALUES) or (model in _DEV_VALUES):
        dev_mode = "active"
    elif not env_exists:
        dev_mode = "inactive"
    elif agent is None or model is None:
        dev_mode = "unknown"
    else:
        dev_mode = "inactive"

    return AgentConfigStatus(
        key=key,
        dev_mode=dev_mode,
        provider=agent if agent in _PUBLIC_PROVIDERS else None,
        model=None,
    )


def agent_config_status(state: Any) -> AgentConfigStatus:
    cfg = getattr(state, "agent_settings", None)
    if cfg is not None:
        return _from_settings(cfg)
    return _from_environment()
