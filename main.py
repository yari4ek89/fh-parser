import asyncio
import logging
import httpx
from fastapi import FastAPI
from aiogram import Bot
from openai import AsyncOpenAI

TELEGRAM_TOKEN = "8226489943:AAHrww1U8oBKrTKqIfzuKy8-KonCbrtKy-Y"
CHAT_ID = "7420183488"
GROQ_API_KEY = "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"
FH_API_TOKEN = "5eaedd1edeff786df8ae6e396c02950da04b9121"

PORTFOLIO_URL = "https://github.com/yari4ek89"

API_URL = "https://api.freelancehunt.com/v2"
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
        "Твоя задача — написать короткий, коммерческий отклик на фриланс-заказ.\n"
        "ПРАВИЛА:\n"
        "1. Пиши строго на языке заказа (украинский или русский).\n"
        "2. Будь лаконичен (3-5 предложений), без воды.\n"
        "3. Предложи техническое решение проблемы из описания, упомяни стек Python/FastAPI.\n"
        "4. Предложи обсудить детали в ЛС и прикрепи портфолио: {portfolio}."
    ).format(portfolio=PORTFOLIO_URL)

    try:
        response = await ai_client.chat.completions.create(
            model="llama3-8b-8192", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Заказ: {task_title}\nОписание: {task_description}"}
            ],
            temperature=0.6
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        return "Не удалось сгенерировать отклик автоматически."

async def check_freelancehunt_api():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(API_URL, headers=HEADERS)
            if response.status_code != 200:
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
                link = project.get("links", {}).get("self", {}).get("html")
                
                budget_data = attributes.get("budget")
                budget = f"{budget_data['amount']} {budget_data['currency']}" if budget_data else "Договорной"
                
                cover_letter = await generate_groq_cover_letter(title, description)
                
                message_text = (
                    f"🟢 **Новый заказ на Freelancehunt!**\n"
                    f"📌 **{title}**\n"
                    f"💰 **Бюджет:** {budget}\n\n"
                    f"🤖 **Отклик от Groq (Llama-3):**\n"
                    f"```{cover_letter}```\n\n"
                    f"🔗 [ОТКРЫТЬ И ОТПРАВИТЬ]({link})"
                )
                await bot.send_message(chat_id=CHAT_ID, text=message_text, parse_mode="Markdown")
                await asyncio.sleep(1)
        except Exception as e:
            logging.error(f"Ошибка парсинга: {e}")

async def monitor_loop():
    print("Фоновый мониторинг запущен...")
    while True:
        await check_freelancehunt_api()
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(monitor_loop())