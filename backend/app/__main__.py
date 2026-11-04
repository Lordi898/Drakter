"""Entry point: python -m app. Electron main habla por stdin y stdout (D-14)."""

from __future__ import annotations

import os
import socket
import sys


def main() -> int:
    os.umask(0o077)

    from app.core.bootstrap import (
        HandshakeError,
        announce_port,
        read_credentials,
        take_standard_streams,
        watch_eof,
    )

    control_in, control_out = take_standard_streams()
    try:
        credentials = read_credentials(control_in)
    except HandshakeError:
        print("invalid handshake", file=sys.stderr)
        return 2

    import uvicorn
    from pydantic import ValidationError

    from app.core.config import BIND_HOST, load_settings
    from app.main import create_app

    try:
        settings = load_settings()
    except ValidationError as exc:
        # Only field names: the error text would echo the offending (possibly secret) values.
        fields = sorted({".".join(str(part) for part in err["loc"]) or "?" for err in exc.errors()})
        print(f"invalid configuration: {', '.join(fields)}", file=sys.stderr)
        return 1

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((BIND_HOST, 0))
        sock.listen(128)
    except OSError as exc:
        sock.close()
        print(f"cannot bind {BIND_HOST}: {exc.strerror}", file=sys.stderr)
        return 1
    port = sock.getsockname()[1]

    config = uvicorn.Config(
        create_app(
            settings,
            credentials=credentials,
            port=port,
            on_ready=lambda: announce_port(control_out, port),
        ),
        host=BIND_HOST,  # informational only: the bound socket is passed to run()
        port=port,
        log_config=None,
        access_log=False,
        server_header=False,
        proxy_headers=False,
        ws="websockets-sansio",
        ws_max_size=1048576,
        lifespan="on",
        timeout_graceful_shutdown=5,
    )
    server = uvicorn.Server(config)

    def stop() -> None:
        server.should_exit = True

    watch_eof(control_in, stop)
    try:
        server.run(sockets=[sock])
    finally:
        sock.close()
    return 0 if server.started else 1


if __name__ == "__main__":
    sys.exit(main())
