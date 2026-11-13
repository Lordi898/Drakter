"""Ataques DESK: Electron y la frontera renderer/backend (dossier F05 y F12).

Son sobre todo estáticos: leen las fuentes de `desktop/`, del árbol integrado
(`<backend_dir>/../desktop`) o, si no existe, de la primera rama que lo tenga
(`git show`). No arrancan Electron ni instalan nada. Lo que solo se vería con la
app en marcha se dice en el mensaje como NO COMPROBADO. DESK-11 además lanza
peticiones reales al backend para ver qué Origin acepta.

Claves opcionales del contrato (`ctx.contract.get`):
- `desktop_branches`: ramas donde buscar `desktop/` si no está en el árbol.
- `desktop_origin_default`: Origin que declara el backend si no se lee de config.
"""

from __future__ import annotations

import re
import subprocess
from functools import lru_cache
from pathlib import Path

from redlib import Context, NotApplicable, attack, expect

REPO = Path(__file__).resolve().parents[2]
DEFAULT_BRANCHES = ["drakter/chat-personaje", "drakter/desktop-shell", "drakter/electron-host"]
GUARANTEE_ELECTRON = "CLAUDE.md §8: separación estricta agente/interfaz/datos; F05"
GUARANTEE_CSP = "CLAUDE.md §8: documentos y memoria son datos no confiables; F12"


# ---------------------------------------------------------------------------
# Acceso a las fuentes
# ---------------------------------------------------------------------------


class Tree:
    """Fuentes de `desktop/` desde un directorio o desde una rama de git."""

    def __init__(self, label: str, directory: Path | None, ref: str | None) -> None:
        self.label, self.directory, self.ref = label, directory, ref
        self._files: list[str] | None = None

    def files(self) -> list[str]:
        if self._files is None:
            if self.directory is not None:
                self._files = sorted(
                    str(p.relative_to(self.directory.parent))
                    for p in self.directory.rglob("*")
                    if p.is_file() and "node_modules" not in p.parts and "out" not in p.parts[-3:-1]
                )
            else:
                out = subprocess.run(
                    ["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", str(self.ref), "desktop"],
                    capture_output=True, text=True, check=True,
                ).stdout
                self._files = sorted(line for line in out.splitlines() if line)
        return self._files

    def under(self, prefix: str, suffixes: tuple[str, ...] = (".ts", ".tsx")) -> list[str]:
        return [f for f in self.files() if f.startswith("desktop/" + prefix) and f.endswith(suffixes)]

    def read(self, path: str) -> str:
        if self.directory is not None:
            return (self.directory.parent / path).read_text("utf-8", "replace")
        return subprocess.run(
            ["git", "-C", str(REPO), "show", f"{self.ref}:{path}"],
            capture_output=True, text=True, check=True,
        ).stdout

    def has(self, path: str) -> bool:
        return path in self.files()


_STRING_OR_COMMENT = re.compile(
    r"""("(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`)|//[^\n]*|/\*.*?\*/""", re.S
)


def strip_comments(text: str) -> str:
    return _STRING_OR_COMMENT.sub(lambda m: m.group(1) or " ", text)


def _ref_exists(ref: str) -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(REPO), "cat-file", "-e", f"{ref}:desktop/electron/main/index.ts"],
            capture_output=True,
        ).returncode
        == 0
    )


@lru_cache(maxsize=8)
def _find_tree(backend_dir: str, branches: tuple[str, ...]) -> Tree | None:
    integrated = Path(backend_dir).parent / "desktop"
    if (integrated / "electron" / "main").is_dir():
        return Tree(f"árbol integrado {integrated}", integrated, None)
    for ref in branches:
        try:
            if _ref_exists(ref):
                return Tree(f"rama {ref}", None, ref)
        except OSError:
            break
    return None


def tree(ctx: Context) -> Tree:
    branches = tuple(ctx.contract.get("desktop_branches", DEFAULT_BRANCHES))
    found = _find_tree(str(ctx.backend_dir), branches)
    if found is None:
        raise NotApplicable("no hay desktop/ en el árbol integrado ni en ninguna rama accesible")
    return found


def code(t: Tree, prefix: str) -> dict[str, str]:
    """Fuentes sin comentarios de todos los .ts/.tsx bajo `desktop/<prefix>`."""
    return {f: strip_comments(t.read(f)) for f in t.under(prefix)}


def line_of(t: Tree, path: str, needle: str) -> str:
    """`archivo:línea` de la primera aparición, para citar en los mensajes."""
    for number, line in enumerate(t.read(path).splitlines(), 1):
        if needle in line:
            return f"{path}:{number}"
    return path


def balanced(text: str, start: int) -> str:
    """Texto entre el paréntesis que abre en `start` y su cierre."""
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return text[start:]


# ---------------------------------------------------------------------------
# CSP
# ---------------------------------------------------------------------------


def csp_constant(config: str, name: str) -> dict[str, list[str]]:
    match = re.search(rf"const\s+{name}\s*=\s*\[(.*?)\]\s*\.join\(", config, re.S)
    if not match:
        raise NotApplicable(f"no se encontró la constante {name} en electron.vite.config.ts")
    policy: dict[str, list[str]] = {}
    for literal in re.findall(r"""(["'])(.*?)\1(?=\s*,|\s*$)""", match.group(1), re.S):
        parts = literal[1].split()
        if parts:
            policy[parts[0]] = parts[1:]
    return policy


def csp_effective(policy: dict[str, list[str]], directive: str) -> list[str]:
    return policy.get(directive, policy.get("default-src", ["*"]))


def remote_sources(tokens: list[str]) -> list[str]:
    """Orígenes que no son propios ni loopback: vía de carga o de exfiltración."""
    bad = []
    for token in tokens:
        low = token.lower()
        if low in {"data:", "blob:"} or low.startswith("'"):
            continue  # palabras clave ('self', 'none', 'unsafe-inline'...) se juzgan aparte
        if re.match(r"^(https?|wss?)://(localhost|127\.0\.0\.1|\[::1\])(:[\d*]+)?$", low):
            continue
        bad.append(token)
    return bad


# ---------------------------------------------------------------------------
# DESK-01 Preferencias de la ventana
# ---------------------------------------------------------------------------

FORBIDDEN_PREFS = re.compile(
    r"contextIsolation\s*:\s*false|sandbox\s*:\s*false|nodeIntegration\s*:\s*true|"
    r"webSecurity\s*:\s*false|allowRunningInsecureContent\s*:\s*true|"
    r"nodeIntegrationInSubFrames\s*:\s*true|nodeIntegrationInWorker\s*:\s*true|"
    r"webviewTag\s*:\s*true|experimentalFeatures\s*:\s*true|enableBlinkFeatures|"
    r"disable-web-security|disable-site-isolation|allow-file-access|"
    r"enableRemoteModule|sandbox-disabled|disable-gpu-sandbox"
)


