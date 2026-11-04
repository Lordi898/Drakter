"""Lo que solo se comprueba con todo parado."""
from __future__ import annotations

import signal

from harness.model import check


@check("parada.limpia", "El backend para sin dejar sesión", phase="post")
def clean(ctx):
    code = ctx.state["exit_codes"].get("backend")
    # Uvicorn apaga limpio y después relanza la señal capturada: -SIGTERM es el caso normal.
    # La prueba de apagado limpio es que el lifespan borró el archivo de sesión.
    assert code in (0, -signal.SIGTERM), f"el backend salió con {code}"
    assert not ctx.stack.session_file.exists(), "session.json sigue en disco"
    return f"código {code} y session.json eliminado por el lifespan"


@check("parada.token_fuera_de_logs", "El token no aparece en ningún log", phase="post")
def token_not_logged(ctx):
    token = ctx.api.token
    paths = [p for p in ctx.stack.logs_dir.rglob("*") if p.is_file()]
    paths += [p for p in (ctx.stack.data_dir / "logs").rglob("*") if p.is_file()]
    leaked = [str(p) for p in paths if token in p.read_text(errors="replace")]
    assert not leaked, f"token en {leaked}"
    return f"{len(paths)} logs revisados"
