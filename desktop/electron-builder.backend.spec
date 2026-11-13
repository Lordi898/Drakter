# -*- mode: python ; coding: utf-8 -*-
# PyInstaller (onedir) del backend de Drakter. Lo invoca electron-builder.build-backend.mjs;
# no se cross-compila: genera el backend de la plataforma donde se ejecuta.
# SPECPATH (inyectado por PyInstaller) es el directorio de este archivo: desktop/.
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

BACKEND = (Path(SPECPATH) / ".." / "backend").resolve()
MIGRATIONS = BACKEND / "migrations"

# app/database/migrator.py resuelve MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations".
# En un build congelado __file__ vale <_MEIPASS>/app/database/migrator.pyc, asi que parents[2]
# es <_MEIPASS> (= <dist>/drakter-backend/_internal) y las migraciones deben ir en "migrations".
if not any(MIGRATIONS.glob("*.sql")):
    raise SystemExit(f"no hay migraciones .sql en {MIGRATIONS}: el backend no arrancaria")

hiddenimports = (
    # ws="websockets-sansio" y los protocolos que uvicorn elige por nombre en tiempo de ejecucion.
    collect_submodules("uvicorn")
    + collect_submodules("websockets")
    + collect_submodules("app")
)

a = Analysis(
    [str(BACKEND / "app" / "__main__.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    # Solo migraciones: nunca .env ni datos del usuario.
    datas=[(str(MIGRATIONS), "migrations")],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tests", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="drakter-backend",
    debug=False,
    strip=False,
    upx=False,
    console=True,  # el proceso lo lanza Electron sin ventana; stdout/stderr sirven para diagnostico
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="drakter-backend",
)
