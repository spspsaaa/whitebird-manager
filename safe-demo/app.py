import os
import json
import hmac
import sqlite3
import threading
import time
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.parse import urlparse

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OWNER = os.environ.get("TELEGRAM_OWNER_ID", "")
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")

DB_PATH = os.environ.get("DEMO_DB_PATH", "/tmp/telegram_demo.sqlite3")
LOCK = threading.RLock()
DEMO_SEED_ENABLED = os.environ.get("DEMO_SEED_ENABLED", "false").lower() == "true"
DOLPHIN_ACCOUNT_IDS = frozenset(int(x.strip()) for x in os.environ.get("DOLPHIN_ACCOUNT_IDS", "").split(",") if x.strip().isdigit())

STATES = {}
KEYBOARD = {"keyboard": [[{"text": "Вывод средств 💳"}, {"text": "Аккаунты 👥"}], [{"text": "Запросить балансы 💰"}]], "resize_keyboard": True}

def db():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.execute("CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")
    connection.execute("CREATE TABLE IF NOT EXISTS processed_updates (update_id INTEGER PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP, status TEXT NOT NULL DEFAULT 'done', claimed_at INTEGER NOT NULL DEFAULT 0)")
    columns = {row[1] for row in connection.execute("PRAGMA table_info(processed_updates)")}
    if "status" not in columns:
        connection.execute("ALTER TABLE processed_updates ADD COLUMN status TEXT NOT NULL DEFAULT 'done'")
    if "claimed_at" not in columns:
        connection.execute("ALTER TABLE processed_updates ADD COLUMN claimed_at INTEGER NOT NULL DEFAULT 0")
    connection.execute("CREATE TABLE IF NOT EXISTS browser_profiles (account_id INTEGER PRIMARY KEY, browser TEXT NOT NULL, profile_id TEXT NOT NULL, UNIQUE(browser,profile_id))")
    connection.execute("CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, action TEXT NOT NULL, account_id INTEGER)")
    return connection

def accounts():
    with db() as connection:
        return connection.execute("SELECT id, name FROM accounts ORDER BY id").fetchall()

def profile(account_id):
    with db() as connection:
        return connection.execute("SELECT browser, profile_id FROM browser_profiles WHERE account_id=?", (account_id,)).fetchone()

def bind_profile(account_id, browser, profile_id):
    if browser not in ("dolphin", "octo") or not isinstance(profile_id, str) or not 1 <= len(profile_id.strip()) <= 120:
        raise ValueError("Invalid profile")
    profile_id = profile_id.strip()
    if DOLPHIN_ACCOUNT_IDS and ((account_id in DOLPHIN_ACCOUNT_IDS) != (browser == "dolphin")):
        raise ValueError("Browser assignment is locked")
    with LOCK, db() as connection:
        if connection.execute("SELECT 1 FROM accounts WHERE id=?", (account_id,)).fetchone() is None:
            raise ValueError("Unknown account")
        existing = connection.execute("SELECT browser,profile_id FROM browser_profiles WHERE account_id=?", (account_id,)).fetchone()
        if existing and existing[0] != browser:
            raise ValueError("Browser change requires migration")
        if browser == "dolphin":
            count = connection.execute("SELECT COUNT(*) FROM browser_profiles WHERE browser='dolphin' AND account_id != ?", (account_id,)).fetchone()[0]
            if count >= 4:
                raise ValueError("Dolphin limit")
        connection.execute("INSERT INTO browser_profiles(account_id,browser,profile_id) VALUES(?,?,?) ON CONFLICT(account_id) DO UPDATE SET browser=excluded.browser,profile_id=excluded.profile_id", (account_id,browser,profile_id))

