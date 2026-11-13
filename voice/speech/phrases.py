"""Frases fijas de la voz (plan de voz v2 V-14): textos, caché PCM, `PhrasePlayer` y CLI.

- Textos: `agent/identity/voice_phrases.es.toml` (`clave = ["variante", …]`), una clave por
  `PhraseKey`. `load_phrases` valida que no falte ninguna.
- Caché: `~/.local/share/drakter/voice/cache/<sha256>.pcm` (s16le, 24 kHz, mono). La clave es
  `sha256(perfil + hash(id) + modelo + texto)`: lleva el hash del reference_id, nunca el id.
- `PhrasePlayer` (entre la cadena TTS y `transport.output()`): empuja la caché como
  `TTSStartedFrame` + `TTSAudioRawFrame` + `TTSStoppedFrame` (un `OutputAudioRawFrame` simple no pone
  al bot «hablando»). Sin PCM, manda `TTSSpeakFrame` hacia arriba, al TTS activo.
- CLI: `python -m voice phrases` (lo despacha `voice/__main__.py`) → `main(argv)`.

Integración (WP1): `Ctl.play_phrase(key, when)` delega en `PhrasePlayer.play`. El puente llama a
`arm_filler()` al emitir `voice.user_turn` y a `on_tool(turn_id)` con `turn.phase{executing}`.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import random
import sys
import time
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Final

from drakter_contracts.voice_ipc import PHRASE_KEYS

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
PHRASES_FILE: Final = REPO_ROOT / "agent" / "identity" / "voice_phrases.es.toml"
DEFAULT_CACHE_DIR: Final = Path.home() / ".local" / "share" / "drakter" / "voice" / "cache"
SAMPLE_RATE: Final = 24000
CHUNK_BYTES: Final = SAMPLE_RATE * 2 // 10  # 100 ms
ACK_KEYS: Final = ("ack_1", "ack_2", "ack_3")
ALWAYS_AUDIBLE: Final = frozenset({"confirm_on_screen"})
KOKORO_MODEL_TAG: Final = "kokoro:ef_dora"


class PhrasesError(ValueError):
    pass


def load_phrases(path: Path = PHRASES_FILE) -> dict[str, list[str]]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise PhrasesError(f"no se puede leer {path}: {exc}") from exc
    missing = [k for k in PHRASE_KEYS if k not in data]
    unknown = [k for k in data if k not in PHRASE_KEYS]
    if missing or unknown:
        raise PhrasesError(f"{path}: faltan {missing or '-'}; sobran {unknown or '-'}")
    out: dict[str, list[str]] = {}
    for key in PHRASE_KEYS:
        variants = data[key]
        if not isinstance(variants, list) or not variants or not all(
            isinstance(v, str) and v.strip() for v in variants
        ):
            raise PhrasesError(f"{path}: {key} debe ser una lista de textos no vacíos")
        out[key] = [v.strip() for v in variants]
    return out


def voice_hash(voice_id: str | None) -> str:
    return hashlib.sha256((voice_id or "").encode()).hexdigest()[:16]


def cache_key(profile: str, voice_id: str | None, model: str, text: str) -> str:
    raw = "\x1f".join((profile, voice_hash(voice_id), model, text))
    return hashlib.sha256(raw.encode()).hexdigest()


def cache_dir(cfg: Any = None) -> Path:
    value = getattr(cfg, "phrases_cache_dir", None)
    return Path(value) if value else DEFAULT_CACHE_DIR


def model_tag(provider: str, cfg: Any = None) -> str:
    """Etiqueta del modelo para la clave: `fish:<modelo>` o `kokoro:ef_dora`."""
    if provider == "fish":
        from voice.providers.tts._common import FISH_MODEL

        return f"fish:{getattr(cfg, 'tts_model', None) or FISH_MODEL}"
    return KOKORO_MODEL_TAG


def _key_for(provider: str, profile_name: str, voice_id: str | None, cfg: Any, text: str) -> str:
    if provider == "fish":
        return cache_key(profile_name, voice_id, model_tag("fish", cfg), text)
    return cache_key("kokoro", None, KOKORO_MODEL_TAG, text)


# --------------------------------------------------------------------------- reproducción

try:  # el CLI y `load_phrases` funcionan sin Pipecat; PhrasePlayer lo necesita
    from pipecat.frames.frames import (
        BotStartedSpeakingFrame,
        Frame,
        InterruptionFrame,
        TTSAudioRawFrame,
        TTSSpeakFrame,
        TTSStartedFrame,
        TTSStoppedFrame,
        UserStartedSpeakingFrame,
        UserStoppedSpeakingFrame,
    )
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
except ImportError:  # pragma: no cover
    FrameProcessor = object  # type: ignore[assignment,misc]


class PhrasePlayer(FrameProcessor):  # type: ignore[misc,valid-type]
    """Reproduce frases fijas y rellenos. Todo es cancelable (interrupción o voz del usuario)."""

    def __init__(
        self,
        cfg: Any,
        ctl: Any,
        profile: Any,
        *,
        phrases: dict[str, list[str]] | None = None,
        cache: Path | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._cfg = cfg
        self._ctl = ctl
        self._profile = profile  # ResolvedProfile; su `voice` nunca se loguea
        self._phrases = phrases or load_phrases()
        self._cache = cache or cache_dir(cfg)
        self._last_variant: dict[str, str] = {}
        self._user_speaking = False
        self._filler_task: asyncio.Task | None = None
        self._pending: set[asyncio.Task] = set()
        self._tool_turn: str | None = None
        self._tool_at = 0.0

    def set_profile(self, profile: Any) -> None:
        self._profile = profile

    # --- API para Ctl y el puente ---

    async def play(self, key: str, when: str = "now") -> None:
        if key not in self._phrases:
            return
        if not self._ctl.state.tts_enabled and key not in ALWAYS_AUDIBLE:
            return
        text = self._pick(key)
        if when == "when_silent":
            task = asyncio.get_running_loop().create_task(self._when_silent(text))
            self._pending.add(task)
            task.add_done_callback(self._pending.discard)
        else:
            await self._say(text)

    def arm_filler(self) -> None:
        """Fin de turno de usuario: si en `filler_after_ms` no hay primer audio, suena un `ack_*`."""
        self._cancel_filler()
        delay = float(getattr(self._cfg, "filler_after_ms", None) or 900) / 1000
        self._filler_task = asyncio.get_running_loop().create_task(self._filler(delay))

    async def on_tool(self, turn_id: str | None) -> None:
        """`tool_generic` como máximo una vez por turno y cada `tool_phrase_gap_s`."""
        gap = float(getattr(self._cfg, "tool_phrase_gap_s", None) or 8.0)
        now = time.monotonic()
        if turn_id == self._tool_turn or now - self._tool_at < gap:
            return
        # Solo tiene sentido en un silencio de espera: si el bot ya habla o el usuario habla,
        # se descarta (encolarla «en silencio» la haría sonar después de la respuesta).
        if self._ctl.state.bot_speaking or self._user_speaking:
            return
        self._tool_turn, self._tool_at = turn_id, now
        await self.play("tool_generic", "now")

    def cancel(self) -> None:
        self._cancel_filler()
        for task in list(self._pending):
            task.cancel()

    # --- internos ---

    def _pick(self, key: str) -> str:
        variants = self._phrases[key]
        options = [v for v in variants if v != self._last_variant.get(key)] or variants
        text = random.choice(options)
        self._last_variant[key] = text
        return text

    def _cancel_filler(self) -> None:
        if self._filler_task and not self._filler_task.done():
            self._filler_task.cancel()
        self._filler_task = None

    async def _filler(self, delay: float) -> None:
        await asyncio.sleep(delay)
        if self._ctl.state.bot_speaking or self._user_speaking:
            return
        await self.play(random.choice(ACK_KEYS))

    async def _when_silent(self, text: str) -> None:
        deadline = time.monotonic() + 30.0
        while self._ctl.state.bot_speaking or self._user_speaking:
            if time.monotonic() > deadline:
                return
            await asyncio.sleep(0.1)
        await self._say(text)

    async def _say(self, text: str) -> None:
        provider = "fish" if self._ctl.state.tts_active == "fish" else "kokoro"
        voice_id = getattr(self._profile, "voice", None)
        name = getattr(self._profile, "name", "natural")
        path = self._cache / f"{_key_for(provider, name, voice_id, self._cfg, text)}.pcm"
        try:
            pcm = path.read_bytes()
        except OSError:
            pcm = b""
        if not pcm:  # sin caché: lo sintetiza el TTS activo (TTSSpeakFrame va hacia arriba)
            await self.push_frame(TTSSpeakFrame(text, append_to_context=False), FrameDirection.UPSTREAM)
            return
        context_id = f"phrase-{time.monotonic_ns()}"
        await self.push_frame(TTSStartedFrame(context_id=context_id))
        for i in range(0, len(pcm), CHUNK_BYTES):
            await self.push_frame(
                TTSAudioRawFrame(pcm[i : i + CHUNK_BYTES], SAMPLE_RATE, 1, context_id=context_id)
            )
        await self.push_frame(TTSStoppedFrame(context_id=context_id))

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, UserStartedSpeakingFrame):
            self._user_speaking = True
            self._cancel_filler()
        elif isinstance(frame, UserStoppedSpeakingFrame):
            self._user_speaking = False
        elif isinstance(frame, InterruptionFrame):
            self.cancel()
        elif isinstance(frame, (TTSStartedFrame, TTSAudioRawFrame, BotStartedSpeakingFrame)):
            self._cancel_filler()  # ya hay primer audio
        await self.push_frame(frame, direction)

    async def cleanup(self) -> None:
        self.cancel()
        await super().cleanup()


# --------------------------------------------------------------------------- generación (CLI)


def _all_texts(phrases: dict[str, list[str]]) -> Iterator[tuple[str, str]]:
    for key, variants in phrases.items():
        for text in variants:
            yield key, text


async def _fish_pcm(text: str, voice_id: str | None, model: str) -> bytes:
    """Una frase con Fish por WebSocket (mismo protocolo que `FishAudioTTSService`)."""
    import ormsgpack
    from websockets.asyncio.client import connect

    headers = {"Authorization": f"Bearer {os.environ['FISH_API_KEY']}", "model": model}
    request = {
        "text": "",
        "sample_rate": SAMPLE_RATE,
        "latency": "balanced",
        "format": "pcm",
        "normalize": False,
        "prosody": {"speed": 1.0, "volume": 0},
        "reference_id": voice_id,
    }
    audio = bytearray()
    async with connect(
        "wss://api.fish.audio/v1/tts/live", additional_headers=headers, max_size=16 * 2**20
    ) as ws:
        await ws.send(ormsgpack.packb({"event": "start", "request": request}))
        await ws.send(ormsgpack.packb({"event": "text", "text": text}))
        await ws.send(ormsgpack.packb({"event": "flush"}))
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), 4.0 if audio else 20.0)
            except TimeoutError:
                break
            data = ormsgpack.unpackb(msg)
            if data.get("event") == "audio" and data.get("audio"):
                audio += data["audio"]
            elif data.get("event") == "finish":
                if data.get("reason") == "error":
                    raise RuntimeError("Fish devolvió un error al sintetizar")
                break
        await ws.send(ormsgpack.packb({"event": "stop"}))
    return bytes(audio)


def _kokoro_pcm(engine: Any, text: str) -> bytes:
    import numpy as np

    samples, sr = engine.create(text, voice="ef_dora", lang="es")
    if sr != SAMPLE_RATE:
        raise RuntimeError(f"Kokoro devolvió {sr} Hz, se esperaban {SAMPLE_RATE}")
    return (np.clip(samples, -1, 1) * 32767).astype(np.int16).tobytes()


def _spoken(text: str, *, expressive: bool) -> str:
    from drakter_contracts.speech_markup import keep_allowed, strip_tags

    from voice.speech.lexicon import apply_lexicon
    from voice.speech.normalize import normalize_for_speech

    text = keep_allowed(text) if expressive else strip_tags(text)
    return normalize_for_speech(apply_lexicon(text))


def _write(path: Path, pcm: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(pcm)
    tmp.replace(path)


async def generate(
    cfg: Any,
    profile_name: str,
    voice_id: str | None,
    *,
    providers: tuple[str, ...] = ("fish", "kokoro"),
    force: bool = False,
    cache: Path | None = None,
) -> dict[str, int]:
    """Genera la caché PCM de todas las frases. Devuelve cuántas se hicieron por proveedor."""
    from voice.providers.tts._common import FISH_MODEL
    from voice.providers.tts.fish import fish_unavailable

    phrases = load_phrases()
    target = cache or cache_dir(cfg)
    done = {p: 0 for p in providers}
    if "fish" in providers:
        model = getattr(cfg, "tts_model", None) or FISH_MODEL
        if model != FISH_MODEL:
            raise SystemExit(f"modelo de Fish no permitido: {model!r}")
        reason = fish_unavailable(cfg)
        if reason:
            print(f"fish: omitido ({reason})", file=sys.stderr)
        else:
            for _key, text in _all_texts(phrases):
                path = target / f"{_key_for('fish', profile_name, voice_id, cfg, text)}.pcm"
                if path.exists() and not force:
                    continue
                pcm = await _fish_pcm(_spoken(text, expressive=True), voice_id, model)
                if pcm:
                    _write(path, pcm)
                    done["fish"] += 1
    if "kokoro" in providers:
        from voice.providers.tts.kokoro import DEFAULT_THREADS, load_kokoro, model_paths

        model_file, voices_file = model_paths(cfg)
        engine = None
        for _key, text in _all_texts(phrases):
            path = target / f"{_key_for('kokoro', profile_name, None, cfg, text)}.pcm"
            if path.exists() and not force:
                continue
            if engine is None:
                engine = load_kokoro(model_file, voices_file, DEFAULT_THREADS)
            pcm = await asyncio.to_thread(_kokoro_pcm, engine, _spoken(text, expressive=False))
            _write(path, pcm)
            done["kokoro"] += 1
    return done


def resolve_active_profile(name: str | None) -> tuple[str, str | None]:
    """Perfil activo desde voces.toml (`VoiceProfileStore`). El id no se imprime nunca."""
    from drakter_contracts.voice_profiles import VoiceProfileStore

    config = VoiceProfileStore().get()
    canonical = config.resolve(name) if name else config.default
    if canonical is None:
        raise SystemExit(f"perfil de voz desconocido: {name!r}")
    return canonical, config.perfiles[canonical].reference_id or None


def main(argv: list[str] | None = None, cfg: Any = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m voice phrases", description=__doc__.splitlines()[0])
    parser.add_argument("--profile", help="perfil de voces.toml (por defecto, el activo)")
    parser.add_argument("--no-voice", action="store_true", help="Fish sin reference_id (voz por defecto)")
    parser.add_argument("--only", choices=("fish", "kokoro"), help="solo un proveedor")
    parser.add_argument("--force", action="store_true", help="regenera aunque exista")
    parser.add_argument("--check", action="store_true", help="solo valida el TOML")
    args = parser.parse_args(argv)
    phrases = load_phrases()
    if args.check:
        print(f"ok: {len(phrases)} claves, {sum(len(v) for v in phrases.values())} variantes")
        return 0
    if args.no_voice:
        profile_name, voice_id = (args.profile or "natural"), None
    else:
        profile_name, voice_id = resolve_active_profile(args.profile)
    providers = (args.only,) if args.only else ("fish", "kokoro")
    done = asyncio.run(generate(cfg, profile_name, voice_id, providers=providers, force=args.force))
    print("frases generadas: " + ", ".join(f"{k}={v}" for k, v in done.items()) + f" en {cache_dir(cfg)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def create(cfg: Any, ctl: Any, profile: Any = None) -> PhrasePlayer:
    """Fábrica para el núcleo (`VoiceConfig.phrases`). `profile`: ResolvedProfile de la conexión."""
    if profile is None:
        from voice.ports import ResolvedProfile

        profile = ResolvedProfile(getattr(ctl.state, "profile", "natural"))
    return PhrasePlayer(cfg, ctl, profile)
