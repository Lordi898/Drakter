"""Glue of the voice process: manager, IPC server, logging and an orderly shutdown."""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
from datetime import UTC, datetime
from typing import Any

from voice.config import VoiceConfig
from voice.ipc import IpcServer
from voice.manager import VoiceManager

log = logging.getLogger("voice.service")


class JsonLogFormatter(logging.Formatter):
    """One JSON line per record. Only what call sites pass in `data`: never text, never a traceback.

    A traceback can quote values, so exceptions are reduced to their type.
    """

    def format(self, record: logging.LogRecord) -> str:
        line: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage() if record.name.startswith("voice.") else record.msg,
        }
        data = getattr(record, "data", None)
        if data:
            line["data"] = data
        if record.exc_info and record.exc_info[0] is not None:
            line["error"] = record.exc_info[0].__name__
        return json.dumps(line, ensure_ascii=False, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.WARNING)  # engine libraries stay quiet: their INFO may describe the audio
    logging.getLogger("voice").setLevel(logging.INFO)


class VoiceService:
    def __init__(self, config: VoiceConfig, **engines: Any) -> None:
        """`engines` go straight to VoiceManager, so a check can inject doubles."""
        self._stop = asyncio.Event()
        self._manager = VoiceManager(config, self._publish, **engines)
        self._server = IpcServer(config.socket_path, self._on_command, self._on_disconnect)

    def _publish(self, name: str, payload: dict[str, Any]) -> None:
        self._server.publish(name, payload)

    async def _on_command(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "shutdown":
            self._stop.set()
            return {"stopping": True}
        return await self._manager.handle_command(name, args)

    async def _on_disconnect(self) -> None:
        """Without a client nobody sees the mic state, so the safe state is off and silent."""
        try:
            await self._manager.interrupt("user")
        finally:
            await self._manager.mic_set(False)

    def request_stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        for signum in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(signum, self.request_stop)
        await self._manager.start()
        try:
            await self._server.start()
            log.info("service_ready", extra={"data": {}})
            await self._stop.wait()
        finally:
            await self._manager.close()
            await self._server.stop()
            log.info("service_stopped", extra={"data": {}})
