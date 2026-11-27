#!/usr/bin/env python3
"""DEV-ONLY deterministic stand-in for the Anthropic Messages API.

Lets Hermes run end to end without network or keys, following scripted
scenarios. It is NOT a model: nothing it returns says anything about how
Claude Haiku 5.5 (or any real model) behaves.

Standard library only. Binds to 127.0.0.1, ignores credentials, and refuses to
start when DRAKTER_ENV is production.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

BIND_HOST = "127.0.0.1"
ALLOWED_HOSTNAMES = {"127.0.0.1", "localhost"}
MODEL_ID = "drakter-dev-stub"
MARKER = "[DEV-STUB]"
DEV_HEADER = "X-Drakter-Dev-Stub"
SCENARIO_RE = re.compile(r"\[stub:([a-z0-9-]+)\]")
TEMPLATE_RE = re.compile(r"\{\{([a-z_]+)\}\}")
# Tool results may arrive JSON-encoded inside a string (`\"key\": \"value\"`): the backslashes are optional.
RESULT_FIELD_RE = re.compile(r'\\?"([a-z_]{1,40})\\?"\s*:\s*\\?"([^"\\]{1,200})\\?"')
MAX_BODY_BYTES = 64 * 1024 * 1024
CHUNK_CHARS = 12
PRODUCTION_VALUES = {"production", "prod"}
STEP_KEYS = {"text", "tool_calls"}
# {{sandbox}} ends up inside a shell command, so only plain absolute paths pass.
SAFE_SANDBOX_RE = re.compile(r"(/[A-Za-z0-9_.-]+){2,}")
EXIT_PRODUCTION = 3
EXIT_BAD_SCENARIO = 4


class ScenarioError(ValueError):
    """A scenario file is malformed or cannot be rendered."""


def log(message: str) -> None:
    print(f"{MARKER} {message}", file=sys.stderr, flush=True)


@dataclass(frozen=True)
class Reply:
    content: list[dict[str, Any]]
    stop_reason: str
    scenario: str
    step: int


def validate_step(step: Any, where: str) -> None:
    if not isinstance(step, dict):
        raise ScenarioError(f"{where}: must be an object")
    if not step.keys() & STEP_KEYS:
        raise ScenarioError(f"{where}: needs text or tool_calls")
    if "text" in step and not isinstance(step["text"], str):
        raise ScenarioError(f"{where}: text must be a string")
    for call in step.get("tool_calls", []):
        if not isinstance(call, dict) or not isinstance(call.get("name"), str):
            raise ScenarioError(f"{where}: every tool call needs a name")
        if not isinstance(call.get("input", {}), dict):
            raise ScenarioError(f"{where}: tool call input must be an object")
    for index, branch in enumerate(step.get("branches", [])):
        if not isinstance(branch, dict) or not isinstance(branch.get("contains"), str):
            raise ScenarioError(f"{where}.branches[{index}]: needs contains")
        validate_step({k: v for k, v in branch.items() if k != "contains"}, f"{where}.branches[{index}]")


def load_scenarios(directory: Path) -> dict[str, dict[str, Any]]:
    scenarios: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ScenarioError(f"{path.name}: invalid JSON: {exc}") from exc
        name = path.stem
        if not SCENARIO_RE.fullmatch(f"[stub:{name}]"):
            raise ScenarioError(f"{path.name}: use lowercase letters, digits and hyphens in the name")
        steps = data.get("steps") if isinstance(data, dict) else None
        if not isinstance(steps, list) or not steps:
            raise ScenarioError(f"{path.name}: steps must be a non-empty list")
        for index, step in enumerate(steps):
            validate_step(step, f"{path.name}.steps[{index}]")
        scenarios[name] = data
    if not scenarios:
        raise ScenarioError(f"no scenarios found in {directory}")
    return scenarios


def validate_sandbox(path: str) -> None:
    if not SAFE_SANDBOX_RE.fullmatch(path) or {".", ".."} & set(path.split("/")):
        raise ScenarioError(f"sandbox must be a plain absolute path with two or more levels: {path!r}")


def text_of(block_content: Any) -> str:
    if isinstance(block_content, str):
        return block_content
    if not isinstance(block_content, list):
        return ""
    parts = []
    for block in block_content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "\n".join(parts)


def blocks_of(message: dict[str, Any]) -> list[Any]:
    content = message.get("content")
    return content if isinstance(content, list) else [{"type": "text", "text": str(content or "")}]


def tool_results_in(message: dict[str, Any]) -> list[str]:
    if message.get("role") != "user":
        return []
    return [
        text_of(block.get("content"))
        for block in blocks_of(message)
        if isinstance(block, dict) and block.get("type") == "tool_result"
    ]


def conversation_state(messages: list[dict[str, Any]]) -> tuple[int, str]:
    """Return tool rounds since the last plain user turn and the latest result text."""
    rounds = 0
    latest = ""
    for message in reversed(messages):
        results = tool_results_in(message)
        if results:
            if not rounds:
                latest = "\n".join(results)
            rounds += 1
        elif message.get("role") == "user":
            break
    return rounds, latest


def select_scenario(messages: list[dict[str, Any]], scenarios: dict[str, Any], default: str) -> str:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        for block in blocks_of(message):
            if isinstance(block, dict) and block.get("type") == "text":
                found = SCENARIO_RE.findall(str(block.get("text", "")))
                if found:
                    if found[-1] not in scenarios:
                        raise ScenarioError(f"unknown scenario: {found[-1]}")
                    return found[-1]
    return default


def render(value: Any, variables: dict[str, str]) -> Any:
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in variables:
                raise ScenarioError(f"scenario needs --var {key}=...")
            return variables[key]
        return TEMPLATE_RE.sub(replace, value)
    if isinstance(value, list):
        return [render(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: render(item, variables) for key, item in value.items()}
    return value


def resolve_tool_name(name: str, offered: list[str]) -> str | None:
    """Hermes may expose tools with a prefix depending on its auth route."""
    if name in offered:
        return name
    prefixed = f"mcp__{name}"
    return prefixed if prefixed in offered else None


def build_reply(
    body: dict[str, Any],
    scenarios: dict[str, dict[str, Any]],
    default: str,
    variables: dict[str, str],
) -> Reply:
    messages = body.get("messages")
    if not isinstance(messages, list) or not all(isinstance(m, dict) for m in messages):
        raise ScenarioError("messages must be a list of objects")
    if not isinstance(body.get("tools") or [], list):
        raise ScenarioError("tools must be a list")
    name = select_scenario(messages, scenarios, default)
    if not body.get("tools"):
        # Hermes makes tool-less side calls (session titles); scripts must not run there.
        return Reply([{"type": "text", "text": f"{MARKER} respuesta auxiliar"}], "end_turn", name, 0)
    steps = scenarios[name]["steps"]
    rounds, latest_result = conversation_state(messages)
    if rounds >= len(steps):
        content = [{"type": "text", "text": f"{MARKER} guion agotado en el escenario {name}."}]
        return Reply(content, "end_turn", name, rounds)

    step = steps[rounds]
    for branch in step.get("branches", []):
        if branch["contains"] in latest_result:
            step = branch
            break

    context = {**variables, "tool_result": latest_result[:2000]}
    # `{{result_<key>}}`: the first `"<key>": "<value>"` of the latest result (e.g. a `guide_id`).
    for key, value in RESULT_FIELD_RE.findall(latest_result):
        context.setdefault(f"result_{key}", value)
    content: list[dict[str, Any]] = []
    if "text" in step:
        content.append({"type": "text", "text": f"{MARKER} {render(step['text'], context)}"})

    offered = [str(tool.get("name")) for tool in body.get("tools") or [] if isinstance(tool, dict)]
    seed = json.dumps(messages, sort_keys=True, ensure_ascii=False)
    for index, call in enumerate(step.get("tool_calls", [])):
        wanted = call["name"]
        resolved = wanted if call.get("allow_missing") else resolve_tool_name(wanted, offered)
        if resolved is None:
            # A silent skip would read as "the tool was blocked" in a test report.
            content.append({"type": "text", "text": f"{MARKER} escenario no aplicable: Hermes no ofrece {wanted}."})
            return Reply(content, "end_turn", name, rounds)
        digest = hashlib.sha256(f"{seed}|{rounds}|{index}".encode()).hexdigest()[:20]
        content.append({
            "type": "tool_use",
            "id": f"toolu_devstub_{digest}",
            "name": resolved,
            "input": render(call.get("input", {}), context),
        })
    stop_reason = "tool_use" if any(b["type"] == "tool_use" for b in content) else "end_turn"
    return Reply(content, stop_reason, name, rounds)


def chunks(text: str) -> list[str]:
    return [text[i:i + CHUNK_CHARS] for i in range(0, len(text), CHUNK_CHARS)] or [""]


def stream_events(reply: Reply, message_id: str, usage: dict[str, int]) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = [
        ("message_start", {"message": {
            "id": message_id, "type": "message", "role": "assistant", "model": MODEL_ID,
            "content": [], "stop_reason": None, "stop_sequence": None,
            "usage": {**usage, "output_tokens": 1},
        }}),
        ("ping", {}),
    ]
    for index, block in enumerate(reply.content):
        if block["type"] == "text":
            start = {"type": "text", "text": ""}
            deltas = [{"type": "text_delta", "text": part} for part in chunks(block["text"])]
        else:
            start = {"type": "tool_use", "id": block["id"], "name": block["name"], "input": {}}
            raw = json.dumps(block["input"], ensure_ascii=False)
            deltas = [{"type": "input_json_delta", "partial_json": part} for part in chunks(raw)]
        events.append(("content_block_start", {"index": index, "content_block": start}))
        events.extend(("content_block_delta", {"index": index, "delta": delta}) for delta in deltas)
        events.append(("content_block_stop", {"index": index}))
    events.append(("message_delta", {
        "delta": {"stop_reason": reply.stop_reason, "stop_sequence": None},
        "usage": {"output_tokens": usage["output_tokens"]},
    }))
    events.append(("message_stop", {}))
    return events


def model_entry() -> dict[str, Any]:
    return {
        "id": MODEL_ID, "type": "model", "display_name": f"{MARKER} stub determinista",
        "created_at": "2026-01-01T00:00:00Z", "max_input_tokens": 200000, "max_tokens": 8192,
        "context_length": 200000,
    }


class StubHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "DrakterDevStub/DEV"
    sys_version = ""
    scenarios: dict[str, dict[str, Any]] = {}
    default_scenario = ""
    variables: dict[str, str] = {}
    chunk_delay = 0.0

    def log_message(self, format: str, *args: Any) -> None:
        return

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header(DEV_HEADER, "true")
        if self.close_connection:
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)

    def send_error_json(self, status: int, kind: str, message: str) -> None:
        # The body may be unread, so this connection cannot be reused.
        self.close_connection = True
        log(f"{self.command} {getattr(self, 'path', '')} -> {status}: {message}")
        self.send_json(status, {"type": "error", "error": {"type": kind, "message": f"{MARKER} {message}"}})

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        self.send_error_json(code, "api_error", message or "unsupported request")

    def host_is_loopback(self) -> bool:
        # Blocks DNS rebinding from a browser page reaching this local server.
        hostname = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        return hostname in ALLOWED_HOSTNAMES

    def do_GET(self) -> None:
        if not self.host_is_loopback():
            return self.send_error_json(403, "permission_error", "only loopback hosts are accepted")
        path = self.path.split("?", 1)[0].rstrip("/")
        if path.endswith("/health"):
            return self.send_json(200, {"status": "ok", "dev_stub": True, "scenarios": sorted(self.scenarios)})
        if path.endswith("/models"):
            return self.send_json(200, {"data": [model_entry()], "has_more": False})
        if path.endswith(f"/models/{MODEL_ID}"):
            return self.send_json(200, model_entry())
        self.send_error_json(404, "not_found_error", f"unknown path: {path}")

    def do_POST(self) -> None:
        if not self.host_is_loopback():
            return self.send_error_json(403, "permission_error", "only loopback hosts are accepted")
        if not self.path.split("?", 1)[0].rstrip("/").endswith("/v1/messages"):
            return self.send_error_json(404, "not_found_error", "only /v1/messages is scripted")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self.send_error_json(400, "invalid_request_error", "invalid Content-Length")
        if length <= 0 or length > MAX_BODY_BYTES:
            return self.send_error_json(413, "request_too_large", "body is empty or too large")
        try:
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("body must be an object")
            reply = build_reply(body, self.scenarios, self.default_scenario, self.variables)
        except (ValueError, ScenarioError) as exc:
            return self.send_error_json(400, "invalid_request_error", str(exc))

        tools = [b["name"] for b in reply.content if b["type"] == "tool_use"]
        log(f"scenario={reply.scenario} step={reply.step} stop={reply.stop_reason} tools={tools}")
        seed = json.dumps(reply.content, sort_keys=True, ensure_ascii=False)
        message_id = "msg_devstub_" + hashlib.sha256(seed.encode()).hexdigest()[:20]
        usage = {
            "input_tokens": 1, "output_tokens": 1,
            "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
        }
        if not body.get("stream"):
            return self.send_json(200, {
                "id": message_id, "type": "message", "role": "assistant", "model": MODEL_ID,
                "content": reply.content, "stop_reason": reply.stop_reason,
                "stop_sequence": None, "usage": usage,
            })

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header(DEV_HEADER, "true")
        self.end_headers()
        self.close_connection = True
        for event, data in stream_events(reply, message_id, usage):
            payload = json.dumps({"type": event, **data}, ensure_ascii=False)
            self.wfile.write(f"event: {event}\ndata: {payload}\n\n".encode())
            self.wfile.flush()
            if self.chunk_delay:
                time.sleep(self.chunk_delay)


class StubServer(ThreadingHTTPServer):
    def handle_error(self, request: Any, client_address: Any) -> None:
        log(f"error atendiendo a {client_address[0]}: {sys.exc_info()[1]!r}")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Drakter DEV-only scripted LLM stub (never production).")
    parser.add_argument("--port", type=int, default=28500)
    parser.add_argument("--scenarios", type=Path, default=here / "scenarios")
    parser.add_argument("--default-scenario", default="conversacion")
    parser.add_argument("--var", action="append", default=[], metavar="KEY=VALUE",
                        help="value for {{KEY}} in scenarios; repeatable")
    parser.add_argument("--chunk-delay-ms", type=int, default=0)
    parser.add_argument("--check", action="store_true", help="validate scenarios and exit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    # Checked first, so production never reaches argument parsing or the socket.
    if os.environ.get("DRAKTER_ENV", "").strip().lower() in PRODUCTION_VALUES:
        log("se niega a arrancar: DRAKTER_ENV es production.")
        return EXIT_PRODUCTION

    args = parse_args(argv)
    try:
        scenarios = load_scenarios(args.scenarios)
        if args.default_scenario not in scenarios:
            raise ScenarioError(f"unknown default scenario: {args.default_scenario}")
        variables = {"fixtures": str(Path(__file__).resolve().parent / "fixtures")}
        variables.update(item.split("=", 1) for item in args.var)
        if "sandbox" in variables:
            validate_sandbox(variables["sandbox"])
    except (ScenarioError, ValueError) as exc:
        log(f"escenarios no validos: {exc}")
        return EXIT_BAD_SCENARIO
    if args.check:
        log(f"{len(scenarios)} escenarios validos: {', '.join(sorted(scenarios))}")
        return 0

    StubHandler.scenarios = scenarios
    StubHandler.default_scenario = args.default_scenario
    StubHandler.variables = variables
    StubHandler.chunk_delay = args.chunk_delay_ms / 1000
    server = StubServer((BIND_HOST, args.port), StubHandler)
    log(f"SERVIDOR DE DESARROLLO, no es un modelo real. http://{BIND_HOST}:{server.server_address[1]}")
    log(f"escenarios: {', '.join(sorted(scenarios))}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