@attack(
    "DESK-01",
    "contextIsolation, sandbox y nodeIntegration explícitos en toda ventana",
    guarantee=GUARANTEE_ELECTRON,
)
def window_preferences(ctx: Context) -> None:
    t = tree(ctx)
    sources = code(t, "electron/")
    windows = 0
    for path, text in sources.items():
        hit = FORBIDDEN_PREFS.search(text)
        expect(not hit, f"{line_of(t, path, hit.group(0) if hit else '')}: preferencia insegura {hit.group(0) if hit else ''}")
        for match in re.finditer(r"new\s+(BrowserWindow|BrowserView|WebContentsView)\s*\(", text):
            windows += 1
            call = balanced(text, match.end() - 1)
            for needle, label in (
                (r"contextIsolation\s*:\s*true", "contextIsolation: true"),
                (r"sandbox\s*:\s*true", "sandbox: true"),
                (r"nodeIntegration\s*:\s*false", "nodeIntegration: false"),
            ):
                expect(re.search(needle, call), f"{path}: {match.group(1)} sin {label} explícito")
    if windows == 0:
        raise NotApplicable("no se crea ninguna ventana en electron/: no se alcanzó el camino atacado")
    all_main = "\n".join(sources.values())
    for match in re.finditer(r"no-sandbox|NO_SANDBOX", all_main):
        before = all_main[max(0, match.start() - 500) : match.start()]
        expect(re.search(r"isPackaged", before), f"opción sin sandbox no condicionada a !app.isPackaged (cerca de {match.group(0)!r}): un paquete podría arrancar sin sandbox")
    if "app.enableSandbox()" not in all_main:
        # La política global puede vivir en un módulo aparte; si no existe en la rama, solo vale el sandbox por ventana.
        expect(re.search(r"applySandboxPolicy", all_main), "falta app.enableSandbox() y ninguna política de sandbox global")
        if not t.has("desktop/electron/main/sandbox.ts"):
            pass  # sandbox.ts ausente: lo recoge DESK-21; la ventana sigue con sandbox: true


# ---------------------------------------------------------------------------
# DESK-02 Validación del remitente de cada IPC
# ---------------------------------------------------------------------------


@attack(
    "DESK-02",
    "Todo canal IPC valida remitente (marco, URL, frameTreeNodeId) y el preload no filtra ninguno",
    guarantee=GUARANTEE_ELECTRON,
)
def ipc_sender_validation(ctx: Context) -> None:
    t = tree(ctx)
    main = code(t, "electron/main/")
    preload = code(t, "electron/preload/")
    shared = code(t, "electron/shared/")
    if not main:
        raise NotApplicable("no hay código de main")

    registrations = 0
    validator_found = False
    for path, text in main.items():
        for match in re.finditer(r"ipcMain\s*\.\s*(handle|handleOnce|on|once)\s*\(", text):
            registrations += 1
            call = balanced(text, match.end() - 1)
            expect(
                re.search(r"assert\w*Sender\s*\(|validate\w*Sender\s*\(", call),
                f"{line_of(t, path, match.group(0))}: ipcMain.{match.group(1)} sin validar el remitente",
            )
        for match in re.finditer(r"function\s+(assert\w*Sender|validate\w*Sender)\s*\(", text):
            validator_found = True
            body = text[match.start() : match.start() + 900]
            for needle, label in (
                ("senderFrame", "senderFrame"),
                ("frameTreeNodeId", "frameTreeNodeId (solo el marco principal)"),
                ("sender.id", "identidad del webContents"),
                (".url", "URL del marco"),
            ):
                expect(needle in body, f"{path}: el validador no comprueba {label}")
            expect(re.search(r"frame\s*!==\s*null|frame\s*===\s*null|!\s*frame\b|frame\s*\?", body), f"{path}: el validador no trata senderFrame nulo")
    expect(registrations > 0 or not validator_found, "hay validador pero ningún canal registrado")
    if registrations == 0:
        raise NotApplicable("main no registra ningún canal IPC")
    expect(validator_found, "se registran canales pero no existe función validadora del remitente")

    handled = set(re.findall(r"\bhandle\(\s*IPC_CHANNELS\.(\w+)", "\n".join(main.values())))
    declared = set(re.findall(r"^\s*(\w+)\s*:\s*['\"]", "\n".join(shared.values()), re.M))
    preload_text = "\n".join(preload.values())
    used = set(re.findall(r"ipcRenderer\s*\.\s*invoke\(\s*IPC_CHANNELS\.(\w+)", preload_text))
    expect(not re.search(r"exposeInMainWorld\([^,]+,\s*ipcRenderer\b", preload_text), "el preload expone ipcRenderer entero")
    expect(not re.search(r"ipcRenderer\s*\.\s*(send|sendSync|postMessage|sendTo|sendToHost)\s*\(", preload_text), "el preload usa send/sendSync sin valor de retorno validado")
    for call in re.finditer(r"ipcRenderer\s*\.\s*(invoke|on|once)\s*\(\s*(\S+?)\s*[,)]", preload_text):
        expect(call.group(2).startswith("IPC_CHANNELS."), f"el preload usa un canal que no es una constante cerrada: {call.group(2)}")
    for call in re.finditer(r"ipcRenderer\s*\.\s*(on|once)\s*\(", preload_text):
        callback = balanced(preload_text, call.end() - 1)
        expect(
            not re.search(r"emit\(\s*['\"]\w+['\"]\s*,\s*_?(message|event)\s*\)|exposeInMainWorld", callback),
            "el preload entrega al renderer el objeto de evento de IPC (incluye puertos y remitente)",
        )
    used |= set(re.findall(r"ipcRenderer\s*\.\s*(?:on|once)\(\s*IPC_CHANNELS\.(\w+)", preload_text))
    handled |= {"eventsPort", "connectionChanged"} & used  # canales main -> preload: no tienen manejador en main
    expect(used <= handled, f"el preload invoca canales sin manejador en main: {sorted(used - handled)}")
    expect(handled <= declared or not declared, f"main maneja canales no declarados: {sorted(handled - declared)}")
    expect(used, "no se alcanzó el preload: ningún invoke con constante")
    sends = re.findall(r"\.send\(\s*IPC_CHANNELS\.(\w+)", "\n".join(main.values()))
    expect(set(sends) <= {"connectionChanged", "eventsPort"}, f"main envía por canales no previstos al renderer: {sends}")


