"""`python -m voice`, from the repository root. Started by the backend supervisor."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from voice.config import load_config
from voice.service import VoiceService, configure_logging


def main() -> int:
    os.umask(0o077)
    configure_logging()
    log = logging.getLogger("voice.main")
    try:
        config = load_config()

        async def run() -> None:
            await VoiceService(config).run()

        asyncio.run(run())
    except (ValueError, OSError) as exc:
        log.error("startup_failed", extra={"data": {"error": type(exc).__name__, "detail": str(exc)}})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
