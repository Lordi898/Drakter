"""Capa 0 de la voz (V-10): órdenes locales sin LLM, con listas cerradas en `layer0.es.toml`.

`classify` es puro (firma congelada en voice/ports.py §4.7). Lo usan `DrakterStartStrategy`
(barge-in con el bot hablando) y el puente de WP1 (cada turno final).
"""

from __future__ import annotations

import re
import tomllib
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Literal

Command = Literal["stop_speech", "rest", "close", "backchannel"]

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

    return {
        "fillers": words(raw["fillers"]),
        "stop_first": words(raw["stop"]["first_word"]),
        "stop": phrases(raw["stop"]["phrases"]) + tuple((w,) for w in words(raw["stop"]["first_word"])),
        "rest": phrases(raw["rest"]["phrases"]),
        "close": phrases(raw["close"]["phrases"]),
        "backchannel": words(raw["backchannel"]["words"]),
    }


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
