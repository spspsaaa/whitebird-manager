# WhiteBird Manager — Windows local diagnostics (read-only)

This is **not** an Octo profile launcher or remote-control agent. It does not retrieve balances or execute financial operations.

## Files

- `CHECK-OCTO.bat`: manual one-off health check.
- `run-diagnostics.ps1`: writes a small local status report to `%LOCALAPPDATA%\WhiteBirdManager\octo-status.json`.
- `install-local-monitor.ps1`: opt-in Windows Task Scheduler job every 15 minutes.
- `uninstall-local-monitor.ps1`: stops future scheduled checks.

Run the installer only after reviewing it. The task runs under the current Windows user and requires that these scripts remain at the same path. It does not auto-update or upload reports. No credentials, tokens, cookies, proxy settings or profile IDs are read. The only network request is to `127.0.0.1:58888`.

To run once without installing a task: in PowerShell, use `powershell -NoProfile -File .\run-diagnostics.ps1` from this directory.

**Limitations:** CI can check PowerShell syntax on Windows, but cannot verify connectivity to your local Octo instance. Actual integration requires explicit local installation and testing. Do not paste secrets into diagnostic reports.
