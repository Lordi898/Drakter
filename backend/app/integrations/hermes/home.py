"""Deterministic, verifiable HERMES_HOME.

Everything under plugins/ and hooks/ of the home runs inside Hermes, so that tree
holds exactly what this module writes and anything else refuses the start. All
keys in render_config were checked against the Hermes v0.22.7 source.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

from app.core.config import ensure_private_dir
from app.integrations.hermes.settings import AgentSettings

MCP_SERVER_NAME: Final = "drakter"
MCP_URL_ENV: Final = "DRAKTER_MCP_URL"  # ephemeral port: never in config.yaml nor its hash
MCP_TOKEN_ENV: Final = "DRAKTER_MCP_TOKEN"
MCP_TOOL_TIMEOUT_S: Final = 130  # above the 120 s ceiling of ToolSpec.timeout_s
GUARD_NAME: Final = "drakter_guard"
GUARD_NONCE_ENV: Final = "DRAKTER_GUARD_NONCE"
GUARD_PROOF: Final = "drakter_guard.proof"
HERMES_CONFIG_VERSION: Final = 52  # _config_version of v0.22.7: a lower one triggers rewrites on start
CONTEXT_LENGTH: Final = 1_000_000
COMPRESSION_THRESHOLD_TOKENS: Final = 80_000  # stays under the 100K price step of Haiku 5.5
SOUL_MAX_CHARS: Final = 120_000  # Hermes truncates SOUL.md silently beyond context_file_max_chars

_TOOL_NAME_RE: Final = re.compile(r"^[a-z][a-z0-9_]{2,47}$")
_GUARD_SOURCES: Final = ("__init__.py", "plugin.yaml")
_GUARD_ALLOWLIST: Final = "allowed_tools.json"
_GUARD_FILES: Final = frozenset({*_GUARD_SOURCES, _GUARD_ALLOWLIST})
# Under HERMES_HOME these change behaviour without going through config.yaml.
_FORBIDDEN_IN_ROOT: Final = (".env",)
_CONTEXT_MARKERS: Final = (".git", ".hermes.md", "HERMES.md")
_IDENTITY_ORDER: Final = (
    "SOUL.md",
    "VALUES.md",
    "PERSONALITY.md",
    "COMMUNICATION.md",
    "EMOTIONAL_STYLE.md",
    "BEHAVIOR.md",
    "CAPABILITIES.md",
    "TOOL_GUIDE.md",
    "WORKSPACE_GUIDE.md",
    "SYSTEM_GUIDE.md",
    "ENVIRONMENT.md",
    "PREFERENCES.md",
    "USER.md",
    "CURRENT_CONTEXT.md",
)
_NEUTRAL_SOUL: Final = "# Drakter\n\nEres Drakter, el asistente personal de una sola persona. Responde en español.\n"

# Every native toolset name of v0.22.7 that is not a hermes-* composite. Second layer only:
# the list that decides is platform_toolsets.api_server.
_DISABLED_TOOLSETS: Final = (
    "a2a",
    "bot_room",
    "browser",
    "catalog",
    "clarify",
    "code_execution",
    "coding",
    "computer_use",
    "connections",
    "context_engine",
    "cronjob",
    "debugging",
    "delegation",
    "desktop_ui",
    "discord",
    "discord_admin",
    "feishu_doc",
    "feishu_drive",
    "file",
    "image_gen",
    "kanban",
    "memory",
    "onboarding",
    "project",
    "safe",
    "search",
    "session_search",
    "skills",
    "spotify",
    "stt",
    "terminal",
    "todo",
    "tts",
    "video",
    "video_gen",
    "vision",
    "web",
    "x_search",
    "yuanbao",
)
# Marks both lists as already offered, so a future "recently shipped" toolset or a plugin
# toolset cannot widen the saved allowlist.
_KNOWN_BUILTIN_TOOLSETS: Final = tuple(name for name in _DISABLED_TOOLSETS if name not in ("a2a", "spotify"))
_KNOWN_PLUGIN_TOOLSETS: Final = ("a2a", "spotify")
_AUX_TASKS: Final = (
    "approval",
    "compression",
    "curator",
    "goal_judge",
    "kanban_decomposer",
    "mcp",
    "memory_query_rewrite",
    "monitor",
    "profile_describer",
    "review",
    "skills_hub",
    "title_generation",
    "triage_specifier",
    "tts_audio_tags",
    "vision",
    "voice_chat",
)


class HomeError(Exception):
    """The home cannot be trusted or generated. The message is safe to show."""


@dataclass(frozen=True, slots=True)
class HomePaths:
    root: Path
    config: Path
    soul: Path
    plugins: Path
    hooks: Path
    guard: Path
    cwd: Path  # empty, absolute: Hermes reads context files from here
    user_home: Path  # HOME of the child, so ~/.claude and ~/.config/gh are out of reach
    run: Path
    tmp: Path

    @classmethod
    def under(cls, data_dir: Path) -> HomePaths:
        root = data_dir.absolute() / "hermes"
        plugins = root / "plugins"
        return cls(
            root=root,
            config=root / "config.yaml",
            soul=root / "SOUL.md",
            plugins=plugins,
            hooks=root / "hooks",
            guard=plugins / GUARD_NAME,
            cwd=root / "cwd",
            user_home=root / "user-home",
            run=root / "run",
            tmp=root / "tmp",
        )


@dataclass(frozen=True, slots=True)
class HomeManifest:
    paths: HomePaths
    files: Mapping[str, str]  # path relative to the root -> sha256
    digest: str


def captured_tool_name(name: str) -> str:
    return f"mcp__{MCP_SERVER_NAME}__{name}"


def _normalize_tool_names(tool_names: Sequence[str]) -> list[str]:
    for name in tool_names:
        if not _TOOL_NAME_RE.fullmatch(name):
            raise HomeError("invalid tool name in the catalog")
    return sorted(set(tool_names))


def _render_model(s: AgentSettings) -> dict[str, Any]:
    model: dict[str, Any] = {"default": s.model_name, "context_length": CONTEXT_LENGTH}
    if s.model_provider == "dev_stub":
        return {**model, "provider": "custom", "api_mode": "anthropic_messages", "base_url": s.dev_stub_url}
    return {**model, "provider": "anthropic"}


def _render_auxiliary(s: AgentSettings) -> dict[str, Any]:
    # "auto" on the native route would pick Haiku 4.5, the plugin's default aux model.
    block = {"provider": "auto" if s.model_provider == "dev_stub" else "anthropic", "model": s.model_name}
    tasks: dict[str, Any] = {task: dict(block) for task in _AUX_TASKS}
    tasks["background_review"] = {**block, "enabled": False}
    return tasks


def render_config(s: AgentSettings, tool_names: Sequence[str], *, cwd: Path) -> dict[str, Any]:
    """Pure and deterministic. `cwd` is the absolute empty directory for terminal.cwd."""
    if not cwd.is_absolute():
        raise HomeError("terminal.cwd must be absolute")
    return {
        "_config_version": HERMES_CONFIG_VERSION,
        "agent": {"disabled_toolsets": list(_DISABLED_TOOLSETS), "max_turns": s.agent_max_turns},
        "approvals": {"mode": "manual"},
        "auth": {"adopt_external_logins": False},
        "auxiliary": _render_auxiliary(s),
        "compression": {"threshold_tokens": COMPRESSION_THRESHOLD_TOKENS},
        "context_file_max_chars": SOUL_MAX_CHARS,
        "curator": {"enabled": False},
        "fallback_providers": [],
        "gateway": {"api_server": {"max_concurrent_runs": 1}},
        "hooks": {},
        "hooks_auto_accept": False,
        "kanban": {"dispatch_in_gateway": False},
        "known_builtin_toolsets": {"api_server": list(_KNOWN_BUILTIN_TOOLSETS)},
        "known_plugin_toolsets": {"api_server": list(_KNOWN_PLUGIN_TOOLSETS)},
        "lsp": {"enabled": False},
        "mcp_servers": {
            MCP_SERVER_NAME: {
                "url": f"${{{MCP_URL_ENV}}}",
                "headers": {"Authorization": f"Bearer ${{{MCP_TOKEN_ENV}}}"},
                "enabled": True,
                "timeout": MCP_TOOL_TIMEOUT_S,
                "connect_timeout": 15,
                "tools": {"include": _normalize_tool_names(tool_names), "resources": False, "prompts": False},
                "sampling": {"enabled": False},
                "elicitation": {"enabled": False},
            }
        },
        "memory": {"memory_enabled": False, "user_profile_enabled": False},
        "model": _render_model(s),
        "model_catalog": {"enabled": False},
        "platform_toolsets": {"api_server": [MCP_SERVER_NAME], "cron": ["no_mcp"]},
        "plugins": {"auto_update_check_hours": 0, "enabled": [GUARD_NAME], "load_timeout_seconds": 0},
        "security": {"allow_lazy_installs": False},
        "terminal": {"cwd": str(cwd)},
        "tools": {"tool_search": {"enabled": "off"}},
        "updates": {"check": False},
    }


def _read_regular(path: Path) -> bytes:
    """Read without following a symlink; only a regular file of ours passes."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as exc:
        raise HomeError(f"cannot read {path.name}") from exc
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise HomeError(f"{path.name} is not a regular file of this user")
        return handle.read()


