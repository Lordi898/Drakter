"""Safety lists of the hands, shared by the helper and the backend (docs/floating/CONTRACT.md §5).

Single source: the backend loads this file by path (`backend/app/integrations/hands/lists.py`), so the
two barriers can never drift apart. Standard library only: it runs under `/usr/bin/python3 -I` and
under the backend's Python 3.12.

Ported from Roamies (KenKaiii/Roamies@8f0adaa, AGPL-3.0): `HANDS_OFF` and `RISKY` of
`showcase/tauri/src-tauri/hands-linux/roamies-hands`, `RISKY_CLICK` of `showcase/tauri/sidecar/safety.mjs:81`
and the `SECRET` paths of the same file. Drakter adds GNOME app ids, Drakter itself, Spanish button
words and the risky key combos.
"""

from __future__ import annotations

import re
import unicodedata

# ── HANDS_OFF ────────────────────────────────────────────────────────────────
# Apps Drakter may point at but never click or type in: a terminal would run commands past every check,
# the others hold passwords or can change the whole desktop. Keys are lower case: app id, wm_class or the
# executable's basename.
HANDS_OFF: dict[str, str] = {
    # terminals and consoles (Roamies)
    "kitty": "kitty", "alacritty": "Alacritty", "foot": "foot", "wezterm": "WezTerm", "wezterm-gui": "WezTerm",
    "org.wezfurlong.wezterm": "WezTerm", "konsole": "Konsole", "org.kde.konsole": "Konsole",
    "gnome-terminal": "GNOME Terminal", "gnome-terminal-server": "GNOME Terminal", "org.gnome.terminal": "GNOME Terminal",
    "kgx": "GNOME Console", "org.gnome.console": "GNOME Console", "ptyxis": "Ptyxis", "org.gnome.ptyxis": "Ptyxis",
    "xterm": "xterm", "uxterm": "xterm", "urxvt": "urxvt", "rxvt": "rxvt", "terminator": "Terminator",
    "tilix": "Tilix", "terminology": "Terminology", "hyper": "Hyper", "tabby": "Tabby", "warp": "Warp",
    "dev.warp.warp-stable": "Warp", "ghostty": "Ghostty", "com.mitchellh.ghostty": "Ghostty", "rio": "Rio",
    "com.raphaelamorim.rio": "Rio", "contour": "Contour", "st": "st", "blackbox": "Black Box",
    "com.raggesilver.blackbox": "Black Box",
    # Drakter (CONTRACT §5)
    "com.gexperts.tilix": "Tilix", "org.gnome.ptyxis.devel": "Ptyxis",
    # password managers and security prompts (Roamies)
    "1password": "1Password", "onepassword": "1Password", "bitwarden": "Bitwarden",
    "com.bitwarden.desktop": "Bitwarden", "keepass": "KeePass", "keepassxc": "KeePassXC",
    "org.keepassxc.keepassxc": "KeePassXC", "seahorse": "Contraseñas y claves",
    "org.gnome.seahorse.application": "Contraseñas y claves", "gcr-prompter": "Contraseñas y claves",
    "gnome-keyring": "Contraseñas y claves", "kwallet": "KWallet", "kwalletmanager": "KWallet",
    "org.kde.kwalletmanager": "KWallet", "enpass": "Enpass", "dashlane": "Dashlane",
    "lastpass": "LastPass", "buttercup": "Buttercup", "polkit": "PolicyKit",
    "polkit-gnome-authentication-agent-1": "PolicyKit",
    # system settings, disks and package managers (Roamies)
    "gnome-control-center": "Configuración", "org.gnome.settings": "Configuración", "systemsettings": "System Settings",
    "systemsettings5": "System Settings", "systemsettings6": "System Settings",
    "org.kde.systemsettings": "System Settings", "gparted": "GParted", "gnome-disks": "Discos",
    "org.gnome.disks": "Discos", "blivet-gui": "Blivet", "gnome-software": "Software",
    "org.gnome.software": "Software", "plasma-discover": "Discover", "org.kde.discover": "Discover",
    "pamac-manager": "Pamac", "synaptic": "Synaptic", "octopi": "Octopi", "flatseal": "Flatseal",
    "com.github.tchx84.flatseal": "Flatseal",
    # Drakter (CONTRACT §5): GNOME ids that Roamies does not list
    "org.gnome.diskutility": "Discos", "org.gnome.systemmonitor": "Monitor del sistema",
    "gnome-system-monitor": "Monitor del sistema", "snap-store": "Software", "io.snapcraft.store": "Software",
    # editors that can run commands (Roamies)
    "code": "Visual Studio Code", "code-oss": "Code", "codium": "VSCodium", "vscodium": "VSCodium",
    "code-url-handler": "Visual Studio Code",
    # Drakter itself: its windows are refused by pid too (`drakter_window`), this catches a second instance
    "drakter": "Drakter", "org.drakter.drakter": "Drakter", "org.drakter.desktop": "Drakter",
}

