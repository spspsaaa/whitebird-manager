"""Anti-detect browser adapters (Dolphin Anty, Octo Browser)."""
from app.wb.browsers.base import AntiDetectBrowser, BrowserProfile, SessionTokens
from app.wb.browsers.dolphin import DolphinBrowser
from app.wb.browsers.octo import OctoBrowser

BROWSERS = {
    "dolphin": DolphinBrowser,
    "octo": OctoBrowser,
}


def build_browser(profile: BrowserProfile, timeout: float = 60.0) -> AntiDetectBrowser:
    """Create the adapter for the given browser provider."""
    try:
        cls = BROWSERS[profile.provider]
    except KeyError as exc:
        raise ValueError(
            f"Unknown browser provider: {profile.provider} "
            f"(supported: {', '.join(BROWSERS)})"
        ) from exc
    return cls(profile, timeout=timeout)


__all__ = [
    "AntiDetectBrowser",
    "BrowserProfile",
    "SessionTokens",
    "DolphinBrowser",
    "OctoBrowser",
    "build_browser",
]
