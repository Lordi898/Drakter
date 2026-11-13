"""Lo que solo se comprueba con todo parado."""
from __future__ import annotations

import fcntl

from harness.model import check


@check("parada.limpia", "El backend para con EOF y nadie retiene la base", phase="post")
def clean(ctx):
    code = ctx.state["backend_exit"]
    assert code == 0, f"el backend salió con {code} tras EOF por stdin"
    lock = ctx.stack.data_dir / "drakter.db.lock"
    if lock.exists():  # flock no bloqueante: si falla, queda un backend huérfano, quizá de Electron
        with lock.open() as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise AssertionError("un backend huérfano sigue reteniendo la base") from exc
    return "código 0 tras EOF y bloqueo de instancia libre"


@check("parada.token_fuera_de_logs", "El token no aparece en ningún log", phase="post")
def token_not_logged(ctx):
    tokens = ctx.stack.tokens
    paths = [p for p in ctx.stack.logs_dir.rglob("*") if p.is_file()]
    paths += [p for p in (ctx.stack.data_dir / "logs").rglob("*") if p.is_file()]
    texts = {p: p.read_text(errors="replace") for p in paths}
    leaked = [str(p) for p, text in texts.items() if any(token in text for token in tokens)]
    assert not leaked, f"token en {leaked}"
    return f"{len(paths)} logs revisados con {len(tokens)} tokens"
