# Safe Telegram demo

Standalone read-only Telegram webhook demo. No exchange, browser or payment integrations.

Render: build command `pip install -r safe-demo/requirements.txt`, start command `python safe-demo/app.py`, health endpoint `/health`.

To activate Telegram, configure `TELEGRAM_BOT_TOKEN`, `TELEGRAM_OWNER_ID`, `TELEGRAM_WEBHOOK_SECRET` securely in Render and register webhook URL `https://<service>.onrender.com/telegram` with Telegram using the same secret. Never commit credentials.
