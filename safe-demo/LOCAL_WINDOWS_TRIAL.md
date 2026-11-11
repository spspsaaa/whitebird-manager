# Local Windows trial — no VPS required

Goal: validate the existing Octo Browser setup on the user's own Windows PC before paying for cloud hosting. Start with one of 17 Octo profiles. Leave all four Dolphin Anty profiles untouched.

## 1. Environment check

In PowerShell from the `safe-demo` folder:

```powershell
powershell -NoProfile -File .\windows_preflight.ps1
```

This prints only OS/hardware readiness information. It does not access browser profiles, proxies, credentials, or account data. The disk/RAM thresholds are recommendations for a future VPS, not hard requirements for running Octo on an existing computer.

## 2. Manual existing-profile trial

1. Launch the already-installed Octo Browser normally. Do not reinstall it or reset profile settings.
2. Choose **one existing profile** that you own. Verify its configured proxy and settings through the vendor UI without editing them.
3. Avoid opening the same profile simultaneously on another device.
4. Start the profile using the browser's normal controls; record whether it starts and whether the configured proxy passes the vendor's normal connectivity check.
5. Visit WhiteBird only if you are authorized to use that account. If the session is already active, inspect the displayed balance manually. Do not paste credentials, session cookies, OTP seeds, or screenshots of private financial details into Telegram or GitHub.
6. If the site requests verification, complete it only through its normal interface; stop the automated trial.
7. Record only non-sensitive outcomes: profile opened yes/no; proxy working yes/no; already authenticated yes/no; balance visible yes/no. Do not record the balance amount unless necessary.
8. Do not initiate transfers or withdrawals.

## 3. Offline project tests

The repository currently has **offline adapter scaffolding**, not a working Octo/WhiteBird integration. From `safe-demo`:

```powershell
python -m unittest test_secure_auth test_session_manager test_browser_adapter test_cloud_preflight
```

These tests verify mocked session and browser workflows only; passing them does not establish that live WhiteBird balance retrieval works.

## 4. Trial outcome

If the profile launches and a balance is visible manually, the next engineering task is to evaluate official, permitted read-only browser integration, with explicit owner approval and without evading identity or security checks. No VPS purchase is needed to perform the steps above.
