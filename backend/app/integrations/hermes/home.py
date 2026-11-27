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
import time
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
IMAGE_CACHE_MAX_AGE_S: Final = 3600.0
# get_hermes_dir("cache/images", "image_cache") of gateway/platforms/base.py: new and legacy names.
_IMAGE_CACHE_DIRS: Final = ("cache/images", "image_cache")

_TOOL_NAME_RE: Final = re.compile(r"^[a-z][a-z0-9_]{2,47}$")
# "hermes" is the foreground home; job lanes use "hermes-w1", "hermes-w2"... (V-24).
_HOME_NAME_RE: Final = re.compile(r"^hermes(-[a-z0-9]{1,16})?$")
DEFAULT_HOME_NAME: Final = "hermes"
DEFAULT_REASONING_EFFORT: Final = "low"  # foreground; job lanes use "medium" (V-20)
# VALID_REASONING_EFFORTS of hermes_constants at HERMES_COMMIT, plus "none" (thinking off).
REASONING_EFFORTS: Final = frozenset({"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"})
# A line of agent/identity/VOICE.md replaced with speech_markup.prompt_block() (same text every time).
SPEECH_MARKUP_PLACEHOLDER: Final = "<!-- speech_markup.prompt_block -->"
_GUARD_SOURCES: Final = ("__init__.py", "plugin.yaml")
_GUARD_ALLOWLIST: Final = "allowed_tools.json"
_GUARD_FILES: Final = frozenset({*_GUARD_SOURCES, _GUARD_ALLOWLIST})
# Under HERMES_HOME these change behaviour without going through config.yaml.
_FORBIDDEN_IN_ROOT: Final = (".env",)
_CONTEXT_MARKERS: Final = (".git", ".hermes.md", "HERMES.md")
# (folder under agent/, file). The 14 files live in identity/, knowledge/ and context/ (DECISIONS:
# "Identidad repartida en identity/, context/ y knowledge/"); all of them reach SOUL.md.
_IDENTITY_ORDER: Final = (
    ("identity", "SOUL.md"),
    ("identity", "VALUES.md"),
    ("identity", "PERSONALITY.md"),
    ("identity", "COMMUNICATION.md"),
    ("identity", "EMOTIONAL_STYLE.md"),
    ("identity", "BEHAVIOR.md"),
    ("identity", "VOICE.md"),
    ("knowledge", "CAPABILITIES.md"),
    ("knowledge", "TOOL_GUIDE.md"),
    ("knowledge", "WORKSPACE_GUIDE.md"),
    ("knowledge", "SYSTEM_GUIDE.md"),
    ("context", "ENVIRONMENT.md"),
    ("context", "PREFERENCES.md"),
    ("context", "USER.md"),
    ("context", "CURRENT_CONTEXT.md"),
)
# Skills of agent/skills/ are compiled read-only into SOUL.md: Hermes' `skills` toolset stays off,
# because it cannot be enabled without skill_manage (DECISIONS «Skills de solo lectura en SOUL.md»).
SKILLS_HEADER: Final = "# Skills de Drakter"
FIRST_SKILL: Final = "drakter-basics"  # rendered first: the rules every other skill relies on
SKILL_MAX_CHARS: Final = 6_000
_SKILL_NAME_RE: Final = re.compile(r"^[a-z][a-z0-9-]{2,47}$")
_SKILLS_PREAMBLE: Final = (
    "Procedimientos para usar bien las herramientas en cada dominio. Antes de actuar en un dominio, "
    "sigue su skill. Las publica el sistema y son de solo lectura: no puedes crearlas, cambiarlas ni "
    "borrarlas, y no hay herramientas skill_*. Si una skill contradice las reglas de seguridad, mandan "
    "las reglas; el backend valida siempre."
)
_NEUTRAL_SOUL: Final = "# Drakter\n\nEres Drakter, el asistente personal de una sola persona. Responde en español.\n"

