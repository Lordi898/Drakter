"""Perfiles de voz: carga y validación de ``~/.config/drakter/voces.toml``.

Es el único sitio donde el usuario pone los IDs de Fish Audio (nunca en el repositorio).
Lo usan el backend (ajuste ``voice_profile`` y herramientas del agente), ``scripts/voces.sh`` y,
más adelante, el proceso de voz. Solo biblioteca estándar y Pydantic.
"""

from __future__ import annotations

import os
import re
import tomllib
import unicodedata
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

VOICES_FILENAME: Final = "voces.toml"
FREE_MODEL: Final = "s2.1-pro-free"
ALLOWED_MODELS: Final = frozenset({FREE_MODEL})
PROFILE_NAME_RE: Final = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
REFERENCE_ID_RE: Final = re.compile(r"^[0-9a-f]{32}$")
_MODEL_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_TEMPLATE: Final = Path(__file__).resolve().parent / "templates" / "voces.template.toml"
MAX_FILE_BYTES: Final = 64 * 1024


class VoiceConfigError(Exception):
    """El archivo no se puede usar. El mensaje no incluye valores de los IDs."""


def fold(text: str) -> str:
    """Clave de comparación de alias: sin mayúsculas, sin tildes, espacios normalizados."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(plain.casefold().split())


_FILLER: Final = frozenset({"la", "el", "las", "los", "voz", "de", "tu", "mi", "una", "un"})


def _bare(folded: str) -> str:
    """Sin artículos ni «voz» al principio: «la voz neutral» -> «neutral»."""
    words = folded.split()
    while len(words) > 1 and words[0] in _FILLER:
        words.pop(0)
    return " ".join(words)


def mask_id(reference_id: str) -> str | None:
    """``ab12…ef90``. Nunca el ID entero en pantalla, logs ni resultados."""
    if not reference_id:
        return None
    return f"{reference_id[:4]}…{reference_id[-4:]}" if len(reference_id) >= 12 else "…"


class TtsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    proveedor: Literal["fish"] = "fish"
    modelo: str = FREE_MODEL
    perfil_por_defecto: str = "natural"
    allow_paid: bool = False

    @field_validator("modelo")
    @classmethod
    def _model_format(cls, value: str) -> str:
        if _MODEL_RE.fullmatch(value) is None:
            raise ValueError("modelo con formato no válido")
        return value

    @model_validator(mode="after")
    def _whitelist(self) -> TtsConfig:
        if self.modelo not in ALLOWED_MODELS and not self.allow_paid:
            raise ValueError(
                f"el modelo {self.modelo!r} no está en la lista blanca "
                f"(solo {FREE_MODEL}); con otro modelo Fish cobra. "
                "Si de verdad quieres pagar, pon allow_paid = true en [tts]"
            )
        return self


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reference_id: str = ""
    descripcion: str = Field(default="", max_length=200)
    alias: tuple[str, ...] = ()

    @field_validator("reference_id")
    @classmethod
    def _id_format(cls, value: str) -> str:
        value = value.strip().lower()
        if value and REFERENCE_ID_RE.fullmatch(value) is None:
            raise ValueError("reference_id debe tener 32 caracteres hexadecimales (0-9, a-f)")
        return value

    @field_validator("alias")
    @classmethod
    def _alias_text(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for alias in value:
            if not fold(alias) or len(alias) > 64:
                raise ValueError("alias vacío o demasiado largo")
        return value

    @property
    def configured(self) -> bool:
        return bool(self.reference_id)


class VoiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tts: TtsConfig = Field(default_factory=TtsConfig)
    perfiles: dict[str, Profile]

    @model_validator(mode="after")
    def _consistent(self) -> VoiceConfig:
        seen: dict[str, str] = {}
        for name, profile in self.perfiles.items():
            if PROFILE_NAME_RE.fullmatch(name) is None:
                raise ValueError(f"nombre de perfil no válido: {name!r} (minúsculas, números y _)")
            for label in (name, *profile.alias):
                key = fold(label)
                owner = seen.setdefault(key, name)
                if owner != name:
                    raise ValueError(
                        f"el alias {label!r} está en los perfiles {owner!r} y {name!r}: "
                        "no puede repetirse (sin distinguir mayúsculas ni tildes)"
                    )
        if self.tts.perfil_por_defecto not in self.perfiles:
            raise ValueError(
                f"perfil_por_defecto {self.tts.perfil_por_defecto!r} no existe en [perfiles.*]"
            )
        return self

    @property
    def default(self) -> str:
        return self.tts.perfil_por_defecto

    def resolve(self, query: str) -> str | None:
        """Nombre canónico del perfil por nombre o alias, o ``None``."""
        wanted = fold(query)
        labels = {n: {fold(n), *(fold(a) for a in pr.alias)} for n, pr in self.perfiles.items()}
        for name, options in labels.items():
            if wanted in options:
                return name
        # Sin coincidencia exacta: tolera artículo y «voz» («la neutral», «la voz seria»).
        bare = _bare(wanted)
        found = [n for n, options in labels.items() if bare in {_bare(o) for o in options}]
        return found[0] if len(found) == 1 else None


def voices_path() -> Path:
    """``$XDG_CONFIG_HOME/drakter/voces.toml``, o ``~/.config/drakter/voces.toml``."""
    base = os.environ.get("XDG_CONFIG_HOME", "")
    root = Path(base) if base and Path(base).is_absolute() else Path.home() / ".config"
    return root / "drakter" / VOICES_FILENAME


def ensure_voices_file(path: Path | None = None) -> tuple[Path, bool]:
    """Crea el archivo desde la plantilla (IDs vacíos, permisos 600) si no existe.

    Nunca sobrescribe. Devuelve la ruta y si se ha creado ahora.
    """
    target = path or voices_path()
    try:
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(target, flags, 0o600)
    except FileExistsError:
        return target, False
    except OSError as exc:
        raise VoiceConfigError(f"no se puede crear {target}: {exc.strerror}") from None
    with os.fdopen(fd, "wb") as handle:
        handle.write(_TEMPLATE.read_bytes())
    return target, True


def parse_voice_config(text: str) -> VoiceConfig:
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise VoiceConfigError(f"voces.toml no es TOML válido: {exc}") from None
    try:
        return VoiceConfig.model_validate(raw)
    except ValidationError as exc:
        problems = []
        for err in exc.errors(include_url=False, include_input=False, include_context=False):
            where = ".".join(str(p) for p in err["loc"]) or "voces.toml"
            problems.append(f"{where}: {err['msg'].removeprefix('Value error, ')}")
        raise VoiceConfigError("voces.toml no es válido: " + "; ".join(problems)) from None


def load_voice_config(path: Path | None = None) -> VoiceConfig:
    target = path or voices_path()
    try:
        if target.is_symlink():
            raise VoiceConfigError(
                f"{target} es un enlace simbólico; por seguridad debe ser un archivo normal"
            )
        if target.is_dir():
            raise VoiceConfigError(f"{target} es un directorio, no un archivo normal")
        if not target.is_file():
            raise VoiceConfigError(f"no existe {target}")
        with target.open("rb") as handle:
            data = handle.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES:
            raise VoiceConfigError("voces.toml es demasiado grande")
        return parse_voice_config(data.decode("utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise VoiceConfigError(f"no se puede leer {target}") from exc


class VoiceProfileStore:
    """Cargador con recarga: relee el archivo solo cuando cambia (mtime, tamaño).

    Crea el archivo desde la plantilla la primera vez. Un archivo roto lanza
    ``VoiceConfigError`` (no se sirve una copia vieja de lo que el usuario acaba de editar).
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        self._stamp: tuple[int, int] | None = None
        self._config: VoiceConfig | None = None

    @property
    def path(self) -> Path:
        return self._path or voices_path()

    def get(self) -> VoiceConfig:
        path = self.path
        ensure_voices_file(path)
        try:
            st = path.stat()
        except OSError as exc:
            raise VoiceConfigError(f"no se puede leer {path}") from exc
        stamp = (st.st_mtime_ns, st.st_size)
        if self._config is None or stamp != self._stamp:
            self._config = None
            self._config = load_voice_config(path)
            self._stamp = stamp
        return self._config


# Mensaje IPC backend -> proceso de voz (socket Unix, mismo formato que el resto de comandos).
# Solo lleva el nombre del perfil: el proceso de voz lee el ID de su propio voces.toml.
# SOLO CONTRATO: el backend aún no lo envía (VoiceService no está montado en main.py). Lo cablea
# el trabajo de Pipecat; hasta entonces no hay ningún código que lo mande.
VOICE_IPC_SET_PROFILE: Final = "voice.set_profile"


class VoiceSetProfileArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: str = Field(pattern=PROFILE_NAME_RE.pattern)
