from typing import Annotated

from pydantic import Field

from ..common import ContractModel, HexColor, Id
from ._base import OutModel, TagName


class TagCreate(ContractModel):
    name: TagName
    color: HexColor | None = None


class TagUpdate(ContractModel):
    name: TagName | None = None
    color: HexColor | None = None


class TagOut(OutModel):
    id: Id
    name: str
    color: HexColor | None = None
    usage_count: int | None = Field(default=None, description="Solo en `GET /api/v1/tags`")


class EntityTagsReplace(ContractModel):
    names: Annotated[list[TagName], Field(max_length=32)]