def _write_private(path: Path, content: bytes) -> None:
    """Atomic 0600 write: os.replace swaps the entry, so a planted symlink is not followed."""
    temp = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
        os.replace(temp, path)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def _entries(directory: Path) -> dict[str, os.stat_result]:
    try:
        with os.scandir(directory) as entries:
            return {entry.name: entry.stat(follow_symlinks=False) for entry in entries}
    except OSError as exc:
        raise HomeError(f"cannot list {directory.name}") from exc


def _check_private_dir(directory: Path) -> None:
    try:
        info = os.lstat(directory)
    except OSError as exc:
        raise HomeError(f"{directory.name} is missing") from exc
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise HomeError(f"{directory.name} must be a private directory of this user")


def _check_executable_trees(paths: HomePaths) -> None:
    """Refuse anything in plugins/ or hooks/ this module did not write."""
    if _entries(paths.hooks):
        raise HomeError("unexpected content in hooks/")
    plugins = _entries(paths.plugins)
    if set(plugins) - {GUARD_NAME}:
        raise HomeError("unexpected content in plugins/")
    if GUARD_NAME not in plugins:
        return
    if not stat.S_ISDIR(plugins[GUARD_NAME].st_mode):
        raise HomeError("plugins/drakter_guard is not a directory")
    for name, info in _entries(paths.guard).items():
        if name not in _GUARD_FILES or not stat.S_ISREG(info.st_mode):
            raise HomeError("unexpected content in plugins/drakter_guard/")


