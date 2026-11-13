"""HTTP surface of voice (plan §4.3). No route makes Drakter speak, approves anything or
touches the microphone (that is local to the renderer)."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Annotated, TypeVar

from fastapi import APIRouter, Depends, Request

from app.core.errors import AppError, ErrorDetail
from app.integrations.voice.client import VoiceIPCError, VoiceUnavailableError
from app.integrations.voice.schemas import (
    VoiceActivateIn,
    VoiceModeIn,
    VoiceOfferIn,
    VoiceOfferOut,
    VoiceState,
    VoiceStatusOut,
)
from app.integrations.voice.service import VoiceOrchestrator

T = TypeVar("T")


async def require_desktop(request: Request) -> None:
    """Only the desktop app may reach these routes; the agent never.

    It rejects any request the guard marks with another principal, so the switch to a
    separate agent token cannot fail open silently.
    """
    state = request.scope.get("state") or {}
    if state.get("principal", "desktop") != "desktop":
        raise AppError("forbidden", "Desktop session required", 403)


def get_voice(request: Request) -> VoiceOrchestrator:
    voice = getattr(request.app.state, "voice", None)
    if voice is None:
        raise AppError("voice_unavailable", "Voice is not available", 503)
    return voice


Voice = Annotated[VoiceOrchestrator, Depends(get_voice)]

router = APIRouter(prefix="/api/v1/voice", dependencies=[Depends(require_desktop)])


async def _call(operation: Awaitable[T]) -> T:
    try:
        return await operation
    except VoiceUnavailableError as exc:
        raise AppError("voice_unavailable", "Voice is not available", 503) from exc
    except VoiceIPCError as exc:
        if exc.code == "invalid_request":
            raise AppError("invalid_request", exc.message, 409) from exc
        raise AppError(
            "voice_unavailable",
            "Voice is not available",
            503,
            [ErrorDetail(code=exc.code, message=exc.message)],
        ) from exc


@router.post("/offer", response_model=VoiceOfferOut)
async def post_offer(body: VoiceOfferIn, voice: Voice) -> VoiceOfferOut:
    return await _call(voice.offer(body))


@router.post("/activate", response_model=VoiceState)
async def post_activate(body: VoiceActivateIn, voice: Voice) -> VoiceState:
    return await _call(voice.set_mode("conversation", body.trigger))


@router.post("/mode", response_model=VoiceState)
async def post_mode(body: VoiceModeIn, voice: Voice) -> VoiceState:
    return await _call(voice.set_mode(body.mode, "ui"))


@router.get("/status", response_model=VoiceStatusOut)
async def get_status(voice: Voice) -> VoiceStatusOut:
    return await voice.status()
