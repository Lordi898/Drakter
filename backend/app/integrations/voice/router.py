"""HTTP surface of voice. There is no route to make Drakter speak: only the bridge can."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Annotated, TypeVar

from fastapi import APIRouter, Depends, Request

from app.core.errors import AppError, ErrorDetail
from app.integrations.voice.client import VoiceIPCError, VoiceUnavailableError
from app.integrations.voice.schemas import (
    ListenStartResponse,
    MicRequest,
    MicResponse,
    VoiceAck,
    VoiceStatus,
    WakewordRequest,
    WakewordResponse,
)
from app.integrations.voice.service import VoiceService

T = TypeVar("T")


async def require_desktop(request: Request) -> None:
    """Only the desktop app may reach these routes; the agent never.

    REPLACE when drakter/seguridad ships `agent_token`. Today the guard knows a
    single session token, so this cannot tell the two apart and depends on the
    agent never being handed that token. It already rejects any request the
    guard marks with another principal, so the switch cannot fail open silently.
    """
    state = request.scope.get("state") or {}
    if state.get("principal", "desktop") != "desktop":
        raise AppError("forbidden", "Desktop session required", 403)


def get_voice(request: Request) -> VoiceService:
    voice = getattr(request.app.state, "voice", None)
    if voice is None:
        raise AppError("voice_unavailable", "Voice is not available", 503)
    return voice


Voice = Annotated[VoiceService, Depends(get_voice)]

router = APIRouter(prefix="/api/v1/voice", dependencies=[Depends(require_desktop)])


async def _call(operation: Awaitable[T]) -> T:
    try:
        return await operation
    except VoiceUnavailableError as exc:
        raise AppError("voice_unavailable", "Voice is not available", 503) from exc
    except VoiceIPCError as exc:
        # Arguments were validated above, so what is left is the state of the
        # pipeline (microphone off, no wakeword provider...).
        if exc.code == "invalid_request":
            raise AppError("invalid_request", exc.message, 409) from exc
        raise AppError(
            "voice_unavailable",
            "Voice is not available",
            503,
            [ErrorDetail(code=exc.code, message=exc.message)],
        ) from exc


@router.get("/status", response_model=VoiceStatus)
async def get_status(voice: Voice) -> VoiceStatus:
    return await voice.status()


@router.post("/mic", response_model=MicResponse)
async def set_mic(body: MicRequest, voice: Voice) -> MicResponse:
    await _call(voice.set_mic(body.enabled))
    return MicResponse(enabled=body.enabled)


@router.post("/wakeword", response_model=WakewordResponse)
async def set_wakeword(body: WakewordRequest, voice: Voice) -> WakewordResponse:
    await _call(voice.set_wakeword(body.enabled))
    return WakewordResponse(enabled=body.enabled)


@router.post("/listen/start", response_model=ListenStartResponse)
async def listen_start(voice: Voice) -> ListenStartResponse:
    return ListenStartResponse(turn_id=await _call(voice.listen_start()))


@router.post("/listen/stop", response_model=VoiceAck)
async def listen_stop(voice: Voice) -> VoiceAck:
    await _call(voice.listen_stop())
    return VoiceAck()


@router.post("/listen/cancel", response_model=VoiceAck)
async def listen_cancel(voice: Voice) -> VoiceAck:
    await _call(voice.listen_cancel())
    return VoiceAck()


@router.post("/interrupt", response_model=VoiceAck)
async def interrupt(voice: Voice) -> VoiceAck:
    await _call(voice.interrupt())
    return VoiceAck()
