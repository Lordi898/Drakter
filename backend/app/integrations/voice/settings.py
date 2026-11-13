"""Voice integration settings. Kept apart from app/core/config.py on purpose."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from dotenv import dotenv_values
from platformdirs import user_config_dir, user_data_dir
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/integrations/voice/settings.py -> repository root.
REPO_ROOT: Final = Path(__file__).resolve().parents[4]


def default_voice_python() -> Path:
    """The venv `scripts/install-voice.sh` creates: <data dir>/venvs/voice (py3.12)."""
    return Path(user_data_dir("drakter")) / "venvs" / "voice" / "bin" / "python"


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

    # Voice v2 is on by default; a missing venv only publishes `voice.error{dependency_missing}`.
    voice_enabled: bool = True
    voice_python: Path | None = Field(default_factory=default_voice_python)
    voice_project_root: Path = Field(default=REPO_ROOT)
    # Provisional, uncalibrated (plan §4.4). Written turns are read aloud up to this many
    # characters, closing on a sentence end, then `rest_on_screen` (V-30).
    speak_max_chars_text: int = Field(default=350, ge=50, le=20_000)
    # Same meaning as VoiceConfig.bargein_min_words: below this, a turn heard while the
    # agent is busy does not redirect it (V-22).
    bargein_min_words: int = Field(default=3, ge=1, le=20)

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
