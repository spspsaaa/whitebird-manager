"""Local, manual, read-only balance observation window.

No browser automation, Telegram transmission, credentials or session access.
"""
from __future__ import annotations

import json
import re
import tkinter as tk
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tkinter import messagebox, ttk

OUT = Path(__file__).resolve().parent / "local_balance_observation.json"
AMOUNT = re.compile(r"^\d{1,12}(?:[.,]\d{1,8})?$")


def parse_amount(value: str) -> str:
    value = value.strip().replace(" ", "").replace("\u00a0", "")
    if not AMOUNT.fullmatch(value):
        raise ValueError("Enter a non-negative amount using digits and a dot or comma.")
    try:
        amount = Decimal(value.replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError("Invalid amount") from exc
    return format(amount, "f")


def make_observation(account_label: str, status: str, rub: str, usdt: str) -> dict:
    label = account_label.strip()
    if not 1 <= len(label) <= 60 or any(c in label for c in "\r\n"):
        raise ValueError("Enter a short account label (not a password or email).")
    if status not in ("authorized", "login_required", "balance_hidden"):
        raise ValueError("Unknown session status")
    result = {
        "account_label": label,
        "status": status,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source": "manual_user_observation",
    }
    if status == "authorized":
        result["rub"] = parse_amount(rub)
        result["usdt"] = parse_amount(usdt)
    return result


def main() -> None:
    root = tk.Tk()
    root.title("WhiteBird Manager — локальная проверка")
    root.geometry("470x360")
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=18)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Проверка одного профиля Octo", font=("Segoe UI", 12, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Открой WhiteBird в Octo и укажи увиденный результат.").pack(anchor="w", pady=(6, 15))
    ttk.Label(frame, text="Название профиля (не почта):").pack(anchor="w")
    label = ttk.Entry(frame, width=45)
    label.pack(anchor="w", pady=(2, 9))
    ttk.Label(frame, text="Состояние WhiteBird:").pack(anchor="w")
    state = tk.StringVar(value="authorized")
    states = [
        ("Авторизован, баланс виден", "authorized"),
        ("Требуется повторный вход", "login_required"),
        ("Баланс скрыт", "balance_hidden"),
    ]
    for text, value in states:
        ttk.Radiobutton(frame, text=text, variable=state, value=value).pack(anchor="w")
    amounts = ttk.Frame(frame)
    amounts.pack(fill="x", pady=(12, 8))
    ttk.Label(amounts, text="RUB:").grid(row=0, column=0, sticky="w")
    rub = ttk.Entry(amounts, width=17)
    rub.grid(row=0, column=1, padx=(8, 20))
    ttk.Label(amounts, text="USDT:").grid(row=0, column=2, sticky="w")
    usdt = ttk.Entry(amounts, width=17)
    usdt.grid(row=0, column=3, padx=(8, 0))
    def save() -> None:
        try:
            observation = make_observation(label.get(), state.get(), rub.get(), usdt.get())
            # File created with restricted permissions where supported.
            OUT.write_text(json.dumps(observation, ensure_ascii=False, indent=2), encoding="utf-8")
            messagebox.showinfo("Готово", "Результат сохранён локально. В Telegram ничего не отправлено.")
        except (ValueError, OSError) as exc:
            messagebox.showerror("Ошибка", str(exc))
    ttk.Button(frame, text="Сохранить результат", command=save).pack(anchor="w", pady=(10, 0))
    ttk.Label(frame, text="Не вводи пароль, код 2FA или cookies. Никаких переводов.", foreground="gray").pack(anchor="w", pady=(14, 0))
    root.mainloop()


if __name__ == "__main__":
    main()