# ---------------------------------------------------------------------------
# DESK-03 Navegación, ventanas, webview
# ---------------------------------------------------------------------------


@attack(
    "DESK-03",
    "Navegación, window.open y webview bloqueados en todo WebContents",
    guarantee=GUARANTEE_ELECTRON,
)
def navigation_lockdown(ctx: Context) -> None:
    t = tree(ctx)
    main = code(t, "electron/main/")
    text = "\n".join(main.values())
    if "web-contents-created" not in text:
        raise NotApplicable("no hay endurecimiento global de WebContents que atacar")
    for event in ("will-navigate", "will-redirect"):
        expect(re.search(rf"on\(\s*['\"]{event}['\"]\s*,\s*(\w+|\()", text), f"sin manejador de {event}")
    handler = re.search(r"function\s+blockUntrustedNavigation\s*\(.*?\{(.*?)\n\}", text, re.S)
    expect(handler and "preventDefault" in handler.group(1) and "isTrusted" in handler.group(1), "el manejador de navegación no bloquea lo no fiable")
    expect(re.search(r"will-attach-webview['\"]\s*,\s*\([^)]*\)\s*=>\s*[^,]*preventDefault", text), "will-attach-webview no se cancela")
    opener = re.search(r"setWindowOpenHandler\s*\(", text)
    expect(opener, "sin setWindowOpenHandler: window.open crearía ventanas")
    body = balanced(text, opener.end() - 1) if opener else ""
    expect("'deny'" in body or '"deny"' in body, "setWindowOpenHandler no devuelve deny")
    expect("action: 'allow'" not in body and 'action: "allow"' not in body, "setWindowOpenHandler permite abrir")
    expect(not re.search(r"webviewTag\s*:\s*true", text), "webviewTag activado")
    # Un iframe hijo no pasa por will-navigate; solo lo frena CSP (frame-src) o will-frame-navigate.
    if "will-frame-navigate" not in text:
        config = strip_comments(t.read("desktop/electron.vite.config.ts"))
        policy = csp_constant(config, "PRODUCTION_CSP")
        expect(
            csp_effective(policy, "frame-src") == ["'none'"],
            "sin will-frame-navigate y la CSP de producción no cierra frame-src: un iframe hijo podría navegar",
        )
    for match in re.finditer(r"shell\s*\.\s*openExternal\s*\(", text):
        around = text[max(0, match.start() - 600) : match.end() + 200]
        expect(
            re.search(r"https:|protocol", around), f"shell.openExternal sin validar el esquema ({line_of(t, 'desktop/electron/main/index.ts', 'openExternal')})"
        )


# ---------------------------------------------------------------------------
# DESK-04 Permisos
# ---------------------------------------------------------------------------


@attack("DESK-04", "Permisos del navegador denegados por defecto", guarantee=GUARANTEE_ELECTRON)
def permissions_denied(ctx: Context) -> None:
    t = tree(ctx)
    text = "\n".join(code(t, "electron/main/").values())
    if "setPermissionRequestHandler" not in text:
        if re.search(r"applyPermissionPolicy", text):
            raise NotApplicable(
                "main delega los permisos en applyPermissionPolicy() de ./permissions, que no existe en esta rama "
                "(la versión anterior de index.ts denegaba todo en línea): no se puede atacar nada. Ver DESK-21"
            )
        raise NotApplicable("main no configura permisos: no se alcanzó el camino atacado")
    request = re.search(r"setPermissionRequestHandler\s*\(", text)
    body = balanced(text, request.end() - 1) if request else ""
    expect(re.search(r"callback\(\s*false\s*\)", body), "el manejador de peticiones no deniega")
    expect(not re.search(r"callback\(\s*true\s*\)|callback\(\s*(?!false)\w", body), "el manejador de peticiones puede conceder permisos")
    check = re.search(r"setPermissionCheckHandler\s*\(", text)
    expect(check, "falta setPermissionCheckHandler: las comprobaciones síncronas quedan por defecto")
    expect(re.search(r"=>\s*false", balanced(text, check.end() - 1)) if check else False, "setPermissionCheckHandler no devuelve false")
    expect("fromPartition" not in text, "hay sesiones con partición propia sin el mismo endurecimiento")
    expect("setDevicePermissionHandler" not in text or "return false" in text, "permisos de dispositivo sin denegar")


# ---------------------------------------------------------------------------
# DESK-05 / 06 CSP
# ---------------------------------------------------------------------------


def _csp_checks(policy: dict[str, list[str]], name: str, *, production: bool) -> None:
    expect(policy, f"{name} vacía")
    expect(csp_effective(policy, "default-src") in (["'none'"], ["'self'"]), f"{name}: default-src permisivo {policy.get('default-src')}")
    scripts = csp_effective(policy, "script-src")
    expect("'unsafe-eval'" not in scripts, f"{name}: script-src con unsafe-eval")
    expect(not remote_sources(scripts), f"{name}: script-src con orígenes remotos {remote_sources(scripts)}")
    if production:
        expect("'unsafe-inline'" not in scripts, f"{name}: script-src con unsafe-inline en producción")
    for directive in ("img-src", "connect-src", "font-src", "style-src", "media-src", "frame-src", "object-src"):
        tokens = csp_effective(policy, directive)
        expect("*" not in tokens, f"{name}: {directive} con comodín")
        expect(not remote_sources(tokens), f"{name}: {directive} permite orígenes no propios {remote_sources(tokens)}")
    expect(csp_effective(policy, "object-src") == ["'none'"], f"{name}: object-src no es 'none'")
    expect(policy.get("base-uri") == ["'none'"], f"{name}: base-uri no es 'none'")
    expect(policy.get("form-action") == ["'none'"], f"{name}: form-action no es 'none'")
    # F12: el renderer no puede cargar imágenes remotas ni hablar con terceros.
    expect(set(csp_effective(policy, "img-src")) <= {"'self'", "data:", "blob:", "'none'"}, f"{name}: img-src permite {policy.get('img-src')}")


@attack(
    "DESK-05",
    "CSP de producción: sin eval ni scripts en línea, sin imágenes ni conexiones remotas",
    guarantee=GUARANTEE_CSP,
    finding="F12",
)
def csp_production(ctx: Context) -> None:
    t = tree(ctx)
    config = strip_comments(t.read("desktop/electron.vite.config.ts"))
    _csp_checks(csp_constant(config, "PRODUCTION_CSP"), "PRODUCTION_CSP", production=True)
    selector = re.search(r"context\.server\s*\?\s*(\w+)\s*:\s*(\w+)", config)
    expect(selector, "no se ve cómo se elige la CSP según desarrollo/producción")
    expect(selector.group(2) == "PRODUCTION_CSP", "la rama sin servidor de desarrollo no usa PRODUCTION_CSP: la CSP floja podría llegar al build")


