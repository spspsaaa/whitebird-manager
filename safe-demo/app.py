import os
import json
import hmac
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.parse import urlparse

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OWNER = os.environ.get("TELEGRAM_OWNER_ID", "")
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")

DB_PATH = os.environ.get("DEMO_DB_PATH", "/tmp/telegram_demo.sqlite3")
LOCK = threading.RLock()
STATES = {}
KEYBOARD = {"keyboard": [[{"text": "📊 Статус"}, {"text": "📋 Демо-аккаунты"}],
                         [{"text": "➕ Добавить демо"}, {"text": "➖ Удалить демо"}],
                         [{"text": "❌ Отмена"}, {"text": "❓ Помощь"}]], "resize_keyboard": True}

def db():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.execute("CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")
    return connection

def accounts():
    with db() as connection:
        return connection.execute("SELECT id, name FROM accounts ORDER BY id").fetchall()

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
    chat_id = chat["id"]
    raw = (message.get("text") or "").strip()
    command = raw.split(" ", 1)[0].split("@", 1)[0]
    with LOCK:
        rows = accounts()
        if command == "/start":
            STATES.pop(chat_id, None)
            answer = "Бот запущен. Выбирай действие кнопками ниже."
        elif raw == "❌ Отмена" or command == "/cancel":
            STATES.pop(chat_id, None)
            answer = "Действие отменено."
        elif command == "/status" or raw == "📊 Статус":
            answer = "🟢 Сервер работает. Тестовых записей: " + str(len(rows))
        elif command == "/accounts" or raw == "📋 Демо-аккаунты":
            answer = ("Демо-аккаунтов пока нет." if not rows else
                      "Тестовые записи:\n" + "\n".join(str(id) + ". " + name for id, name in rows))
        elif command == "/help" or raw == "❓ Помощь":
            answer = ("Используй кнопки для создания и удаления тестовых записей.\n"
                      "Данные сохраняются в локальную SQLite-базу, но могут пропасть после перезапуска Render Free.\n"
                      "Реальные аккаунты и платежи не подключены.")
        elif raw == "➕ Добавить демо":
            STATES[chat_id] = "add"
            answer = "Напиши название новой тестовой записи (до 60 символов)."
        elif raw == "➖ Удалить демо":
            STATES[chat_id] = "delete"
            answer = ("Удалять пока нечего." if not rows else
                      "Отправь номер записи для удаления:\n" +
                      "\n".join(str(id) + ". " + name for id, name in rows))
            if not rows:
                STATES.pop(chat_id, None)
        elif STATES.get(chat_id) == "add" or command == "/adddemo":
            name = raw.partition(" ")[2].strip() if command == "/adddemo" else raw
            if not name or len(name) > 60 or name.startswith("/"):
                answer = "Название должно быть от 1 до 60 символов. Или нажми «Отмена»."
            elif len(rows) >= 20:
                STATES.pop(chat_id, None)
                answer = "Лимит — 20 тестовых записей."
            else:
                with db() as connection:
                    cursor = connection.execute("INSERT INTO accounts(name) VALUES (?)", (name,))
                    number = cursor.lastrowid
                STATES.pop(chat_id, None)
                answer = "Добавлена тестовая запись №" + str(number) + ": " + name
        elif STATES.get(chat_id) == "delete" or command == "/removedemo":
            arg = raw.partition(" ")[2].strip() if command == "/removedemo" else raw
            if not arg.isdigit() or int(arg) not in {id for id, _ in rows}:
                answer = "Отправь номер из списка или нажми «Отмена»."
            else:
                with db() as connection:
                    connection.execute("DELETE FROM accounts WHERE id = ?", (int(arg),))
                STATES.pop(chat_id, None)
                answer = "Тестовая запись №" + arg + " удалена."
        else:
            answer = "Выбери действие в меню."
    reply(chat_id, answer)

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
