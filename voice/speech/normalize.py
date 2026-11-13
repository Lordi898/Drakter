"""Turn agent text (Markdown, code, links, emojis) into plain text fit to be spoken (voz v2: desde personality/).

The input is untrusted: nothing here interprets it, it only strips formatting. Every
step is linear (no nested quantifiers, no unbounded backtracking), so a hostile input
cannot stall the voice process.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Final

CODE_MENTION: Final = "Bloque de código."

_FENCES: Final = ("```", "~~~")
_LINK = re.compile(r"(!?)\[([^\[\]]{0,500})\]\(([^()]{0,2000})\)")
_URL = re.compile(r"(?:https?|ftp)://[^\s<>\"')\]]+|www\.[^\s<>\"')\]]+")
_URL_TAIL = ".,;:!?"
_HTML_TAG = re.compile(r"</?[A-Za-z][^<>\n]{0,200}>")
_UNDERSCORE = re.compile(r"(?<![A-Za-z0-9])_|_(?![A-Za-z0-9])")
_HEADING = re.compile(r"#{1,6}[ \t]+")
_BULLET = re.compile(r"[-*+•][ \t]+")
_TASKBOX = re.compile(r"\[[ xX]\][ \t]+")
_NUMBERED = re.compile(r"\d{1,3}[.)][ \t]+")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?])")
_END_PUNCT: Final = ".!?…:;"


def _is_dropped_char(ch: str) -> bool:
    cp = ord(ch)
    if (
        0x1F000 <= cp <= 0x1FAFF  # pictographs, flags, skin tones
        or 0x2600 <= cp <= 0x27BF  # misc symbols, dingbats
        or 0x2B00 <= cp <= 0x2BFF
        or 0x2300 <= cp <= 0x23FF
        or 0xFE00 <= cp <= 0xFE0F  # variation selectors
        or cp == 0x20E3
        or 0xE0020 <= cp <= 0xE007F
    ):
        return True
    if ch in "\n\t":
        return False
    return unicodedata.category(ch) in ("Cc", "Cf")  # controls, zero-width, ZWJ


def _strip_code_spans(text: str) -> str:
    if "`" not in text:
        return text
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        j = text.find("`", i)
        if j < 0:
            out.append(text[i:])
            break
        out.append(text[i:j])
        k = j
        while k < n and text[k] == "`":
            k += 1
        run = k - j
        marker = "`" * run
        search = k
        end = -1
        while True:
            c = text.find(marker, search)
            if c < 0:
                break
            e = c + run
            if (c == 0 or text[c - 1] != "`") and (e >= n or text[e] != "`"):
                end = c
                break
            # part of a longer run: skip that whole run
            while e < n and text[e] == "`":
                e += 1
            search = e
        if end < 0:
            i = k  # unmatched backticks: drop them, keep the text
        else:
            out.append(" ")
            i = end + run
    return "".join(out)


def _link_sub(m: re.Match[str]) -> str:
    return m.group(2)  # keep the label (or alt text), drop the target


def _url_sub(m: re.Match[str]) -> str:
    url = m.group(0)
    stripped = url.rstrip(_URL_TAIL)
    return url[len(stripped) :]  # keep trailing sentence punctuation


def _clean_inline(text: str) -> str:
    text = _strip_code_spans(text)
    text = _LINK.sub(_link_sub, text)
    text = _URL.sub(_url_sub, text)
    text = _HTML_TAG.sub(" ", text)
    for mark in ("**", "__", "~~"):
        text = text.replace(mark, "")
    text = text.replace("*", "")
    text = _UNDERSCORE.sub("", text)
    text = text.replace("\\", "")
    return "".join(ch for ch in text if not _is_dropped_char(ch))


def _is_table_separator(s: str) -> bool:
    return "|" in s and "-" in s and all(c in " \t:|-" for c in s)


def _is_rule(s: str) -> bool:
    compact = s.replace(" ", "").replace("\t", "")
    return len(compact) >= 3 and len(set(compact)) == 1 and compact[0] in "-*_"


def _terminate(text: str) -> str:
    return text if not text or text[-1] in _END_PUNCT else text + "."


def _process_line(line: str) -> str:
    s = line.strip()
    if not s:
        return ""
    if _is_rule(s) or _is_table_separator(s):
        return ""
    block = False
    if s.startswith(">"):
        s = s.lstrip("> \t")
        block = True
    m = _HEADING.match(s)
    if m:
        s, block = s[m.end() :], True
    else:
        m = _BULLET.match(s)
        if m:
            s, block = s[m.end() :], True
            m = _TASKBOX.match(s)
            if m:
                s = s[m.end() :]
        elif _NUMBERED.match(s):
            block = True
    if "|" in s and (s.startswith("|") or s.count("|") >= 2):
        cells = [_clean_inline(c).strip() for c in s.strip("|").split("|")]
        return _terminate(", ".join(c for c in cells if c))
    cleaned = " ".join(_clean_inline(s).split())
    return _terminate(cleaned) if block else cleaned


def normalize_for_speech(text: str) -> str:
    """Plain, speakable Spanish text. Code blocks become a short spoken mention."""
    if not text:
        return ""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    fence = ""
    for line in lines:
        s = line.lstrip(" \t")
        if fence:
            if s.startswith(fence):
                fence = ""
            continue
        if s.startswith(_FENCES):
            out.append(CODE_MENTION)
            if s[3:].find(s[:3]) < 0:  # a fence closed on its own line opens nothing
                fence = s[:3]
            continue
        piece = _process_line(line)
        if piece:
            out.append(piece)
    result = " ".join(" ".join(out).split())
    return _SPACE_BEFORE_PUNCT.sub(r"\1", result)


async def normalize_es(text: str, _text_type: object = None) -> str:
    """`TextTransform` de Pipecat. Conserva las etiquetas `[tag]` (no son Markdown)."""
    return normalize_for_speech(text)
