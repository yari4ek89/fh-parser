# bot.py
import json
import time
import telebot
from parser import get_projects
from config import BOT_TOKEN, ADMIN_CHAT_ID
import html

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


def load_storage():
    try:
        with open("storage.json", "r") as f:
            return json.load(f)
    except:
        return {"last_ids": []}


def save_storage(data):
    with open("storage.json", "w") as f:
        json.dump(data, f, indent=4)


def format_project(p):
    desc = p["description"].replace("\n", " ").strip()
    if len(desc) > 300:
        desc = desc[:300] + "..."

    budget = p["budget"]
    if budget:
        budget_text = f"{budget.get('amount')} {budget.get('currency')}"
    else:
        budget_text = "Не вказано"

    text = (
        f"🔥 {p['name']}\n"
        f"💰 Бюджет: {budget_text}\n"
        f"📅 Дата: {p['published_at']}\n\n"
        f"{desc}\n\n"
        f"👉 {p['link']}"   # обычная ссылка, Telegram сам делает её кликабельной
    )

    return text

def check_new_projects():
    storage = load_storage()
    known = set(storage["last_ids"])

    projects = get_projects()
    new = []

    for p in projects:
        if p["id"] not in known:
            new.append(p)
            known.add(p["id"])

    storage["last_ids"] = list(known)
    save_storage(storage)

    return new


@bot.message_handler(commands=["start"])
def start(msg):
    bot.send_message(msg.chat.id, "Бот запущен. Отслеживаю новые заказы 🔍")


def loop():
    while True:
        new_projects = check_new_projects()

        if new_projects:
            for p in new_projects:
                bot.send_message(ADMIN_CHAT_ID, format_project(p))

        time.sleep(60)  # чекать каждые 60 секунд


if __name__ == "__main__":
    print("Бот запущен!")
    loop()