# gnome-shell owns the polkit and keyring dialogs: any window whose app is the shell is hands-off.
HANDS_OFF_SHELL: frozenset[str] = frozenset({"gnome-shell", "org.gnome.shell"})


def hands_off_name(*keys: str | None) -> str | None:
    """Display name of the HANDS_OFF app behind any of these ids (app id, wm_class, exe), or None."""
    for key in keys:
        if not key:
            continue
        k = str(key).strip().lower()
        if k.endswith(".desktop"):
            k = k[: -len(".desktop")]
        base = k.rsplit("/", 1)[-1]
        for cand in (k, base):
            if cand in HANDS_OFF:
                return HANDS_OFF[cand]
            if cand in HANDS_OFF_SHELL:
                return "GNOME Shell"
    return None


# ── RISKY ────────────────────────────────────────────────────────────────────
# Clicks that delete, pay, send or sign out need the user's yes first. Literal port of `RISKY_CLICK`
# (safety.mjs:81): JS `(?:^|[^\p{L}])…(?![\p{L}])` becomes "not after / not before a letter", written
# with `[^\W\d_]` (a Unicode letter) because Python's `re` has no `\p{L}`.
_LETTER = r"[^\W\d_]"
RISKY_WORDS = (
    r"delete|remove|erase|destroy|wipe|reset|deactivate|close (my |your )?account|"
    r"cancel (my |your |the )?(subscription|plan|membership|account|order)|unsubscribe|pay|purchase|buy|"
    r"place (the |your )?order|checkout|check out|confirm (payment|order|purchase|transfer)|send|transfer|"
    r"withdraw|uninstall|empty trash|discard|sign out|log out|logout|format|revoke|publish|eliminar|borrar|"
    r"pagar|comprar|enviar|cerrar sesi[oó]n|supprimer|effacer|payer|acheter|envoyer|se d[eé]connecter|"
    r"d[eé]connexion|l[oö]schen|entfernen|bezahlen|kaufen|senden|abmelden|excluir|apagar|terminar sess[aã]o|"
    r"elimina|cancella|paga|acquista|invia|esci|verwijderen|betalen|kopen|verzenden|uitloggen|afmelden|padam|"
    r"hapus|bayar|beli|hantar|kirim|log keluar|nyahlanggan"
)
RISKY_CJK = (
    "删除", "刪除", "移除", "清空", "支付", "付款", "购买", "購買", "发送", "發送", "退出登录", "登出", "注销",
    "削除", "消去", "支払", "購入", "送信", "ログアウト", "退会", "삭제", "결제", "구매", "전송", "보내기", "로그아웃",
)
# Drakter: Spanish wording of the same actions that Roamies' list misses (GNOME in Spanish says
# «Mover a la papelera», «Vaciar papelera», «Desinstalar», «Suprimir»…).
RISKY_WORDS_ES = (
    r"suprimir|quitar|vaciar( la)? papelera|vaciar|mover a la papelera|desinstalar|restablecer|formatear|"
    r"descartar|revocar|publicar|transferir|retirar|desactivar|darse de baja|dar de baja|desuscribirse|"
    r"cancelar (mi |tu |la |el )?(suscripci[oó]n|plan|membres[ií]a|cuenta|pedido)|cerrar (mi |tu |la )?cuenta|"
    r"confirmar (el )?(pago|pedido|compra|transferencia)|(realizar|tramitar|hacer) (el )?pedido|"
    r"finalizar (la )?compra|comprar ahora|pagar ahora|reenviar|responder a todos|salir de la cuenta|"
    r"desconectar|destruir|sobrescribir|reemplazar todo"
)
RISKY_CLICK = re.compile(
    rf"(?<!{_LETTER})({RISKY_WORDS}|{RISKY_WORDS_ES})(?!{_LETTER})|" + "|".join(RISKY_CJK),
    re.IGNORECASE,
)


