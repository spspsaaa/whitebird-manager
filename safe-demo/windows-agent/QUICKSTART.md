# WhiteBird Manager — one Windows PC

Octo Browser (17 profiles) and Dolphin Anty (4 profiles) can be open simultaneously.

## First launch

1. Install Python 3 on the Windows computer.
2. Download this `windows-agent` folder from the development branch.
3. Copy `accounts.example.json` to `accounts.json` and fill in account names and profile IDs. **Do not add passwords, cookies, browser API tokens, or 2FA codes.**
4. Double-click `START-WHITEBIRD.bat`. This checks both local ports and validates inventory.
5. To see account names: `py -3 whitebird_agent.py accounts`.
6. To select a profile: `py -3 whitebird_agent.py select "Account 01"`.

## Current scope

- Inventory validation and selection: implemented.
- Independent TCP checks for Octo on 127.0.0.1:58888 and Dolphin on 127.0.0.1:3001: implemented. These are **port checks**, not authenticated API health checks.
- Browser profile startup: **not implemented**. It requires confirming the installed browser versions and supported local API endpoints; no speculative requests are sent.
- Real wallet balances: **not connected**. Existing extension can read visible wallet balances separately.
- Telegram bot: existing server demo is separate; **this Windows CLI is not yet connected to Telegram**.
- Withdrawals: draft-only; no money movement.

No internet requests, no hidden service, no automatic money transfers. Keep `accounts.json` on the PC, out of GitHub.
