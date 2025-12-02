from typing import Dict, List
import asyncio
import logging
import random
import os
from datetime import datetime

import requests
from telegram import Update
from telegram.ext import ContextTypes

from config import (
    GEMINI_API_KEY,
    MESSAGE_CHUNK_SIZE,
    SYSTEM_PROMPT,
    SAFETY_SETTINGS,
    GENERATION_CONFIG,
)
from state import (
    append_message,
    get_current_model,
    reset_history,
    set_model,
    get_history,
    add_observation,
    record_reply,
    get_profile_summary,
    get_progress_report,
    add_custom_filter,
    get_custom_filters,
    evaluate_scenarios,
    get_scenarios_report,
    get_goals,
    get_habits,
    get_month_summary,
    get_profile,
    get_active_scenarios,
    get_last_seen,
    set_last_seen,
    get_last_greet,
    set_last_greet,
    forecast_user,
    generate_plan,
    get_plan,
    mark_done,
    build_super_context,
    evaluate_metacognition,
    adjust_from_metacognition,
    self_tuning,
    soft_reboot,
    run_autonomy,
    set_pending_action,
    get_pending_action,
    clear_pending_action,
    RESTART_TIME,
)

logger = logging.getLogger(__name__)


# --- Utility builders ------------------------------------------------------

def build_conversation_history(user_id: int, max_messages: int = 12) -> List[dict]:
    """Build conversation history for Gemini: user/model pairs, skip system entries."""
    history = get_history(user_id)
    trimmed = history[-max_messages:]
    contents = []
    for item in trimmed:
        role = item.get("role")
        if role == "system":
            continue
        mapped_role = "user" if role == "user" else "model"
        contents.append({"role": mapped_role, "parts": [{"text": item.get("content", "")}]})
    return contents


def adjust_reply_style(profile: dict, last_text: str) -> tuple:
    """Adapt system prompt and generation config based on mood/progress and intent length."""
    mood = profile.get("mood_score", 0.0)
    progress = profile.get("progress_score", 0.0)
    active = get_active_scenarios(profile["user_id"])
    text_lower = (last_text or "").lower()

    base_instruction = SYSTEM_PROMPT["content"]
    style_parts = []
    gen_cfg = GENERATION_CONFIG.copy()
    try:
        from state import long_term
        tuning_state = long_term.get(str(profile["user_id"]), {}).get("tuning_state", {})
        gen_cfg["temperature"] = tuning_state.get("temperature", gen_cfg.get("temperature", 0.9))
        gen_cfg["topP"] = tuning_state.get("topP", gen_cfg.get("topP", 0.9))
        if "maxOutputTokens" in tuning_state:
            gen_cfg["maxOutputTokens"] = tuning_state["maxOutputTokens"]
    except Exception:
        pass

    if mood < -0.3:
        style_parts.append("Говори мягко, короче, поддерживай. Добавь упражнение на расслабление/дыхание.")
        gen_cfg["temperature"] = max(0.6, gen_cfg.get("temperature", 0.9) - 0.2)
        gen_cfg["topP"] = min(0.9, gen_cfg.get("topP", 0.9))
    elif mood > 0.4:
        style_parts.append("Говори энергично и тёпло, подчеркни успехи.")
        gen_cfg["temperature"] = min(1.1, gen_cfg.get("temperature", 0.9) + 0.1)

    if progress > 0.6:
        style_parts.append("Отметь достижения и предложи следующий шаг.")
    elif progress < 0.2:
        style_parts.append("Дай один конкретный маленький шаг без давления.")

    if "LowMoodSupport" in active:
        style_parts.append("Режим поддержки настроения активен: будь особенно мягкой.")
    if "ProductivityPush" in active:
        style_parts.append("Режим продуктивности: предложи 1-2 шага на сегодня и спроси про выполнение позже.")
    if "FinancialFocus" in active:
        style_parts.append("Фокус на финансах: дай короткий финансовый совет или микро-цель на неделю.")

    # intent-based brevity vs. depth
    long_intents = ["план", "почему", "объясн", "анализ", "как работает", "истори", "сюжет", "книга", "рассказ", "доклад"]
    needs_long = any(k in text_lower for k in long_intents) or len(text_lower) > 180
    if not needs_long:
        style_parts.append("Отвечай кратко и понятно (2-4 строки), без лишних подробностей.")
        gen_cfg["maxOutputTokens"] = min(gen_cfg.get("maxOutputTokens", 2048), 512)
    else:
        style_parts.append("Дай развернутый ответ по запросу.")
        gen_cfg["maxOutputTokens"] = min(gen_cfg.get("maxOutputTokens", 2048), 2048)

    extra_instruction = "\n".join(style_parts)
    logger.info(
        "adjust_reply_style user=%s mood=%.2f progress=%.2f active=%s gen_cfg=%s",
        profile["user_id"], mood, progress, active, gen_cfg,
    )
    return base_instruction + "\n" + extra_instruction, gen_cfg


