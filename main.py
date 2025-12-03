import logging
import os
import sys
import atexit
import asyncio

import psutil
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    JobQueue,
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
    fbthreads,
    fbthread,
    fbsearch,
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
    # Новые команды для обучения
    learning_stats,
    trigger_learning,
    show_insights,
    knowledge_base,
    list_commands,
    self_analyze,
    run_python,
    web_search_cmd,
    read_code,
    analyze_code,
    # Команды для памяти
    search_memory,
    show_episodes,
    create_episode,
    # Команды для целей
    add_goal,
    list_goals,
    check_in_goal,
    add_milestone,
    complete_milestone,
    goal_stats,
    show_achievements,
    # Команды для проактивности
    toggle_proactive,
    set_schedule,
    manual_checkin,
    # Команды для аналитики
    mood_chart,
    goals_chart,
    activity_chart,
    weekly_report,
    offline_eval_cmd,
    offline_eval_report,
    mark_bad_reply,
    feedback_log,
)
from state import load_memory, get_current_model


LOG_FILE = "bot.log"
LOCK_FILE = "bot.lock"


class SafeJobQueue(JobQueue):
    """Custom JobQueue storing a strong reference instead of weakref to Application."""

    def set_application(self, application):
        # Avoid weakref TypeError on some Python builds by keeping a direct reference.
        self._application = application


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


def save_on_exit() -> None:
    from state import user_memory, long_term, _save_json, MEMORY_FILE, LONG_TERM_FILE

    _save_json(MEMORY_FILE, user_memory)
    _save_json(LONG_TERM_FILE, long_term)


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


async def start_proactive_agents(application: Application) -> None:
    """
    Запуск проактивных агентов для всех активных пользователей.
    Вызывается один раз при старте бота.
    """
    from state import user_memory, proactive_manager
    
    logger = logging.getLogger(__name__)
    logger.info("Starting proactive agents for active users...")
    
    # Получаем всех пользователей из памяти
    for user_id_str in user_memory.keys():
        try:
            user_id = int(user_id_str)
            # Запускаем агента для каждого пользователя
            proactive_manager.start_agent(application.bot, user_id)
            logger.info("Proactive agent started for user %s", user_id)
        except Exception as e:
            logger.error("Failed to start proactive agent for user %s: %s", user_id_str, e)
    
    logger.info("Proactive agents initialization complete")


async def post_init(application: Application) -> None:
    """
    Выполняется после инициализации бота, но до начала polling.
    Здесь запускаем все фоновые задачи.
    """
    # Запуск проактивных агентов
    await start_proactive_agents(application)



async def on_shutdown(application: Application):
    from state import proactive_manager
    proactive_manager.stop_all_agents()

def main() -> None:
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN is required (set env or .env).")

    acquire_single_instance_lock()
    atexit.register(save_on_exit)
    atexit.register(release_lock)

    load_memory()

    application = (
        Application.builder()
        .job_queue(SafeJobQueue())
        .token(TELEGRAM_TOKEN)
        .concurrent_updates(True)
        .post_init(post_init)  # Важно: запускаем post_init
        .post_shutdown(on_shutdown)
        .build()
    )

    # admin ids set
    application.bot_data["admin_ids"] = set(ADMIN_USER_IDS)

    # ============ Базовые команды ============
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
    
    # ============ Facebook messages ============
    application.add_handler(CommandHandler("fbthreads", fbthreads))
    application.add_handler(CommandHandler("fbthread", fbthread))
    application.add_handler(CommandHandler("fbsearch", fbsearch))
    
    # ============ Планы ============
    application.add_handler(CommandHandler("plan", plan))
    application.add_handler(CommandHandler("done", done))
    
    # ============ Самоанализ ============
    application.add_handler(CommandHandler("selfcheck", selfcheck))
    application.add_handler(CommandHandler("selfanalyze", self_analyze))
    application.add_handler(CommandHandler("websearch", web_search_cmd))
    application.add_handler(CommandHandler("commands", list_commands))
    application.add_handler(CommandHandler("runpython", run_python))
    application.add_handler(CommandHandler("tuning", tuning))
    application.add_handler(CommandHandler("reboot", reboot))
    application.add_handler(CommandHandler("restart", restart))
    
    # ============ Стратегия ============
    application.add_handler(CommandHandler("strategy", strategy))
    application.add_handler(CommandHandler("mindset", mindset))
    application.add_handler(CommandHandler("personality", personality))
    application.add_handler(CommandHandler("goaldeep", goaldeep))
    
    # ============ Админ команды ============
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("die", die))
    
    # ============ НОВЫЕ: Самообучение ============
    application.add_handler(CommandHandler("learnstats", learning_stats))
    application.add_handler(CommandHandler("learn", trigger_learning))
    application.add_handler(CommandHandler("insights", show_insights))
    application.add_handler(CommandHandler("knowledge", knowledge_base))
    application.add_handler(CommandHandler("readcode", read_code))
    application.add_handler(CommandHandler("analyzecode", analyze_code))
    
    # ============ НОВЫЕ: Продвинутая память ============
    application.add_handler(CommandHandler("search", search_memory))
    application.add_handler(CommandHandler("episodes", show_episodes))
    application.add_handler(CommandHandler("episode", create_episode))
    
    # ============ НОВЫЕ: Система целей ============
    application.add_handler(CommandHandler("addgoal", add_goal))
    application.add_handler(CommandHandler("listgoals", list_goals))
    application.add_handler(CommandHandler("checkin", check_in_goal))
    application.add_handler(CommandHandler("milestone", add_milestone))
    application.add_handler(CommandHandler("complete", complete_milestone))
    application.add_handler(CommandHandler("goalstats", goal_stats))
    application.add_handler(CommandHandler("achievements", show_achievements))
    
    # ============ НОВЫЕ: Проактивность ============
    application.add_handler(CommandHandler("proactive", toggle_proactive))
    application.add_handler(CommandHandler("schedule", set_schedule))
    application.add_handler(CommandHandler("morningcheck", manual_checkin))
    
    # ============ НОВЫЕ: Аналитика ============
    application.add_handler(CommandHandler("moodchart", mood_chart))
    application.add_handler(CommandHandler("goalschart", goals_chart))
    application.add_handler(CommandHandler("activitychart", activity_chart))
    application.add_handler(CommandHandler("weeklyreport", weekly_report))

    # ============ Качество и фидбек ============
    application.add_handler(CommandHandler("offlineeval", offline_eval_cmd))
    application.add_handler(CommandHandler("evalreport", offline_eval_report))
    application.add_handler(CommandHandler("bad", mark_bad_reply))
    application.add_handler(CommandHandler("feedbacklog", feedback_log))

    # text handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # error handler
    application.add_error_handler(error_handler)

    logging.getLogger(__name__).info("Bot started with model %s", get_current_model())
    logging.getLogger(__name__).info("All subsystems initialized (learning, memory, goals, proactive, analytics)")

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
