# Windows cloud trial — read-only first stage

Scope: 17 existing Octo profiles, 4 existing Dolphin Anty profiles. No new Dolphin profiles. Preserve existing profile configuration, proxy assignments and synced data. Do not export cookies, session tokens, passwords, or TOTP seeds into GitHub, Telegram, logs or shared storage.

## Infrastructure

Use a licensed Windows VPS with an interactive desktop, persistent SSD, at least 8 GiB RAM (prefer 16 GiB for headroom), 4 vCPU and 80 GiB disk for an initial **single-profile** manual trial. These are planning values, not guaranteed vendor minimums. Check vendor support and cloud provider billing before purchase. Do not assume a free Windows VPS runs 24/7.

Keep the Telegram demo separate from the Windows host. The browser agent is not yet connected to real browser APIs. Render's demo storage must not be treated as durable account storage.

## Trial steps

1. Create a VM with a legitimate Windows installation, patch it, enable MFA on the provider account and restrict remote desktop access to trusted operators.
2. Run `powershell -NoProfile -File .\windows_preflight.ps1` in a local interactive PowerShell session. Review output before sharing; it contains system specifications.
3. Install Octo from the vendor's official download page, in its default installation path.
4. Sign in to the browser vendor through its own interface. Verify existing profile count without creating new profiles. Do not paste credentials into Telegram.
5. Inspect one non-sensitive test profile manually, confirming its existing proxy configuration and browser settings without changing them. Avoid simultaneous use of the same profile on two computers.
6. Check browser vendor diagnostics for compatibility. A cloud VM's hardware, IP path and environment can differ; no guarantee of identical browser fingerprint.
7. For WhiteBird, limit the first integration test to a read-only balance check with appropriate account-owner authorization. Stop if an identity/security challenge appears; do not bypass it.
8. Record pass/fail without storing account secrets or sensitive browser data. If checks fail, stop and revert to local operation.

## Out of scope

No automatic sign-in with passwords/TOTP, no session extraction, no spoofing to defeat account checks, and no unattended withdrawals. Any future transfer requires independent owner confirmation.

Vendor references:
- https://docs.octobrowser.net/en/start/system-requirements/
- https://docs.dolphin-anty.com/cn/getting-started/dolphin-anty-system-requirements-for-pc