def readiness_report(chat_id):
    rows = accounts()
    with db() as connection:
        links = dict((account_id, (browser, pid)) for account_id, browser, pid in connection.execute("SELECT account_id,browser,profile_id FROM browser_profiles"))
    missing = [(i, name) for i, name in rows if i not in links]
    dolphin = sum(1 for browser, _ in links.values() if browser == "dolphin")
    octo = sum(1 for browser, _ in links.values() if browser == "octo")
    lines = ["🧰 ДИАГНОСТИКА ПРОФИЛЕЙ", "", "Аккаунтов: " + str(len(rows)),
             "Привязано: " + str(len(rows) - len(missing)),
             "Dolphin: " + str(dolphin) + "/4", "Octo: " + str(octo),
             "Без привязки: " + str(len(missing)), "",
             "Браузеры на сервере не подключены. Балансы тестовые."]
    if missing:
        lines += ["", "Не привязаны (первые 20):"]
        lines += [str(i) + ". " + name[:40] for i, name in missing[:20]]
    reply(chat_id, "\n".join(lines))

def export_profiles(chat_id):
    """Plain-text, non-secret inventory, split to fit Telegram message limits."""
    rows = accounts()
    with db() as connection:
        links = dict((i, (b, p)) for i, b, p in connection.execute("SELECT account_id,browser,profile_id FROM browser_profiles"))
    chunks = ["📄 ЭКСПОРТ ПРОФИЛЕЙ (без паролей и 2FA)\n\n"]
    for i, name in rows:
        browser, pid = links.get(i, ("не привязан", "—"))
        line = str(i) + " | " + name.replace("\n", " ") + " | " + browser + " | " + pid + "\n"
        if len(chunks[-1]) + len(line) > 3500:
            chunks.append("📄 ЭКСПОРТ (продолжение)\n\n")
        chunks[-1] += line
    for chunk in chunks:
        reply(chat_id, chunk)

def audit_event(action, account_id=None):
    with db() as connection:
        connection.execute("INSERT INTO audit_log(action,account_id) VALUES (?,?)", (action, account_id))
        connection.execute("DELETE FROM audit_log WHERE id NOT IN (SELECT id FROM audit_log ORDER BY id DESC LIMIT 500)")

def audit_report(chat_id):
    with db() as connection:
        rows = connection.execute("SELECT created_at,action,account_id FROM audit_log ORDER BY id DESC LIMIT 15").fetchall()
    lines = ["📋 ЖУРНАЛ ДЕЙСТВИЙ", "", "Последние 15 событий:"]
    lines += [str(t) + " · " + action + ((" · #" + str(i)) if i is not None else "") for t,action,i in rows]
    reply(chat_id, "\n".join(lines) if rows else "📋 Журнал пока пуст.")

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

