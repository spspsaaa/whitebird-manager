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
KEYBOARD = {"keyboard": [
    [{"text": "📊 Статус"}, {"text": "📋 Демо-аккаунты"}],
    [{"text": "➕ Добавить демо"}, {"text": "➖ Удалить демо"}],
    [{"text": "✏️ Переименовать"}, {"text": "🔎 Поиск"}],
    [{"text": "📤 Экспорт"}, {"text": "🗑 Очистить список"}],
    [{"text": "❓ Помощь"}]
], "resize_keyboard": True}

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

BACKUP_PREFIX = "DEMO_BACKUP_V1:"
SYNCED_CHATS = set()

def telegram_api(method, data):
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    request = Request("https://api.telegram.org/bot" + TOKEN + "/" + method,
                      data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=10) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError("Telegram API rejected " + method)
    return result["result"]

def sync_from_telegram(chat_id):
    if chat_id in SYNCED_CHATS:
        return
    chat_info = telegram_api("getChat", {"chat_id": chat_id})
    pinned = chat_info.get("pinned_message") or {}
    text = pinned.get("text", "")
    if text.startswith(BACKUP_PREFIX):
        snapshot = json.loads(text[len(BACKUP_PREFIX):])
        if not isinstance(snapshot, list) or len(snapshot) > 20:
            raise ValueError("Invalid backup")
        restored = []
        for entry in snapshot:
            if not isinstance(entry, list) or len(entry) != 2 or not isinstance(entry[0], int) or not isinstance(entry[1], str) or len(entry[1]) > 60:
                raise ValueError("Invalid backup entry")
            restored.append(entry)
        with db() as connection:
            connection.execute("DELETE FROM accounts")
            connection.executemany("INSERT INTO accounts(id, name) VALUES (?, ?)", restored)
    SYNCED_CHATS.add(chat_id)

def save_to_telegram(chat_id):
    content = BACKUP_PREFIX + json.dumps([[i, n] for i, n in accounts()], ensure_ascii=False, separators=(",", ":"))
    chat_info = telegram_api("getChat", {"chat_id": chat_id})
    pinned = chat_info.get("pinned_message") or {}
    if (pinned.get("text") or "").startswith(BACKUP_PREFIX):
        try:
            telegram_api("editMessageText", {"chat_id": chat_id, "message_id": pinned["message_id"], "text": content})
            return
        except Exception:
            pass
    sent = telegram_api("sendMessage", {"chat_id": chat_id, "text": content, "disable_notification": True})
    telegram_api("pinChatMessage", {"chat_id": chat_id, "message_id": sent["message_id"], "disable_notification": True})