def is_risky_text(label: str | None) -> bool:
    return bool(label) and RISKY_CLICK.search(str(label)) is not None


def risky_kind(label: str | None) -> str | None:
    """Which risky word a label has («Eliminar foto» → «eliminar»)."""
    m = RISKY_CLICK.search(str(label or ""))
    if m is None:
        return None
    return " ".join((m.group(1) or m.group(0)).lower().split())


# Key combos that close, delete, send or lock (CONTRACT §5). Normalised with `normalize_combo`.
_MODS = ("ctrl", "alt", "shift", "super")
_MOD_ALIASES = {"control": "ctrl", "ctl": "ctrl", "meta": "super", "win": "super", "cmd": "super", "logo": "super"}


def normalize_combo(combo: str) -> str:
    """`Shift+ctrl+W` → `ctrl+shift+w`: modifiers in a fixed order, key in lower case."""
    parts = [p for p in str(combo or "").strip().split("+") if p]
    if not parts:
        return ""
    *mods, key = parts
    names = {_MOD_ALIASES.get(m.lower(), m.lower()) for m in mods}
    ordered = [m for m in _MODS if m in names]
    return "+".join([*ordered, key.lower()])


RISKY_KEYS: frozenset[str] = frozenset(
    normalize_combo(c)
    for c in ("alt+F4", "ctrl+w", "ctrl+q", "ctrl+shift+w", "Delete", "shift+Delete", "ctrl+Return", "super+l",
              # Drakter: the same keys under their other names
              "KP_Delete", "shift+KP_Delete", "ctrl+KP_Enter")
)


def is_risky_combo(combo: str | None) -> bool:
    return normalize_combo(combo or "") in RISKY_KEYS


# ── secret paths in window titles ────────────────────────────────────────────
# Port of `SECRET` (safety.mjs:16) for window titles: «.env (~/.config/drakter) - Editor de texto».
# Anchored at a path or word boundary instead of a whole path, because a title is not a path.
_B = r"(?:^|[\s/\\«\"'(\[~:])"
_E = r"(?=$|[\s/\\»\"')\],:;—–-])"
SECRET_TITLE = re.compile(
    "|".join(
        (
            rf"{_B}\.ssh{_E}", rf"{_B}\.gnupg{_E}", rf"{_B}\.aws{_E}", rf"{_B}\.azure{_E}", r"\.kube/config",
            r"\.docker/config\.json", rf"{_B}\.netrc{_E}", rf"{_B}\.npmrc{_E}", rf"{_B}\.pypirc{_E}",
            rf"{_B}\.git-credentials{_E}", r"\.config/(gh|gcloud)\b", r"secrets\.json", rf"{_B}\.env(\.[\w-]+)?{_E}",
            r"\.(pem|p12|pfx|key|keystore|jks)" + _E, rf"{_B}id_(rsa|ed25519|ecdsa|dsa)(\.pub)?{_E}",
            r"\.(bash|zsh|fish)_history", r"\.zsh_sessions", r"\b(Cookies|Login Data|Web Data)(-journal)?\b",
            r"\.local/share/(keyrings|kwalletd)", r"\.password-store", rf"{_B}\.pki{_E}",
            r"\b(cookies\.sqlite|logins\.json|key4\.db|cert9\.db)\b", r"\bcredentials(\.json)?\b",
        )
    ),
    re.IGNORECASE,
)


def secret_title(title: str | None) -> bool:
    return bool(title) and SECRET_TITLE.search(str(title)) is not None


# ── text matching (shared by `atspi.find` and the backend's OCR lookup) ─────
def fold(text: str | None) -> str:
    """Case, accents and spacing folded: «  Exportar  cómo » → «exportar como»."""
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.casefold().split())


def match_score(name: str | None, query: str) -> int:
    """3 exact, 2 whole words, 1 start of a word, 0 no match. Never a word inside another word."""
    n, q = fold(name), fold(query)
    if not n or not q:
        return 0
    if n == q:
        return 3
    if re.search(rf"(?<!\w){re.escape(q)}(?!\w)", n):
        return 2
    if re.search(rf"(?<!\w){re.escape(q)}", n):
        return 1
    return 0