def account_menu(chat_id, message_id=None, page=0):
    rows = accounts()
    per_page = 10
    pages = max(1, (len(rows) + per_page - 1) // per_page)
    page = max(0, min(page, pages - 1))
    start = page * per_page
    visible = rows[start:start + per_page]
    buttons = []
    for offset in range(0, len(visible), 2):
        buttons.append([{"text": "👤 " + name[:19], "callback_data": "acc:" + str(i)} for i, name in visible[offset:offset + 2]])
    if pages > 1:
        nav = []
        if page > 0:
            nav.append({"text": "◀️", "callback_data": "page:" + str(page - 1)})
        nav.append({"text": str(page + 1) + "/" + str(pages), "callback_data": "page:" + str(page)})
        if page + 1 < pages:
            nav.append({"text": "▶️", "callback_data": "page:" + str(page + 1)})
        buttons.append(nav)
    buttons.append([{"text": "➕ Добавить аккаунт", "callback_data": "add"}])
    text = "👥 АККАУНТЫ\n\n" + (str(len(rows)) + " тестовых записей · страница " + str(page + 1) + "/" + str(pages) if rows else "Пока нет аккаунтов.")
    show(chat_id, text, buttons, message_id)

def demo_balances(account_id):
    """Read-only, deterministic fictional amounts. No external financial access."""
    rub = ((account_id * 13679 + 401) % 900000) / 100
    usdt = ((account_id * 7919 + 137) % 125000) / 100
    return rub, usdt

def balances_report(chat_id):
    rows = accounts()
    if not rows:
        return reply(chat_id, "💰 ДЕМО-БАЛАНСЫ\n\nАккаунтов пока нет.")
    total_rub = sum(demo_balances(i)[0] for i, _ in rows)
    total_usdt = sum(demo_balances(i)[1] for i, _ in rows)
    header = "💰 ДЕМО-БАЛАНСЫ — НЕ РЕАЛЬНЫЕ СРЕДСТВА\n\n"
    footer = ("\nАккаунтов: " + str(len(rows)) + "\nИтого RUB: " +
              f"{total_rub:,.2f}" + " ₽\nИтого USDT: " + f"{total_usdt:,.2f}" + " USDT")
    lines = [f"{index:02d}. {name[:24]}\n   {demo_balances(i)[0]:,.2f} ₽ | {demo_balances(i)[1]:,.2f} USDT"
             for index, (i, name) in enumerate(rows, 1)]
    chunk = header
    for line in lines:
        if len(chunk) + len(line) + len(footer) + 2 > 3500:
            reply(chat_id, chunk.rstrip())
            chunk = "💰 ДЕМО-БАЛАНСЫ (продолжение)\n\n"
        chunk += line + "\n"
    reply(chat_id, chunk + footer)

def withdrawal_account_menu(chat_id, message_id=None, page=0):
    rows = accounts()
    if not rows:
        return show(chat_id, "Нет тестовых аккаунтов.", [[{"text": "⬅️ Назад", "callback_data": "withdraw"}]], message_id)
    pages = max(1, (len(rows) + 9) // 10)
    page = max(0, min(page, pages - 1))
    visible = rows[page * 10:(page + 1) * 10]
    buttons = []
    for offset in range(0, len(visible), 2):
        buttons.append([{"text": "👤 " + name[:18], "callback_data": "wacc:" + str(i)}
                        for i, name in visible[offset:offset + 2]])
    if pages > 1:
        nav = []
        if page > 0:
            nav.append({"text": "◀️", "callback_data": "wpage:" + str(page - 1)})
        nav.append({"text": str(page + 1) + "/" + str(pages), "callback_data": "wpage:" + str(page)})
        if page + 1 < pages:
            nav.append({"text": "▶️", "callback_data": "wpage:" + str(page + 1)})
        buttons.append(nav)
    buttons.append([{"text": "⬅️ Назад", "callback_data": "withdraw"}])
    show(chat_id, "💳 ДЕМО-ВЫВОД\n\nВыбери тестовый аккаунт:", buttons, message_id)

def withdrawal_preview(chat_id, account_id, message_id=None):
    row = next(((i, name) for i, name in accounts() if i == account_id), None)
    if row is None:
        return withdrawal_account_menu(chat_id, message_id)
    STATES[chat_id] = ("draft_currency", account_id)
    show(chat_id, "💳 ЗАЯВКА НА ВЫВОД — ЧЕРНОВИК\\n\\nАккаунт: " + row[1] +
         "\\nВыбери валюту. Реальные операции отключены.",
         [[{"text": "RUB.wb", "callback_data": "draft:rub:" + str(account_id)},
           {"text": "USDT", "callback_data": "draft:usdt:" + str(account_id)}],
          [{"text": "⬅️ Назад", "callback_data": "withdraw:single"}]], message_id)


def account_detail(chat_id, account_id, message_id=None):
    row = next(((i, n) for i, n in accounts() if i == account_id), None)
    if row is None:
        return account_menu(chat_id, message_id)
    linked = profile(account_id)
    browser_label = (("Dolphin Anty" if linked[0] == "dolphin" else "Octo Browser") + " / " + linked[1]) if linked else "Не привязан"
    show(chat_id, "👤 АККАУНТ №" + str(row[0]) + "\nНазвание: " + row[1] + "\nБраузер: " + browser_label + "\nРежим: демонстрация",
         [[{"text": "🐬 Dolphin", "callback_data": "browser:dolphin:" + str(account_id)}, {"text": "🐙 Octo", "callback_data": "browser:octo:" + str(account_id)}],
          [{"text": "✏️ Редактировать", "callback_data": "edit:" + str(account_id)},
           {"text": "🗑 Удалить", "callback_data": "delete:" + str(account_id)}],
          [{"text": "⬅️ К аккаунтам", "callback_data": "accounts"}]], message_id)

def withdrawal_menu(chat_id, message_id=None):
    show(chat_id, "💳 ВЫВОД СРЕДСТВ\n\nВыбери режим. Это только демонстрация, переводы не выполняются.",
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
        elif data.startswith("page:") and data[5:].isdigit():
            STATES.pop(chat_id, None)
            account_menu(chat_id, message_id, int(data[5:]))
        elif data == "withdraw":
            STATES.pop(chat_id, None)
            withdrawal_menu(chat_id, message_id)
        elif data == "withdraw:single":
            STATES.pop(chat_id, None)
            withdrawal_account_menu(chat_id, message_id)
        elif data.startswith("wpage:") and data[6:].isdigit():
            withdrawal_account_menu(chat_id, message_id, int(data[6:]))
        elif data.startswith("wacc:") and data[5:].isdigit():
            withdrawal_preview(chat_id, int(data[5:]), message_id)
        elif data.startswith("draft:"):
            parts = data.split(":")
            if len(parts) == 3 and parts[1] in ("rub", "usdt") and parts[2].isdigit():
                account_id = int(parts[2])
                if account_id in {i for i, _ in accounts()}:
                    currency = "RUB.wb" if parts[1] == "rub" else "USDT"
                    STATES[chat_id] = ("draft_amount:" + currency, account_id)
                    show(chat_id, "Введи сумму " + currency + " для черновика заявки.\\nРеальные переводы отключены.",
                         [[{"text": "⬅️ Назад", "callback_data": "wacc:" + str(account_id)}]], message_id)
        elif data == "withdraw:bulk":
            show(chat_id, "💳 МАССОВЫЙ ДЕМО-ВЫВОД\n\nТестовый сценарий. Реальные переводы отключены.",
                 [[{"text": "⬅️ Назад", "callback_data": "withdraw"}]], message_id)
        elif data.startswith("browser:"):
            parts = data.split(":")
            if len(parts) == 3 and parts[1] in ("dolphin", "octo") and parts[2].isdigit():
                account_id = int(parts[2])
                if account_id in {i for i, _ in accounts()}:
                    STATES[chat_id] = ("profile:" + parts[1], account_id)
                    show(chat_id, "Отправь ID профиля браузера. Не присылай пароли и 2FA.",
                         [[{"text": "⬅️ Назад", "callback_data": "acc:" + str(account_id)}]], message_id)
        elif data == "add":
            STATES[chat_id] = ("add", None)
            show(chat_id, "➕ НОВЫЙ АККАУНТ\n\nОтправь название обычным сообщением (до 60 символов).",
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
                show(chat_id, "✏️ РЕДАКТИРОВАНИЕ\n\nОтправь новое название аккаунта.",
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
                connection.execute("DELETE FROM browser_profiles WHERE account_id=?", (account_id,))
            audit_event("account_deleted", account_id)
            save_to_telegram(chat_id)
            STATES.pop(chat_id, None)
            account_menu(chat_id, message_id)

BACKUP_PREFIX = "DEMO_BACKUP_V1:"
SEED_DONE = set()
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
        profiles_snapshot = snapshot.get("profiles", []) if isinstance(snapshot, dict) else []
        if isinstance(snapshot, dict):
            if snapshot.get("seeded"):
                SEED_DONE.add(chat_id)
            snapshot = snapshot.get("accounts", [])
        if not isinstance(snapshot, list) or len(snapshot) > 100:
            raise ValueError("Invalid backup")
        restored = []
        for entry in snapshot:
            if not isinstance(entry, list) or len(entry) != 2 or not isinstance(entry[0], int) or not isinstance(entry[1], str) or len(entry[1]) > 60:
                raise ValueError("Invalid backup entry")
            restored.append(entry)
        with db() as connection:
            connection.execute("DELETE FROM browser_profiles")
            connection.execute("DELETE FROM accounts")
            connection.executemany("INSERT INTO accounts(id, name) VALUES (?, ?)", restored)
            if isinstance(profiles_snapshot, list) and len(profiles_snapshot) <= 100:
                for entry in profiles_snapshot:
                    if (isinstance(entry, list) and len(entry) == 3 and isinstance(entry[0], int)
                        and entry[1] in ("dolphin", "octo") and isinstance(entry[2], str)
                        and 1 <= len(entry[2]) <= 120):
                        connection.execute("INSERT OR IGNORE INTO browser_profiles(account_id,browser,profile_id) VALUES(?,?,?)", tuple(entry))
    SYNCED_CHATS.add(chat_id)
    if DEMO_SEED_ENABLED and chat_id not in SEED_DONE:
        existing = accounts()
        missing = max(0, 40 - len(existing))
        if missing:
            with db() as connection:
                connection.executemany("INSERT INTO accounts(name) VALUES (?)",
                    [("Демо-аккаунт " + str(n).zfill(2),) for n in range(1, missing + 1)])
        SEED_DONE.add(chat_id)
        save_to_telegram(chat_id)
    elif not text.startswith(BACKUP_PREFIX) and accounts():
        save_to_telegram(chat_id)

def save_to_telegram(chat_id):
    with db() as connection:
        profiles = [list(row) for row in connection.execute("SELECT account_id,browser,profile_id FROM browser_profiles ORDER BY account_id")]
    content = BACKUP_PREFIX + json.dumps({"seeded": True, "accounts": [[i, n] for i, n in accounts()], "profiles": profiles}, ensure_ascii=False, separators=(",", ":"))
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
    update_id = update.get("update_id")
    with LOCK:
        if isinstance(update_id, int) and update_id >= 0:
            now = int(time.time())
            with db() as connection:
                seen = connection.execute("SELECT status,claimed_at FROM processed_updates WHERE update_id=?", (update_id,)).fetchone()
                if seen and (seen[0] == "done" or (seen[0] == "processing" and now - seen[1] < 120)):
                    return
                connection.execute("INSERT INTO processed_updates(update_id,status,claimed_at) VALUES (?,'processing',?) ON CONFLICT(update_id) DO UPDATE SET status='processing',claimed_at=excluded.claimed_at", (update_id, now))
        try:
            _dispatch_update(update)
        except Exception:
            if isinstance(update_id, int) and update_id >= 0:
                with db() as connection:
                    connection.execute("DELETE FROM processed_updates WHERE update_id=? AND status='processing'", (update_id,))
            raise
        else:
            if isinstance(update_id, int) and update_id >= 0:
                with db() as connection:
                    connection.execute("UPDATE processed_updates SET status='done' WHERE update_id=?", (update_id,))
                    connection.execute("DELETE FROM processed_updates WHERE status='done' AND update_id NOT IN (SELECT update_id FROM processed_updates WHERE status='done' ORDER BY update_id DESC LIMIT 1000)")

def _dispatch_update(update):
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
        if raw in ("/status", "/help"):
            STATES.pop(chat_id, None)
            count = len(accounts())
            with db() as connection:
                linked = dict(connection.execute("SELECT browser, COUNT(*) FROM browser_profiles GROUP BY browser").fetchall())
            reply(chat_id, "🟢 БОТ РАБОТАЕТ\n\nАккаунтов: " + str(count) +
                  "\nDolphin: " + str(linked.get("dolphin", 0)) + "/4" +
                  "\nOcto: " + str(linked.get("octo", 0)) +
                  "\nРежим: демонстрация\nRUB/USDT: тестовые данные\nРеальные переводы отключены")
        elif raw == "/start":
            STATES.pop(chat_id, None)
            reply(chat_id, "Добро пожаловать! Выбери раздел ниже.")
        elif raw == "/diagnostics":
            STATES.pop(chat_id, None)
            readiness_report(chat_id)
        elif raw == "/export":
            STATES.pop(chat_id, None)
            export_profiles(chat_id)
        elif raw == "/journal":
            STATES.pop(chat_id, None)
            audit_report(chat_id)
        elif raw in ("Аккаунты 👥", "/accounts"):
            STATES.pop(chat_id, None)
            account_menu(chat_id)
        elif raw in ("Запросить балансы 💰", "/balances"):
            STATES.pop(chat_id, None)
            balances_report(chat_id)
        elif raw in ("Вывод средств 💳", "/withdraw"):
            STATES.pop(chat_id, None)
            withdrawal_menu(chat_id)
        elif isinstance(STATES.get(chat_id), tuple):
            action, account_id = STATES[chat_id]
            if action.startswith("draft_amount:"):
                currency = action.split(":", 1)[1]
                normalized = raw.replace(",", ".")
                if not re.fullmatch(r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,8})?", normalized) or not 0 < float(normalized) <= 1000000000000:
                    return reply(chat_id, "Введи положительную сумму числом, например 100 или 0.5.")
                STATES[chat_id] = ("draft_recipient:" + currency + ":" + normalized, account_id)
                return reply(chat_id, "Введи обозначение получателя для черновика (без паролей, кодов и секретов).")
            if action.startswith("draft_recipient:"):
                if not 1 <= len(raw) <= 120 or raw.startswith("/"):
                    return reply(chat_id, "Обозначение получателя — от 1 до 120 символов.")
                _, currency, amount = action.split(":", 2)
                row = next(((i, n) for i, n in accounts() if i == account_id), None)
                STATES.pop(chat_id, None)
                if row is None:
                    return reply(chat_id, "Аккаунт больше не найден.")
                audit_event("withdrawal_draft_prepared", account_id)
                return reply(chat_id, "📋 ЧЕРНОВИК ЗАЯВКИ\n\nАккаунт: " + row[1] +
                             "\nВалюта: " + currency + "\nСумма: " + amount +
                             "\nПолучатель: " + raw +
                             "\n\nЭто только предварительный просмотр. Комиссия и доступный баланс не проверены. " +
                             "Кнопки подтверждения и отправки денег нет.")
            limit = 120 if action.startswith("profile:") else 60
            if not 1 <= len(raw) <= limit or raw.startswith("/"):
                reply(chat_id, "Недопустимый ввод. Название — до 60 символов, ID профиля — до 120.")
            elif action == "add":
                if len(accounts()) >= 100:
                    STATES.pop(chat_id, None)
                    reply(chat_id, "Достигнут лимит 100 тестовых аккаунтов.")
                else:
                    with db() as connection:
                        connection.execute("INSERT INTO accounts(name) VALUES (?)", (raw,))
                    save_to_telegram(chat_id)
                    audit_event("account_added")
                    STATES.pop(chat_id, None)
                    account_menu(chat_id)
            elif action.startswith("profile:"):
                try:
                    bind_profile(account_id, action.split(":")[1], raw)
                except (ValueError, sqlite3.IntegrityError):
                    return reply(chat_id, "Ошибка привязки: Dolphin — максимум 4 профиля, ID должен быть уникальным.")
                STATES.pop(chat_id, None)
                audit_event("profile_bound", account_id)
                save_to_telegram(chat_id)
                account_detail(chat_id, account_id)
            elif action == "edit":
                with db() as connection:
                    connection.execute("UPDATE accounts SET name=? WHERE id=?", (raw, account_id))
                save_to_telegram(chat_id)
                audit_event("account_renamed", account_id)
                STATES.pop(chat_id, None)
                account_detail(chat_id, account_id)
        else:
            reply(chat_id, "Выбери раздел в нижнем меню: аккаунты, вывод или балансы.")

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

def validate_config():
    if not TOKEN or not re.fullmatch(r"[0-9]{6,15}:[A-Za-z0-9_-]{20,}", TOKEN):
        raise RuntimeError("Invalid TELEGRAM_BOT_TOKEN")
    if not OWNER.isdigit() or int(OWNER) <= 0:
        raise RuntimeError("Invalid TELEGRAM_OWNER_ID")
    if not WEBHOOK_SECRET or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", WEBHOOK_SECRET):
        raise RuntimeError("Invalid TELEGRAM_WEBHOOK_SECRET")
    if len(DOLPHIN_ACCOUNT_IDS) not in (0, 4):
        raise RuntimeError("DOLPHIN_ACCOUNT_IDS must contain exactly four IDs when configured")
    if DEMO_SEED_ENABLED and os.environ.get("ALLOW_DEMO_SEED_IN_PRODUCTION") != "true":
        raise RuntimeError("Demo seeding requires explicit authorization")

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
    validate_config()
    register_webhook()
    port = int(os.environ.get("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
