"""Data models of the backup bundles and of their HTTP API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["database", "config", "indexes", "openviking", "storage"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ManifestFile(_Strict):
    path: str = Field(min_length=1, max_length=4096)
    role: Role
    size: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ExcludedItem(_Strict):
    what: str
    reason: str


class BundleManifest(_Strict):
    format_version: int = Field(ge=1)
    created_at: str
    app_version: str
    schema_version: int = Field(ge=0)
    label: str = Field(pattern=r"^[a-z0-9-]+$", max_length=32)
    files: list[ManifestFile]
    excluded: list[ExcludedItem]


class BundleInfo(_Strict):
    """`list_bundles` fills only what the name and `stat` tell: the manifest is compressed."""

    name: str
    label: str
    created_at: str
    size_bytes: int
    schema_version: int | None = None
    app_version: str | None = None
    file_count: int | None = None
    includes_storage: bool | None = None
    excluded: list[ExcludedItem] = Field(default_factory=list)


class RestoreReport(_Strict):
    status: Literal["ok", "partial"]
    bundle: str
    pre_restore: str
    pre_restore_database: str
    schema_version: int
    restored: list[Role]
    skipped: list[ExcludedItem]
    retired: list[str]
    hooks_run: int
    hook_failures: list[str]
    audit_recorded: bool = True


class CreateBundleRequest(_Strict):
    """The label is the server's: a client cannot forge `initial` or `pre-restore`."""

    label: Literal["manual"] = "manual"
    include_storage: bool = False


class ConfirmRequest(_Strict):
    confirmation_id: str = Field(min_length=1, max_length=128)


class ConfirmationResponse(_Strict):
    confirmation_id: str


class VerifyResponse(_Strict):
    name: str
    valid: bool
    schema_version: int
    file_count: int


class DeleteResponse(_Strict):
    name: str
    deleted: bool


class ExportResponse(_Strict):
    name: str
    size_bytes: int
