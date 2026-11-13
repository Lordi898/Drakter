"""`python -m voice <run|phrases|check>`, desde la raíz del repositorio.

- `run`: el proceso de voz. Lo arranca y supervisa el backend; habla con él por el socket IPC.
- `phrases`: genera la caché PCM de frases fijas (lo implementa `voice/speech/phrases.py`).
- `check`: comprueba configuración, proveedores y modelos sin abrir audio ni red.

Con `DRAKTER_VOICE_NULL=1` (o `run --null`) arranca con proveedores vacíos.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import logging
import os
import signal
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from voice.config import NULL, VoiceConfig, load_config

if TYPE_CHECKING:
    from pipecat.pipeline.worker import PipelineWorker
    from pipecat.transports.base_transport import BaseTransport
    from pydantic import BaseModel

log = logging.getLogger("voice.main")
PIPELINE_STOP_TIMEOUT_S = 5.0


class JsonLogFormatter(logging.Formatter):
    """Una línea JSON por registro, solo con lo que el código pasa en `data`.

    Nunca texto del usuario ni trazas: una traza puede citar valores, así que una excepción
    se reduce a su tipo.
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
    root.setLevel(logging.WARNING)
    logging.getLogger("voice").setLevel(logging.INFO)
    # Pipecat registra con loguru y, en DEBUG, escribe el texto transcrito y el sintetizado.
    # Ni audio ni transcripciones se registran: solo avisos y errores.
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level=os.environ.get("DRAKTER_VOICE_PIPECAT_LOG", "WARNING"))


class VoiceProcess:
    """Une el servidor IPC, el canal WebRTC, la sesión y el pipeline de cada conexión."""

    def __init__(self, cfg: VoiceConfig) -> None:
        from voice.ipc import IpcServer
        from voice.session import Session, SharedModels

        self.cfg = cfg
        self.shared = SharedModels(cfg.models_dir)
        self.server = IpcServer(cfg.socket_path, self._on_command, self._on_backend, self._on_backend_gone)
        self.session = Session(cfg, self.server.publish)
        self.channel: Any = None
        self.pipelines_built = 0
        self._stop = asyncio.Event()
        self._worker: PipelineWorker | None = None
        self._run_task: asyncio.Task[None] | None = None

    # ── backend (IPC) ───────────────────────────────────────────────────────
    async def _on_backend(self) -> None:
        await self.session.emit("voice.ready", self.session.ready_payload())
        await self.session.emit_state()

    async def _on_backend_gone(self) -> None:
        """Sin backend no hay agente: se calla y se vuelve a reposo. La conexión WebRTC sigue."""
        await self.session.interrupt("user")
        await self.session.set_mode("standby", "ui")

    async def _on_command(self, type_: str, payload: BaseModel) -> dict[str, Any]:
        from voice.ipc import IpcError

        if type_ == "shutdown":
            self._stop.set()
            return {}
        if type_ == "rtc.offer":
            try:
                return await self.channel.accept_offer(
                    payload.sdp, payload.type, payload.pc_id, payload.restart_pc  # type: ignore[attr-defined]
                )
            except Exception as exc:  # noqa: BLE001 - el SDP viene de fuera; el motivo va al cliente
                log.warning("offer_rejected", extra={"data": {"error": type(exc).__name__}})
                raise IpcError("rtc_failed", type(exc).__name__) from None
        return await self.session.handle_command(type_, payload)

    # ── conexión WebRTC: un pipeline por conexión ───────────────────────────
    async def _on_connection(self, transport: BaseTransport) -> None:
        from pipecat.workers.runner import WorkerRunner

        from voice.pipeline import build

        await self._drop_pipeline()
        try:
            worker = build(transport, self.session, self.shared, self.cfg)
        except Exception as exc:  # noqa: BLE001 - falta un modelo o un proveedor: se avisa y no se conecta
            log.error("pipeline_build_failed", extra={"data": {"error": type(exc).__name__, "detail": str(exc)}})
            await self.session.emit(
                "voice.error", {"code": "pipeline_build_failed", "stage": "transport", "recoverable": False}
            )
            raise
        self.pipelines_built += 1

        @transport.event_handler("on_client_connected")
        async def on_client_connected(_transport: Any, _client: Any) -> None:
            await self.session.set_connected(True)

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(_transport: Any, _client: Any) -> None:
            await worker.cancel()

        runner = WorkerRunner(handle_sigint=False)
        await runner.add_workers(worker)
        self._worker = worker
        self._run_task = asyncio.create_task(self._run_pipeline(runner, worker))
        log.info("pipeline_started", extra={"data": {"n": self.pipelines_built, "models_loaded": self.shared.loads}})

    async def _run_pipeline(self, runner: Any, worker: PipelineWorker) -> None:
        try:
            await runner.run()
        except Exception as exc:  # noqa: BLE001 - un pipeline roto no acaba con el proceso
            log.error("pipeline_failed", extra={"data": {"error": type(exc).__name__}})
        finally:
            self.session.unbind(worker)
            if self._worker is worker:  # terminó solo (el cliente se fue), no por sustitución
                self._worker = self._run_task = None
                await self.session.set_connected(False)
            log.info("pipeline_stopped", extra={"data": {}})

    async def _drop_pipeline(self) -> None:
        """Cancela el pipeline activo. `Shared` y `SessionState` sobreviven."""
        worker, task = self._worker, self._run_task
        self._worker = self._run_task = None
        if worker is None or task is None:
            return
        await worker.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(task), PIPELINE_STOP_TIMEOUT_S)
        except TimeoutError:
            task.cancel()

    # ── ciclo de vida ───────────────────────────────────────────────────────
    async def run(self) -> None:
        from voice.registry import create

        loop = asyncio.get_running_loop()
        for signum in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(signum, self._stop.set)
        self.channel = create("channel", self.cfg.channel, self.cfg)
        self.channel.on_connection = self._on_connection
        self.channel.make_mixer = self.session.new_mixer
        await self.server.start()
        log.info("service_ready", extra={"data": {"stt": self.cfg.stt, "tts": list(self.cfg.tts)}})
        try:
            await self._stop.wait()
        finally:
            await self._drop_pipeline()
            await self.channel.close()
            await self.server.stop()
            log.info("service_stopped", extra={"data": {}})