def handle_update(update):
    message = update.get("message") or {}
    sender = message.get("from") or {}
    chat = message.get("chat") or {}
    if not OWNER or str(sender.get("id", "")) != OWNER or chat.get("id") is None:
        return
    chat_id = chat["id"]
    raw = (message.get("text") or "").strip()
    command = raw.split(" ", 1)[0].split("@", 1)[0]
    buttons = {
        "➕ Добавить демо": ("add", "Напиши название новой тестовой записи (до 60 символов)."),
        "➖ Удалить демо": ("delete", "Напиши номер записи для удаления."),
        "✏️ Переименовать": ("rename_id", "Напиши номер записи для переименования."),
        "🔎 Поиск": ("search", "Напиши часть названия для поиска."),
        "🗑 Очистить список": ("clear", "Для подтверждения напиши ОЧИСТИТЬ. Любое другое сообщение отменит очистку."),
    }
    with LOCK:
        sync_from_telegram(chat_id)
        rows = accounts()
        changed = False
        ids = {id for id, _ in rows}
        state = STATES.get(chat_id)
        if command == "/start":
            STATES.pop(chat_id, None)
            answer = "Демо-бот готов. Все действия доступны через меню."
        elif command == "/status" or raw == "📊 Статус":
            STATES.pop(chat_id, None)
            answer = "🟢 Сервер работает. Тестовых записей: " + str(len(rows)) + "/20."
        elif command == "/accounts" or raw == "📋 Демо-аккаунты":
            STATES.pop(chat_id, None)
            answer = "Тестовых записей нет." if not rows else "Тестовые записи:\n" + "\\n".join(str(i) + ". " + n for i, n in rows)
        elif command == "/help" or raw == "❓ Помощь":
            STATES.pop(chat_id, None)
            answer = ("Создавай, удаляй, переименовывай и ищи тестовые записи кнопками.\n"
                      "Экспорт выдаёт текстовый список для копирования.\n"
                      "Данные в SQLite на Render Free могут пропасть при перезапуске или развёртывании.\n"
                      "Никаких реальных аккаунтов или финансовых операций.")
        elif raw == "📤 Экспорт":
            STATES.pop(chat_id, None)
            answer = ("Список пуст." if not rows else
                      "Экспорт тестовых записей (ID;Название):\n" +
                      "\\n".join(str(i) + ";" + n.replace(";", ",").replace("\n", " ") for i, n in rows))
        elif raw in buttons:
            new_state, answer = buttons[raw]
            if not rows and new_state in ("delete", "rename_id", "clear"):
                STATES.pop(chat_id, None)
                answer = "Список пуст — сначала добавь запись."
            else:
                STATES[chat_id] = new_state
                if new_state in ("delete", "rename_id"):
                    answer += "\n" + "\\n".join(str(i) + ". " + n for i, n in rows)
        elif command == "/adddemo" or state == "add":
            name = raw.partition(" ")[2].strip() if command == "/adddemo" else raw
            if not 1 <= len(name) <= 60 or name.startswith("/"):
                answer = "Напиши название от 1 до 60 символов."
            elif len(rows) >= 20:
                STATES.pop(chat_id, None)
                answer = "Лимит — 20 записей."
            else:
                with db() as connection:
                    number = connection.execute("INSERT INTO accounts(name) VALUES (?)", (name,)).lastrowid
                changed = True
                STATES.pop(chat_id, None)
                answer = "Добавлена тестовая запись №" + str(number) + ": " + name
        elif command == "/removedemo" or state == "delete":
            value = raw.partition(" ")[2].strip() if command == "/removedemo" else raw
            if not value.isdigit() or int(value) not in ids:
                answer = "Напиши номер существующей записи."
            else:
                with db() as connection:
                    connection.execute("DELETE FROM accounts WHERE id=?", (int(value),))
                changed = True
                STATES.pop(chat_id, None)
                answer = "Тестовая запись №" + value + " удалена."
        elif state == "rename_id":
            if not raw.isdigit() or int(raw) not in ids:
                answer = "Напиши номер существующей записи."
            else:
                STATES[chat_id] = ("rename_name", int(raw))
                answer = "Напиши новое название (до 60 символов)."
        elif isinstance(state, tuple) and state[0] == "rename_name":
            if not 1 <= len(raw) <= 60 or raw.startswith("/"):
                answer = "Напиши название от 1 до 60 символов."
            else:
                with db() as connection:
                    connection.execute("UPDATE accounts SET name=? WHERE id=?", (raw, state[1]))
                changed = True
                STATES.pop(chat_id, None)
                answer = "Запись №" + str(state[1]) + " переименована: " + raw
        elif state == "search":
            STATES.pop(chat_id, None)
            matches = [(i, n) for i, n in rows if raw.casefold() in n.casefold()]
            answer = ("Ничего не найдено." if not matches else
                      "Результаты поиска:\n" + "\\n".join(str(i) + ". " + n for i, n in matches))
        elif state == "clear":
            STATES.pop(chat_id, None)
            if raw == "ОЧИСТИТЬ":
                with db() as connection:
                    connection.execute("DELETE FROM accounts")
                changed = True
                answer = "Все тестовые записи удалены."
            else:
                answer = "Очистка отменена."
        else:
            answer = "Выбери действие в меню."
        if changed:
            save_to_telegram(chat_id)
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
