import httpx
import pytest
import respx

from app.wb.browsers import BrowserProfile, build_browser
from app.wb.browsers.dolphin import DolphinBrowser
from app.wb.browsers.octo import OctoBrowser


@respx.mock
async def test_dolphin_start_builds_ws_url():
    route = respx.get(
        "http://localhost:3001/v1.0/browser_profiles/abc123/start"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "success": True,
                "automation": {
                    "port": 50568,
                    "wsEndpoint": "/devtools/browser/xyz",
                },
            },
        )
    )
    browser = DolphinBrowser(BrowserProfile(provider="dolphin", profile_id="abc123"))
    ws = await browser.start()
    assert ws == "ws://127.0.0.1:50568/devtools/browser/xyz"
    assert route.called


@respx.mock
async def test_dolphin_start_failure():
    respx.get("http://localhost:3001/v1.0/browser_profiles/abc/start").mock(
        return_value=httpx.Response(200, json={"success": False, "message": "no"})
    )
    browser = DolphinBrowser(BrowserProfile(provider="dolphin", profile_id="abc"))
    with pytest.raises(Exception):
        await browser.start()


@respx.mock
async def test_octo_start_returns_ws_endpoint():
    respx.post("http://localhost:58888/api/profiles/start").mock(
        return_value=httpx.Response(
            200, json={"ws_endpoint": "ws://127.0.0.1:53215/devtools/browser/abc"}
        )
    )
    browser = OctoBrowser(BrowserProfile(provider="octo", profile_id="uuid-1"))
    ws = await browser.start()
    assert ws == "ws://127.0.0.1:53215/devtools/browser/abc"


@respx.mock
async def test_octo_start_failure():
    respx.post("http://localhost:58888/api/profiles/start").mock(
        return_value=httpx.Response(200, json={"error": "nope"})
    )
    browser = OctoBrowser(BrowserProfile(provider="octo", profile_id="uuid-1"))
    with pytest.raises(Exception):
        await browser.start()


def test_build_browser_dispatch():
    assert isinstance(
        build_browser(BrowserProfile(provider="dolphin", profile_id="x")), DolphinBrowser
    )
    assert isinstance(
        build_browser(BrowserProfile(provider="octo", profile_id="x")), OctoBrowser
    )
    with pytest.raises(ValueError):
        build_browser(BrowserProfile(provider="unknown", profile_id="x"))
