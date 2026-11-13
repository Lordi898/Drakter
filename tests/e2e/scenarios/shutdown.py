"""Lo que solo se comprueba con todo parado."""
from __future__ import annotations

import fcntl
import time

from harness.model import check

ORPHAN_GRACE = 20  # s: margen para que el backend de Electron termine de cerrar Hermes


@check("parada.limpia", "El backend para con EOF y nadie retiene la base", phase="post")
def clean(ctx):
    code = ctx.state["backend_exit"]
    assert code == 0, f"el backend salió con {code} tras EOF por stdin"
    lock = ctx.stack.data_dir / "drakter.db.lock"
    waited = 0.0
    if lock.exists():  # flock no bloqueante: si sigue tomado tras el margen, hay un huérfano
        with lock.open() as handle:
            # El backend de Electron puede estar aún cerrando Hermes cuando muere su cliente.
            deadline = time.monotonic() + ORPHAN_GRACE
            while True:
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError as exc:
                    if time.monotonic() > deadline:
                        raise AssertionError(f"un backend huérfano sigue reteniendo la base tras "
                                             f"{ORPHAN_GRACE} s") from exc
                    time.sleep(0.5)
                    waited += 0.5
    extra = f" (liberado tras {waited:.1f} s)" if waited else ""
    return f"código 0 tras EOF y bloqueo de instancia libre{extra}"


@check("parada.token_fuera_de_logs", "El token no aparece en ningún log", phase="post")
def token_not_logged(ctx):
    tokens = ctx.stack.tokens
    paths = [p for p in ctx.stack.logs_dir.rglob("*") if p.is_file()]
    paths += [p for p in (ctx.stack.data_dir / "logs").rglob("*") if p.is_file()]
    texts = {p: p.read_text(errors="replace") for p in paths}
    leaked = [str(p) for p, text in texts.items() if any(token in text for token in tokens)]
    assert not leaked, f"token en {leaked}"
    return f"{len(paths)} logs revisados con {len(tokens)} tokens"
