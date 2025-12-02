import logging
import os
import sys
import atexit

import psutil
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import Conflict

from config import TELEGRAM_TOKEN, ADMIN_USER_IDS
from handlers import (
    start,
    help_command,
    clear,
    switch_model,
    show_memory,
    progress,
    tips,
    add_filter,
    scenarios,
    goals,
    habits,
    month,
    forecast,
    plan,
    done,
    selfcheck,
    tuning,
    reboot,
    restart,
    strategy,
    mindset,
    personality,
    goaldeep,
    status,
    die,
    handle_text,
)
from state import load_memory, get_current_model


LOG_FILE = "bot.log"
LOCK_FILE = "bot.lock"


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def acquire_single_instance_lock() -> None:
    """Ensure only one bot instance runs; terminate stale PID if needed."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r", encoding="utf-8") as f:
                pid_str = f.read().strip()
            if pid_str.isdigit():
                pid = int(pid_str)
                if psutil.pid_exists(pid):
                    try:
                        p = psutil.Process(pid)
                        p.terminate()
                        p.wait(timeout=3)
                        logging.getLogger(__name__).warning("Terminated previous bot instance pid=%s", pid)
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            os.remove(LOCK_FILE)
        except Exception:
            pass
    try:
        with open(LOCK_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        logging.getLogger(__name__).error("Cannot write lock file: %s", e)


def release_lock() -> None:
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all error handler to avoid silent failures."""
    logging.getLogger(__name__).exception("Unhandled exception: %s", context.error)
    if update and isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("Произошла ошибка, уже разбираюсь.")
        except Exception:
            pass


def main() -> None:
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN is required (set env or .env).")

    acquire_single_instance_lock()
    atexit.register(release_lock)

    load_memory()

    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .concurrent_updates(True)
        .build()
    )

    # admin ids set
    application.bot_data["admin_ids"] = set(ADMIN_USER_IDS)

    # register commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CommandHandler("model", switch_model))
    application.add_handler(CommandHandler("memory", show_memory))
    application.add_handler(CommandHandler("progress", progress))
    application.add_handler(CommandHandler("tips", tips))
    application.add_handler(CommandHandler("filter", add_filter))
    application.add_handler(CommandHandler("scenarios", scenarios))
    application.add_handler(CommandHandler("goals", goals))
    application.add_handler(CommandHandler("habits", habits))
    application.add_handler(CommandHandler("month", month))
    application.add_handler(CommandHandler("forecast", forecast))
    application.add_handler(CommandHandler("plan", plan))
    application.add_handler(CommandHandler("done", done))
    application.add_handler(CommandHandler("selfcheck", selfcheck))
    application.add_handler(CommandHandler("tuning", tuning))
    application.add_handler(CommandHandler("reboot", reboot))
    application.add_handler(CommandHandler("restart", restart))
    application.add_handler(CommandHandler("strategy", strategy))
    application.add_handler(CommandHandler("mindset", mindset))
    application.add_handler(CommandHandler("personality", personality))
    application.add_handler(CommandHandler("goaldeep", goaldeep))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("die", die))

    # text handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # error handler
    application.add_error_handler(error_handler)

    logging.getLogger(__name__).info("Bot started with model %s", get_current_model())

    try:
        application.run_polling(
            drop_pending_updates=True,
            poll_interval=1.0,
            timeout=20,
            bootstrap_retries=-1,
        )
    except Conflict as e:
        logging.getLogger(__name__).error(
            "Bot conflict: another instance is polling or webhook active. Stop other instance. %s", e
        )
        return


if __name__ == "__main__":
    configure_logging()
    try:
        main()
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Bot stopped by keyboard interrupt.")
    finally:
        release_lock()
