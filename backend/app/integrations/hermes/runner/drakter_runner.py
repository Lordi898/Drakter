"""Drakter's own Hermes process: JSONL over stdio around AIAgent, no gateway, no scheduler.

Started as `<hermes_python> -I drakter_runner.py` with an allowlisted environment
(see CONTRACT.md, section 2bis). Standard library and Hermes only: it runs in the
Python 3.14 venv of Hermes and never imports `app`. Hermes is not trusted, and
neither is this process: the backend checks everything `ready` claims.
"""

from __future__ import annotations

import ctypes
import json
import os
import queue
import signal
import sys
import threading
import time
import traceback
from typing import Any

TOOLSET = "mcp-drakter"
SERVER = "drakter"
TOOL_PREFIX = "mcp__drakter__"
PROOF_NAME = "drakter_guard.proof"
MAX_LINE_BYTES = 1024 * 1024
EOF_INTERRUPT_S = 0.2
EXIT_FOREIGN_TOOLS = 3
EXIT_BOOT_FAILED = 4
PR_SET_PDEATHSIG = 1
USAGE_KEYS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "api_calls")
SESSION_USAGE_KEYS = USAGE_KEYS[:4]  # AIAgent.session_<key>: cumulative per agent; api_calls is per turn


def die_with_parent() -> None:
    """EOF covers a live backend; this covers one killed with SIGKILL while Hermes is stuck."""
    ctypes.CDLL(None, use_errno=True).prctl(PR_SET_PDEATHSIG, signal.SIGKILL)
    if str(os.getppid()) != os.environ.get("DRAKTER_PARENT_PID"):  # died before the prctl
        os._exit(EXIT_BOOT_FAILED)


class Protocol:
    """Takes fds 0 and 1 for itself, so nothing Hermes prints can corrupt the JSONL."""

    def __init__(self) -> None:
        self._input = os.fdopen(os.dup(0), "rb")
        self._output = os.fdopen(os.dup(1), "wb", buffering=0)
        self._lock = threading.Lock()
        devnull = os.open(os.devnull, os.O_RDONLY)
        os.dup2(devnull, 0)
        os.close(devnull)
        os.dup2(2, 1)
        sys.stdout = sys.stderr

    def emit(self, ev: str, **fields: Any) -> None:
        line = json.dumps({"ev": ev, **fields}, ensure_ascii=False, default=str).encode() + b"\n"
        with self._lock:
            self._output.write(line)

    def read_message(self) -> dict[str, Any] | None:
        """Next message, {} for an invalid one, None on EOF."""
        raw = self._input.readline(MAX_LINE_BYTES + 1)
        if not raw:
            return None
        if len(raw) > MAX_LINE_BYTES:
            while raw and not raw.endswith(b"\n"):
                raw = self._input.readline(MAX_LINE_BYTES + 1)
            return {}
        try:
            message = json.loads(raw)
        except ValueError:
            return {}
        return message if isinstance(message, dict) else {}


def tool_names(tools: Any) -> list[str]:
    names = []
    for tool in tools or []:
        function = tool.get("function") if isinstance(tool, dict) else None
        names.append(str((function or tool).get("name")) if isinstance(tool, dict) else str(tool))
    return names


def tool_failed(result: Any) -> bool:
    """Whatever the wrapping, an error outcome of ours or of the MCP layer."""
    for _ in range(3):
        if not isinstance(result, str):
            break
        try:
            result = json.loads(result)
        except ValueError:
            return False
    if not isinstance(result, dict):
        return False
    if result.get("error") or result.get("status") == "error" or result.get("isError") is True:
        return True
    return "result" in result and isinstance(result["result"], str) and tool_failed(result["result"])


def read_guard_proof() -> str:
    path = os.path.join(os.environ["HERMES_HOME"], "run", PROOF_NAME)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, encoding="utf-8") as handle:
        return handle.read()


