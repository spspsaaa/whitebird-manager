"""Minimal Chrome DevTools Protocol client.

We do not need a full browser automation stack: reading localStorage is a
single Runtime.evaluate call. Talking CDP directly over WebSocket keeps the
deployment light - no Chromium download, no root, no Playwright.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import websockets

log = logging.getLogger(__name__)


class CDPError(RuntimeError):
    """The CDP connection failed or returned an error."""


class CDPClient:
    """A very small CDP session over a browser websocket endpoint."""

    def __init__(self, ws_url: str, timeout: float = 30.0) -> None:
        self.ws_url = ws_url
        self.timeout = timeout
        self._ws: Any = None
        self._id = 0

    async def __aenter__(self) -> "CDPClient":
        try:
            self._ws = await websockets.connect(
                self.ws_url,
                max_size=16 * 1024 * 1024,
                open_timeout=self.timeout,
            )
        except Exception as exc:
            raise CDPError(f"Could not connect to CDP: {exc}") from exc
        return self

    async def __aexit__(self, *exc_info) -> None:
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # pragma: no cover - best effort
                log.debug("Closing the CDP websocket failed", exc_info=True)

    async def send(
        self, method: str, params: dict[str, Any] | None = None, session_id: str | None = None
    ) -> dict[str, Any]:
        """Send a CDP command and wait for its answer."""
        if self._ws is None:
            raise CDPError("The CDP client is not connected")
        self._id += 1
        message_id = self._id
        payload: dict[str, Any] = {"id": message_id, "method": method}
        if params:
            payload["params"] = params
        if session_id:
            payload["sessionId"] = session_id

        await self._ws.send(json.dumps(payload))

        while True:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=self.timeout)
            try:
                message = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if message.get("id") != message_id:
                continue  # an event, skip it
            if "error" in message:
                raise CDPError(f"{method} failed: {message['error']}")
            return message.get("result", {})

    async def evaluate(self, expression: str, session_id: str | None = None) -> Any:
        """Evaluate a JS expression in the page and return the value."""
        result = await self.send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
            session_id=session_id,
        )
        if result.get("exceptionDetails"):
            raise CDPError(f"JS exception: {result['exceptionDetails']}")
        remote = result.get("result", {})
        if remote.get("subtype") == "error":
            raise CDPError(f"JS error: {remote.get('description')}")
        return remote.get("value")
