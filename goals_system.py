# goals_system.py - Продвинутая система целей

from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from telegram import Update
from telegram.ext import ContextTypes
import json

class GoalStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"
    ARCHIVED = "archived"

class GoalPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

class Goal:
    """Продвинутая структура цели."""
    
    def __init__(self, user_id: int, title: str, description: str = "",
                 priority: GoalPriority = GoalPriority.MEDIUM,
                 deadline: Optional[datetime] = None):
        self.id = f"goal_{user_id}_{datetime.utcnow().timestamp()}"
        self.user_id = user_id
        self.title = title
        self.description = description
        self.priority = priority
        self.status = GoalStatus.ACTIVE
        self.created_at = datetime.utcnow()
        self.deadline = deadline
        self.progress = 0.0  # 0.0 - 1.0
        self.milestones = []  # Промежуточные этапы
        self.dependencies = []  # Зависимости от других целей
        self.tags = []
        self.linked_habits = []  # Связанные привычки
        self.check_ins = []  # История проверок
        self.notes = []
        self.completion_date = None
        self.estimated_hours = 0
        self.actual_hours = 0
        
    def add_milestone(self, title: str, description: str = "") -> dict:
        """Добавить промежуточный этап."""
        milestone = {
            "id": len(self.milestones) + 1,
            "title": title,
            "description": description,
            "completed": False,
            "created_at": datetime.utcnow().isoformat()
        }
        self.milestones.append(milestone)
        self._update_progress()
        return milestone
    
    def complete_milestone(self, milestone_id: int) -> bool:
        """Отметить этап выполненным."""
        for m in self.milestones:
            if m["id"] == milestone_id:
                m["completed"] = True
                m["completed_at"] = datetime.utcnow().isoformat()
                self._update_progress()
                return True
        return False
    
    def _update_progress(self):
        """Обновить прогресс на основе этапов."""
        if not self.milestones:
            return
        completed = sum(1 for m in self.milestones if m["completed"])
        self.progress = completed / len(self.milestones)
    
    def add_check_in(self, note: str, mood: str, progress_delta: float = 0.0):
        """Добавить отметку о проверке цели."""
        check_in = {
            "timestamp": datetime.utcnow().isoformat(),
            "note": note,
            "mood": mood,
            "progress": self.progress,
            "progress_delta": progress_delta
        }
        self.check_ins.append(check_in)
        self.progress = min(1.0, self.progress + progress_delta)
        
        if self.progress >= 1.0:
            self.complete()
    
    def complete(self):
        """Завершить цель."""
        self.status = GoalStatus.COMPLETED
        self.completion_date = datetime.utcnow()
        self.progress = 1.0
    
    def pause(self):
        """Приостановить цель."""
        self.status = GoalStatus.PAUSED
    
    def resume(self):
        """Возобновить цель."""
        if self.status == GoalStatus.PAUSED:
            self.status = GoalStatus.ACTIVE
    
    def is_overdue(self) -> bool:
        """Проверка просрочки."""
        if not self.deadline:
            return False
        return datetime.utcnow() > self.deadline and self.status == GoalStatus.ACTIVE
    
    def days_remaining(self) -> Optional[int]:
        """Дней до дедлайна."""
        if not self.deadline:
            return None
        delta = self.deadline - datetime.utcnow()
        return max(0, delta.days)
    
    def to_dict(self) -> dict:
        """Сериализация."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "progress": self.progress,
            "milestones": self.milestones,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "linked_habits": self.linked_habits,
            "check_ins": self.check_ins,
            "notes": self.notes,
            "completion_date": self.completion_date.isoformat() if self.completion_date else None,
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours
        }


class GoalsManager:
    """Менеджер целей пользователя."""
    
    def __init__(self):
        self.goals = defaultdict(list)  # user_id -> [Goal]
        self.achievements = defaultdict(list)  # user_id -> [Achievement]
    
    def create_goal(self, user_id: int, title: str, **kwargs) -> Goal:
        """Создать новую цель."""
        goal = Goal(user_id, title, **kwargs)
        self.goals[user_id].append(goal)
        self._check_achievements(user_id)
        return goal
    
    def get_active_goals(self, user_id: int) -> List[Goal]:
        """Получить активные цели."""
        return [g for g in self.goals[user_id] if g.status == GoalStatus.ACTIVE]
    
    def get_overdue_goals(self, user_id: int) -> List[Goal]:
        """Получить просроченные цели."""
        return [g for g in self.goals[user_id] if g.is_overdue()]
    
    def get_goal_by_id(self, user_id: int, goal_id: str) -> Optional[Goal]:
        """Найти цель по ID."""
        for g in self.goals[user_id]:
            if g.id == goal_id:
                return g
        return None
    
    def suggest_next_action(self, user_id: int) -> Optional[str]:
        """Предложить следующее действие по целям."""
        active = self.get_active_goals(user_id)
        if not active:
            return "Создай новую цель через /addgoal"
        
        # Сортируем по приоритету и прогрессу
        active.sort(key=lambda g: (g.priority.value, -g.progress))
        
        next_goal = active[0]
        uncompleted_milestones = [m for m in next_goal.milestones if not m["completed"]]
        
        if uncompleted_milestones:
            return f"Следующий шаг по цели '{next_goal.title}': {uncompleted_milestones[0]['title']}"
        else:
            return f"Обнови прогресс по цели '{next_goal.title}' через /checkin"
    
    def analyze_goal_patterns(self, user_id: int) -> dict:
        """Анализ паттернов выполнения целей."""
        all_goals = self.goals[user_id]
        completed = [g for g in all_goals if g.status == GoalStatus.COMPLETED]
        failed = [g for g in all_goals if g.status == GoalStatus.FAILED]
        
        if not all_goals:
            return {"status": "no_goals"}
        
        completion_rate = len(completed) / len(all_goals)
        
        # Средний прогресс активных целей
        active = self.get_active_goals(user_id)
        avg_progress = sum(g.progress for g in active) / len(active) if active else 0
        
        # Теги успешных целей
        successful_tags = []
        for g in completed:
            successful_tags.extend(g.tags)
        tag_counts = Counter(successful_tags)
        
        return {
            "total_goals": len(all_goals),
            "completed": len(completed),
            "failed": len(failed),
            "active": len(active),
            "completion_rate": round(completion_rate, 2),
            "avg_active_progress": round(avg_progress, 2),
            "successful_tags": tag_counts.most_common(3),
            "overdue": len(self.get_overdue_goals(user_id))
        }
    
    def _check_achievements(self, user_id: int):
        """Проверить достижения."""
        completed = [g for g in self.goals[user_id] if g.status == GoalStatus.COMPLETED]
        
        # Достижение: первая цель
        if len(completed) == 1 and not self._has_achievement(user_id, "first_goal"):
            self._award_achievement(user_id, "first_goal", "Первая цель", 
                                   "Завершил свою первую цель!")
        
        # Достижение: 10 целей
        if len(completed) >= 10 and not self._has_achievement(user_id, "goal_master"):
            self._award_achievement(user_id, "goal_master", "Мастер целей", 
                                   "Завершил 10 целей!")
        
        # Достижение: цель за 24 часа
        for goal in completed:
            if goal.completion_date and goal.created_at:
                delta = goal.completion_date - goal.created_at
                if delta.days == 0 and not self._has_achievement(user_id, "speed_demon"):
                    self._award_achievement(user_id, "speed_demon", "Скоростной дьявол", 
                                           "Завершил цель за 24 часа!")
    
    def _has_achievement(self, user_id: int, achievement_id: str) -> bool:
        """Проверка наличия достижения."""
        return any(a["id"] == achievement_id for a in self.achievements[user_id])
    
    def _award_achievement(self, user_id: int, achievement_id: str, 
                          title: str, description: str):
        """Выдать достижение."""
        achievement = {
            "id": achievement_id,
            "title": title,
            "description": description,
            "awarded_at": datetime.utcnow().isoformat()
        }
        self.achievements[user_id].append(achievement)
        logger.info("Achievement awarded to user %s: %s", user_id, achievement_id)


# Глобальный менеджер целей
goals_manager = GoalsManager()


# Команды для работы с целями

async def add_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создать новую цель."""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "Использование: /addgoal <название> | <описание> | <приоритет: 1-4> | <дней до дедлайна>\n"
            "Пример: /addgoal Выучить Python | Основы за месяц | 2 | 30"
        )
        return
    
    text = " ".join(context.args)
    parts = [p.strip() for p in text.split("|")]
    
    title = parts[0] if len(parts) > 0 else "Новая цель"
    description = parts[1] if len(parts) > 1 else ""
    
    priority = GoalPriority.MEDIUM
    if len(parts) > 2:
        try:
            priority = GoalPriority(int(parts[2]))
        except:
            pass
    
    deadline = None
    if len(parts) > 3:
        try:
            days = int(parts[3])
            deadline = datetime.utcnow() + timedelta(days=days)
        except:
            pass
    
    goal = goals_manager.create_goal(user_id, title, description=description, 
                                     priority=priority, deadline=deadline)
    
    response = (
        f"✅ Цель создана:\n"
        f"ID: {goal.id}\n"
        f"📌 {title}\n"
        f"Приоритет: {priority.name}\n"
    )
    
    if deadline:
        response += f"⏰ Дедлайн: {deadline.strftime('%Y-%m-%d')} ({goal.days_remaining()} дней)\n"
    
    response += f"\nДобавь этапы через /milestone {goal.id} <название>"
    
    await update.message.reply_text(response)