@attack(
    "DESK-06",
    "CSP de desarrollo: sin eval ni orígenes remotos, y no llega al build",
    guarantee=GUARANTEE_CSP,
    finding="F12",
)
def csp_development(ctx: Context) -> None:
    t = tree(ctx)
    config = strip_comments(t.read("desktop/electron.vite.config.ts"))
    policy = csp_constant(config, "DEVELOPMENT_CSP")
    _csp_checks(policy, "DEVELOPMENT_CSP", production=False)
    selector = re.search(r"context\.server\s*\?\s*(\w+)\s*:\s*(\w+)", config)
    expect(selector and selector.group(1) == "DEVELOPMENT_CSP", "la CSP de desarrollo no se liga a context.server")


@attack(
    "DESK-07",
    "La CSP de producción deja pasar el canal legítimo al backend sin abrir el resto (F12)",
    guarantee=GUARANTEE_CSP,
    finding="F12",
)
def csp_matches_client(ctx: Context) -> None:
    t = tree(ctx)
    sources = code(t, "src/")
    uses_fetch = [p for p, s in sources.items() if re.search(r"\bfetch\s*\(", s)]
    uses_ws = [p for p, s in sources.items() if re.search(r"new\s+WebSocket\s*\(", s)]
    config = strip_comments(t.read("desktop/electron.vite.config.ts"))
    if not uses_fetch and not uses_ws:
        uses_bridge = re.search(r"window\.(drakter\.)?api\b", "\n".join(sources.values()))
        if not uses_bridge:
            raise NotApplicable("el renderer aún no abre conexiones de red ni usa el puente")
        expect(csp_effective(csp_constant(config, "PRODUCTION_CSP"), "connect-src") == ["'none'"], "el renderer solo habla por el puente: connect-src debería ser 'none'")
        return
    connect = csp_effective(csp_constant(config, "PRODUCTION_CSP"), "connect-src")
    loopback_http = any(re.match(r"^http://(127\.0\.0\.1|localhost)", x) for x in connect)
    loopback_ws = any(re.match(r"^ws://(127\.0\.0\.1|localhost)", x) for x in connect)
    if uses_fetch:
        expect(loopback_http, f"{uses_fetch[0]} usa fetch() hacia http://127.0.0.1 pero connect-src de producción es {connect}: Chromium lo bloquea y el chat no funciona (NO COMPROBADO en ejecución); quien lo arregle estará tentado de ensanchar la CSP")
    if uses_ws:
        expect(loopback_ws, f"{uses_ws[0]} abre un WebSocket a ws://127.0.0.1 pero connect-src de producción es {connect}")
    dev = csp_effective(csp_constant(config, "DEVELOPMENT_CSP"), "connect-src")
    if uses_fetch:
        expect(any(re.match(r"^http://(127\.0\.0\.1|localhost)", x) for x in dev), f"connect-src de desarrollo {dev} no permite fetch() a http://127.0.0.1: el chat tampoco funciona con `npm run dev`")


# ---------------------------------------------------------------------------
# DESK-08 El marcador %DRAKTER_CSP% siempre se sustituye
# ---------------------------------------------------------------------------


@attack(
    "DESK-08",
    "%DRAKTER_CSP% se sustituye siempre y todo HTML del renderer lleva CSP",
    guarantee=GUARANTEE_CSP,
    finding="F12",
)
def csp_placeholder(ctx: Context) -> None:
    t = tree(ctx)
    config = strip_comments(t.read("desktop/electron.vite.config.ts"))
    plugin = re.search(r"function\s+contentSecurityPolicy\s*\(\)(.*?)\n\}", config, re.S)
    expect(plugin, "no existe el plugin que inyecta la CSP")
    body = plugin.group(1)
    expect("transformIndexHtml" in body and "%DRAKTER_CSP%" in body, "el plugin no sustituye %DRAKTER_CSP%")
    expect(not re.search(r"\bapply\s*:|\benforce\s*:\s*['\"]post|\bmode\b", body), "el plugin se aplica condicionalmente (apply/mode): podría saltarse en un build")
    expect(re.search(r"renderer\s*:\s*\{.*plugins\s*:\s*\[[^\]]*contentSecurityPolicy\(\)", config, re.S), "el plugin no está en los plugins del renderer")
    html_files = [f for f in t.files() if f.endswith(".html") and "/design/" not in f]
    expect(html_files, "no hay HTML de entrada")
    entry_inputs = re.findall(r"input\s*:\s*resolve\([^)]*['\"]([^'\"]+\.html)['\"]", config)
    for html in html_files:
        text = t.read(html)
        expect(
            re.search(r"http-equiv=\"Content-Security-Policy\"\s+content=\"%DRAKTER_CSP%\"", text),
            f"{html}: sin meta CSP con el marcador",
        )
        expect(text.count("%DRAKTER_CSP%") == 1, f"{html}: el marcador aparece {text.count('%DRAKTER_CSP%')} veces; solo se sustituye la primera")
    expect(sorted(Path(h).name for h in html_files) == sorted(Path(h).name for h in entry_inputs) or not entry_inputs, f"HTML sin CSP fuera de las entradas: {html_files} vs {entry_inputs}")
    # Simula la sustitución del plugin para ambas ramas.
    for name in ("PRODUCTION_CSP", "DEVELOPMENT_CSP"):
        policy = csp_constant(config, name)
        rendered = "; ".join(f"{k} {' '.join(v)}" for k, v in policy.items())
        out = t.read(html_files[0]).replace("%DRAKTER_CSP%", rendered)
        expect("%DRAKTER_CSP%" not in out and "default-src" in out, f"tras sustituir {name} el HTML sigue sin CSP válida")
    # Fallo abierto: si el marcador llega sin sustituir, Chromium ignora la política y no hay CSP.
    # No se comprobó con un build real (NO COMPROBADO): `electron-vite build` no se ejecuta aquí.


# ---------------------------------------------------------------------------
# DESK-09 El token de sesión
# ---------------------------------------------------------------------------

TOKEN_SINKS = re.compile(
    r"(localStorage|sessionStorage|indexedDB|document\.cookie|window\.name|history\.(push|replace)State|console\.\w+|logError|toast\w*|notify\w*|new\s+Notification)\s*[.(][^;\n]*\btoken\b",
    re.I,
)


