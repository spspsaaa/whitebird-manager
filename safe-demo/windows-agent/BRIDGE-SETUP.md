# Windows ↔ Telegram read-only balance bridge

This integration transfers **only balance observations** to the bot. No browser credentials, profile IDs, cookies, tokens, or transfer instructions are included.

1. Configure the **same new random secret** as `AGENT_REPORT_SECRET` on the bot's server and `WHITEBIRD_AGENT_SECRET` on Windows (minimum 32 characters). Do not send it in chat or commit it.
2. Set `WHITEBIRD_AGENT_URL` on Windows to the bot's real HTTPS address ending in `/agent/balances`. Do not use an example URL.
3. Add matching account names in the Telegram bot and local `accounts.json`. The server rejects unknown names.
4. Populate local `balances.json` with observed RUB.wb/USDT values. These are not automatically fetched or independently verified.
5. On Windows, run `py -3 whitebird_agent.py upload` **only when you want to send a report**.
6. In Telegram, send `/agent_balances` as the configured bot owner. The bot labels them as unverified local observations.

Security: the upload is opt-in, HTTPS-only, and authenticated by a separate shared secret. Keep all secrets in environment variables. Avoid exposing the balance endpoint without HTTPS. Existing `/balances` remains explicitly demo-only.

**Deployment warning:** these changes are on `feature/secure-auth-approval`, not necessarily the branch deployed to Render. The bridge will not work until the bot server is deployed with this code and configured. No live profile launching or automated WhiteBird extraction is implemented here.