def _check_location(paths: HomePaths) -> None:
    if _entries(paths.cwd):
        raise HomeError("the Hermes working directory is not empty")
    for parent in paths.cwd.parents:
        if any(os.path.lexists(parent / marker) for marker in _CONTEXT_MARKERS):
            raise HomeError("the Hermes working directory sits under a repository or context file")
    if any(os.path.lexists(paths.root / name) for name in _FORBIDDEN_IN_ROOT):
        raise HomeError("unexpected file in the Hermes home")


def render_soul(repo_root: Path) -> str:
    """Safety rules first, then the identity files in a fixed order."""
    configuration = repo_root / "agent" / "configuration"
    safety = _read_regular(configuration / "safety_instructions.md").decode("utf-8")
    identity_dir = repo_root / "agent" / "identity"
    identity: list[str] = []
    if identity_dir.is_dir() and not identity_dir.is_symlink():
        extra = sorted(p.name for p in identity_dir.glob("*.md") if p.name not in _IDENTITY_ORDER)
        for name in (*_IDENTITY_ORDER, *extra):
            if os.path.lexists(identity_dir / name):
                identity.append(_read_regular(identity_dir / name).decode("utf-8").strip() + "\n")
    soul = "\n\n".join([safety.strip() + "\n", *(identity or [_NEUTRAL_SOUL])])
    if len(soul) > SOUL_MAX_CHARS:
        raise HomeError("the identity is too long for SOUL.md")
    return soul


def _desired_files(
    s: AgentSettings, tool_names: Sequence[str], repo_root: Path, paths: HomePaths
) -> dict[Path, bytes]:
    names = _normalize_tool_names(tool_names)
    source = repo_root / "agent" / "configuration" / "hermes_plugins" / GUARD_NAME
    config = render_config(s, names, cwd=paths.cwd)
    allowed = {"allowed": [captured_tool_name(name) for name in names]}
    files: dict[Path, bytes] = {
        paths.config: (json.dumps(config, indent=2, sort_keys=True) + "\n").encode(),
        paths.soul: render_soul(repo_root).encode(),
        paths.guard / _GUARD_ALLOWLIST: (json.dumps(allowed, indent=2, sort_keys=True) + "\n").encode(),
    }
    for name in _GUARD_SOURCES:
        files[paths.guard / name] = _read_regular(source / name)
    return files


def _build_manifest(paths: HomePaths, files: Mapping[Path, bytes]) -> HomeManifest:
    hashes = {str(path.relative_to(paths.root)): hashlib.sha256(data).hexdigest() for path, data in files.items()}
    lines = "".join(f"{name}\0{digest}\n" for name, digest in sorted(hashes.items()))
    return HomeManifest(paths, MappingProxyType(hashes), hashlib.sha256(lines.encode()).hexdigest())


def materialize_home(
    s: AgentSettings, data_dir: Path, tool_names: Sequence[str], repo_root: Path
) -> HomeManifest:
    """Write the home and return its hashes. Raises HomeError on anything unexpected."""
    paths = HomePaths.under(data_dir)
    try:
        for directory in (paths.root, paths.plugins, paths.hooks, paths.cwd, paths.user_home, paths.run, paths.tmp):
            ensure_private_dir(directory)
        _check_executable_trees(paths)
        _check_location(paths)
        ensure_private_dir(paths.guard)
        files = _desired_files(s, tool_names, repo_root, paths)
        for path, content in files.items():
            _write_private(path, content)
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        raise HomeError(f"cannot prepare the Hermes home: {type(exc).__name__}") from exc
    manifest = _build_manifest(paths, files)
    verify_home(manifest)
    return manifest


def verify_home(manifest: HomeManifest) -> None:
    """Called right before each spawn: any change since materialize_home refuses the start."""
    paths = manifest.paths
    for directory in (paths.root, paths.plugins, paths.hooks, paths.guard, paths.cwd):
        _check_private_dir(directory)
    _check_executable_trees(paths)
    _check_location(paths)
    if {name for name in _entries(paths.guard)} != set(_GUARD_FILES):
        raise HomeError("plugins/drakter_guard/ is incomplete")
    for name, expected in manifest.files.items():
        path = paths.root / name
        content = _read_regular(path)
        if os.lstat(path).st_mode & 0o077:
            raise HomeError(f"{path.name} must not be accessible to group or others")
        if hashlib.sha256(content).hexdigest() != expected:
            raise HomeError(f"{path.name} changed after it was generated")