def _check(cfg: VoiceConfig) -> int:
    """Proveedores importables y modelos en disco. No abre audio ni red, ni carga modelos."""
    from voice.registry import resolve

    failures = 0

    def report(ok: bool, label: str, detail: str) -> None:
        nonlocal failures
        failures += not ok
        print(f"{'OK  ' if ok else 'FALL'} {label}: {detail}")

    kinds = ("stt", "vad", "turn_start", "turn_stop", "wake", "tts_chain", "mixer", "channel",
             "guard", "phrases", "playback", "idle")
    for kind, name in [(k, getattr(cfg, k)) for k in kinds] + [("tts", n) for n in cfg.tts]:
        module, _, attr = resolve(kind, name).partition(":")
        try:
            ok = hasattr(importlib.import_module(module), attr)
            report(ok, f"{kind}/{name}", f"{module}:{attr}" if ok else f"{module} no define {attr}")
        except ImportError as exc:
            report(False, f"{kind}/{name}", f"no se puede importar {module} ({exc.name or exc})")

    models = cfg.models_dir
    wanted = [
        (cfg.stt != NULL, models / "moonshine/download.moonshine.ai/model" / f"{cfg.stt_model}-streaming-es"),
        (cfg.turn_stop != NULL, models / "smart-turn/smart-turn-v3.2-cpu.onnx"),
        ("kokoro" in cfg.tts, models / "kokoro/kokoro-v1.0.int8.onnx"),
        ("kokoro" in cfg.tts, models / "kokoro/voices-v1.0.bin"),
        *((cfg.wake != NULL, models / "openwakeword" / name) for name in cfg.wake_models),
    ]
    for needed, path in wanted:
        if needed:
            report(path.exists(), "modelo", str(path))
    print("Todo en orden." if not failures else f"{failures} comprobaciones fallidas.")
    return 1 if failures else 0


def _phrases(cfg: VoiceConfig, argv: list[str]) -> int:
    try:
        from voice.speech.phrases import main as phrases_main
    except ImportError as exc:
        print(f"ERROR: la caché de frases no está disponible ({exc.name or exc}).", file=sys.stderr)
        return 1
    return int(phrases_main(cfg, argv) or 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m voice", description="Proceso de voz de Drakter")
    parser.add_argument("command", nargs="?", default="run", choices=("run", "phrases", "check"))
    parser.add_argument("--null", action="store_true", help="proveedores vacíos (sin modelos ni red)")
    args, rest = parser.parse_known_args(argv)

    os.umask(0o077)
    configure_logging()
    try:
        if args.null:
            os.environ["DRAKTER_VOICE_NULL"] = "1"
        cfg = load_config()
        if args.command == "check":
            return _check(cfg)
        if args.command == "phrases":
            return _phrases(cfg, rest)

        async def run() -> None:
            await VoiceProcess(cfg).run()

        asyncio.run(run())
    except (ValueError, OSError) as exc:
        log.error("startup_failed", extra={"data": {"error": type(exc).__name__, "detail": str(exc)}})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