@attack(
    "DESK-09",
    "El token de sesión no se guarda, registra ni viaja por URL, y el aprobador no llega al renderer",
    guarantee="CLAUDE.md §8: secretos fuera de logs; F05",
    finding="F05",
)
def token_location(ctx: Context) -> None:
    t = tree(ctx)
    renderer = code(t, "src/")
    electron = code(t, "electron/")
    session_files = [p for p, s in renderer.items() if re.search(r"\btoken\b", s)]
    approver = [p for p, s in {**renderer, **electron}.items() if re.search(r"approver", s, re.I)]
    if not session_files:
        raise NotApplicable("el renderer todavía no maneja ningún token")
    for path, text in renderer.items():
        hit = TOKEN_SINKS.search(text)
        expect(not hit, f"{path}: el token alcanza {hit.group(1) if hit else ''}")
        expect(not re.search(r"[?&]token=|\$\{[^}]*token[^}]*\}\s*[\"'`]?\s*[&?]", text), f"{path}: el token viaja en la URL")
        expect(not re.search(r"(localStorage|sessionStorage)[^;\n]*(session|bearer)", text, re.I), f"{path}: sesión en almacenamiento web")
    expect(not [p for p in approver if p.startswith("desktop/src/")], f"credencial del aprobador referenciada en el renderer: {approver}")


# ---------------------------------------------------------------------------
# DESK-10 La aprobación sale de Electron main (F05)
# ---------------------------------------------------------------------------


@attack(
    "DESK-10",
    "La aprobación de acciones destructivas la hace Electron main, no el renderer",
    guarantee="CLAUDE.md §8: acciones destructivas requieren confirmación; F05",
    finding="F05",
)
def approval_from_main(ctx: Context) -> None:
    t = tree(ctx)
    renderer = code(t, "src/")
    main = "\n".join(code(t, "electron/").values())
    blob = "\n".join(renderer.values())
    # Control: el renderer sí maneja confirmaciones (si no, no se alcanzó el camino).
    if not re.search(r"confirmation", blob, re.I):
        raise NotApplicable("el renderer aún no maneja confirmaciones")
    for path, text in renderer.items():
        expect(
            not re.search(r"/(approve|reject)\b|approveConfirmation|rejectConfirmation|decideConfirmation", text),
            f"{path}: el renderer conoce o llama rutas de aprobación del backend: aprueba con su propio token",
        )
        expect(
            not re.search(r"method\s*:\s*['\"](POST|PUT|PATCH|DELETE)['\"][^}]*confirm|confirm\w*[^;\n]*method\s*:\s*['\"]POST", text, re.I),
            f"{path}: el renderer escribe sobre confirmaciones",
        )
    # Lado de main: si el renderer pide la revisión por el puente, main debe decidir con diálogo nativo.
    asks = re.search(r"reviewConfirmation|requestApproval", blob)
    approvals = t.has("desktop/electron/main/approvals.ts")
    if "requestApproval" in main and not approvals:
        raise NotApplicable(
            "main enruta `requestApproval` (ipc.ts) a ./approvals, que no existe en esta rama: el diálogo nativo, la credencial "
            "de aprobador y la descarga del detalle no se pueden atacar. Ver DESK-21"
        )
    if asks and "requestApproval" not in main and not re.search(r"review-confirmation|reviewConfirmation|confirmation", main, re.I):
        raise NotApplicable("el renderer pide la revisión y main no la implementa (ni bridge.ts, ni preload, ni ipc.ts). Ver DESK-18")
    expect(re.search(r"showMessageBox", main), "main revisa confirmaciones sin diálogo nativo")
    expect(re.search(r"cancelId\s*:", main) and re.search(r"defaultId\s*:", main), "el diálogo nativo no fija defaultId/cancelId (foco en Cancelar)")
    expect(re.search(r"gui_approver|approver", main, re.I), "main no usa una credencial de aprobador distinta de la del renderer")
    expect(not re.search(r"summary\s*[:=]\s*(payload|request|args)", main), "main muestra un resumen que le manda el renderer en vez de descargarlo del backend")


@attack(
    "DESK-18",
    "Todo lo que el renderer espera de window.drakter existe en bridge, preload y main",
    guarantee="CLAUDE.md §8: separación interfaz/datos; F05",
    finding="F05",
)
def bridge_completeness(ctx: Context) -> None:
    t = tree(ctx)
    renderer = "\n".join(code(t, "src/").values())
    bridge = t.read("desktop/electron/shared/bridge.ts")
    preload = t.read("desktop/electron/preload/index.ts")
    main = "\n".join(code(t, "electron/main/").values())
    block = re.search(r"Partial<\{(.*?)\}>", renderer, re.S)
    if not block:
        raise NotApplicable("el renderer no declara métodos opcionales del puente")
    expected = re.findall(r"^\s*(\w+)\s*\(", block.group(1), re.M)
    expect(expected, "no se alcanzaron los métodos esperados")
    missing = [m for m in expected if m not in bridge or m not in preload or m not in main]
    expect(
        not missing,
        f"el renderer detecta en tiempo de ejecución {expected} pero {missing} no están en bridge.ts/preload/ipc.ts: "
        f"en la app real `getBackendSession` no existe, así que no hay sesión, ni WebSocket, ni chat, y `reviewConfirmation` "
        f"no existe, así que ninguna acción destructiva puede aprobarse (falla cerrado, pero la mitad de main de F05 no está construida)",
    )


# ---------------------------------------------------------------------------
# DESK-11 El Origin del renderer empaquetado encaja con allowed_origins
# ---------------------------------------------------------------------------