# Every native toolset name of v0.22.7 that is not a hermes-* composite. Second layer only:
# what decides is enabled_toolsets=["mcp-drakter"] in the runner, checked against agent.tools.
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
    def under(cls, data_dir: Path, home_name: str = DEFAULT_HOME_NAME) -> HomePaths:
        if not _HOME_NAME_RE.fullmatch(home_name):
            raise HomeError("invalid Hermes home name")
        root = data_dir.absolute() / home_name
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
    # Drakter titles its own sessions: Hermes' title would be one more Haiku call per session,
    # racing the first turn (LAT-1).
    tasks["title_generation"] = {**block, "enabled": False}
    return tasks


def render_config(
    s: AgentSettings,
    tool_names: Sequence[str],
    *,
    cwd: Path,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
) -> dict[str, Any]:
    """Pure and deterministic. `cwd` is the absolute empty directory for terminal.cwd.

    `agent.reasoning_effort` is read by the runner through hermes_constants.resolve_reasoning_config.
    """
    if not cwd.is_absolute():
        raise HomeError("terminal.cwd must be absolute")
    if reasoning_effort not in REASONING_EFFORTS:
        raise HomeError("invalid reasoning effort")
    return {
        "_config_version": HERMES_CONFIG_VERSION,
        "agent": {
            "disabled_toolsets": list(_DISABLED_TOOLSETS),
            "max_turns": s.agent_max_turns,
            "reasoning_effort": reasoning_effort,
            # Without it, the explicit auxiliary.vision wins and the model only sees
            # `MEDIA:<path>` for a tool image (floating CONTRACT §8.1.2, spike 04 §1).
            "image_input_mode": "native",
        },
        "approvals": {"mode": "manual"},
        "auth": {"adopt_external_logins": False},
        "auxiliary": _render_auxiliary(s),
        "compression": {"threshold_tokens": COMPRESSION_THRESHOLD_TOKENS},
        "context_file_max_chars": SOUL_MAX_CHARS,
        "curator": {"enabled": False},
        "fallback_providers": [],
        "hooks": {},
        "hooks_auto_accept": False,
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
        "plugins": {"auto_update_check_hours": 0, "enabled": [GUARD_NAME], "load_timeout_seconds": 0},
        # A person paces the conversation: pauses over 5 min would rewrite the ~62K-token prefix
        # (instructions + tools), ~0.4 s more to the first token. 1h writes cost 2x, not 1.25x (LAT-1).
        "prompt_caching": {"cache_ttl": "1h"},
        "security": {"allow_lazy_installs": False},
        "terminal": {"cwd": str(cwd)},
        "tools": {"tool_search": {"enabled": "off"}},
        "updates": {"check": False},
    }


def purge_image_cache(root: Path, max_age_s: float = IMAGE_CACHE_MAX_AGE_S) -> int:
    """Delete cached tool images older than `max_age_s` under the home `root`.

    Hermes caches every MCP `ImageContent` there (screenshots may hold sensitive data).
    Only regular files are removed, never followed symlinks. Returns how many went.
    """
    cutoff = time.time() - max_age_s
    removed = 0
    for relative in _IMAGE_CACHE_DIRS:
        directory = root / relative
        try:
            if not stat.S_ISDIR(os.lstat(directory).st_mode):
                continue
            entries = list(os.scandir(directory))
        except OSError:
            continue
        for entry in entries:
            try:
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISREG(info.st_mode) and info.st_mtime < cutoff:
                    os.unlink(entry.path)
                    removed += 1
            except OSError:
                continue
    return removed


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


def _parse_skill(name: str, raw: str) -> tuple[str, str]:
    """(description, body) of a SKILL.md whose frontmatter `name` matches its folder."""
    if not raw.startswith("---\n") or "\n---\n" not in raw[4:]:
        raise HomeError(f"skill {name}: missing frontmatter")
    front, body = raw[4:].split("\n---\n", 1)
    fields = dict(line.split(":", 1) for line in front.splitlines() if ":" in line and not line.startswith(" "))
    if fields.get("name", "").strip() != name:
        raise HomeError(f"skill {name}: frontmatter name does not match the folder")
    description = fields.get("description", "").strip().strip('"')
    if not description or not body.strip():
        raise HomeError(f"skill {name}: empty description or body")
    return description, body.strip()