class Runner:
    def __init__(self, protocol: Protocol) -> None:
        self.protocol = protocol
        self.turns: queue.SimpleQueue[dict[str, Any]] = queue.SimpleQueue()
        self.lock = threading.Lock()
        self.active_turn: str | None = None
        self.stop_requested = False
        self.agent: Any = None
        self.warm: tuple[Any, tuple[str, str | None]] | None = None
        self.histories: dict[str, list[dict[str, Any]]] = {}
        self.current_turn = ""
        self.marks: dict[str, float] = {}

    def boot(self) -> None:
        from hermes_cli.config import load_config
        from hermes_cli.runtime_provider import resolve_runtime_provider
        from hermes_cli.version_info import get_version_info
        from hermes_constants import resolve_reasoning_config
        from hermes_state import SessionDB
        from run_agent import AIAgent
        from tools.mcp_tool_discovery import discover_mcp_tools

        class DrakterAgent(AIAgent):
            """Hermes rewrites a misspelt tool name into a real one: never here. Tied to HERMES_COMMIT."""

            def _repair_tool_call(self, _name: str) -> None:
                return None

        self.agent_class = DrakterAgent
        self.config = load_config()
        self.runtime = resolve_runtime_provider()
        self.session_db = SessionDB()
        # agent.reasoning_effort of the home: low in the foreground, medium in job lanes (V-20).
        self.reasoning = resolve_reasoning_config(self.config, str(self.config["model"]["default"]))
        include = self.config["mcp_servers"][SERVER]["tools"]["include"]
        self.allowed = {f"{TOOL_PREFIX}{name}" for name in include}
        if not self.allowed:
            raise RuntimeError("empty tool catalog")
        discover_mcp_tools([SERVER])
        probe = self.build_agent("", None, persist=False)
        names = self.checked_tools(probe)
        probe.close()
        self.protocol.emit("ready", nonce=read_guard_proof(), commit=get_version_info().commit, tools=names)

    def checked_tools(self, agent: Any) -> list[str]:
        """Both views of the surface must be exactly the catalog, before any turn."""
        names = set(tool_names(agent.tools))
        if names - self.allowed or set(agent.valid_tool_names) - self.allowed:
            print("drakter_runner: tools outside the catalog", file=sys.stderr, flush=True)
            os._exit(EXIT_FOREIGN_TOOLS)
        if names != self.allowed or set(agent.valid_tool_names) != self.allowed:
            raise RuntimeError("the Drakter tools are not available")
        return sorted(names)

    def build_agent(self, session_id: str, instructions: str | None, *, persist: bool = True) -> Any:
        config = self.config
        model = config["model"]
        runtime = self.runtime
        return self.agent_class(
            model=model["default"],
            api_key=runtime.get("api_key"),
            base_url=runtime.get("base_url"),
            provider=runtime.get("provider"),
            requested_provider=runtime.get("requested_provider"),
            api_mode=runtime.get("api_mode"),
            request_overrides=runtime.get("request_overrides"),
            enabled_toolsets=[TOOLSET],
            disabled_toolsets=list(config["agent"]["disabled_toolsets"]),
            max_iterations=int(config["agent"]["max_turns"]),
            ephemeral_system_prompt=instructions or None,
            session_id=session_id or None,
            session_db=self.session_db if persist else None,
            platform="api_server",
            quiet_mode=True,
            verbose_logging=False,
            skip_memory=True,
            skip_background_review=True,
            skip_context_files=True,
            load_soul_identity=True,
            cwd=str(config["terminal"]["cwd"]),
            fallback_model=None,
            reasoning_config=self.reasoning,
            stream_delta_callback=self.on_delta,
            tool_start_callback=self.on_tool_start,
            tool_complete_callback=self.on_tool_complete,
        )

    def on_delta(self, text: str | None) -> None:
        if text:
            self.marks.setdefault("delta", time.monotonic())
            self.protocol.emit("delta", turn_id=self.current_turn, text=text)

    def on_tool_start(self, call_id: str, name: str, _args: Any) -> None:
        self.protocol.emit("tool_started", turn_id=self.current_turn, tool=name, call_id=call_id)

    def on_tool_complete(self, call_id: str, name: str, _args: Any, result: Any) -> None:
        # On interrupt this fires while the MCP call may still be running on the server.
        with self.lock:
            unconfirmed = self.stop_requested
        self.protocol.emit(
            "tool_completed",
            turn_id=self.current_turn,
            tool=name,
            call_id=call_id,
            error=tool_failed(result),
            **({"interrupted": True} if unconfirmed else {}),
        )

    def history_for(self, session_id: str) -> list[dict[str, Any]]:
        history = self.histories.get(session_id)
        if history is None:  # a restarted runner resumes from the home's SessionDB
            history = self.session_db.get_messages_as_conversation(session_id) or []
        return history

    def reasoning_for(self, effort: Any) -> Any:
        """The turn's effort if it is a valid Hermes level, else the home's agent.reasoning_effort."""
        from hermes_constants import parse_reasoning_effort

        parsed = parse_reasoning_effort(effort) if isinstance(effort, str) else None
        return parsed if parsed is not None else self.reasoning

    def take_agent(self, session_id: str, instructions: str | None) -> Any:
        """The warm agent of the previous turn when session and instructions match, else a new one.

        Hermes keeps an agent across turns the same way (gateway agent cache): its cached system
        prompt, tool schemas and HTTP client survive, so the turn skips their rebuild (LAT-1).
        """
        warm, self.warm = self.warm, None
        if warm is not None:
            agent, key = warm
            if key == (session_id, instructions or None):
                return agent
            agent.close()
        return self.build_agent(session_id, instructions)

    def run_turn(self, message: dict[str, Any]) -> dict[str, Any]:
        """Returns the terminal event. SOUL.md, instructions and tools are the same each time (H-21)."""
        from tools.terminal_tool import set_approval_callback

        # Per-thread slot. No human can answer here: real confirmations live in the backend.
        set_approval_callback(lambda *_args, **_kwargs: "deny")
        turn_id = str(message["turn_id"])
        session_id = str(message["session_id"])
        instructions = message.get("instructions")
        self.current_turn = turn_id
        self.marks = {"recv": float(message.get("_recv", time.monotonic())), "start": time.monotonic()}
        self.protocol.emit("thinking", turn_id=turn_id)
        agent = self.take_agent(session_id, instructions)
        # Per turn, like Hermes' gateway does on a reused agent: voice asks for "none" (LAT-1).
        agent.reasoning_config = self.reasoning_for(message.get("reasoning_effort"))
        self.marks["built"] = time.monotonic()
        keep = False
        try:
            self.checked_tools(agent)
            with self.lock:
                self.agent = agent
                stopped = self.stop_requested
            if stopped:
                return {"ev": "cancelled"}
            before = {key: getattr(agent, f"session_{key}", 0) for key in SESSION_USAGE_KEYS}
            result = agent.run_conversation(
                str(message["input"]), conversation_history=self.history_for(session_id), task_id=session_id
            )
            # A warm agent's session_* counters span every turn it ran: report this turn's share.
            for key in SESSION_USAGE_KEYS:
                if isinstance(result.get(key), int) and isinstance(before[key], int):
                    result[key] -= before[key]
            if isinstance(result.get("messages"), list):
                self.histories[session_id] = result["messages"]
            self.log_timing(turn_id, result)
            with self.lock:
                stopped = self.stop_requested
            terminal = self.outcome(result, stopped)
            # Only a clean turn leaves its agent warm: interrupt or failure state never carries over.
            keep = terminal["ev"] == "completed" and not result.get("interrupted")
            return terminal
        finally:
            with self.lock:
                self.agent = None
            if keep:
                self.warm = (agent, (session_id, instructions or None))
            else:
                agent.close()

    def log_timing(self, turn_id: str, result: dict[str, Any]) -> None:
        """One stderr line per turn (the supervisor logs it): where the first delta's time goes."""
        marks, end = self.marks, time.monotonic()

        def ms(a: str, b: str | None = None) -> int | None:
            stop = marks.get(b) if b else end
            return round((stop - marks[a]) * 1000) if a in marks and stop is not None else None

        # The log redacts any key with "token" in it: input_tokens → input.
        usage = " ".join(
            f"{k.removesuffix('_tokens')}={result[k]}" for k in USAGE_KEYS if isinstance(result.get(k), int)
        )
        print(
            f"drakter_runner: timing turn={turn_id[:8]} queue_ms={ms('recv', 'start')} build_ms={ms('start', 'built')} "
            f"first_delta_ms={ms('start', 'delta')} total_ms={ms('start')} {usage}",
            file=sys.stderr,
            flush=True,
        )

    def outcome(self, result: dict[str, Any], stopped: bool) -> dict[str, Any]:
        final = result.get("final_response")
        if stopped or result.get("interrupted"):  # final_response may be partial here
            return {"ev": "cancelled"}
        if result.get("failed") or not final:
            print(f"drakter_runner: turn failed: {result.get('error')}", file=sys.stderr, flush=True)
            return {"ev": "failed", "code": classify_failure(result.get("error")), "message": "El modelo no respondió."}
        usage = {key: result[key] for key in USAGE_KEYS if isinstance(result.get(key), int)}
        terminal: dict[str, Any] = {"ev": "completed", "output": str(final), "usage": usage}
        pending = result.get("pending_steer")
        if isinstance(pending, str) and pending.strip():
            terminal["pending_steer"] = pending  # accepted but never consumed: the backend reopens it
        return terminal

    def guarded_turn(self, message: dict[str, Any]) -> None:
        try:
            terminal = self.run_turn(message)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            terminal = {"ev": "failed", "code": "provider_error", "message": "Fallo interno del agente."}
        with self.lock:
            self.active_turn = None
            self.stop_requested = False
        # Last, so that a terminal event means the next turn is already accepted.
        self.protocol.emit(terminal.pop("ev"), turn_id=str(message["turn_id"]), **terminal)

    def work(self) -> None:
        """One thread per turn, one turn at a time; stdin has its own thread."""
        while True:
            message = self.turns.get()
            thread = threading.Thread(target=self.guarded_turn, args=(message,), name="drakter-turn")
            thread.start()
            thread.join()

    def interrupt(self, turn_id: str) -> None:
        with self.lock:
            if turn_id != self.active_turn:
                return
            self.stop_requested = True
            agent = self.agent
        if agent is not None:
            agent.hard_interrupt("Detenido por el usuario")

    def steer(self, turn_id: str, text: str) -> None:
        """Voice v2 (V-22): a correction into the running turn, same turn_id. Always answers."""
        with self.lock:
            agent = self.agent if turn_id == self.active_turn and not self.stop_requested else None
        accepted = False
        if agent is not None:
            try:
                accepted = bool(agent.redirect(text))
            except Exception:
                traceback.print_exc(file=sys.stderr)
        self.protocol.emit("steered", turn_id=turn_id, accepted=accepted)

    def exit_now(self) -> None:
        """EOF means the backend is gone: no orphan, whatever Hermes is doing."""
        with self.lock:
            agent = self.agent
        if agent is not None:
            threading.Thread(target=agent.hard_interrupt, daemon=True).start()
            time.sleep(EOF_INTERRUPT_S)
        os._exit(0)

    def read(self) -> None:
        while True:
            message = self.protocol.read_message()
            if message is None:
                self.exit_now()
            op = message.get("op") if message else None
            if op == "turn" and all(isinstance(message.get(k), str) for k in ("turn_id", "session_id", "input")):
                with self.lock:
                    busy = self.active_turn is not None
                    if not busy:
                        self.active_turn = message["turn_id"]
                if busy:
                    self.protocol.emit(
                        "failed", turn_id=message["turn_id"], code="agent_busy", message="Ya hay un turno en curso."
                    )
                else:
                    message["_recv"] = time.monotonic()
                    self.turns.put(message)
            elif op == "stop" and isinstance(message.get("turn_id"), str):
                self.interrupt(message["turn_id"])
            elif op == "steer" and isinstance(message.get("turn_id"), str) and isinstance(message.get("text"), str):
                self.steer(message["turn_id"], message["text"])
            elif op == "shutdown":
                self.exit_now()
            else:
                self.protocol.emit("error", code="invalid_message")


def classify_failure(error: Any) -> str:
    text = str(error or "").lower()
    if any(mark in text for mark in ("401", "403", "unauthorized", "authentication", "invalid x-api-key")):
        return "provider_auth"
    return "provider_error"


def main() -> None:
    die_with_parent()
    protocol = Protocol()
    runner = Runner(protocol)
    # Before boot: an EOF during slow imports must also end the process.
    threading.Thread(target=runner.read, name="drakter-stdin", daemon=True).start()
    try:
        runner.boot()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        os._exit(EXIT_BOOT_FAILED)
    runner.work()


if __name__ == "__main__":
    main()
