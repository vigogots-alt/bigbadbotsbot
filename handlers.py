import os
from typing import Dict

import requests
from telegram import Update
from telegram.ext import ContextTypes

from config import GEMINI_API_KEY, MESSAGE_CHUNK_SIZE, SYSTEM_PROMPT
from state import append_message, get_current_model, reset_history, set_model, toggle_voice, voice_enabled
from voice_utils import text_to_voice, voice_to_text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reset_history(user_id)
    await update.message.reply_text(
        "Привет! Я голосовой и текстовый ассистент на базе Gemini.\n\n"
        "Команды:\n"
        "/voice — включить или выключить озвучку ответов\n"
        "/clear — очистить историю диалога\n"
        "/model — выбрать модель Gemini\n\n"
        "Спроси о чём угодно или пришли голосовое сообщение."
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_history(update.effective_user.id)
    await update.message.reply_text("История очищена!")


async def toggle_voice_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    voice_status = toggle_voice(user_id)
    status_text = "включены" if voice_status else "отключены"
    await update.message.reply_text(
        f"Голосовые ответы {status_text}.\n\n"
        f"{'Буду дублировать ответы озвучкой.' if voice_status else 'Буду отвечать только текстом.'}"
    )


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


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("Жду голосовое сообщение...")

    try:
        voice_file = await update.message.voice.get_file()
        voice_path = f"voice_{user_id}.ogg"
        await voice_file.download_to_drive(voice_path)

        text = voice_to_text(voice_path)
        os.remove(voice_path)

        if not text:
            await update.message.reply_text("Не удалось распознать речь, попробуй еще раз.")
            return

        await update.message.reply_text(f"Текст из аудио: {text}")
        await process_message(update, context, text)

    except Exception as e:
        await update.message.reply_text(f"Ошибка при обработке голосового сообщения: {str(e)}")


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

            if voice_enabled(user_id):
                await update.message.chat.send_action("record_voice")
                voice_file = text_to_voice(answer)
                if voice_file:
                    await update.message.reply_voice(voice=open(voice_file, "rb"))
                    os.remove(voice_file)
        else:
            await update.message.reply_text(f"Ошибка Gemini API: {r.status_code}")

    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {str(e)}")
