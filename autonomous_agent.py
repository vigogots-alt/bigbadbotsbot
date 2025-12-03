# autonomous_agent.py - Проактивная Аврора

import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Optional, Dict, List
from telegram import Update
from telegram.ext import ContextTypes
import random

logger = logging.getLogger(__name__)

class ProactiveAgent:
    """
    Автономный агент который проактивно взаимодействует с пользователем:
    - Напоминания о целях
    - Проверка самочувствия
    - Предложения активностей
    - Мотивационные сообщения
    """
    
    def __init__(self, bot, user_id: int):
        self.bot = bot
        self.user_id = user_id
        self.last_proactive_message = None
        self.proactive_enabled = True
        self.schedule = {
            "morning_checkin": time(9, 0),      # Утренний чекин
            "midday_reminder": time(14, 0),     # Дневное напоминание
            "evening_reflection": time(21, 0),  # Вечерняя рефлексия
        }
    
    async def run(self):
        """Основной цикл агента."""
        while self.proactive_enabled:
            await asyncio.sleep(300)  # Проверка каждые 5 минут
            
            try:
                await self.check_schedule()
                await self.check_user_state()
                await self.check_goals_progress()
            except Exception as e:
                logger.error("Proactive agent error for user %s: %s", self.user_id, e)
    
    async def check_schedule(self):
        """Проверка расписания проактивных сообщений."""
        now = datetime.now().time()
        
        for event_name, scheduled_time in self.schedule.items():
            if self._is_time_for_event(now, scheduled_time, event_name):
                await self.send_scheduled_message(event_name)
    
    def _is_time_for_event(self, current_time: time, scheduled_time: time, 
                           event_name: str) -> bool:
        """Проверка что пришло время для события."""
        # Проверяем что время совпало (с точностью до 5 минут)
        diff = abs((current_time.hour * 60 + current_time.minute) - 
                   (scheduled_time.hour * 60 + scheduled_time.minute))
        
        if diff <= 5:
            # Проверяем что не отправляли недавно
            last_key = f"last_{event_name}"
            from state import long_term
            lt = long_term.get(str(self.user_id), {})
            last_sent = lt.get(last_key)
            
            if last_sent:
                last_dt = datetime.fromisoformat(last_sent)
                if datetime.now() - last_dt < timedelta(hours=12):
                    return False
            
            # Обновляем время последней отправки
            lt[last_key] = datetime.now().isoformat()
            from state import save_long_term
            save_long_term()
            return True
        
        return False
    
    async def send_scheduled_message(self, event_name: str):
        """Отправить запланированное сообщение."""
        from state import get_profile, goals_manager
        profile = get_profile(self.user_id)
        
        message = ""
        
        if event_name == "morning_checkin":
            mood = profile.get("mood_score", 0)
            greeting = "Доброе утро! ☀️" if mood >= 0 else "Доброе утро 🌤️"
            
            active_goals = goals_manager.get_active_goals(self.user_id)
            if active_goals:
                top_goal = active_goals[0]
                message = (
                    f"{greeting}\n\n"
                    f"Сегодня фокус на цели: '{top_goal.title}'\n"
                    f"Прогресс: {top_goal.progress * 100:.0f}%\n\n"
                    f"Что планируешь сделать сегодня?"
                )
            else:
                message = f"{greeting}\n\nКак себя чувствуешь? Есть планы на день?"
        
        elif event_name == "midday_reminder":
            active_goals = goals_manager.get_active_goals(self.user_id)
            if active_goals:
                next_action = goals_manager.suggest_next_action(self.user_id)
                message = (
                    f"⏰ Дневное напоминание:\n\n"
                    f"{next_action}\n\n"
                    f"Уже есть прогресс?"
                )
            else:
                message = "👋 Как дела? Нужна помощь с чем-то?"
        
        elif event_name == "evening_reflection":
            message = (
                "🌙 Время вечерней рефлексии:\n\n"
                "Что удалось сегодня?\n"
                "Что можно улучшить завтра?\n\n"
                "Поделись мыслями или просто скажи как прошёл день."
            )
        
        if message:
            try:
                await self.bot.send_message(chat_id=self.user_id, text=message)
                logger.info("Proactive message sent to user %s: %s", self.user_id, event_name)
            except Exception as e:
                logger.error("Failed to send proactive message to %s: %s", self.user_id, e)
    
    async def check_user_state(self):
        """Проверка состояния пользователя и проактивная помощь."""
        from state import get_profile, get_last_seen
        
        last_seen = get_last_seen(self.user_id)
        if not last_seen:
            return
        
        # Если не было активности больше 3 дней
        if datetime.utcnow() - last_seen > timedelta(days=3):
            await self.send_comeback_message()
        
        # Если настроение низкое несколько дней
        profile = get_profile(self.user_id)
        mood = profile.get("mood_score", 0)
        if mood < -0.4:
            await self.send_support_message()
    
    async def send_comeback_message(self):
        """Сообщение для возвращения пользователя."""
        messages = [
            "Давно не виделись! 👋\nКак дела? Нужна помощь с чем-то?",
            "Привет! Соскучилась 🙂\nЧем занимался? Как проекты?",
            "Хей! 👋\nВсё в порядке? Может помочь с чем-то?",
        ]
        
        message = random.choice(messages)
        
        try:
            await self.bot.send_message(chat_id=self.user_id, text=message)
        except Exception as e:
            logger.error("Failed to send comeback message to %s: %s", self.user_id, e)
    
    async def send_support_message(self):
        """Сообщение поддержки при низком настроении."""
        from state import long_term
        lt = long_term.get(str(self.user_id), {})
        
        # Проверяем что не отправляли недавно
        last_support = lt.get("last_support_message")
        if last_support:
            last_dt = datetime.fromisoformat(last_support)
            if datetime.now() - last_dt < timedelta(hours=24):
                return
        
        messages = [
            "Вижу что непросто сейчас 💙\nХочешь поговорить? Или может помочь с чем-то конкретным?",
            "Держись 💪\nПомни: сложные периоды временны. Чем могу помочь?",
            "Эй, всё будет хорошо ✨\nДавай вместе найдём что-то что поднимет настроение?",
        ]
        
        message = random.choice(messages)
        
        try:
            await self.bot.send_message(chat_id=self.user_id, text=message)
            lt["last_support_message"] = datetime.now().isoformat()
            from state import save_long_term
            save_long_term()
        except Exception as e:
            logger.error("Failed to send support message to %s: %s", self.user_id, e)
    
    async def check_goals_progress(self):
        """Проверка прогресса по целям."""
        from state import goals_manager
        
        overdue = goals_manager.get_overdue_goals(self.user_id)
        if overdue:
            await self.send_overdue_reminder(overdue[0])
    
    async def send_overdue_reminder(self, goal):
        """Напоминание о просроченной цели."""
        from state import long_term
        lt = long_term.get(str(self.user_id), {})
        
        # Не спамим напоминаниями
        last_reminder = lt.get(f"last_reminder_{goal.id}")
        if last_reminder:
            last_dt = datetime.fromisoformat(last_reminder)
            if datetime.now() - last_dt < timedelta(days=1):
                return
        
        message = (
            f"⚠️ Напоминание о цели:\n\n"
            f"'{goal.title}' просрочена\n"
            f"Прогресс: {goal.progress * 100:.0f}%\n\n"
            f"Варианты:\n"
            f"1. Продлить дедлайн\n"
            f"2. Пересмотреть цель\n"
            f"3. Разбить на меньшие шаги\n\n"
            f"Что выберешь?"
        )
        
        try:
            await self.bot.send_message(chat_id=self.user_id, text=message)
            lt[f"last_reminder_{goal.id}"] = datetime.now().isoformat()
            from state import save_long_term
            save_long_term()
        except Exception as e:
            logger.error("Failed to send overdue reminder to %s: %s", self.user_id, e)


