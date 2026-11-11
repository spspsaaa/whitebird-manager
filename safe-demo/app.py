import os
import json
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.parse import urlparse

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OWNER = os.environ.get("TELEGRAM_OWNER_ID", "")
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")

DEMO_ACCOUNTS = []
KEYBOARD = {"keyboard": [[{"text": "📊 Статус"}, {"text": "📋 Демо-аккаунты"}],
                         [{"text": "➕ Добавить демо"}, {"text": "➖ Удалить демо"}],
                         [{"text": "❓ Помощь"}]], "resize_keyboard": True}

def reply(chat_id, text):
    if not TOKEN:
        return
    payload = json.dumps({"chat_id": chat_id, "text": text, "reply_markup": KEYBOARD}).encode()
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
    raw = (message.get("text") or "").strip()
    command = raw.split(" ", 1)[0].split("@", 1)[0]
    if command == "/start":
        answer = "Тестовый бот запущен. Выбирай действие кнопками ниже."
    elif command == "/status" or raw == "📊 Статус":
        answer = "🟢 Сервер работает. Режим: демонстрация. Демо-аккаунтов: " + str(len(DEMO_ACCOUNTS))
    elif command == "/accounts" or raw == "📋 Демо-аккаунты":
        answer = ("Демо-аккаунтов пока нет." if not DEMO_ACCOUNTS else
                  "Тестовые записи:\\n" + "\\n".join(str(i + 1) + ". " + name for i, name in enumerate(DEMO_ACCOUNTS)))
    elif command == "/help" or raw == "❓ Помощь":
        answer = ("Это локальное демо без реальных аккаунтов и платежей.\\n"
                  "/adddemo Название — создать запись\\n"
                  "/removedemo Номер — удалить запись\\n"
                  "/accounts — показать записи")
    elif raw == "➕ Добавить демо":
        answer = "Отправь: /adddemo Название (например, /adddemo Тест 1)"
    elif raw == "➖ Удалить демо":
        answer = "Отправь: /removedemo Номер (например, /removedemo 1)"
    elif command == "/adddemo":
        name = raw.partition(" ")[2].strip()
        if not name or len(name) > 60:
            answer = "Укажи название до 60 символов: /adddemo Название"
        elif len(DEMO_ACCOUNTS) >= 20:
            answer = "Достигнут лимит 20 тестовых записей."
        else:
            DEMO_ACCOUNTS.append(name)
            answer = "Добавлена тестовая запись №" + str(len(DEMO_ACCOUNTS)) + ": " + name
    elif command == "/removedemo":
        arg = raw.partition(" ")[2].strip()
        if not arg.isdigit() or not (1 <= int(arg) <= len(DEMO_ACCOUNTS)):
            answer = "Укажи номер существующей записи: /removedemo 1"
        else:
            name = DEMO_ACCOUNTS.pop(int(arg) - 1)
            answer = "Удалена тестовая запись: " + name
    else:
        answer = "Выбери действие в меню или отправь /help."
    reply(chat["id"], answer)

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

def register_webhook():
    if not TOKEN or not WEBHOOK_SECRET:
        return
    payload = json.dumps({
        "url": "https://telegram-safe-demo.onrender.com/telegram",
        "secret_token": WEBHOOK_SECRET,
        "allowed_updates": ["message"]
    }).encode()
    req = Request("https://api.telegram.org/bot" + TOKEN + "/setWebhook",
                  data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=12) as response:
            result = json.load(response)
        print("Webhook registration:", "success" if result.get("ok") else "failed", flush=True)
    except Exception as exc:
        print("Webhook registration failed:", type(exc).__name__, flush=True)

if __name__ == "__main__":
    register_webhook()
    port = int(os.environ.get("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
