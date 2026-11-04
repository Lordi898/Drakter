"""Entry point: python -m app."""

from __future__ import annotations

import os
import socket
import sys


def main() -> int:
    os.umask(0o077)

    import uvicorn

    from app.core.config import BIND_HOST, load_settings
    from app.main import create_app

    from pydantic import ValidationError

    try:
        settings = load_settings()
    except ValidationError as exc:
        # Only field names: the error text would echo the offending (possibly secret) values.
        fields = sorted({".".join(str(part) for part in err["loc"]) or "?" for err in exc.errors()})
        print(f"invalid configuration: {', '.join(fields)}", file=sys.stderr)
        return 1

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((BIND_HOST, settings.port))
        # Con SO_REUSEADDR, dos procesos pueden enlazar el puerto hasta que uno escucha.
        sock.listen(128)
    except OSError as exc:
        sock.close()
        print(f"cannot bind {BIND_HOST}:{settings.port}: {exc.strerror}", file=sys.stderr)
        return 1

    config = uvicorn.Config(
        create_app(settings),
        host=BIND_HOST,  # informational only: the bound socket is passed to run()
        port=settings.port,
        log_config=None,
        access_log=False,
        server_header=False,
        proxy_headers=False,
        ws="websockets-sansio",
        ws_max_size=1048576,
        lifespan="on",
    )
    server = uvicorn.Server(config)
    try:
        server.run(sockets=[sock])
    finally:
        sock.close()
    return 0 if server.started else 1


if __name__ == "__main__":
    sys.exit(main())
