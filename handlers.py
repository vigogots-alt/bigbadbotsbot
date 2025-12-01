from typing import Dict

import requests
from telegram import Update
from telegram.ext import ContextTypes

from config import GEMINI_API_KEY, MESSAGE_CHUNK_SIZE, SYSTEM_PROMPT
from state import append_message, get_current_model, reset_history, set_model


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reset_history(user_id)
    await update.message.reply_text(
        "Привет! Я текстовый ассистент на базе Gemini.\n\n"
        "Команды:\n"
        "/clear — очистить историю диалога\n"
        "/model — выбрать модель Gemini\n\n"
        "Спроси о чём угодно."
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_history(update.effective_user.id)
    await update.message.reply_text("История очищена!")


async def switch_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    models: Dict[str, tuple] = {
        "1": ("gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite — экономичный режим"),
        "2": ("gemini-2.5-flash", "Gemini 2.5 Flash — баланс качества и скорости"),
        "3": ("gemini-3-pro-preview", "Gemini 3 Pro Preview — максимальные возможности"),
    }

    if not context.args:
        menu = "Доступные модели:\n\n"
        for key, (model_id, description) in models.items():
            current = "→" if get_current_model() == model_id else " "
            menu += f"{current} {key}. {description}\n"
        menu += f"\nТекущая модель: {get_current_model()}\n"
        menu += "\nИспользование: /model <номер>\nПример: /model 3"
        await update.message.reply_text(menu)
        return

    choice = context.args[0]
    if choice in models:
        set_model(models[choice][0])
        await update.message.reply_text(f"Активирована модель {get_current_model()}.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    await process_message(update, context, text)


async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user_id = update.effective_user.id
    append_message(user_id, "user", text)

    await update.message.chat.send_action("typing")

    model = get_current_model()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT["content"]}]},
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 8192},
    }

    try:
        r = requests.post(url, json=payload, timeout=60)

        if r.status_code == 200:
            answer = r.json()["candidates"][0]["content"]["parts"][0]["text"]

            for i in range(0, len(answer), MESSAGE_CHUNK_SIZE):
                await update.message.reply_text(answer[i : i + MESSAGE_CHUNK_SIZE])
        else:
            await update.message.reply_text(f"Ошибка Gemini API: {r.status_code}")

    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {str(e)}")
