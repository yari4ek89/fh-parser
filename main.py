import asyncio
import logging
import httpx
from fastapi import FastAPI
from aiogram import Bot
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FH_API_TOKEN = os.getenv("FH_API_TOKEN")

PORTFOLIO_URL = "https://github.com/yari4ek89"

# ФИКС: Добавлен фильтр категории [category_id]=1, чтобы слать только программирование
API_URL = "https://api.freelancehunt.com/v2/projects?filter[category_id]=1"
HEADERS = {
    "Authorization": f"Bearer {FH_API_TOKEN}",
    "Accept-Language": "uk"
}

app = FastAPI()
bot = Bot(token=TELEGRAM_TOKEN)
ai_client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

processed_tasks = set()
logging.basicConfig(level=logging.INFO)

@app.get("/")
async def root():
    return {"status": "Бот активен и ловит заказы"}

async def generate_groq_cover_letter(task_title: str, task_description: str) -> str:
    system_prompt = (
        "Ты — уверенный и опытный Python/FastAPI веб-разработчик по имени Ярослав. "
        "Твоя задача — написать короткий отклик на фриланс-заказ.\n"
        "ПРАВИЛА:\n"
        "1. Пиши строго на языке заказа.\n"
        "2. Будь лаконичен (3-4 предложения), без воды.\n"
        "3. Предложи техническое решение, упомяни стек Python/FastAPI.\n"
        "4. В конце укажи ссылку на портфолио: {portfolio}."
    ).format(portfolio=PORTFOLIO_URL)

    clean_description = task_description.replace("<p>", "").replace("</p>", "").replace("<br>", "\n")

    try:
        response = await ai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Заказ: {task_title}\nОписание: {clean_description}"}
            ],
            temperature=0.5
        )
        reply = response.choices[0].message.content
        # Экранируем символы HTML, чтобы не ломать parse_mode="HTML"
        return reply.replace("<", "&lt;").replace(">", "&gt;")
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        return "Привет! Готов обсудить детали проекта в ЛС. Опыт работы с бэкендом и API есть, сделаю всё быстро и качественно."

async def check_freelancehunt_api():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(API_URL, headers=HEADERS)
            if response.status_code != 200:
                logging.error(f"Ошибка Freelancehunt API: {response.status_code}")
                return
            
            projects = response.json().get("data", [])
            for project in reversed(projects):
                status_id = project.get("attributes", {}).get("status", {}).get("id")
                if status_id != 11:
                    continue
                
                project_id = project.get("id")
                if project_id in processed_tasks:
                    continue
                
                if not processed_tasks:
                    processed_tasks.add(project_id)
                    continue

                processed_tasks.add(project_id)
                
                attributes = project.get("attributes", {})
                title = attributes.get("name")
                description = attributes.get("description_html", "")
                
                # ФИКС: В Freelancehunt API v2 прямая ссылка лежит прямо в project["links"]["html"]
                link = project.get("links", {}).get("html", "")
                
                # Защитная проверка ссылки
                if not link or link == "None":
                    link = f"https://freelancehunt.com/project/{project_id}.html"
                
                budget_data = attributes.get("budget")
                budget = f"{budget_data['amount']} {budget_data['currency']}" if budget_data else "Договорной"
                
                cover_letter = await generate_groq_cover_letter(title, description)
                
                # Формируем сообщение через чистый HTML
                message_text = (
                    f"🟢 <b>Новый заказ на Freelancehunt!</b>\n"
                    f"📌 <b>{title}</b>\n"
                    f"💰 <b>Бюджет:</b> {budget}\n\n"
                    f"🤖 <b>Отклик от Groq:</b>\n"
                    f"<pre>{cover_letter}</pre>\n\n"
                    f"🔗 <a href='{link}'>ОТКРЫТЬ И ОТПРАВИТЬ</a>"
                )
                
                await bot.send_message(
                    chat_id=CHAT_ID, 
                    text=message_text, 
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                await asyncio.sleep(1)
        except Exception as e:
            logging.error(f"Ошибка парсинга: {e}")

async def monitor_loop():
    print("Фоновый мониторинг запущен...")
    while True:
        await check_freelancehunt_api()
        await asyncio.sleep(60)

# Используем современный способ управления жизненным циклом FastAPI вместо устаревшего on_event
@app.router.on_startup.append
async def startup_event():
    asyncio.create_task(monitor_loop())