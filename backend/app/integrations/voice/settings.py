"""Voice integration settings. Kept apart from app/core/config.py on purpose."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from dotenv import dotenv_values
from platformdirs import user_config_dir
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/integrations/voice/settings.py -> repository root.
_REPO_ROOT: Final = Path(__file__).resolve().parents[4]


def env_file() -> Path:
    """Same per-user file as app.core.config.Settings."""
    return Path(user_config_dir("drakter")) / ".env"


class VoiceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DRAKTER_",
        env_file=env_file(),
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # an empty `KEY=` in .env means "default", not ""
        extra="ignore",
        frozen=True,
    )

    voice_enabled: bool = False
    voice_python: Path | None = None
    voice_project_root: Path = Field(default=_REPO_ROOT)

    @field_validator("voice_python", "voice_project_root", mode="after")
    @classmethod
    def _absolute(cls, value: Path | None) -> Path | None:
        if value is None:
            return None
        value = value.expanduser()
        if not value.is_absolute():
            raise ValueError("path must be absolute")
        return value


def load_voice_settings() -> VoiceSettings:
    """Resolve the ``.env`` at call time, like app.core.config.load_settings."""
    return VoiceSettings(_env_file=env_file())  # type: ignore[call-arg]


def read_env_file(path: Path | None = None) -> dict[str, str]:
    """Raw values of the per-user file. Callers MUST filter them through a whitelist."""
    try:
        values = dotenv_values(path or env_file(), interpolate=False)
    except OSError:
        return {}
    return {key: value for key, value in values.items() if value is not None}