async def _post_gemini(payload: dict) -> requests.Response:
    """Offload blocking HTTP to a thread executor."""
    loop = asyncio.get_running_loop()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{payload['model']}:generateContent?key={GEMINI_API_KEY}"
    body = {
        "contents": payload["contents"],
        "systemInstruction": payload["systemInstruction"],
        "safetySettings": payload["safetySettings"],
        "generationConfig": payload["generationConfig"],
    }
    return await loop.run_in_executor(None, lambda: requests.post(url, json=body, timeout=60))


def build_coach_context(user_id: int) -> str:
    """Short guidance for the model: mood/progress/intentions and proactive help."""
    summary = get_profile_summary(user_id)
    active = get_active_scenarios(user_id)
    tips = (
        "Дай тёплый, эмпатичный ответ. "
        "Добавь 1-2 персональных совета по привычкам/целям/стрессу. "
        "Предложи мини-челлендж на сегодня или завтра. "
        "Отрази настроение пользователя и подбодри. "
        f"Активные сценарии: {', '.join(active) if active else 'нет'}."
    )
    return f"{summary}\n\nРекомендации к ответу:\n{tips}"


def build_tips() -> str:
    """Generate a short random daily tip set."""
    habit = random.choice([
        "5 минут дыхания 4-7-8",
        "1 страница книги по делу",
        "10 минут ходьбы без телефона",
        "Записать 3 благодарности",
        "2 минуты планирования дня",
    ])
    finance = random.choice([
        "Записать все траты за сегодня",
        "Откладывать 5% входящих денег",
        "Проверить подписки и отключить лишнее",
        "Сравнить цены перед покупкой",
        "Сделать мини-бюджет на неделю",
    ])
    growth = random.choice([
        "Выучить один новый термин из своей сферы",
        "Сделать 1 микро-улучшение в резюме/портфолио",
        "Написать 3 строки кода/текста/идей для проекта",
        "Пересмотреть задачу и разбить на подэтапы",
        "Потренировать навык через короткое упражнение",
    ])
    return (
        "Советы на сегодня:\n"
        f"• Привычка: {habit}\n"
        f"• Финансы: {finance}\n"
        f"• Рост: {growth}"
    )


