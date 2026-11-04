"""Voice Personality Engine (MASTER_PLAN 21.3): context -> engine parameters.

Only what the TTS engine really offers (TTSCapabilities) is applied. Everything the
profile asks for and the engine cannot do is listed in SpeechSegment.ignored. Volume
(gain) and pauses are applied by the player, so they hold on any engine.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from voice.config import VoiceConfig
from voice.contracts import SpeechSegment, TTSCapabilities, VoiceContext, VoiceError, VoiceParams

DEFAULT_PROFILE: Final = Path(__file__).with_name("default_profile.json")

SPEED_RANGE: Final = (0.8, 1.2)
GAIN_RANGE: Final = (0.5, 1.0)
PAUSE_RANGE: Final = (0, 2000)

_SECTIONS: Final = ("expression", "intent", "priority")
_BASE_KEYS: Final = frozenset({"speed", "gain", "pause_after_ms"})
_ENTRY_KEYS: Final = _BASE_KEYS | {"emotion", "intonation"}


def _bad(path: Path | str, msg: str) -> VoiceError:
    return VoiceError("invalid_request", f"invalid voice profile {path}: {msg}")


def _num(path: Path | str, where: str, value: object, lo: float, hi: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise _bad(path, f"{where} must be a finite number")
    if not lo <= value <= hi:
        raise _bad(path, f"{where}={value} outside [{lo}, {hi}]")
    return float(value)


def _validate(raw: object, path: Path | str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise _bad(path, "top level must be an object")
    extra = set(raw) - {"version", "voice", "base", *_SECTIONS}
    if extra:
        raise _bad(path, f"unknown keys {sorted(extra)}")
    if raw.get("version") != 1:
        raise _bad(path, "version must be 1")
    voice = raw.get("voice")
    if voice is not None and (not isinstance(voice, str) or not voice.strip()):
        raise _bad(path, "voice must be null or a non-empty string")
    base = raw.get("base")
    if not isinstance(base, dict) or set(base) != _BASE_KEYS:
        raise _bad(path, "base must define exactly speed, gain and pause_after_ms")
    _num(path, "base.speed", base["speed"], *SPEED_RANGE)
    _num(path, "base.gain", base["gain"], *GAIN_RANGE)
    _num(path, "base.pause_after_ms", base["pause_after_ms"], *PAUSE_RANGE)
    for section in _SECTIONS:
        table = raw.get(section, {})
        if not isinstance(table, dict):
            raise _bad(path, f"{section} must be an object")
        for name, entry in table.items():
            if not isinstance(entry, dict) or set(entry) - _ENTRY_KEYS:
                raise _bad(path, f"{section}.{name} must be an object with keys in {sorted(_ENTRY_KEYS)}")
            for key, value in entry.items():
                where = f"{section}.{name}.{key}"
                if key == "pause_after_ms":
                    _num(path, where, value, -1000, 1000)
                elif key in ("emotion", "intonation"):
                    _num(path, where, value, 0.0, 1.0)
                else:
                    _num(path, where, value, -0.5, 0.5)
    return raw


def _load(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise _bad(path, f"cannot read file ({exc.strerror})") from exc
    except ValueError as exc:
        raise _bad(path, f"not valid JSON ({exc})") from exc
    return _validate(raw, path)


def _clamp(value: float, bounds: tuple[float, float]) -> float:
    return max(bounds[0], min(bounds[1], value))


class VoicePersonalityEngine:
    def __init__(self, config: VoiceConfig, profile_path: Path | None = None) -> None:
        self._profile = _load(profile_path or DEFAULT_PROFILE)
        self._voice: str = self._profile.get("voice") or config.tts_voice

    def plan(self, sentence: str, context: VoiceContext, caps: TTSCapabilities) -> SpeechSegment:
        p = self._profile
        entries: list[Mapping[str, float]] = [
            p["expression"].get(context.expression, {}),
            p["intent"].get(context.intent, {}),
            p["priority"].get(context.priority, {}),
        ]
        speed = float(p["base"]["speed"])
        gain = float(p["base"]["gain"])
        pause = float(p["base"]["pause_after_ms"])
        for e in entries:
            speed += e.get("speed", 0.0)
            gain += e.get("gain", 0.0)
            pause += e.get("pause_after_ms", 0.0)
        speed = round(_clamp(speed, SPEED_RANGE), 3)
        gain = round(_clamp(gain, GAIN_RANGE), 3)
        pause_ms = int(_clamp(round(pause), PAUSE_RANGE))

        ignored: list[str] = []
        voice: str | None = self._voice
        if not caps.voices:
            ignored.append(f"voice={voice}")
            voice = None
        if not caps.speed:
            if speed != 1.0:
                ignored.append(f"speed={speed}")
            speed = 1.0

        extra: dict[str, float] = {}
        for key, flag, label in (
            ("emotion", caps.emotion, context.expression),
            ("intonation", caps.intonation, context.intent),
        ):
            value = next((e[key] for e in entries if key in e), None)
            if value is None:
                continue
            if flag and key in caps.extra_params:
                extra[key] = float(value)
            else:
                ignored.append(f"{key}={label}")

        return SpeechSegment(
            text=sentence,
            params=VoiceParams(voice=voice, speed=speed, gain=gain, pause_after_ms=pause_ms, extra=extra),
            ignored=tuple(ignored),
        )