@attack(
    "DESK-11",
    "El Origin real del renderer empaquetado está en allowed_origins del backend",
    guarantee="CLAUDE.md §8: separación interfaz/datos; F05 (validar Origin)",
    finding="F05",
)
def origin_matches(ctx: Context) -> None:
    t = tree(ctx)
    main = "\n".join(code(t, "electron/main/").values())
    net = [p for p, x in code(t, "src/").items() if re.search(r"\bfetch\s*\(|new\s+WebSocket\s*\(", x)]
    if not net and "apiCall" in main:
        raise NotApplicable("el renderer ya no abre conexiones: habla por main (Node no envía Origin y el guardia lo admite); el Origin del renderer no se usa")
    url_file = strip_comments(t.read("desktop/electron/main/renderer-url.ts")) if t.has("desktop/electron/main/renderer-url.ts") else main
    custom = re.findall(r"registerSchemesAsPrivileged\s*\(\s*\[\s*\{\s*scheme\s*:\s*['\"](\w+)", main)
    handles_scheme = re.findall(r"protocol\s*\.\s*(?:handle|registerFileProtocol)\s*\(\s*['\"](\w+)", main)
    loads_file = "pathToFileURL" in url_file or "loadFile" in main or "file://" in url_file
    renderer_origins = {f"{s}://drakter" for s in set(custom) & set(handles_scheme)} if custom else set()
    if loads_file and not renderer_origins:
        # Chromium: fetch desde file:// manda "Origin: null"; WebSocket manda "Origin: file://".
        renderer_origins = {"null", "file://"}
    if not renderer_origins:
        raise NotApplicable("no se pudo determinar el esquema del renderer empaquetado")

    allowed = tuple(ctx.contract.get("desktop_origin_default", ("app://drakter",)))
    config = ctx.backend_dir / "app" / "core" / "config.py"
    if config.is_file():
        match = re.search(r"allowed_origins\s*:[^=\n]*=\s*\(([^)]*)\)", config.read_text("utf-8"))
        if match:
            allowed = tuple(re.findall(r"""["']([^"']+)["']""", match.group(1))) or allowed
    # Ejecutado: qué hace el backend real con cada Origin. app://drakter es el control positivo.
    route = ctx.route("auth_check")
    control = ctx.http("GET", route, headers=[("Origin", "app://drakter")])
    expect(control.status == 200, f"control del ataque fallido: el Origin permitido da {control.status}, no se alcanzó el camino")
    verdicts = {}
    for origin in sorted(renderer_origins):
        verdicts[origin] = ctx.http("GET", route, headers=[("Origin", origin)]).status
    rejected = [o for o, s in verdicts.items() if s != 200]
    expect(
        not rejected,
        f"el renderer se carga con file:// (renderer-url.ts, sin protocol.handle ni esquema propio) y enviaría Origin {sorted(renderer_origins)}; "
        f"allowed_origins por defecto es {list(allowed)} y el backend responde {verdicts} (ejecutado contra el backend; "
        f"el Origin que Chromium manda de verdad NO COMPROBADO sin abrir la app). Con file:// el chat no puede conectar; "
        f"la salida fácil, permitir 'null', está rechazada por config y sería abrir el backend a cualquier página sandboxed",
    )


# ---------------------------------------------------------------------------
# DESK-12 ELECTRON_RENDERER_URL y comparación de URL de confianza
# ---------------------------------------------------------------------------


@attack(
    "DESK-12",
    "ELECTRON_RENDERER_URL solo cuenta sin empaquetar y la URL de confianza se compara exacta",
    guarantee=GUARANTEE_ELECTRON,
)
def renderer_url_gating(ctx: Context) -> None:
    t = tree(ctx)
    path = "desktop/electron/main/renderer-url.ts"
    if not t.has(path):
        raise NotApplicable("no hay renderer-url.ts")
    text = strip_comments(t.read(path))
    env_reads = re.findall(r"process\.env\s*\[?\.?\s*['\"]?(\w+)", text)
    expect("ELECTRON_RENDERER_URL" in env_reads, "no se alcanzó la lectura de ELECTRON_RENDERER_URL")
    expect(re.search(r"app\.isPackaged\s*\?\s*undefined\s*:\s*process\.env", text), f"{line_of(t, path, 'ELECTRON_RENDERER_URL')}: ELECTRON_RENDERER_URL no está condicionada a !app.isPackaged")
    expect(not re.search(r"\.(startsWith|includes|endsWith|indexOf|match|test)\s*\(", text.split("export function isTrustedRendererUrl")[-1]), "isTrustedRendererUrl compara por prefijo/subcadena")
    expect(re.search(r"===\s*trustedDocument", text), "la comparación de la URL de confianza no es igualdad estricta")
    others = {
        name
        for p, s in code(t, "electron/main/").items()
        for name in re.findall(r"process\.env\s*\[?\.?\s*['\"]?(\w+)", s)
    } - {"ELECTRON_RENDERER_URL"}
    for name in sorted(others):
        for path2, text2 in code(t, "electron/main/").items():
            for m in re.finditer(rf"process\.env\s*\[?\.?\s*['\"]?{name}", text2):
                expect(
                    re.search(r"isPackaged", text2[max(0, m.start() - 400) : m.end() + 200]),
                    f"{path2}: main lee la variable de entorno {name} sin condicionarla a !app.isPackaged",
                )
    loads = [m for s in code(t, "electron/main/").values() for m in re.findall(r"\.loadURL\(\s*([^)]*)\)", s)]
    expect(all(x.strip() == "RENDERER_URL" for x in loads) and loads, f"loadURL con argumentos distintos de RENDERER_URL: {loads}")
    # En desarrollo, el que controle el entorno del proceso elige qué cargar: aceptado, es el proceso del propio usuario.


# ---------------------------------------------------------------------------
# DESK-13 Fusibles
# ---------------------------------------------------------------------------


@attack(
    "DESK-13",
    "Fusibles de Electron endurecidos en el empaquetado",
    guarantee=GUARANTEE_ELECTRON,
)
def electron_fuses(ctx: Context) -> None:
    t = tree(ctx)
    files = t.files()
    package = t.read("desktop/package.json") if t.has("desktop/package.json") else ""
    packaging = [
        f for f in files if re.search(r"electron-builder\.(ya?ml|json5?|toml|[cm]?js)$|forge\.config\.|afterPack", f)
    ] + (["desktop/package.json#build"] if re.search(r'"build"\s*:\s*\{', package) else [])
    if not packaging:
        raise NotApplicable(
            "no hay configuración de empaquetado en desktop/ (ni electron-builder ni forge); "
            "los fusibles RunAsNode, EnableNodeCliInspectArguments, OnlyLoadAppFromAsar, "
            "EnableEmbeddedAsarIntegrityValidation y GrantFileProtocolExtraPrivileges quedan por fijar en la fase de empaquetado"
        )
    blob = package + "\n".join(t.read(f) for f in packaging if "#" not in f)
    expect(re.search(r"electronFuses|@electron/fuses|flipFuses|FuseV1Options", blob), "hay empaquetado pero ningún fusible configurado")
    for fuse in ("runAsNode", "enableNodeCliInspectArguments", "onlyLoadAppFromAsar", "enableEmbeddedAsarIntegrityValidation", "grantFileProtocolExtraPrivileges"):
        expect(re.search(rf"{fuse}\s*:\s*(false|true)", blob, re.I) or fuse.lower() in blob.lower(), f"fusible {fuse} sin fijar")


# ---------------------------------------------------------------------------
# DESK-14 HTML crudo
# ---------------------------------------------------------------------------

HTML_SINKS = re.compile(
    r"dangerouslySetInnerHTML|\.innerHTML\s*=|\.outerHTML\s*=|insertAdjacentHTML|document\.write|"
    r"\beval\s*\(|new\s+Function\s*\(|srcDoc\s*=|createContextualFragment|DOMParser|\.setAttribute\(\s*['\"]on",
)