async def list_goals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать все цели."""
    user_id = update.effective_user.id
    active = goals_manager.get_active_goals(user_id)
    
    if not active:
        await update.message.reply_text(
            "У тебя нет активных целей.\n"
            "Создай первую через /addgoal"
        )
        return
    
    text = "🎯 Твои цели:\n\n"
    for i, goal in enumerate(active, 1):
        progress_bar = "█" * int(goal.progress * 10) + "░" * (10 - int(goal.progress * 10))
        text += (
            f"{i}. {goal.title}\n"
            f"   {progress_bar} {goal.progress * 100:.0f}%\n"
            f"   Приоритет: {goal.priority.name}\n"
        )
        
        if goal.deadline:
            days_left = goal.days_remaining()
            text += f"   ⏰ Осталось: {days_left} дней\n"
        
        if goal.milestones:
            completed = sum(1 for m in goal.milestones if m["completed"])
            text += f"   📋 Этапы: {completed}/{len(goal.milestones)}\n"
        
        text += f"   ID: {goal.id}\n\n"
    
    await update.message.reply_text(text)


async def check_in_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отметиться по цели."""
    user_id = update.effective_user.id
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Использование: /checkin <goal_id> <прогресс 0-100> [заметка]\n"
            "Пример: /checkin goal_123_456 25 Сделал первый модуль"
        )
        return
    
    goal_id = context.args[0]
    try:
        progress = float(context.args[1]) / 100
    except:
        await update.message.reply_text("Прогресс должен быть числом 0-100")
        return
    
    note = " ".join(context.args[2:]) if len(context.args) > 2 else ""
    
    goal = goals_manager.get_goal_by_id(user_id, goal_id)
    if not goal:
        await update.message.reply_text(f"Цель {goal_id} не найдена")
        return
    
    old_progress = goal.progress
    goal.add_check_in(note, mood="neutral", progress_delta=progress - old_progress)
    
    response = f"✅ Прогресс обновлён для '{goal.title}':\n"
    response += f"{'█' * int(goal.progress * 10)}{'░' * (10 - int(goal.progress * 10))} {goal.progress * 100:.0f}%\n"
    
    if goal.status == GoalStatus.COMPLETED:
        response += "\n🎉 ЦЕЛЬ ЗАВЕРШЕНА! Поздравляю!"
        
        # Проверка достижений
        achievements = goals_manager.achievements[user_id]
        if achievements:
            latest = achievements[-1]
            response += f"\n\n🏆 Получено достижение: {latest['title']}\n{latest['description']}"
    
    await update.message.reply_text(response)