class ProactiveManager:
    """Менеджер проактивных агентов для всех пользователей."""
    
    def __init__(self):
        self.agents = {}  # user_id -> ProactiveAgent
    
    def start_agent(self, bot, user_id: int):
        """Запустить агента для пользователя."""
        if user_id not in self.agents:
            agent = ProactiveAgent(bot, user_id)
            self.agents[user_id] = agent
            loop = asyncio.get_event_loop()
            loop.create_task(agent.run())
            logger.info("Proactive agent started for user %s", user_id)
    
    def stop_agent(self, user_id: int):
        """Остановить агента."""
        if user_id in self.agents:
            self.agents[user_id].proactive_enabled = False
            del self.agents[user_id]
            logger.info("Proactive agent stopped for user %s", user_id)
    
    def stop_all_agents(self):
        for user_id in list(self.agents.keys()):
            self.stop_agent(user_id)
    
    def toggle_schedule(self, user_id: int, event_name: str, enabled: bool):
        """Включить/выключить конкретное событие."""
        if user_id in self.agents:
            agent = self.agents[user_id]
            if enabled:
                # Восстановить дефолтное время
                defaults = {
                    "morning_checkin": time(9, 0),
                    "midday_reminder": time(14, 0),
                    "evening_reflection": time(21, 0),
                }
                if event_name in defaults:
                    agent.schedule[event_name] = defaults[event_name]
            else:
                # Удалить из расписания
                if event_name in agent.schedule:
                    del agent.schedule[event_name]


