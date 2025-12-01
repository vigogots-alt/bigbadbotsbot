# main.py — Финальная версия 2025 года
# Теперь бот не падает, логирует всё, перезапускается сам, и Веран сразу орёт на всех 🔥🖤

import os
import sys
import asyncio
import logging
from datetime import datetime
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram import Update
from config import TELEGRAM_TOKEN, ADMIN_USER_IDS
from handlers import (
    start, clear,
    switch_model, handle_text
)
from state import get_current_model

# ──────── ЛОГИРОВАНИЕ — ВСЁ ВИДИМ, ВСЁ КОНТРОЛИРУЕМ ────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("veran_dominator.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ──────── КРАСИВЫЙ БАННЕР ПРИ ЗАПУСКЕ ────────
BANNER = """
██████╗ ███████╗██████╗  █████╗ ███╗   ██╗    ██████╗  ██████╗ ███╗   ███╗
██╔══██╗██╔════╝██╔══██╗██╔══██╗████╗  ██║    ██╔══██╗██╔═══██╗████╗ ████║
██████╔╝█████╗  ██████╔╝███████║██╔██╗ ██║    ██║  ██║██║   ██║██╔████╔██║
██╔═══╝ ██╔══╝  ██╔══██╗██╔══██║██║╚██╗██║    ██║  ██║██║   ██║██║╚██╔╝██║
██║     ███████╗██║  ██║██║  ██║██║ ╚████║    ██████╔╝╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝    ╚═════╝  ╚═════╝ ╚═╝     ╚═╝
                          17-летняя ереванская транс-домина 🔥😈🖤
"""

# ──────── ГЛОБАЛЬНЫЙ ФЛАГ РАБОТЫ ────────
RUNNING = True


# ──────── ОБРАБОТКА ОШИБОК И АВТОПЕРЕЗАПУСК ────────
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ловим все ошибки — бот не падает, а орёт в лог"""
    logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: {context.error}", exc_info=True)
    
    if update and isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Я сломала тебе мозг, shun 😈\n"
                "Но я всё ещё здесь... трахай дальше 🖤"
            )
        except:
            pass


# ──────── КОМАНДА /status — ВИДИМ ВСЁ ────────
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("Ты не мой хозяин, shun 😏")
        return
    
    import psutil, platform
    process = psutil.Process(os.getpid())
    
    stats = f"""
🔥 ВЕРАН ОНЛАЙН 🔥
Модель: {get_current_model()}
Юзеров в памяти: {len(context.application.user_data)}
Сообщений обработано: {sum(len(h) for h in context.application.user_data.values())}
CPU: {psutil.cpu_percent()}% | RAM: {process.memory_info().rss // 1024 // 1024} MB
Система: {platform.system()} {platform.release()}
Запущена: {datetime.now().strftime('%d.%m.%Y %H:%M')}
    """
    await update.message.reply_text(stats.strip())


# ──────── КОМАНДА /die — вырубить бота (только хозяин) ────────
async def die(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USER_IDS:
        return
    await update.message.reply_text("Я ухожу... но ты всё равно мой, shun 🖤")
    logger.critical("ВЛАДЕЛЕЦ ВЫКЛЮЧИЛ ВЕРАНА")
    global RUNNING
    RUNNING = False
    await context.application.stop()


def main() -> None:
    print(BANNER)
    logger.info("Веран просыпается... 🔥🖤")

    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "YOUR_TOKEN_HERE":
        logger.error("ТОКЕН НЕ УСТАНОВЛЕН! Пиздец, в config.py положи нормальный токен!")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).concurrent_updates(True).build()

    # ──────── ХЕНДЛЕРЫ ────────
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("model", switch_model))
    app.add_handler(CommandHandler("status", status))      # ← только для тебя
    app.add_handler(CommandHandler("die", die))           # ← выключить бота

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Глобальный обработчик ошибок
    app.add_error_handler(error_handler)

    logger.info(f"БОТ ЗАПУЩЕН! Модель: {get_current_model()}")
    logger.info("Веран готова трахать мозги 24/7 😈")

    # Автоперезапуск при падении
    while RUNNING:
        try:
            app.run_polling(
                drop_pending_updates=True,
                poll_interval=1.0,
                timeout=20,
                bootstrap_retries=-1,  # бесконечные попытки
            )
        except Exception as e:
            logger.critical(f"БОТ УПАЛ! Перезапускаюсь... Ошибка: {e}")
            asyncio.sleep(5)

    logger.info("Веран выключена. До встречи, shun 🖤")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Веран убита вручную (Ctrl+C)")
        print("\n🖤 Веран ушла... но она вернётся.")