async def add_milestone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавить этап к цели."""
    user_id = update.effective_user.id
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Использование: /milestone <goal_id> <название> [описание]"
        )
        return
    
    goal_id = context.args[0]
    title = context.args[1]
    description = " ".join(context.args[2:]) if len(context.args) > 2 else ""
    
    goal = goals_manager.get_goal_by_id(user_id, goal_id)
    if not goal:
        await update.message.reply_text(f"Цель {goal_id} не найдена")
        return
    
    milestone = goal.add_milestone(title, description)
    
    await update.message.reply_text(
        f"✅ Этап добавлен к цели '{goal.title}':\n"
        f"#{milestone['id']}: {title}\n"
        f"\nОтметь выполнение через /complete {goal_id} {milestone['id']}"
    )


async def complete_milestone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отметить этап выполненным."""
    user_id = update.effective_user.id
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Использование: /complete <goal_id> <milestone_id>"
        )
        return
    
    goal_id = context.args[0]
    try:
        milestone_id = int(context.args[1])
    except:
        await update.message.reply_text("milestone_id должен быть числом")
        return
    
    goal = goals_manager.get_goal_by_id(user_id, goal_id)
    if not goal:
        await update.message.reply_text(f"Цель {goal_id} не найдена")
        return
    
    if goal.complete_milestone(milestone_id):
        progress_bar = "█" * int(goal.progress * 10) + "░" * (10 - int(goal.progress * 10))
        await update.message.reply_text(
            f"✅ Этап завершён!\n"
            f"Прогресс '{goal.title}':\n"
            f"{progress_bar} {goal.progress * 100:.0f}%"
        )
    else:
        await update.message.reply_text(f"Этап {milestone_id} не найден")


