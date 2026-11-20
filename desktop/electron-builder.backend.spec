# -*- mode: python ; coding: utf-8 -*-
# PyInstaller (onedir) del backend de Drakter. Lo invoca electron-builder.build-backend.mjs;
# no se cross-compila: genera el backend de la plataforma donde se ejecuta.
# SPECPATH (inyectado por PyInstaller) es el directorio de este archivo: desktop/.
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

BACKEND = (Path(SPECPATH) / ".." / "backend").resolve()
MIGRATIONS = BACKEND / "migrations"
RUNNER = BACKEND / "app" / "integrations" / "hermes" / "runner" / "drakter_runner.py"

# app/database/migrator.py resuelve MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations".
# En un build congelado __file__ vale <_MEIPASS>/app/database/migrator.pyc, asi que parents[2]
# es <_MEIPASS> (= <dist>/drakter-backend/_internal) y las migraciones deben ir en "migrations".
if not any(MIGRATIONS.glob("*.sql")):
    raise SystemExit(f"no hay migraciones .sql en {MIGRATIONS}: el backend no arrancaria")

# collect_submodules corre en un subproceso aislado que hereda sys.path pero no pathex: sin esto
# "app" no se encuentra, la lista sale vacia sin error y el backend congelado no monta ningun
# router (app.main los descubre con pkgutil y los importa por nombre).
sys.path.insert(0, str(BACKEND))
app_modules = collect_submodules("app")
if "app.api.health" not in app_modules:
    raise SystemExit("collect_submodules('app') no encontro app.api.health: el backend no montaria rutas")
# Hermes ejecuta el runner como archivo (`<hermes_python> -I drakter_runner.py`): debe existir en
# disco junto a supervisor.pyc, no solo compilado dentro del PYZ.
if not RUNNER.is_file():
    raise SystemExit(f"falta el runner de Hermes: {RUNNER}")

hiddenimports = (
    # ws="websockets-sansio" y los protocolos que uvicorn elige por nombre en tiempo de ejecucion.
    collect_submodules("uvicorn")
    + collect_submodules("websockets")
    + app_modules
)

a = Analysis(
    [str(BACKEND / "app" / "__main__.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    # Migraciones, runner de Hermes y pyproject (version del backend en las copias). Nunca .env ni
    # datos del usuario. agent/ y voice/ van como extraResources (electron-builder.yml): el
    # REPO_ROOT del backend congelado es el padre de _internal, es decir resources/backend/.
    datas=[
        (str(MIGRATIONS), "migrations"),
        (str(RUNNER), "app/integrations/hermes/runner"),
        (str(BACKEND / "pyproject.toml"), "."),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    # `drakter-backend -B -m app.services.readers.worker`: ver el propio hook.
    runtime_hooks=[str(Path(SPECPATH) / "electron-builder.rthook-module.py")],
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