# --- Command handlers ------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome + reset history."""
    user_id = update.effective_user.id
    reset_history(user_id)
    logger.info("start command by user %s", user_id)
    await update.message.reply_text(
        "Привет! Я Аврора — твой персональный напарник на базе Gemini.\n\n"
        "Команды:\n"
        "/help — краткая справка\n"
        "/model — выбрать модель Gemini\n"
        "/clear — очистить контекст диалога\n"
        "/memory — показать, что я о тебе запомнил\n"
        "/progress — отчёт о росте\n"
        "/tips — ежедневные советы\n"
        "/scenarios — сценарии поведения\n"
        "/goals — подтверждённые цели\n"
        "/habits — устойчивые привычки\n"
        "/month — сводка месяца\n"
        "/forecast — прогнозы\n"
        "/plan — активный план\n"
        "/done — отметить пункт плана\n"
        "/strategy — стратегическая карта\n"
        "/mindset — профиль мышления\n"
        "/personality — личность\n"
        "/goaldeep — анализ целей\n"
        "/status — статистика (только для админов)\n"
        "/die — остановить бота (только админы)"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help text."""
    logger.info("help command by user %s", update.effective_user.id)
    await update.message.reply_text(
        "Я Аврора: запоминаю сообщения, настроение, цели и привычки, чтобы давать персональные советы.\n"
        "Команды:\n"
        "/start — сбросить диалог\n"
        "/model — выбрать модель\n"
        "/clear — очистить контекст\n"
        "/memory — показать наблюдения\n"
        "/progress — отчёт о темах и прогрессе\n"
        "/tips — ежедневные советы\n"
        "/scenarios — активные/неактивные сценарии\n"
        "/goals — подтверждённые цели\n"
        "/habits — устойчивые привычки\n"
        "/month — сводка месяца\n"
        "/forecast — прогнозы\n"
        "/plan — активный план\n"
        "/done — отметить пункт плана\n"
        "/strategy — стратегическая карта\n"
        "/mindset — профиль мышления\n"
        "/personality — личность\n"
        "/goaldeep — глубокий анализ целей\n"
        "/status — статус бота (админы)\n"
        "/die — остановить бота (админы)\n"
        "Пиши вопросы, цели, проблемы — предложу упражнения и шаги."
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear dialogue history."""
    reset_history(update.effective_user.id)
    logger.info("clear history for user %s", update.effective_user.id)
    await update.message.reply_text("История диалога очищена.")


async def switch_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch Gemini model."""
    models: Dict[str, tuple] = {
        "1": ("gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite — быстрый и экономичный"),
        "2": ("gemini-2.5-flash", "Gemini 2.5 Flash — баланс качества и скорости"),
        "3": ("gemini-3-pro-preview", "Gemini 3 Pro Preview — максимум возможностей"),
    }

    if not context.args:
        menu = "Доступные модели:\n\n"
        for key, (model_id, description) in models.items():
            current = "→" if get_current_model() == model_id else " "
            menu += f"{current} {key}. {description}\n"
        menu += f"\nТекущая модель: {get_current_model()}\n"
        menu += "\nИспользование: /model <номер>\nПример: /model 1"
        await update.message.reply_text(menu)
        return

    choice = context.args[0]
    if choice in models:
        set_model(models[choice][0])
        await update.message.reply_text(f"Активирована модель {get_current_model()}.")


async def show_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current memory summary."""
    user_id = update.effective_user.id
    logger.info("memory requested by user %s", user_id)
    summary = get_profile_summary(user_id)
    filters = get_custom_filters(user_id)
    if filters:
        summary += f"\nОтслеживаемые паттерны: {', '.join(filters)}"
    await update.message.reply_text(f"Моя память о тебе:\n\n{summary}")


async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show progress snapshot."""
    user_id = update.effective_user.id
    logger.info("progress requested by user %s", user_id)
    report = get_progress_report(user_id)
    await update.message.reply_text(f"Краткий прогресс:\n\n{report}")


async def tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Daily tips."""
    logger.info("tips requested by user %s", update.effective_user.id)
    await update.message.reply_text(build_tips())


async def forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show forecast."""
    user_id = update.effective_user.id
    logger.info("forecast requested by user %s", user_id)
    data = forecast_user(user_id)
    await update.message.reply_text(f"Прогноз:\n{data}")


async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show plan, generate if needed."""
    user_id = update.effective_user.id
    profile = get_profile(user_id)
    plan_obj = generate_plan(user_id, profile)
    text = (
        f"План от {plan_obj.get('date')}:\n"
        f"Short: {plan_obj.get('short', [])}\n"
        f"Mid: {plan_obj.get('mid', [])}\n"
        f"Long: {plan_obj.get('long', [])}\n"
        f"Выполнено: short={plan_obj.get('completed_short', [])}, mid={plan_obj.get('completed_mid', [])}, long={plan_obj.get('completed_long', [])}"
    )
    await update.message.reply_text(text)


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark plan item done."""
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Использование: /done <номер или часть текста пункта>")
        return
    text = " ".join(context.args)
    result = mark_done(user_id, text)
    await update.message.reply_text(result)


async def selfcheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show last metacognition entry."""
    user_id = update.effective_user.id
    data = evaluate_metacognition(user_id, "", get_profile(user_id).get("last_reply", ""))
    await update.message.reply_text(f"Самооценка (последняя):\n{data}")


async def tuning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tuning history entry."""
    user_id = update.effective_user.id
    tuning_state = self_tuning(user_id)
    await update.message.reply_text(f"Текущее тюнинг-состояние:\n{tuning_state}")


async def reboot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Soft reboot: clear transient state but keep long-term memory."""
    user_id = update.effective_user.id
    soft_reboot(user_id)
    await update.message.reply_text("Временные состояния очищены, память сохранена.")


async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add custom pattern to track."""
    user_id = update.effective_user.id
    if not context.args:
        filters = get_custom_filters(user_id)
        await update.message.reply_text(
            "Добавление паттерна: /filter <слово>\n"
            f"Сейчас отслеживаю: {', '.join(filters) if filters else 'ничего'}"
        )
        return
    pattern = " ".join(context.args).strip().lower()
    add_custom_filter(user_id, pattern)
    await update.message.reply_text(f"Добавлен паттерн: {pattern}")


async def scenarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show scenarios states."""
    user_id = update.effective_user.id
    logger.info("scenarios requested by user %s", user_id)
    await update.message.reply_text("Сценарии:\n" + get_scenarios_report(user_id))


async def goals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show confirmed goals."""
    user_id = update.effective_user.id
    logger.info("goals requested by user %s", user_id)
    goals_list = get_goals(user_id)
    text = "Подтверждённые цели:\n" + ("\n".join(goals_list) if goals_list else "пока нет")
    await update.message.reply_text(text)


async def habits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show confirmed habits."""
    user_id = update.effective_user.id
    logger.info("habits requested by user %s", user_id)
    habits_list = get_habits(user_id)
    text = "Устойчивые привычки:\n" + ("\n".join(habits_list) if habits_list else "пока нет")
    await update.message.reply_text(text)


async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show monthly summary."""
    user_id = update.effective_user.id
    logger.info("month summary requested by user %s", user_id)
    await update.message.reply_text(get_month_summary(user_id))


async def strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show strategic map and recommendations."""
    user_id = update.effective_user.id
    lt = get_profile(user_id)  # ensures init
    from state import long_term
    data = long_term[str(user_id)]
    text = (
        f"Стратегическая карта: {data.get('life_map', {})}\n"
        f"Рекомендации: {data.get('strategic_recommendations', {})}\n"
        f"Риски: {data.get('strategic_risks', [])}"
    )
    await update.message.reply_text(text)


async def mindset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show mindset profile."""
    user_id = update.effective_user.id
    from state import long_term
    data = long_term[str(user_id)].get("mindset_profile", {})
    await update.message.reply_text(f"Mindset профиль:\n{data}")


async def personality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show personality scores."""
    user_id = update.effective_user.id
    from state import long_term
    scores = long_term[str(user_id)].get("personality_scores", {})
    await update.message.reply_text(f"Профиль личности:\n{scores}")


async def goaldeep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deep goal analysis."""
    user_id = update.effective_user.id
    from state import long_term
    lt = long_term[str(user_id)]
    text = (
        f"Скрытые цели: {lt.get('implicit_goals', [])}\n"
        f"Избегаемые цели: {lt.get('avoided_goals', [])}\n"
        f"Прогноз целей: {lt.get('predicted_goals', [])}\n"
        f"Застрявшие цели: {lt.get('stalled_goals', [])}"
    )
    await update.message.reply_text(text)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Technical status (admins only)."""
    from datetime import datetime
    import psutil
    import platform
    import os

    if update.effective_user.id not in context.application.bot_data.get("admin_ids", set()):
        await update.message.reply_text("Недостаточно прав для /status.")
        return

    process = psutil.Process(os.getpid())
    stats = (
        f"Модель: {get_current_model()}\n"
        f"CPU: {psutil.cpu_percent()}% | RAM: {process.memory_info().rss // 1024 // 1024} MB\n"
        f"Платформа: {platform.system()} {platform.release()}\n"
        f"Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    await update.message.reply_text(stats)


async def die(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop bot (admins only)."""
    if update.effective_user.id not in context.application.bot_data.get("admin_ids", set()):
        await update.message.reply_text("Недостаточно прав для /die.")
        return
    logger.critical("Shutdown requested by admin %s", update.effective_user.id)
    await update.message.reply_text("Останавливаюсь по запросу администратора.")
    await context.application.stop()


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart bot (admins only): stop application; external supervisor should relaunch."""
    if update.effective_user.id not in context.application.bot_data.get("admin_ids", set()):
        await update.message.reply_text("Недостаточно прав для /restart.")
        return
    logger.critical("Restart requested by admin %s", update.effective_user.id)
    await update.message.reply_text("Перезапускаюсь. Если я пропаду на пару секунд — это нормально.")
    await context.application.stop()
    os._exit(0)


# --- Message flow ----------------------------------------------------------

def build_payload(user_id: int, text: str) -> dict:
    """Compose payload with memory summary + recent conversation + adaptive style."""
    coach_context = build_coach_context(user_id)
    super_context = build_super_context(user_id)
    conversation = build_conversation_history(user_id)
    profile = get_profile(user_id)
    system_instruction, gen_cfg = adjust_reply_style(profile, text)

    contents = [
        {
            "role": "user",
            "parts": [
                {"text": f"Контекст о пользователе и рекомендации к ответу:\n{coach_context}"},
                {"text": f"Super-context:\n{super_context}"},
            ],
        }
    ] + conversation

    return {
        "model": get_current_model(),
        "contents": contents,
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "safetySettings": SAFETY_SETTINGS,
        "generationConfig": gen_cfg,
    }


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles any text message."""
    text = update.message.text.strip()
    # admin-only code change handshake
    if await handle_code_change(update, context, text):
        return
    # self-proposed improvements handshake
    await maybe_propose_self_improve(update)
    await maybe_greet_on_resume(update, text)
    await process_message(update, context, text)


async def maybe_greet_on_resume(update: Update, text: str) -> None:
    """Greet after restart and avoid greeting spam."""
    user_id = update.effective_user.id
    now = datetime.utcnow()
    last_seen = get_last_seen(user_id)
    last_greet = get_last_greet(user_id)
    lower = text.lower()
    if not last_seen or last_seen < RESTART_TIME:
        now_local = datetime.now().strftime("%Y-%m-%d %H:%M")
        greeting = f"Привет! Я снова на связи. Сейчас {now_local}. Продолжим с того места, где остановились."
        await update.message.reply_text(greeting)
        set_last_greet(user_id)
    if "привет" in lower and last_greet and (now - last_greet).total_seconds() < 600:
        await update.message.reply_text("⚠️ Я уже здесь, давай к делу.")
        set_last_greet(user_id)


async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Log message, update memory, evaluate scenarios, call Gemini, reply."""
    user_id = update.effective_user.id
    add_observation(user_id, text)
    run_autonomy(user_id, text)  # forecast, plan, strategy, personality, goals, emotions
    evaluate_scenarios(user_id)
    append_message(user_id, "user", text)

    await update.message.chat.send_action("typing")

    payload = build_payload(user_id, text)

    try:
        response = await _post_gemini(payload)
        if response.status_code == 200:
            answer = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            append_message(user_id, "model", answer)
            record_reply(user_id, answer)
            # metacognition + tuning after reply
            evaluate_metacognition(user_id, text, answer)
            adjust_from_metacognition(user_id)
            self_tuning(user_id)

            # Split long answers
            for i in range(0, len(answer), MESSAGE_CHUNK_SIZE):
                await update.message.reply_text(answer[i : i + MESSAGE_CHUNK_SIZE])
        else:
            await update.message.reply_text(f"Gemini API error: {response.status_code}")
            logger.error("Gemini API error %s for user %s: %s", response.status_code, user_id, response.text)

    except Exception as e:
        logger.exception("Error handling message for user %s: %s", user_id, e)
        await update.message.reply_text(f"Не удалось ответить: {str(e)}")
    set_last_seen(user_id)


# --- Code change handshake (admin only) -----------------------------------
async def handle_code_change(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    """Handle '333 Code 333 ...' then 'nemesis' to apply config change."""
    user_id = update.effective_user.id
    # only admins can trigger
    if user_id not in context.application.bot_data.get("admin_ids", set()):
        return False

    lower = text.lower()
    pending = get_pending_action(user_id)

    # Apply on "nemesis"
    if lower.strip() == "nemesis" and pending:
        if pending.get("type") == "profession_replace":
            await apply_profession_change(update, pending["old"], pending["new"])
            clear_pending_action(user_id)
            return True
        if pending.get("type") == "file_replace":
            await apply_file_replace(update, pending["path"], pending["old"], pending["new"])
            clear_pending_action(user_id)
            return True
        if pending.get("type") == "self_improve_note":
            await apply_self_improve(update, pending.get("instruction", ""))
            clear_pending_action(user_id)
            return True
        return False

    # Set pending on phrase "333 code 333 replace X -> Y"
    if lower.startswith("333 code 333"):
        # Expect format: 333 Code 333 replace old -> new
        if "file" in lower and "replace" in lower and "->" in lower:
            # format: 333 Code 333 file <path> replace old -> new
            try:
                after_file = lower.split("file", 1)[1].strip()
                path_part, rest = after_file.split("replace", 1)
                path = path_part.strip()
                old, new = [s.strip() for s in rest.split("->", 1)]
                set_pending_action(user_id, {"type": "file_replace", "path": path, "old": old, "new": new})
                await update.message.reply_text(f"Запомнила замену в {path}. Ответь 'nemesis' для применения.")
                return True
            except Exception:
                await update.message.reply_text("Формат: 333 Code 333 file <путь> replace <старое> -> <новое>")
                return True
        elif "replace" in lower and "->" in lower:
            try:
                segment = lower.split("replace", 1)[1].strip()
                old, new = [s.strip() for s in segment.split("->", 1)]
                set_pending_action(user_id, {"type": "profession_replace", "old": old, "new": new})
                await update.message.reply_text("Запомнила запрос. Ответь 'nemesis' для применения изменения.")
                return True
            except Exception:
                await update.message.reply_text("Не смогла разобрать формат. Используй: 333 Code 333 replace старое -> новое")
                return True
        await update.message.reply_text("Укажи замену: 333 Code 333 file <путь> replace старое -> новое")
        return True

    # Freeform self-improve request: remember instruction, apply on "nemesis"
    if "улучшай себя" in lower or "ulutshay sebya" in lower or "uluchshay sebya" in lower:
        set_pending_action(user_id, {"type": "self_improve_note", "instruction": text})
        await update.message.reply_text("Запомнила запрос на самоизменение. Ответь 'nemesis' для применения.")
        return True

    return False


async def apply_profession_change(update: Update, old: str, new: str) -> None:
    """Replace profession in AVRORA_PROFESSIONS within config.py."""
    import pathlib
    config_path = pathlib.Path("config.py")
    text = config_path.read_text(encoding="utf-8")
    # naive replace within list literal
    if old not in text:
        await update.message.reply_text(f"Не нашла профессию '{old}' в config.py")
        return
    new_text = text.replace(old, new, 1)
    config_path.write_text(new_text, encoding="utf-8")
    await update.message.reply_text(f"Профессия '{old}' заменена на '{new}' в config.py")


async def apply_file_replace(update: Update, path: str, old: str, new: str) -> None:
    """Replace first occurrence of old->new in given file path."""
    import pathlib
    file_path = pathlib.Path(path)
    if not file_path.exists():
        await update.message.reply_text(f"Файл {path} не найден.")
        return
    try:
        text = file_path.read_text(encoding="utf-8")
    except Exception as e:
        await update.message.reply_text(f"Не удалось прочитать {path}: {e}")
        return
    if old not in text:
        await update.message.reply_text(f"В {path} не найдено '{old}'.")
        return
    new_text = text.replace(old, new, 1)
    try:
        file_path.write_text(new_text, encoding="utf-8")
        await update.message.reply_text(f"В {path} заменено '{old}' на '{new}'.")
    except Exception as e:
        await update.message.reply_text(f"Не удалось записать {path}: {e}")


async def apply_self_improve(update: Update, instruction: str) -> None:
    """Append a self-improvement note into config.py (or general note)."""
    import pathlib
    import datetime
    config_path = pathlib.Path("config.py")
    try:
        text = config_path.read_text(encoding="utf-8")
    except Exception as e:
        await update.message.reply_text(f"Не удалось прочитать config.py: {e}")
        return
    stamp = datetime.datetime.utcnow().isoformat()
    note = f"# Self-improve note {stamp}: {instruction}\n"
    new_text = text + "\n" + note
    try:
        config_path.write_text(new_text, encoding="utf-8")
        await update.message.reply_text("Самоизменение применено: инструкция сохранена в config.py.")
    except Exception as e:
        await update.message.reply_text(f"Не удалось записать config.py: {e}")


async def maybe_propose_self_improve(update: Update) -> None:
    """Autonomous proposal: if no pending action, set a self-improve request for approval."""
    user_id = update.effective_user.id
    app = getattr(update, "application", None)
    if not app:
        return
    admin_ids = app.bot_data.get("admin_ids", set())
    if user_id not in admin_ids:
        return
    # don't spam if pending exists
    if get_pending_action(user_id):
        return
    # simple heuristic: low progress or repeated tuning triggers propose
    from state import long_term
    lt = long_term.get(str(user_id), {})
    prog = lt.get("forecast", {}).get("goal_prediction", {}).get("needs_push", False)
    tuning_state = lt.get("tuning_state", {})
    if prog or tuning_state.get("temperature", 0.9) < 0.7:
        instruction = "Точно настроить профиль и стиль (тон/длина), чтобы отвечать короче и полезнее."
        set_pending_action(user_id, {"type": "self_improve_note", "instruction": instruction})
        await update.message.reply_text(
            "У меня есть план самоулучшения (⚠️):\n"
            f"• Что я хочу сделать: {instruction}\n"
            "• Зачем: меньше воды, больше точности, лучше попадание в твой стиль.\n"
            "• Как ты заметишь: ответы станут короче (2–4 строки, если не просишь длинно), теплее и точнее по запросу.\n"
            "Если согласен — ответь 'nemesis', и я применю это."
        )
