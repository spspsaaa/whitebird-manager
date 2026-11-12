"""Opt-in HTTPS transfer of manually observed balances to user's own bot server.

Requires WHITEBIRD_AGENT_URL and WHITEBIRD_AGENT_SECRET environment variables.
Never sends browser profiles, passwords, cookies, or transfers money.
"""
import json
import os
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from balance_import import validate_balances


def upload_observations(data, account_names, url=None, secret=None, opener=urlopen):
    report = validate_balances(data, account_names)
    url = url if url is not None else os.environ.get("WHITEBIRD_AGENT_URL", "")
    secret = secret if secret is not None else os.environ.get("WHITEBIRD_AGENT_SECRET", "")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.query or parsed.path != "/agent/balances":
        raise ValueError("Set HTTPS URL ending in /agent/balances")
    if not isinstance(secret, str) or len(secret) < 32 or len(secret) > 256:
        raise ValueError("Set WHITEBIRD_AGENT_SECRET (32-256 characters)")
    payload = json.dumps({"balances": report["balances"]}, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "X-WhiteBird-Agent-Secret": secret,
    }, method="POST")
    with opener(request, timeout=12) as response:
        result = json.load(response)
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise RuntimeError("Server rejected balance report")
    return {"uploaded": result.get("stored", 0), "source": "manually_observed_not_verified"}
