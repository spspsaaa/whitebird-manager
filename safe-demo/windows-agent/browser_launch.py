"""Explicit, local-only profile launch using documented Octo and Dolphin APIs.

No cloud endpoints, credentials, wallet interaction, transfers, or batch starts.
"""
import json
import os
import re
from urllib.parse import quote
from urllib.request import Request, urlopen

_PROFILE_ID = re.compile(r"[A-Za-z0-9_-]{1,120}\Z")


def start_profile(browser, profile_id, opener=urlopen, dolphin_port=None):
    if browser not in ("octo", "dolphin"):
        raise ValueError("Unsupported browser")
    if not isinstance(profile_id, str) or not _PROFILE_ID.fullmatch(profile_id):
        raise ValueError("Invalid profile ID")
    if browser == "octo":
        url = "http://127.0.0.1:58888/api/profiles/start"
        request = Request(url, data=json.dumps({"uuid": profile_id, "headless": False,
                                                "debug_port": False, "only_local": True}).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
    else:
        if dolphin_port is None:
            dolphin_port = int(os.environ.get("DOLPHIN_LOCAL_PORT", "3001"))
        if not isinstance(dolphin_port, int) or not 1 <= dolphin_port <= 65535:
            raise ValueError("Invalid Dolphin port")
        url = ("http://127.0.0.1:%d/v1.0/browser_profiles/%s/start?automation=1"
               % (dolphin_port, quote(profile_id, safe="")))
        request = Request(url, method="GET")
    with opener(request, timeout=90) as response:
        result = json.load(response)
    if not isinstance(result, dict):
        raise RuntimeError("Unexpected local API response")
    if result.get("success") is False or result.get("error"):
        raise RuntimeError("Browser rejected profile start")
    return {"browser": browser, "profile_id": profile_id, "status": "start_requested",
            "notice": "Confirm the profile window opened on your Windows PC"}


def start_selected(data, name, opener=urlopen, dolphin_port=None):
    from select_profile import select_account
    selected = select_account(data, name)
    return start_profile(selected["browser"], selected["profile_id"],
                         opener=opener, dolphin_port=dolphin_port)