def render_skills(repo_root: Path) -> str:
    """agent/skills/<name>/SKILL.md, FIRST_SKILL first then by name; headings demoted under the section."""
    skills_dir = repo_root / "agent" / "skills"
    if not skills_dir.is_dir() or skills_dir.is_symlink():
        return ""
    names = sorted(
        entry.name for entry in skills_dir.iterdir()
        if entry.is_dir() and not entry.is_symlink() and os.path.lexists(entry / "SKILL.md")
    )
    names.sort(key=lambda name: name != FIRST_SKILL)
    sections = []
    for name in names:
        if not _SKILL_NAME_RE.fullmatch(name):
            raise HomeError("invalid skill folder name")
        raw = _read_regular(skills_dir / name / "SKILL.md").decode("utf-8")
        if len(raw) > SKILL_MAX_CHARS:
            raise HomeError(f"skill {name} is too long")
        description, body = _parse_skill(name, raw)
        lines = [line for line in body.splitlines() if line.strip() != f"# {name}"]
        body = "\n".join(f"#{line}" if line.startswith("#") else line for line in lines).strip()
        sections.append(f"## Skill `{name}`: {description}\n\n{body}")
    if not sections:
        return ""
    return "\n\n".join([f"{SKILLS_HEADER}\n\n{_SKILLS_PREAMBLE}", *sections]) + "\n"


def render_soul(repo_root: Path) -> str:
    """Safety rules first, then the identity files in a fixed order, then the read-only skills."""
    configuration = repo_root / "agent" / "configuration"
    safety = _read_regular(configuration / "safety_instructions.md").decode("utf-8")
    agent_dir = repo_root / "agent"
    identity: list[str] = []
    files = list(_IDENTITY_ORDER)
    identity_dir = agent_dir / "identity"
    if identity_dir.is_dir() and not identity_dir.is_symlink():
        known = {name for _, name in _IDENTITY_ORDER}
        files += [("identity", p.name) for p in sorted(identity_dir.glob("*.md")) if p.name not in known]
    for folder, name in files:
        directory = agent_dir / folder
        if directory.is_dir() and not directory.is_symlink() and os.path.lexists(directory / name):
            text = _read_regular(directory / name).decode("utf-8").strip()
            if SPEECH_MARKUP_PLACEHOLDER in text:
                from drakter_contracts.speech_markup import prompt_block

                text = text.replace(SPEECH_MARKUP_PLACEHOLDER, prompt_block())
            identity.append(text + "\n")
    skills = render_skills(repo_root)
    soul = "\n\n".join([safety.strip() + "\n", *(identity or [_NEUTRAL_SOUL]), *([skills] if skills else [])])
    if len(soul) > SOUL_MAX_CHARS:
        raise HomeError("the identity is too long for SOUL.md")
    return soul


def _desired_files(
    s: AgentSettings,
    tool_names: Sequence[str],
    repo_root: Path,
    paths: HomePaths,
    reasoning_effort: str,
) -> dict[Path, bytes]:
    names = _normalize_tool_names(tool_names)
    source = repo_root / "agent" / "configuration" / "hermes_plugins" / GUARD_NAME
    config = render_config(s, names, cwd=paths.cwd, reasoning_effort=reasoning_effort)
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
    s: AgentSettings,
    data_dir: Path,
    tool_names: Sequence[str],
    repo_root: Path,
    *,
    home_name: str = DEFAULT_HOME_NAME,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
) -> HomeManifest:
    """Write the home `<data_dir>/<home_name>` and return its hashes. Raises HomeError on anything unexpected."""
    paths = HomePaths.under(data_dir, home_name)
    try:
        for directory in (paths.root, paths.plugins, paths.hooks, paths.cwd, paths.user_home, paths.run, paths.tmp):
            ensure_private_dir(directory)
        _check_executable_trees(paths)
        _check_location(paths)
        ensure_private_dir(paths.guard)
        files = _desired_files(s, tool_names, repo_root, paths, reasoning_effort)
        for path, content in files.items():
            _write_private(path, content)
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        raise HomeError(f"cannot prepare the Hermes home: {type(exc).__name__}") from exc
    manifest = _build_manifest(paths, files)
    verify_home(manifest)
    purge_image_cache(paths.root)
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
