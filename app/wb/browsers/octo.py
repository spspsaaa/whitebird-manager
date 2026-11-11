"""Octo Browser adapter.

Local client API (the desktop app must be running on the same machine):
    POST http://localhost:58888/api/profiles/start  {"uuid": ..., "debug_port": true}
    POST http://localhost:58888/api/profiles/stop   {"uuid": ...}

The start response contains "ws_endpoint" - a ready to use CDP websocket URL.
The local API needs no token; the cloud API (profiles management) needs one.
"""
from __future__ import annotations

import logging
from typing import Any

from app.wb.browsers.base import AntiDetectBrowser, BrowserError

log = logging.getLogger(__name__)


class OctoBrowser(AntiDetectBrowser):
    provider = "octo"
    default_base = "http://localhost:58888"

    async def start(self) -> str:
        body: dict[str, Any] = {
            "uuid": self.profile.profile_id,
            "headless": bool(self.profile.extra.get("headless")),
            "debug_port": True,
            "timeout": int(self.profile.extra.get("timeout", 120)),
            "only_local": bool(self.profile.extra.get("only_local", True)),
        }
        if self.profile.extra.get("flags"):
            body["flags"] = list(self.profile.extra["flags"])
        if self.profile.extra.get("password"):
            body["password"] = self.profile.extra["password"]

        resp = await self._request("POST", "/api/profiles/start", json=body)
        try:
            payload = resp.json()
        except ValueError as exc:
            raise BrowserError(f"Octo Browser returned a non-JSON answer: {resp}") from exc

        ws_endpoint = payload.get("ws_endpoint")
        if not ws_endpoint:
            raise BrowserError(f"Octo Browser start failed: {payload}")
        return ws_endpoint

    async def stop(self) -> None:
        try:
            await self._request(
                "POST", "/api/profiles/stop", json={"uuid": self.profile.profile_id}
            )
        except Exception:  # pragma: no cover - best effort
            log.warning("Could not stop the Octo Browser profile", exc_info=True)

    async def list_profiles(self) -> list[dict[str, Any]]:
        """List the profiles known to the local client."""
        resp = await self._request("GET", "/api/profiles")
        payload = resp.json()
        if isinstance(payload, dict):
            return payload.get("data", []) or []
        return payload or []

    async def list_cloud_profiles(self) -> list[dict[str, Any]]:
        """List the profiles of the cloud account (needs the API token)."""
        if not self.profile.api_token:
            raise BrowserError("An Octo Browser API token is required")
        resp = await self._request(
            "GET",
            "https://app.octobrowser.net/api/v2/automation/profiles",
        )
        payload = resp.json()
        return payload.get("data", []) or []
