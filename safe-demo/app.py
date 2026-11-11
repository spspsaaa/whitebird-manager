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
KEYBOARD = {"keyboard": [[{"text": "Вывод средств 💳"}, {"text": "Аккаунты 👥"}]], "resize_keyboard": True}

def db():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.execute("CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")
    return connection

def accounts():
    with db() as connection:
        return connection.execute("SELECT id, name FROM accounts ORDER BY id").fetchall()

def reply(chat_id, text, inline=None):
    payload = {"chat_id": chat_id, "text": text,
               "reply_markup": {"inline_keyboard": inline} if inline is not None else KEYBOARD}
    return telegram_api("sendMessage", payload)

def show(chat_id, text, buttons, message_id=None):
    payload = {"chat_id": chat_id, "text": text, "reply_markup": {"inline_keyboard": buttons}}
    if message_id is not None:
        payload["message_id"] = message_id
        try:
            return telegram_api("editMessageText", payload)
        except Exception:
            pass
    return telegram_api("sendMessage", payload)

def account_menu(chat_id, message_id=None):
    rows = accounts()
    buttons = [[{"text": "👤 " + name[:45], "callback_data": "acc:" + str(i)}] for i, name in rows]
    buttons.append([{"text": "➕ Добавить аккаунт", "callback_data": "add"}])
    text = "👥 АККАУНТЫ\\n\\n" + (str(len(rows)) + " тестовых записей. Выбери аккаунт:" if rows else "Пока нет аккаунтов.")
    show(chat_id, text, buttons, message_id)

def account_detail(chat_id, account_id, message_id=None):
    row = next(((i, n) for i, n in accounts() if i == account_id), None)
    if row is None:
        return account_menu(chat_id, message_id)
    show(chat_id, "👤 АККАУНТ №" + str(row[0]) + "\\nНазвание: " + row[1] + "\\nРежим: демонстрация",
         [[{"text": "✏️ Редактировать", "callback_data": "edit:" + str(account_id)},
           {"text": "🗑 Удалить", "callback_data": "delete:" + str(account_id)}],
          [{"text": "⬅️ К аккаунтам", "callback_data": "accounts"}]], message_id)

def withdrawal_menu(chat_id, message_id=None):
    show(chat_id, "💳 ВЫВОД СРЕДСТВ\\n\\nВыбери режим. Это только демонстрация, переводы не выполняются.",
         [[{"text": "👤 Одиночный", "callback_data": "withdraw:single"}],
          [{"text": "👥 Массовый", "callback_data": "withdraw:bulk"}]], message_id)

def handle_callback(callback):
    sender = callback.get("from") or {}
    message = callback.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not OWNER or str(sender.get("id", "")) != OWNER or chat_id is None:
        return
    telegram_api("answerCallbackQuery", {"callback_query_id": callback["id"]})
    data = callback.get("data", "")
    message_id = message.get("message_id")
    with LOCK:
        sync_from_telegram(chat_id)
        if data == "accounts":
            STATES.pop(chat_id, None)
            account_menu(chat_id, message_id)
        elif data == "withdraw":
            STATES.pop(chat_id, None)
            withdrawal_menu(chat_id, message_id)
        elif data in ("withdraw:single", "withdraw:bulk"):
            mode = "Одиночный" if data == "withdraw:single" else "Массовый"
            show(chat_id, "💳 " + mode + " вывод\\n\\nДемонстрационный экран. Реальные операции отключены.",
                 [[{"text": "⬅️ Назад", "callback_data": "withdraw"}]], message_id)
        elif data == "add":
            STATES[chat_id] = ("add", None)
            show(chat_id, "➕ НОВЫЙ АККАУНТ\\n\\nОтправь название обычным сообщением (до 60 символов).",
                 [[{"text": "⬅️ К аккаунтам", "callback_data": "accounts"}]], message_id)
        elif data.startswith("acc:") and data[4:].isdigit():
            STATES.pop(chat_id, None)
            account_detail(chat_id, int(data.split(":")[1]), message_id)
        elif data.startswith("edit:") and data[5:].isdigit():
            account_id = int(data.split(":")[1])
            if account_id not in {i for i, _ in accounts()}:
                account_menu(chat_id, message_id)
            else:
                STATES[chat_id] = ("edit", account_id)
                show(chat_id, "✏️ РЕДАКТИРОВАНИЕ\\n\\nОтправь новое название аккаунта.",
                     [[{"text": "⬅️ Назад", "callback_data": "acc:" + str(account_id)}]], message_id)
        elif data.startswith("delete:") and data[7:].isdigit():
            account_id = int(data.split(":")[1])
            show(chat_id, "Удалить тестовый аккаунт №" + str(account_id) + "?",
                 [[{"text": "🗑 Да, удалить", "callback_data": "confirm:" + str(account_id)}],
                  [{"text": "⬅️ Назад", "callback_data": "acc:" + str(account_id)}]], message_id)
        elif data.startswith("confirm:") and data[8:].isdigit():
            account_id = int(data.split(":")[1])
            with db() as connection:
                connection.execute("DELETE FROM accounts WHERE id=?", (account_id,))
            save_to_telegram(chat_id)
            STATES.pop(chat_id, None)
            account_menu(chat_id, message_id)

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
    if not text.startswith(BACKUP_PREFIX) and accounts():
        save_to_telegram(chat_id)
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
    if update.get("callback_query"):
        return handle_callback(update["callback_query"])
    message = update.get("message") or {}
    sender = message.get("from") or {}
    chat = message.get("chat") or {}
    if not OWNER or str(sender.get("id", "")) != OWNER or chat.get("id") is None:
        return
    chat_id = chat["id"]
    raw = (message.get("text") or "").strip()
    with LOCK:
        sync_from_telegram(chat_id)
        if raw == "/start":
            STATES.pop(chat_id, None)
            reply(chat_id, "Добро пожаловать! Выбери один из двух разделов ниже.")
        elif raw in ("Аккаунты 👥", "/accounts"):
            STATES.pop(chat_id, None)
            account_menu(chat_id)
        elif raw in ("Вывод средств 💳", "/withdraw"):
            STATES.pop(chat_id, None)
            withdrawal_menu(chat_id)
        elif isinstance(STATES.get(chat_id), tuple):
            action, account_id = STATES[chat_id]
            if not 1 <= len(raw) <= 60 or raw.startswith("/"):
                reply(chat_id, "Напиши название длиной от 1 до 60 символов.")
            elif action == "add":
                if len(accounts()) >= 20:
                    STATES.pop(chat_id, None)
                    reply(chat_id, "Достигнут лимит 20 тестовых аккаунтов.")
                else:
                    with db() as connection:
                        connection.execute("INSERT INTO accounts(name) VALUES (?)", (raw,))
                    save_to_telegram(chat_id)
                    STATES.pop(chat_id, None)
                    account_menu(chat_id)
            elif action == "edit":
                with db() as connection:
                    connection.execute("UPDATE accounts SET name=? WHERE id=?", (raw, account_id))
                save_to_telegram(chat_id)
                STATES.pop(chat_id, None)
                account_detail(chat_id, account_id)
        else:
            reply(chat_id, "Выбери «Аккаунты 👥» или «Вывод средств 💳» в нижнем меню.")

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
        "allowed_updates": ["message", "callback_query"]
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
