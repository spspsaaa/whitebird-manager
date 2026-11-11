"""Dolphin Anty adapter.

Local API (the desktop app must be running on the same machine):
    GET http://localhost:3001/v1.0/browser_profiles/{id}/start?automation=1
    GET http://localhost:3001/v1.0/browser_profiles/{id}/stop
    GET http://localhost:3001/v1.0/browser_profiles

The start response contains the CDP info:
    {"success": true, "automation": {"port": 50568,
     "wsEndpoint": "/devtools/browser/<uuid>"}}
"""
from __future__ import annotations

import logging
from typing import Any

from app.wb.browsers.base import AntiDetectBrowser, BrowserError

log = logging.getLogger(__name__)


class DolphinBrowser(AntiDetectBrowser):
    provider = "dolphin"
    default_base = "http://localhost:3001"

    async def start(self) -> str:
        params = {"automation": "1"}
        if self.profile.extra.get("headless"):
            params["headless"] = "1"
        resp = await self._request(
            "GET",
            f"/v1.0/browser_profiles/{self.profile.profile_id}/start",
            params=params,
        )
        payload = resp.json()
        if not payload.get("success"):
            raise BrowserError(f"Dolphin Anty start failed: {payload}")

        automation = payload.get("automation") or {}
        ws_endpoint = automation.get("wsEndpoint")
        port = automation.get("port")
        if ws_endpoint:
            # The endpoint is relative to the debug port.
            return f"ws://127.0.0.1:{port}{ws_endpoint}"
        if port:
            return f"http://127.0.0.1:{port}"
        raise BrowserError(f"Dolphin Anty returned no debug port: {payload}")

    async def stop(self) -> None:
        try:
            await self._request(
                "GET", f"/v1.0/browser_profiles/{self.profile.profile_id}/stop"
            )
        except Exception:  # pragma: no cover - best effort
            log.warning("Could not stop the Dolphin Anty profile", exc_info=True)

    async def list_profiles(self) -> list[dict[str, Any]]:
        resp = await self._request("GET", "/v1.0/browser_profiles")
        payload = resp.json()
        if isinstance(payload, dict):
            return payload.get("data", []) or []
        return payload or []
