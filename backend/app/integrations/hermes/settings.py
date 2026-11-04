"""Agent settings (see backend/app/integrations/hermes/CONTRACT.md, section 2)."""

from __future__ import annotations

import re
from typing import Final, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import Settings

_LOOPBACK_HOSTS: Final = frozenset({"127.0.0.1", "localhost"})
_MODEL_NAME_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:\-]{0,127}$")


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DRAKTER_",
        env_file=Settings.model_config.get("env_file"),
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
        populate_by_name=True,
    )

    env: Literal["development", "production"] = "development"
    agent_provider: Literal["hermes", "fake"] = "hermes"
    model_provider: Literal["anthropic", "dev_stub"] = "anthropic"
    model_name: str = "claude-haiku-5-5"
    dev_stub_url: str = "http://127.0.0.1:28517"
    hermes_command: str = "hermes"
    hermes_port: int = Field(default=8767, ge=1024, le=65535)
    agent_tools_port: int = Field(default=8766, ge=1024, le=65535)
    agent_max_turns: int = Field(default=12, ge=1, le=200)
    turn_timeout_s: float = Field(default=300, gt=0)
    idle_timeout_s: float = Field(default=120, gt=0)
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    @field_validator("model_name")
    @classmethod
    def _valid_model_name(cls, value: str) -> str:
        if not _MODEL_NAME_RE.fullmatch(value):
            raise ValueError("model_name has unexpected characters")
        return value

    @field_validator("hermes_command")
    @classmethod
    def _valid_command(cls, value: str) -> str:
        if not value or value != value.strip() or "\x00" in value:
            raise ValueError("hermes_command must be one executable, without arguments")
        return value

    @field_validator("dev_stub_url")
    @classmethod
    def _loopback_stub(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme != "http" or parts.hostname not in _LOOPBACK_HOSTS or parts.username or parts.password:
            raise ValueError("dev_stub_url must be plain http on loopback")
        if parts.path not in ("", "/") or parts.query or parts.fragment:
            raise ValueError("dev_stub_url must not have a path, query or fragment")
        return value.rstrip("/")

    @model_validator(mode="after")
    def _coherent(self) -> Self:
        if self.model_provider == "dev_stub" and self.env == "production":
            raise ValueError("model_provider=dev_stub is not allowed with env=production")
        if self.hermes_port == self.agent_tools_port:
            raise ValueError("hermes_port and agent_tools_port must differ")
        return self
