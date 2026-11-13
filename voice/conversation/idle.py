"""Silencio del usuario en conversación: aviso y vuelta a reposo (V-18).

Se engancha al `on_user_turn_idle` del `UserTurnProcessor` único, que WP1 crea con
`user_idle_timeout=cfg.idle_nudge_s`. En Pipecat 1.16.0 ese evento salta una vez cada vez que el
bot se calla y el usuario no habla en `user_idle_timeout` segundos (`UserIdleController`).

- Primer aviso: `idle_nudge` solo si el bot esperaba respuesta (`state.awaiting_answer`).
- Segundo aviso (tras el `idle_nudge`), o `cfg.followup_s` sin voz desde que se calló el bot:
  `ctl.set_mode("standby", "followup")`.
- Cualquier turno del usuario reinicia la cuenta. En `standby` no hace nada.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipecat.turns.user_turn_processor import UserTurnProcessor

    from voice.config import VoiceConfig
    from voice.ports import Ctl


class IdleWatcher:
    def __init__(self, ctl: Ctl, idle_nudge_s: float, followup_s: float) -> None:
        self._ctl = ctl
        self._idle_nudge_s = idle_nudge_s
        self._followup_s = followup_s
        self._count = 0
        self._followup: asyncio.Task | None = None

    def reset(self) -> None:
        self._count = 0
        if self._followup is not None:
            self._followup.cancel()
            self._followup = None

    async def on_idle(self) -> None:
        state = self._ctl.state
        if state.mode != "conversation":
            self.reset()
            return
        self._count += 1
        if self._count >= 2:
            await self._to_standby()
            return
        if state.awaiting_answer:
            await self._ctl.play_phrase("idle_nudge")
        if self._followup is None:
            delay = max(0.0, self._followup_s - self._idle_nudge_s)
            self._followup = asyncio.get_running_loop().create_task(self._followup_after(delay))

    async def _followup_after(self, delay: float) -> None:
        await asyncio.sleep(delay)
        self._followup = None
        state = self._ctl.state
        if state.mode == "conversation" and not state.bot_speaking:
            await self._to_standby()

    async def _to_standby(self) -> None:
        self.reset()
        await self._ctl.set_mode("standby", "followup")


def attach(utp: UserTurnProcessor, ctl: Ctl, cfg: VoiceConfig) -> IdleWatcher:
    """Registra los handlers en el `UserTurnProcessor`. Devuelve el vigilante (para `reset`)."""
    watcher = IdleWatcher(
        ctl,
        idle_nudge_s=float(getattr(cfg, "idle_nudge_s", 8.0)),
        followup_s=float(getattr(cfg, "followup_s", 20.0)),
    )

    async def _on_idle(_processor) -> None:
        await watcher.on_idle()

    async def _on_user_turn_started(_processor, _strategy) -> None:
        watcher.reset()

    utp.add_event_handler("on_user_turn_idle", _on_idle)
    utp.add_event_handler("on_user_turn_started", _on_user_turn_started)
    return watcher
