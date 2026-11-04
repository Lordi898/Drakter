from typing import Annotated

from pydantic import Field

from ..common import ContractModel, Instant
from ._base import OutModel

SettingKey = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.]{0,63}$")]
SettingValue = Annotated[str, Field(min_length=1, max_length=64)]


class SettingCreate(ContractModel):
    """Los secretos no van en ajustes (README §4). Los ajustes sensibles exigen confirmación."""

    key: SettingKey
    value: SettingValue


class SettingUpdate(ContractModel):
    value: SettingValue


class SettingOut(OutModel):
    key: str
    value: str
    updated_at: Instant
