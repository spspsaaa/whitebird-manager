"""Base class for anti-detect browsers.

The browser is used only to obtain an OAuth session for an account.
Afterwards all work happens over the plain HTTP API.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

log = logging.getLogger(__name__)

# localStorage keys used by the Whitebird web app to keep the OAuth session.
TOKEN_KEYS = (
    "access_token",
    "refresh_token",
    "expires_at",
    "accessToken",
    "refreshToken",
    "expiresAt",
)


class BrowserError(RuntimeError):
    """The anti-detect browser is unreachable or returned an error."""


@dataclass
class BrowserProfile:
    """One browser profile, bound to exactly one Whitebird account."""

    provider: str  # "dolphin" | "octo"
    profile_id: str
    label: str = ""
    base_url: str = ""
    api_token: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionTokens:
    access_token: str
    refresh_token: str | None = None
    expires_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
        }


class AntiDetectBrowser:
    """Common behaviour of every anti-detect browser adapter."""

    provider: str = ""
    default_base: str = ""

    def __init__(self, profile: BrowserProfile, timeout: float = 60.0) -> None:
        self.profile = profile
        self.timeout = timeout

    # ------------------------------------------------------------- helpers
    @property
    def base(self) -> str:
        return (self.profile.base_url or self.default_base).rstrip("/")

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self.base}{path}"
        headers = kwargs.pop("headers", None) or {}
        if self.profile.api_token:
            headers.setdefault("X-Octo-Api-Token", self.profile.api_token)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await client.request(method, url, headers=headers, **kwargs)

    # ------------------------------------------------------------ interface
    async def start(self) -> str:
        """Start the profile, return the CDP websocket URL."""
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError

    async def list_profiles(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    async def health(self) -> dict[str, Any]:
        """Check that the local API answers."""
        try:
            resp = await self._request("GET", "/")
            return {"ok": resp.status_code < 500, "status": resp.status_code}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # -------------------------------------------------------------- session
    async def extract_session(
        self, origin: str = "https://whitebird.io"
    ) -> SessionTokens:
        """Read the OAuth tokens from localStorage of the running profile.

        The tokens live in localStorage of the Whitebird web app, so we open
        the page (if needed) and read them with a single CDP evaluate call.
        """
        from app.wb.browsers.cdp import CDPClient, CDPError

        ws_url = await self.start()
        if not ws_url:
            raise BrowserError(
                "The browser did not return a CDP endpoint. Check that the "
                "browser app is running and the profile can be started."
            )

        try:
            async with CDPClient(ws_url, timeout=self.timeout) as cdp:
                target_id = await self._pick_target(cdp, origin)
                if target_id is None:
                    target_id = await self._open_target(cdp, origin)
                if target_id is None:
                    raise CDPError("Could not open a page in the browser")

                attached = await cdp.send(
                    "Target.attachToTarget", {"targetId": target_id, "flatten": True}
                )
                session_id = attached.get("sessionId")
                if not session_id:
                    raise CDPError("Could not attach to the browser page")

                await cdp.send("Runtime.enable", {}, session_id=session_id)

                raw = await cdp.evaluate(
                    "JSON.stringify(Object.fromEntries("
                    + json.dumps(list(TOKEN_KEYS))
                    + ".map(k => [k, localStorage.getItem(k)])))",
                    session_id=session_id,
                )
                if isinstance(raw, str):
                    raw = json.loads(raw)
        except BrowserError:
            raise
        except Exception as exc:
            raise BrowserError(
                f"Could not read the session from the browser: {exc}"
            ) from exc

        if not isinstance(raw, dict):
            raise BrowserError("Unexpected answer while reading localStorage")

        access = raw.get("access_token") or raw.get("accessToken")
        if not access:
            raise BrowserError(
                "No access token in localStorage - log into Whitebird in "
                "this browser profile first."
            )
        refresh = raw.get("refresh_token") or raw.get("refreshToken")
        expires_raw = raw.get("expires_at") or raw.get("expiresAt")
        expires_at: float | None = None
        if expires_raw:
            try:
                expires_at = float(expires_raw)
                if expires_at > 1e12:  # stored in milliseconds
                    expires_at /= 1000.0
            except (TypeError, ValueError):
                expires_at = None
        return SessionTokens(
            access_token=access, refresh_token=refresh, expires_at=expires_at
        )

    # ------------------------------------------------------------- helpers
    async def _list_targets(self, cdp) -> list[dict]:
        result = await cdp.send("Target.getTargets")
        return list(result.get("targetInfos", []))

    async def _pick_target(self, cdp, origin: str) -> str | None:
        """Find an already open page of the site."""
        for target in await self._list_targets(cdp):
            if target.get("type") != "page":
                continue
            if origin in (target.get("url") or ""):
                return target.get("targetId")
        return None

    async def _open_target(self, cdp, origin: str) -> str | None:
        """Open a new page with the site."""
        result = await cdp.send("Target.createTarget", {"url": origin})
        target_id = result.get("targetId")
        # Give the page a moment to load its scripts.
        await asyncio.sleep(3)
        return target_id