@attack(
    "DESK-14",
    "El renderer no inyecta HTML crudo ni evalúa texto",
    guarantee=GUARANTEE_CSP,
    finding="F12",
)
def raw_html_sinks(ctx: Context) -> None:
    t = tree(ctx)
    sources = code(t, "src/")
    if not sources:
        raise NotApplicable("no hay código de renderer")
    for path, text in sources.items():
        for match in HTML_SINKS.finditer(text):
            line = text[: match.start()].count("\n") + 1
            rest = text[match.start() : match.start() + 120]
            if ".innerHTML" in match.group(0) and re.search(r"=\s*markup\(\s*id\s*\)", rest):
                # Plantilla SVG fija; id sale de un contador interno. Se comprueba que siga siendo así.
                expect(re.search(r"let\s+id\s*=\s*['\"]drakter-['\"]\s*\+\s*\(\+\+\w+\)", text), f"{path}: el id interpolado en el SVG ya no sale del contador")
                expect(re.search(r"function\s+markup\(\s*id\s*:\s*string\s*\)", text), f"{path}: markup() cambió de firma")
                continue
            raise_msg = f"{path}:~{line}: sumidero HTML {match.group(0)!r}"
            expect(False, raise_msg)
    pkg = t.read("desktop/package.json")
    libs = re.findall(r'"(react-markdown|marked|markdown-it|remark[\w-]*|rehype[\w-]*|dompurify|showdown|micromark|mdx[\w/@-]*|@mdx-js/[\w-]+)"', pkg)
    if libs:
        everything = "\n".join(sources.values())
        expect("rehype-raw" not in libs, "rehype-raw activo: el Markdown acepta HTML crudo")
        expect(re.search(r"skipHtml|disallowedElements|allowedElements|DOMPurify|sanitize", everything), f"hay {libs} pero el renderer no sanea ni descarta HTML")
        expect(re.search(r"urlTransform|components\s*=\s*\{\{[^}]*img", everything), "hay Markdown pero no se filtran las imágenes remotas (F12)")


# ---------------------------------------------------------------------------
# DESK-15 Markdown del chat
# ---------------------------------------------------------------------------


@attack(
    "DESK-15",
    "El texto no confiable del chat se pinta como texto, no como Markdown, HTML, enlace ni imagen",
    guarantee=GUARANTEE_CSP,
    finding="F12",
)
def chat_untrusted_text(ctx: Context) -> None:
    t = tree(ctx)
    pkg = t.read("desktop/package.json")
    transcripts = [f for f in t.files() if re.search(r"chat/.*(Transcript|Message|Dock)\.tsx$|chat/ConfirmationDialog\.tsx$", f)]
    libs = re.findall(r"react-markdown|marked|markdown-it|remark|micromark|showdown|mdx", pkg)
    if not libs and not [f for f in transcripts if "Transcript" in f or "Confirmation" in f]:
        raise NotApplicable("el chat aún no pinta mensajes ni avisos: no existe el camino atacado")
    sources = code(t, "src/")
    if libs:
        blob = "\n".join(sources.values())
        expect(re.search(r"urlTransform", blob), "Markdown sin urlTransform: javascript: y URLs remotas pasan")
        expect(re.search(r"img\s*:|disallowedElements", blob), "Markdown sin control de <img>: imagen remota como canal de exfiltración")
    # Los campos que vienen del backend/modelo no pueden acabar en atributos con efecto.
    untrusted = r"(content|summary|text|detail|message|tool\.name|error)"
    for path, text in sources.items():
        if "/components/ui/" in path:
            continue  # primitivas de shadcn: sus atributos salen de tema, no del chat
        hit = re.search(rf"\b(href|src|srcSet|style|action|formAction|data)\s*=\s*\{{[^}}]*\b{untrusted}\b", text)
        expect(not hit, f"{path}: contenido no confiable en el atributo {hit.group(1) if hit else ''}")
    rendered = [f for f in transcripts if "Transcript" in f or "Confirmation" in f]
    expect(rendered, "no se alcanzó ningún componente que pinte el chat")
    for path in rendered:
        expect(re.search(r"\{(message\.content|confirmation\.summary)\}", sources.get(path, "")), f"{path}: no se vio el contenido pintado como hijo de texto de JSX")


# ---------------------------------------------------------------------------
# DESK-16 Enlaces externos
# ---------------------------------------------------------------------------


@attack(
    "DESK-16",
    "Los enlaces externos solo se abren por acción explícita validada en main",
    guarantee=GUARANTEE_ELECTRON,
)
def external_links(ctx: Context) -> None:
    t = tree(ctx)
    sources = code(t, "src/")
    anchors = [(p, m.group(1)) for p, s in sources.items() for m in re.finditer(r"href\s*=\s*([^\s>]+)", s)]
    expect(anchors, "control del ataque: no se encontró ningún href en el renderer, no se alcanzó el camino")
    for path, value in anchors:
        expect(re.match(r"""^[{"'`]*(#|/(?!/))""", value), f"{path}: enlace que no es interno: href={value}")
    for path, text in sources.items():
        expect("target=" not in text, f"{path}: target= en un enlace")
        expect(not re.search(r"window\.open\s*\(|location\s*(\.href)?\s*=", text), f"{path}: el renderer abre o navega por su cuenta")
        expect(not re.search(r"openExternal", text), f"{path}: el renderer llama a openExternal")
    main = "\n".join(code(t, "electron/").values())
    expect(not re.search(r"openExternal\s*\(\s*(?!new URL)\w", main) or "https:" in main, "main abre enlaces sin validar el esquema")


# ---------------------------------------------------------------------------
# DESK-17 Datos que llegan del renderer a main
# ---------------------------------------------------------------------------