# Глобальный менеджер
proactive_manager = ProactiveManager()


# Команды для управления проактивностью

async def toggle_proactive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включить/выключить проактивные сообщения."""
    user_id = update.effective_user.id
    
    if user_id in proactive_manager.agents:
        proactive_manager.stop_agent(user_id)
        await update.message.reply_text("✅ Проактивные сообщения отключены")
    else:
        bot = context.bot
        proactive_manager.start_agent(bot, user_id)
        await update.message.reply_text(
            "✅ Проактивные сообщения включены!\n\n"
            "Я буду:\n"
            "• Напоминать о целях\n"
            "• Проверять как дела\n"
            "• Мотивировать и поддерживать\n\n"
            "Отключить: /proactive снова"
        )


async def set_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настроить расписание проактивных сообщений."""
    user_id = update.effective_user.id
    
    if user_id not in proactive_manager.agents:
        await update.message.reply_text("Сначала включи проактивные сообщения через /proactive")
        return
    
    if not context.args:
        agent = proactive_manager.agents[user_id]
        text = "⏰ Текущее расписание:\n\n"
        for event, scheduled_time in agent.schedule.items():
            text += f"• {event}: {scheduled_time.strftime('%H:%M')}\n"
        
        text += "\nИзменить: /schedule <событие> <время HH:MM> или off\n"
        text += "События: morning_checkin, midday_reminder, evening_reflection"
        
        await update.message.reply_text(text)
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Использование: /schedule <событие> <время HH:MM или off>"
        )
        return
    
    event_name = context.args[0]
    time_str = context.args[1]
    
    if time_str.lower() == "off":
        proactive_manager.toggle_schedule(user_id, event_name, False)
        await update.message.reply_text(f"✅ Событие {event_name} отключено")
    else:
        try:
            hour, minute = map(int, time_str.split(":"))
            new_time = time(hour, minute)
            agent = proactive_manager.agents[user_id]
            agent.schedule[event_name] = new_time
            await update.message.reply_text(
                f"✅ Событие {event_name} установлено на {time_str}"
            )
        except:
            await update.message.reply_text("Неверный формат времени. Используй HH:MM")


async def manual_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ручной триггер утреннего чекина."""
    user_id = update.effective_user.id
    
    if user_id not in proactive_manager.agents:
        await update.message.reply_text("Проактивные сообщения не включены. Включи через /proactive")
        return
    
    agent = proactive_manager.agents[user_id]
    await agent.send_scheduled_message("morning_checkin")
