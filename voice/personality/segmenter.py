"""Incremental sentence splitter for streamed agent text.

feed() accepts arbitrary deltas (even cut mid-word) and returns only complete
sentences. A sentence end is decided on the accumulated buffer, never on a delta, and a
terminator at the very end of the buffer stays undecided until more text (or flush())
arrives. Fenced code blocks are collapsed into a single "```" marker sentence so that
normalize_for_speech can turn it into a spoken mention without reading the code.
"""

from __future__ import annotations

from typing import Final

_TERMINATORS: Final = ".!?…"
_CLOSERS: Final = "\"'”’»)]}"
_FENCES: Final = ("```", "~~~")
_FENCE_MARKER: Final = "```"
_FENCE_LINE_KEEP: Final = 16  # only the start of a code line matters (closing fence check)

# Never end a sentence: the period belongs to the abbreviation.
_HARD_ABBR: Final = frozenset(
    {
        "sr", "sra", "srta", "sres", "dr", "dra", "drs", "ud", "uds", "vd", "vds",
        "pág", "pag", "págs", "pags", "núm", "nº", "núms", "prof", "profa", "lic",
        "ing", "av", "avda", "tel", "dpto", "admón", "gral", "cap", "vol", "art",
        "fig", "ed", "aprox", "sta", "sto", "excmo", "excma", "ilmo", "ilma",
        "ej", "p.ej", "cf", "ref",
    }
)  # fmt: skip
# May or may not end a sentence: break only if the next word starts a new one.
_SOFT_ABBR: Final = frozenset({"etc", "ee.uu", "a.m", "p.m", "s.a", "s.l"})
_OPENERS: Final = "\"'“‘«(¿¡[¡"


def _starts_sentence(ch: str) -> bool:
    return ch.isupper() or ch.isdigit() or ch in _OPENERS


class SentenceSegmenter:
    def __init__(self, *, max_chars: int = 200) -> None:
        if max_chars < 20:
            raise ValueError("max_chars must be at least 20")
        self._max = max_chars
        self._buf = ""
        self._bol = True  # buffer start is at the start of a line
        self._in_fence = False

    def feed(self, delta: str) -> list[str]:
        self._buf += delta
        return self._drain(final=False)

    def flush(self) -> list[str]:
        out = self._drain(final=True)
        self._buf = ""
        self._bol = True
        self._in_fence = False
        return out

    # -- internals ---------------------------------------------------------

    def _drain(self, *, final: bool) -> list[str]:
        out: list[str] = []
        while True:
            buf = self._buf
            if self._in_fence:
                nl = buf.find("\n")
                if nl < 0:
                    self._buf = buf[:_FENCE_LINE_KEEP]  # bounded: keep the line start only
                    if final:
                        self._in_fence = False
                        self._buf = ""
                    break
                line = buf[:nl].lstrip()
                self._buf = buf[nl + 1 :]
                self._bol = True
                if line.startswith(_FENCES):
                    self._in_fence = False
                continue

            stripped = buf.lstrip()
            if len(stripped) != len(buf):
                if "\n" in buf[: len(buf) - len(stripped)]:
                    self._bol = True
                buf = self._buf = stripped
            if not buf:
                break

            if self._bol and buf.startswith(_FENCES):
                nl = buf.find("\n")
                if nl < 0 and not final:
                    break  # need the whole opening line to know if it closes itself
                line = buf if nl < 0 else buf[:nl]
                self._buf = "" if nl < 0 else buf[nl + 1 :]
                self._bol = True
                out.append(_FENCE_MARKER)
                self._in_fence = line[3:].find(line[:3]) < 0
                continue
            if self._bol and not final and len(buf) < 3 and any(f.startswith(buf) for f in _FENCES):
                break  # could still become a fence

            cut = self._find_end(buf, final)
            if cut is None:
                break
            end, nxt = cut
            sentence = buf[:end].strip()
            self._bol = nxt > 0 and buf[nxt - 1] == "\n"
            self._buf = buf[nxt:]
            if sentence:
                out.append(sentence)
        return out

    def _find_end(self, buf: str, final: bool) -> tuple[int, int] | None:
        n = len(buf)
        limit = min(n, self._max)
        i = 0
        while i < limit:
            c = buf[i]
            if c == "\n":
                return i, i + 1
            if c in _TERMINATORS:
                j = i
                while j < n and buf[j] in _TERMINATORS:
                    j += 1
                run = buf[i:j]
                k = j
                while k < n and buf[k] in _CLOSERS:
                    k += 1
                if k >= n:
                    if final:
                        return n, n
                    return None  # undecided until more text arrives
                if not buf[k].isspace():
                    i = k  # 3.5, e.g, example.com, ?"x
                    continue
                m = k
                while m < n and buf[m].isspace() and buf[m] != "\n":
                    m += 1
                if m >= n and not final:
                    return None
                nxt = buf[m] if m < n else ""
                if buf[m : m + 1] == "\n" or not nxt:
                    return k, k
                if self._is_boundary(buf, i, run, nxt):
                    return k, k
                i = k
                continue
            i += 1
        if n > self._max:
            return self._forced_cut(buf)
        if final and n:
            return n, n
        return None

    @staticmethod
    def _is_boundary(buf: str, i: int, run: str, nxt: str) -> bool:
        if run in ("?", "!") or any(ch in run for ch in "?!"):
            return True
        if len(run) > 1:  # ellipsis: continues if followed by lowercase
            return _starts_sentence(nxt)
        if run == "…":
            return _starts_sentence(nxt)
        # single period: look at the token before it
        s = i
        while s > 0 and not buf[s - 1].isspace() and buf[s - 1] not in _OPENERS:
            s -= 1
        token = buf[s:i]
        low = token.lower()
        if low in _HARD_ABBR:
            return False
        if low in _SOFT_ABBR:
            return _starts_sentence(nxt)
        if token.isdigit() and not buf[:s].strip():
            return False  # list numbering: "1. Texto"
        if len(token) == 1 and token.isupper() and nxt.isupper():
            return False  # initial: "J. García"
        return True

    def _forced_cut(self, buf: str) -> tuple[int, int]:
        window = buf[: self._max + 1]
        p = max(window.rfind(", "), window.rfind("; "), window.rfind(": "))
        if p >= self._max // 2:
            return p + 1, p + 1
        sp = window.rfind(" ")
        if sp > 0:
            return sp, sp + 1
        return self._max, self._max
