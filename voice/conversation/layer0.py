"""Capa 0 de la voz (V-10): órdenes locales sin LLM, con listas cerradas en `layer0.es.toml`.

`classify` es puro (firma congelada en voice/ports.py §4.7). Lo usan `DrakterStartStrategy`
(barge-in con el bot hablando) y el puente de WP1 (cada turno final). `classify_ui` (modo Jarvis,
W5) va aparte para no tocar esa firma: también es puro y lo usa solo el puente.
"""

from __future__ import annotations

import re
import tomllib
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Literal

Command = Literal["stop_speech", "rest", "close", "backchannel"]
UiCommand = Literal["ui_jarvis", "ui_drakter"]

_TOML = Path(__file__).with_name("layer0.es.toml")
_WORD = re.compile(r"[a-z0-9ñ]+")


def normalize(text: str) -> list[str]:
    """Minúsculas, sin tildes ni signos; devuelve las palabras."""
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return _WORD.findall(t)


@lru_cache(maxsize=1)
def _lists() -> dict[str, object]:
    raw = tomllib.loads(_TOML.read_text(encoding="utf-8"))

    def phrases(xs: list[str]) -> tuple[tuple[str, ...], ...]:
        return tuple(tuple(normalize(x)) for x in xs if normalize(x))

    def words(xs: list[str]) -> frozenset[str]:
        return frozenset(w for x in xs for w in normalize(x))

    wake = raw.get("wake", {})
    wake_words = words(wake.get("words", ["jarvis"]))
    drakter_words = words(raw.get("ui", {}).get("drakter_words", ["drakter"]))
    # Variantes de «jarvis» y de «drakter» → forma canónica, solo para las frases de modo.
    canon = {w: "drakter" for w in drakter_words} | {
        w: "jarvis" for w in wake_words - drakter_words - {"despierta"}
    }

    def ui_phrases(section: str) -> tuple[tuple[str, ...], ...]:
        return tuple(tuple(canon.get(t, t) for t in p) for p in phrases(raw.get(section, {}).get("phrases", [])))

    return {
        "fillers": words(raw["fillers"]) | words(wake.get("words", [])),
        "wake_words": words(wake.get("words", ["jarvis"])),
        "wake_lead": words(wake.get("lead", ["hey"])),
        "stop_first": words(raw["stop"]["first_word"]),
        "stop": phrases(raw["stop"]["phrases"]) + tuple((w,) for w in words(raw["stop"]["first_word"])),
        "rest": phrases(raw["rest"]["phrases"]),
        "close": phrases(raw["close"]["phrases"]),
        "backchannel": words(raw["backchannel"]["words"]),
        "ui_canon": canon,
        "ui_jarvis": ui_phrases("ui_jarvis"),
        "ui_drakter": ui_phrases("ui_drakter"),
    }


def wake_words() -> tuple[frozenset[str], frozenset[str]]:
    """(variantes de «jarvis», palabras que pueden precederla) desde `[wake]` del TOML."""
    lists = _lists()
    return lists["wake_words"], lists["wake_lead"]  # type: ignore[return-value]


def _only_phrase(tokens: list[str], phrases: tuple[tuple[str, ...], ...], fillers: frozenset[str]) -> bool:
    """True si alguna frase aparece entera y el resto del enunciado son muletillas."""
    for p in phrases:
        n = len(p)
        for i in range(len(tokens) - n + 1):
            if tuple(tokens[i : i + n]) == p:
                rest = tokens[:i] + tokens[i + n :]
                if all(t in fillers or t in p for t in rest):
                    return True
    return False


def classify(
    text: str, bot_speaking: bool, awaiting_answer: bool
) -> Literal["stop_speech", "rest", "close", "backchannel"] | None:
    """Clasifica un enunciado. `None` = no es una orden local (va al agente o sigue el barge-in).

    - `stop_speech`: con el bot hablando, si la primera palabra (tras muletillas) es de parada; en
      cualquier caso, si el enunciado es solo una frase de parada.
    - `rest` / `close`: el enunciado es solo esa frase (más muletillas).
    - `backchannel`: todas las palabras son asentimientos y el bot no espera respuesta.
    """
    tokens = normalize(text)
    if not tokens:
        return None
    lists = _lists()
    fillers: frozenset[str] = lists["fillers"]  # type: ignore[assignment]
    content = [t for t in tokens if t not in fillers] or tokens
    if bot_speaking and content[0] in lists["stop_first"]:  # type: ignore[operator]
        return "stop_speech"
    if _only_phrase(tokens, lists["stop"], fillers):  # type: ignore[arg-type]
        return "stop_speech"
    if _only_phrase(tokens, lists["close"], fillers):  # type: ignore[arg-type]
        return "close"
    if _only_phrase(tokens, lists["rest"], fillers):  # type: ignore[arg-type]
        return "rest"
    if not awaiting_answer and all(t in lists["backchannel"] for t in tokens):  # type: ignore[operator]
        return "backchannel"
    return None


def classify_ui(text: str) -> UiCommand | None:
    """Orden local de cambio de modo de interfaz (`[ui_jarvis]`/`[ui_drakter]`), o `None`.

    Cuenta solo si el enunciado es la frase entera más muletillas; «¿qué es el modo Jarvis?» no.
    Las variantes del STT de «jarvis» y «drakter» (`[wake]`, `[ui]`) se leen en su forma canónica.
    """
    lists = _lists()
    canon: dict[str, str] = lists["ui_canon"]  # type: ignore[assignment]
    tokens = [canon.get(t, t) for t in normalize(text)]
    if not tokens:
        return None
    fillers: frozenset[str] = lists["fillers"]  # type: ignore[assignment]
    if _only_phrase(tokens, lists["ui_jarvis"], fillers):  # type: ignore[arg-type]
        return "ui_jarvis"
    if _only_phrase(tokens, lists["ui_drakter"], fillers):  # type: ignore[arg-type]
        return "ui_drakter"
    return None
