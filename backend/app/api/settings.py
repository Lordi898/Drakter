"""REST routes of `/api/v1/settings`."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.services import settings as service
from app.services.settings_models import (
    BackupItem,
    BackupList,
    SettingItem,
    SettingsList,
    SettingsStatus,
    SettingUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["settings"])


def _request_id(request: Request) -> str:
    return str(request.scope.get("state", {}).get("request_id", ""))


@router.get("/settings")
def get_settings(request: Request) -> SettingsList:
    return service.list_settings(request.app.state.settings.db_path)


@router.get("/settings/status")
def get_status(request: Request) -> SettingsStatus:
    cfg = request.app.state.settings
    return service.settings_status(request.app.state, cfg.data_dir, cfg.db_path, cfg.backups_dir)


@router.get("/settings/backups")
def get_backups(request: Request) -> BackupList:
    return service.list_backups(request.app.state.settings.backups_dir)


@router.post("/settings/backups", status_code=201)
def post_backup(request: Request) -> BackupItem:
    cfg = request.app.state.settings
    return service.create_manual_backup(cfg.db_path, cfg.backups_dir, _request_id(request))


@router.post("/settings/{key}")
def post_setting(key: str, body: SettingUpdate, request: Request) -> SettingItem:
    return service.update_setting(
        request.app.state.settings.db_path, key, body.value, _request_id(request)
    )
