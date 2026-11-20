"""Cliente mínimo de Chrome DevTools Protocol para la ventana de Electron."""
from __future__ import annotations

import base64
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def find_page(port: int, timeout: float = 30) -> str:
    """Devuelve el WebSocket de la ventana principal (no DevTools ni about:blank)."""
    deadline = time.monotonic() + timeout
    last: Exception | str = "sin páginas"
    while time.monotonic() < deadline:
        try:
            with _OPENER.open(f"http://127.0.0.1:{port}/json/list", timeout=2) as reply:
                targets = json.load(reply)
            for target in targets:
                url = target.get("url", "")
                if target.get("type") == "page" and url and not url.startswith(("devtools:", "about:")):
                    return target["webSocketDebuggerUrl"]
        except OSError as exc:
            last = exc
        time.sleep(0.2)
    raise TimeoutError(f"CDP sin ventana tras {timeout} s: {last}")


class Cdp:
    def __init__(self, ws_url: str) -> None:
        from websockets.sync.client import connect

        self._ws = connect(ws_url, max_size=None, proxy=None, open_timeout=10)
        self._next_id = 0
        self.console_errors: list[str] = []
        self.exceptions: list[str] = []
        self.send("Runtime.enable")
        self.send("Log.enable")
        self.send("Page.enable")

    def close(self) -> None:
        self._ws.close()

    def _collect(self, message: dict[str, Any]) -> None:
        method, params = message.get("method"), message.get("params", {})
        if method == "Runtime.exceptionThrown":
            detail = params.get("exceptionDetails", {})
            self.exceptions.append(detail.get("exception", {}).get("description")
                                   or detail.get("text", "excepción"))
        elif method == "Runtime.consoleAPICalled" and params.get("type") == "error":
            parts = [str(a.get("value", a.get("description", ""))) for a in params.get("args", [])]
            self.console_errors.append(" ".join(parts))
        elif method == "Log.entryAdded" and params.get("entry", {}).get("level") == "error":
            entry = params["entry"]
            url = entry.get("url")
            self.console_errors.append(entry.get("text", "error") + (f" [{url}]" if url else ""))

    def send(self, method: str, params: dict[str, Any] | None = None, timeout: float = 30) -> dict:
        self._next_id += 1
        call = self._next_id
        self._ws.send(json.dumps({"id": call, "method": method, "params": params or {}}))
        deadline = time.monotonic() + timeout
        while True:
            message = json.loads(self._ws.recv(timeout=max(deadline - time.monotonic(), 0.01)))
            if message.get("id") == call:
                if "error" in message:
                    raise RuntimeError(f"CDP {method}: {message['error']}")
                return message.get("result", {})
            self._collect(message)

    def evaluate(self, expression: str, timeout: float = 30) -> Any:
        """Evalúa en la página y devuelve el valor; esperar promesas está incluido."""
        reply = self.send("Runtime.evaluate", {"expression": expression, "awaitPromise": True,
                                               "returnByValue": True}, timeout)
        if "exceptionDetails" in reply:
            raise RuntimeError(reply["exceptionDetails"].get("exception", {}).get("description")
                               or reply["exceptionDetails"].get("text"))
        return reply.get("result", {}).get("value")

    def wait_for(self, expression: str, timeout: float = 15) -> Any:
        deadline = time.monotonic() + timeout
        while True:
            value = self.evaluate(expression)
            if value:
                return value
            if time.monotonic() > deadline:
                raise AssertionError(f"tiempo agotado esperando: {expression}")
            time.sleep(0.1)

    def click(self, selector: str) -> None:
        """Clic con eventos reales de ratón, no `element.click()`."""
        box = self.wait_for(
            f"(() => {{ const e = document.querySelector({json.dumps(selector)}); if (!e) return null;"
            " e.scrollIntoView({block: 'center'}); const r = e.getBoundingClientRect();"
            " return {x: r.x + r.width / 2, y: r.y + r.height / 2}; })()")
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            self.send("Input.dispatchMouseEvent", {"type": kind, "x": box["x"], "y": box["y"],
                                                   "button": "left", "clickCount": 1})

    def type_text(self, text: str) -> None:
        self.send("Input.insertText", {"text": text})

    def press(self, key: str) -> None:
        for kind in ("keyDown", "keyUp"):
            self.send("Input.dispatchKeyEvent", {"type": kind, "key": key, "code": key,
                                                 "windowsVirtualKeyCode": 13 if key == "Enter" else 0})

    def screenshot(self, path: Path) -> Path:
        reply = self.send("Page.captureScreenshot", {"format": "png"})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(reply["data"]))
        return path
