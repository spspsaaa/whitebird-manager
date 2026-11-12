# WhiteBird Manager — one Windows PC

Octo Browser (17 profiles) and Dolphin Anty (4 profiles) can be open simultaneously.

## First launch

1. Install Python 3 on the Windows computer.
2. Download this `windows-agent` folder from the development branch.
3. Copy `accounts.example.json` to `accounts.json` and fill in account names and profile IDs. **Do not add passwords, cookies, browser API tokens, or 2FA codes.**
4. Double-click `START-WHITEBIRD.bat`. This checks both local ports and validates inventory.
5. To see account names: `py -3 whitebird_agent.py accounts`.
6. To select a profile: `py -3 whitebird_agent.py select "Account 01"`.

## Local balance report

1. Copy `balances.example.json` to `balances.json` on the Windows PC.
2. Enter amounts observed in the WhiteBird wallet page for each named account. This does **not** automatically read a wallet.
3. Run `py -3 whitebird_agent.py report` to show validated per-account balances, totals and accounts still missing observations.
4. Keep `balances.json` private and local. Never commit it to GitHub.

## Telegram balance bridge

After deploying the matching bot server, follow `BRIDGE-SETUP.md`. Run `py -3 whitebird_agent.py upload` to send only manually observed balances. The bot owner can use `/agent_balances` to view the report. This is opt-in, not an automatic wallet scan.


## Open a selected browser profile

Run `py -3 whitebird_agent.py open "Account 01"` on the Windows PC after both desktop browsers are running and signed in. This explicitly requests opening only the selected mapped profile through the browser's local API. Octo uses port 58888; Dolphin defaults to 3001. If Dolphin uses another port, set `DOLPHIN_LOCAL_PORT` to the port displayed in its Health window. Dolphin API automation may require a paid plan and prior local authorization. This command does not request browser passwords or API tokens. Real Windows behavior remains unverified.

## Current scope

- Inventory validation and selection: implemented.
- Independent TCP checks for Octo on 127.0.0.1:58888 and Dolphin on 127.0.0.1:3001: implemented. These are **port checks**, not authenticated API health checks.
- Browser profile startup: explicit local API launch implemented, not yet verified on the installed Windows versions.
- Balance report: **implemented** for manually observed values, with exact decimal totals. Automated extraction from WhiteBird is **not connected**.
- Telegram bot: existing server demo is separate; **this Windows CLI is not yet connected to Telegram**.
- Withdrawals: draft-only; no money movement.

No internet requests, no hidden service, no automatic money transfers. Keep `accounts.json` on the PC, out of GitHub.
