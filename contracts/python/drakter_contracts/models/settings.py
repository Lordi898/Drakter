from typing import Annotated, Any

from pydantic import Field

from ..common import ActorType, ContractModel, Instant
from ._base import OutModel

SettingKey = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.]{0,63}$")]


class SettingCreate(ContractModel):
    """Los secretos no van en ajustes (README §4). Los ajustes sensibles exigen confirmación."""

    key: SettingKey
    value: Any


class SettingUpdate(ContractModel):
    value: Any


class SettingOut(OutModel):
    key: str
    value: Any
    updated_at: Instant
    updated_by: ActorType