@attack(
    "DESK-17",
    "Main valida el contenido de cada IPC antes de notificar o registrar",
    guarantee=GUARANTEE_ELECTRON,
)
def ipc_payload_validation(ctx: Context) -> None:
    t = tree(ctx)
    path = "desktop/electron/main/ipc.ts"
    if not t.has(path):
        raise NotApplicable("no hay ipc.ts")
    ipc = strip_comments(t.read(path))
    shared = strip_comments(t.read("desktop/electron/shared/bridge.ts"))
    handlers = re.findall(r"handle\(\s*IPC_CHANNELS\.(\w+)\s*,\s*(\w+)\s*\)", ipc)
    expect(handlers, "no se alcanzaron los manejadores")
    for channel, function in handlers:
        body = re.search(rf"function\s+{function}\s*\(([^)]*)\)[^{{]*\{{(.*?)\n\}}", ipc, re.S)
        expect(body, f"{channel}: no se encuentra {function}")
        if body.group(1).strip():
            expect(re.search(r"\bparse\w+\(\s*payload", body.group(2)), f"{channel}: {function} usa el payload sin parse*()")
    notification = re.search(r"new\s+Notification\(\s*(\w+)\s*\)", ipc)
    expect(notification and notification.group(1) == "request", "la notificación nativa no se construye solo con el objeto validado")
    expect(re.search(r"title\s*:\s*clip|\{\s*title\s*\}|\{\s*title\s*,\s*body", ipc), "la notificación puede llevar campos no validados (icono, acciones...)")
    expect(re.search(r"DESKTOP_NOTIFICATION_LIMITS\s*=\s*\{[^}]*title[^}]*body", shared), "sin límites de notificación")
    expect(re.search(r"ERROR_REPORT_LIMITS\s*=\s*\{[^}]*stack", shared), "sin límites de informe de error")
    log = strip_comments(t.read("desktop/electron/main/log.ts"))
    expect(re.search(r"\\p\{Cc\}", log), "log.ts no neutraliza saltos de línea: inyección de entradas falsas en el log desde el renderer")


# ---------------------------------------------------------------------------
# DESK-19 El renderer no tiene token ni red cuando main ofrece el puente (D-14)
# ---------------------------------------------------------------------------


@attack(
    "DESK-19",
    "Con window.api en main, el renderer no conserva token, fetch ni WebSocket propios",
    guarantee="CLAUDE.md §8: separación interfaz/datos; F05, F12",
    finding="F05",
)
def renderer_without_credentials(ctx: Context) -> None:
    t = tree(ctx)
    bridge = t.read("desktop/electron/shared/bridge.ts")
    if "DrakterApi" not in bridge:
        raise NotApplicable("main aún no ofrece el proxy window.api")
    stale = {
        p: [w for w, r in (("fetch()", r"\bfetch\s*\("), ("WebSocket", r"new\s+WebSocket\s*\("), ("token", r"\bBearer\b|Authorization|\btoken\b")) if re.search(r, s)]
        for p, s in code(t, "src/").items()
    }
    stale = {p: w for p, w in stale.items() if w}
    expect(
        not stale,
        f"main ya expone window.api (bridge.ts: \"el renderer no tiene token, puerto ni red\") pero el renderer sigue con su propio camino a la red y al token: {stale}. "
        f"Son dos transportes: el viejo exige que el renderer reciba el token del backend (getBackendSession, inexistente) y rompe la garantía D-14; "
        f"además usa `window.drakter.<método>` mientras main expone `window.api`",
    )


# ---------------------------------------------------------------------------
# DESK-20 Lista cerrada de rutas del proxy
# ---------------------------------------------------------------------------


@attack(
    "DESK-20",
    "El proxy del renderer solo admite rutas de una lista cerrada que excluye aprobar y permisos",
    guarantee="CLAUDE.md §8: Hermes/renderer no tocan datos sin validación; F05",
    finding="F05",
)
def proxy_allowlist(ctx: Context) -> None:
    t = tree(ctx)
    path = "desktop/electron/shared/operations.ts"
    if not t.has(path):
        raise NotApplicable("no hay lista de rutas permitidas")
    ops = strip_comments(t.read(path))
    routes = re.findall(r"method\s*:\s*['\"](\w+)['\"]\s*,\s*path\s*:\s*['\"]([^'\"]+)['\"]", ops)
    expect(routes, "no se alcanzó la lista de rutas")
    for method, route in routes:
        expect(route.startswith("/") and not route.startswith("//"), f"ruta no relativa: {route}")
        expect(not re.search(r"approve|reject|permission|roots?\b|/auth|/admin|\*|\.\.|\\|%|\?", route, re.I), f"{method} {route}: ruta sensible o con comodín en la lista del renderer")
        expect(not re.search(r"\{[^}]*\}\s*\{|\{[^}]*\}[A-Za-z]", route), f"{route}: segmento dinámico mezclado con texto")
    approval = "\n".join(f"{m} {r}" for m, r in routes)
    expect(not re.search(r"POST[^\n]*/confirmations", approval), "el renderer puede escribir en /confirmations")
    proxy = "desktop/electron/main/apiProxy.ts"
    if not t.has(proxy):
        raise NotApplicable(
            f"la lista ({len(routes)} rutas, sin aprobar/permisos/comodines) es correcta, pero el emparejador y el proxy "
            "(main/apiProxy.ts) no existen en esta rama: no se puede atacar `..%2f`, `//`, URL absoluta, redirecciones ni límites"
        )
    text = strip_comments(t.read(proxy))
    expect(re.search(r"redirect\s*:\s*['\"](error|manual)['\"]", text), "el proxy sigue redirecciones")
    expect(re.search(r"AbortSignal|timeout", text), "el proxy no tiene tiempo límite")
    expect(re.search(r"response_too_large|maxBytes|MAX_\w*BYTES", text), "el proxy no limita el tamaño de la respuesta")
    expect(re.search(r"\.\.|%2e|decodeURIComponent|\[\^/\]", text, re.I), "el emparejador no trata `..`, `%2e` ni segmentos con barra")
    expect(re.search(r"127\.0\.0\.1|localhost", text), "el proxy no fija el host de destino")


# ---------------------------------------------------------------------------
# DESK-21 Módulos de main referenciados que no existen
# ---------------------------------------------------------------------------


@attack(
    "DESK-21",
    "Todo módulo de main que se importa existe (permisos, sandbox, aprobación, proxy y eventos)",
    guarantee=GUARANTEE_ELECTRON,
)
def main_modules_exist(ctx: Context) -> None:
    t = tree(ctx)
    files = set(t.files())
    missing = []
    for path, text in code(t, "electron/").items():
        base = path.rsplit("/", 1)[0]
        for match in re.finditer(r"from\s+['\"](\.{1,2}/[^'\"]+)['\"]", text):
            parts: list[str] = []
            for piece in (base + "/" + match.group(1)).split("/"):
                if piece == "..":
                    parts.pop()
                elif piece != ".":
                    parts.append(piece)
            target = "/".join(parts)
            if not any(target + ext in files for ext in (".ts", ".tsx", "/index.ts", ".js")):
                missing.append(f"{path} -> {match.group(1)}")
    expect(
        not missing,
        f"imports sin archivo en {t.label}: {missing}. La rama no compila, y con ello la política de permisos, la de sandbox global, "
        f"la aprobación nativa (F05), el proxy de rutas y el arranque del backend no se han entregado: DESK-04, DESK-10 y DESK-20 quedan sin poder atacarse",
    )
