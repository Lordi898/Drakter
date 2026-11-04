"""Application settings (see backend/CONTRACT.md, section app/core/config.py)."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Final, Literal

from platformdirs import user_config_dir, user_data_dir
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BIND_HOST: Final = "127.0.0.1"

_APP_NAME: Final = "drakter"


def _env_file() -> Path:
    return Path(user_config_dir(_APP_NAME)) / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DRAKTER_",
        env_file=_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    data_dir: Path = Field(default_factory=lambda: Path(user_data_dir(_APP_NAME)))
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("data_dir", mode="after")
    @classmethod
    def _absolute_dir(cls, value: Path) -> Path:
        value = value.expanduser()
        if not value.is_absolute():
            raise ValueError("directory must be an absolute path")
        return value

    @property
    def db_path(self) -> Path:
        return self.data_dir / "drakter.db"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"


def ensure_private_dir(path: Path) -> None:
    """Create ``path`` (and missing parents) as 0700, or validate/tighten an existing one."""
    path = Path(path)
    missing: list[Path] = []
    probe = path
    while not probe.exists() and not probe.is_symlink():
        missing.append(probe)
        if probe.parent == probe:
            break
        probe = probe.parent
    for directory in reversed(missing):
        try:
            os.mkdir(directory, 0o700)
        except FileExistsError:
            pass  # lost a race; validated below if it is the leaf

    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"not a safe directory (symlink or not a directory): {path}") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISDIR(st.st_mode):
            raise ValueError(f"not a directory: {path}")
        if hasattr(os, "getuid") and st.st_uid != os.getuid():
            raise ValueError(f"directory not owned by the current user: {path}")
        if hasattr(os, "fchmod") and stat.S_IMODE(st.st_mode) != 0o700:
            os.fchmod(fd, 0o700)
    finally:
        os.close(fd)


def load_settings() -> Settings:
    """Load settings from the environment and the per-user ``.env`` (resolved at call time)."""
    return Settings(_env_file=_env_file())  # type: ignore[call-arg]
