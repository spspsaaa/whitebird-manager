"""Base class for anti-detect browsers.

The browser is used only to obtain an OAuth session for an account.
Afterwards all work happens over the plain HTTP API.
"""
from __future__ import annotations

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
        """Read the OAuth tokens from localStorage of the running profile."""
        from playwright.async_api import async_playwright

        ws_url = await self.start()
        if not ws_url:
            raise BrowserError(
                "The browser did not return a CDP endpoint. Check that the "
                "browser app is running and the profile can be started."
            )

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.connect_over_cdp(ws_url)
                try:
                    context = (
                        browser.contexts[0]
                        if browser.contexts
                        else await browser.new_context()
                    )
                    page = None
                    for candidate in context.pages:
                        if origin in (candidate.url or ""):
                            page = candidate
                            break
                    if page is None:
                        page = await context.new_page()
                        await page.goto(origin, wait_until="domcontentloaded")

                    raw = await page.evaluate(
                        "(keys) => Object.fromEntries("
                        "keys.map(k => [k, localStorage.getItem(k)]))",
                        list(TOKEN_KEYS),
                    )
                finally:
                    await browser.close()
        except BrowserError:
            raise
        except Exception as exc:
            raise BrowserError(
                f"Could not read the session from the browser: {exc}"
            ) from exc

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
