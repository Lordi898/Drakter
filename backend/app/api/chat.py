"""Chat REST API, behind SecurityGuardMiddleware. Its events go out through /api/v1/events."""

from __future__ import annotations

from typing import Annotated, Final
from uuid import UUID

from drakter_contracts.errors import HTTP_STATUS, ErrorCode
from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.errors import AppError
from app.integrations.hermes.chat_store import ChatMessage, ChatSession
from app.integrations.hermes.events import SAFE_MESSAGES
from app.integrations.hermes.runtime import AgentRuntime

MAX_MESSAGE_CHARS: Final = 32_000
MAX_PAGE_SIZE: Final = 200

router = APIRouter(prefix="/api/v1")


class SendMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    client_message_id: UUID | None = None

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text is blank")
        return value


class SendMessageResponse(BaseModel):
    turn_id: UUID
    message_id: UUID


class SessionPage(BaseModel):
    items: list[ChatSession]
    total: int


class MessagePage(BaseModel):
    items: list[ChatMessage]
    total: int


class CancelResponse(BaseModel):
    turn_id: UUID
    status: str = "cancelling"


class AgentStatusResponse(BaseModel):
    state: str
    provider: str | None
    model: str | None
    detail: str | None


def get_runtime(request: Request) -> AgentRuntime:
    runtime = getattr(request.app.state, "agent_runtime", None)
    if runtime is None:
        code = ErrorCode.AGENT_UNAVAILABLE
        raise AppError(code.value, SAFE_MESSAGES[code], HTTP_STATUS[code])
    return runtime


Runtime = Annotated[AgentRuntime, Depends(get_runtime)]
Limit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]
Offset = Annotated[int, Query(ge=0)]


@router.post("/chat/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(runtime: Runtime) -> ChatSession:
    return await runtime.create_session()


@router.get("/chat/sessions")
async def list_sessions(runtime: Runtime, limit: Limit = 50, offset: Offset = 0) -> SessionPage:
    items, total = await runtime.store.list_sessions(limit, offset)
    return SessionPage(items=items, total=total)


@router.post("/chat/sessions/{session_id}/close")
async def close_session(session_id: UUID, runtime: Runtime) -> ChatSession:
    return await runtime.close_session(session_id)


@router.get("/chat/sessions/{session_id}/messages")
async def list_messages(
    session_id: UUID, runtime: Runtime, limit: Limit = 50, offset: Offset = 0
) -> MessagePage:
    items, total = await runtime.list_messages(session_id, limit, offset)
    return MessagePage(items=items, total=total)


@router.post("/chat/sessions/{session_id}/messages", status_code=status.HTTP_202_ACCEPTED)
async def send_message(
    session_id: UUID, body: SendMessageRequest, runtime: Runtime
) -> SendMessageResponse:
    turn_id, message_id = await runtime.submit_message(session_id, body.text, body.client_message_id)
    return SendMessageResponse(turn_id=turn_id, message_id=message_id)


@router.post("/chat/turns/{turn_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_turn(turn_id: UUID, runtime: Runtime) -> CancelResponse:
    await runtime.cancel_turn(turn_id)
    return CancelResponse(turn_id=turn_id)


@router.get("/agent/status")
async def agent_status(runtime: Runtime) -> AgentStatusResponse:
    """`state` is `runtime.status_arbiter.current`: the same as the last agent.status_changed."""
    status = runtime.status()
    status["state"] = runtime.status_arbiter.current.state.value
    return AgentStatusResponse(**status)
