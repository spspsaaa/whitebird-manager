import os
import json
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.parse import urlparse

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OWNER = os.environ.get("TELEGRAM_OWNER_ID", "")
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")

def reply(chat_id, text):
    if not TOKEN:
        return
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode()
    req = Request("https://api.telegram.org/bot" + TOKEN + "/sendMessage", data=payload,
                  headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=8) as response:
        response.read()

def handle_update(update):
    message = update.get("message") or {}
    sender = message.get("from") or {}
    chat = message.get("chat") or {}
    if not OWNER or str(sender.get("id", "")) != OWNER or chat.get("id") is None:
        return
    command = (message.get("text") or "").split(" ", 1)[0].split("@", 1)[0]
    responses = {
        "/start": "Тестовый бот запущен. Команды: /status, /accounts, /help",
        "/help": "Демо без подключения к биржам, браузерам и платежам. /status /accounts",
        "/status": "Сервис работает. Режим: безопасная демонстрация.",
        "/accounts": "Демо-аккаунты: 0. Реальные аккаунты не подключены.",
    }
    if command in responses:
        reply(chat["id"], responses[command])

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, obj):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if urlparse(self.path).path == "/health":
            return self.send_json(200, {"ok": True, "mode": "demo"})
        return self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/telegram":
            return self.send_json(404, {"error": "not found"})
        if not WEBHOOK_SECRET or not hmac.compare_digest(
            self.headers.get("X-Telegram-Bot-Api-Secret-Token", ""), WEBHOOK_SECRET
        ):
            return self.send_json(403, {"error": "forbidden"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size < 1 or size > 65536:
                return self.send_json(413, {"error": "invalid size"})
            update = json.loads(self.rfile.read(size))
            if not isinstance(update, dict):
                return self.send_json(400, {"error": "invalid update"})
            handle_update(update)
            return self.send_json(200, {"ok": True})
        except (ValueError, json.JSONDecodeError):
            return self.send_json(400, {"error": "invalid json"})
        except Exception:
            return self.send_json(503, {"error": "temporary failure"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