async def goal_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика по целям."""
    user_id = update.effective_user.id
    analysis = goals_manager.analyze_goal_patterns(user_id)
    
    if analysis.get("status") == "no_goals":
        await update.message.reply_text("У тебя ещё нет целей. Создай первую через /addgoal")
        return
    
    text = (
        f"📊 Статистика целей:\n\n"
        f"Всего целей: {analysis['total_goals']}\n"
        f"✅ Завершено: {analysis['completed']}\n"
        f"❌ Провалено: {analysis['failed']}\n"
        f"🔄 Активных: {analysis['active']}\n"
        f"⏰ Просрочено: {analysis['overdue']}\n\n"
        f"Процент завершения: {analysis['completion_rate'] * 100:.0f}%\n"
        f"Средний прогресс активных: {analysis['avg_active_progress'] * 100:.0f}%\n"
    )
    
    if analysis['successful_tags']:
        text += f"\nУспешные темы:\n"
        for tag, count in analysis['successful_tags']:
            text += f"  • {tag}: {count}\n"
    
    await update.message.reply_text(text)


async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать достижения."""
    user_id = update.effective_user.id
    achievements = goals_manager.achievements[user_id]
    
    if not achievements:
        await update.message.reply_text(
            "У тебя пока нет достижений.\n"
            "Завершай цели чтобы получить первое!"
        )
        return
    
    text = "🏆 Твои достижения:\n\n"
    for ach in achievements:
        text += (
            f"🏅 {ach['title']}\n"
            f"   {ach['description']}\n"
            f"   {ach['awarded_at'][:10]}\n\n"
        )
    
    await update.message.reply_text(text)
