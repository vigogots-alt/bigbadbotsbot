# analytics.py - Продвинутая аналитика

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
import numpy as np

class Analytics:
    """Генерация графиков и аналитики."""
    
    @staticmethod
    def plot_mood_trend(user_id: int) -> BytesIO:
        """График тренда настроения."""
        from state import user_memory
        profile = user_memory.get(str(user_id), {})
        obs = profile.get("observations", [])
        
        if len(obs) < 2:
            return None
        
        # Извлекаем данные
        dates = []
        moods = []
        for o in obs[-30:]:  # Последние 30 наблюдений
            try:
                ts = datetime.fromisoformat(o["ts"])
                dates.append(ts)
                moods.append(o.get("tone", 0))
            except:
                continue
        
        if not dates:
            return None
        
        # Создаём график
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(dates, moods, marker='o', linestyle='-', linewidth=2, 
                markersize=6, color='#2ecc71', label='Настроение')
        
        # Линия нуля
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        
        # Скользящее среднее
        if len(moods) > 5:
            window = 5
            moving_avg = np.convolve(moods, np.ones(window)/window, mode='valid')
            moving_dates = dates[window-1:]
            ax.plot(moving_dates, moving_avg, linestyle='--', linewidth=2, 
                   color='#e74c3c', label='Тренд (MA5)')
        
        ax.set_xlabel('Дата')
        ax.set_ylabel('Настроение')
        ax.set_title('Тренд настроения за последний месяц')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Форматирование дат
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Сохраняем в буфер
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        plt.close()
        
        return buf
    
    @staticmethod
    def plot_progress_breakdown(user_id: int) -> BytesIO:
        """Pie chart прогресса по целям."""
        from state import goals_manager
        
        all_goals = goals_manager.goals.get(user_id, [])
        if not all_goals:
            return None
        
        # Подсчёт по статусам
        from state import GoalStatus
        status_counts = {
            'Активные': 0,
            'Завершённые': 0,
            'Приостановленные': 0,
            'Проваленные': 0
        }
        
        for goal in all_goals:
            if goal.status == GoalStatus.ACTIVE:
                status_counts['Активные'] += 1
            elif goal.status == GoalStatus.COMPLETED:
                status_counts['Завершённые'] += 1
            elif goal.status == GoalStatus.PAUSED:
                status_counts['Приостановленные'] += 1
            elif goal.status == GoalStatus.FAILED:
                status_counts['Проваленные'] += 1
        
        # Фильтруем нулевые
        labels = []
        sizes = []
        colors = []
        color_map = {
            'Активные': '#3498db',
            'Завершённые': '#2ecc71',
            'Приостановленные': '#f39c12',
            'Проваленные': '#e74c3c'
        }
        
        for label, count in status_counts.items():
            if count > 0:
                labels.append(f'{label}\n({count})')
                sizes.append(count)
                colors.append(color_map[label])
        
        if not sizes:
            return None
        
        # Создаём pie chart
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
               startangle=90, textprops={'fontsize': 12})
        ax.set_title('Распределение целей по статусам', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        plt.close()
        
        return buf
    
    @staticmethod
    def plot_weekly_activity(user_id: int) -> BytesIO:
        """Heatmap активности по дням недели и часам."""
        from state import user_memory
        profile = user_memory.get(str(user_id), {})
        obs = profile.get("observations", [])
        
        if len(obs) < 10:
            return None
        
        # Матрица: день недели x час
        heatmap = np.zeros((7, 24))
        
        for o in obs[-100:]:  # Последние 100 наблюдений
            try:
                ts = datetime.fromisoformat(o["ts"])
                day = ts.weekday()  # 0=Monday
                hour = ts.hour
                heatmap[day, hour] += 1
            except:
                continue
        
        # График
        fig, ax = plt.subplots(figsize=(12, 6))
        im = ax.imshow(heatmap, cmap='YlOrRd', aspect='auto')
        
        # Подписи
        days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        ax.set_yticks(range(7))
        ax.set_yticklabels(days)
        ax.set_xticks(range(0, 24, 2))
        ax.set_xticklabels([f'{h:02d}:00' for h in range(0, 24, 2)])
        
        ax.set_xlabel('Час дня')
        ax.set_ylabel('День недели')
        ax.set_title('Тепловая карта активности')
        
        # Colorbar
        plt.colorbar(im, ax=ax, label='Количество сообщений')
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        plt.close()
        
        return buf
    
    @staticmethod
    def generate_weekly_report(user_id: int) -> str:
        """Текстовый отчёт за неделю."""
        from state import user_memory, long_term, goals_manager
        
        profile = user_memory.get(str(user_id), {})
        lt = long_term.get(str(user_id), {})
        
        # Активность
        obs = profile.get("observations", [])
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_obs = [o for o in obs if datetime.fromisoformat(o["ts"]) > week_ago]
        
        # Настроение
        moods = [o.get("tone", 0) for o in recent_obs]
        avg_mood = sum(moods) / len(moods) if moods else 0
        
        # Темы
        tags = []
        for o in recent_obs:
            tags.extend(o.get("tags", []))
        tag_counts = Counter(tags)
        top_themes = tag_counts.most_common(3)
        
        # Цели
        goals = goals_manager.goals.get(user_id, [])
        completed_this_week = [
            g for g in goals
            if g.completion_date and 
            datetime.fromisoformat(g.completion_date.isoformat()) > week_ago
        ]
        
        # Формируем отчёт
        report = "📊 НЕДЕЛЬНЫЙ ОТЧЁТ\n"
        report += "=" * 30 + "\n\n"
        
        report += f"📅 Период: {week_ago.strftime('%d.%m')} - {datetime.utcnow().strftime('%d.%m.%Y')}\n\n"
        
        report += "📈 АКТИВНОСТЬ:\n"
        report += f"  • Сообщений: {len(recent_obs)}\n"
        report += f"  • Среднее настроение: {avg_mood:+.2f}\n"
        mood_emoji = "😊" if avg_mood > 0.3 else "😐" if avg_mood > -0.3 else "😔"
        report += f"  • Общий тон: {mood_emoji}\n\n"
        
        if top_themes:
            report += "🔥 ГЛАВНЫЕ ТЕМЫ:\n"
            for theme, count in top_themes:
                report += f"  • {theme}: {count}x\n"
            report += "\n"
        
        report += "🎯 ЦЕЛИ:\n"
        active = goals_manager.get_active_goals(user_id)
        report += f"  • Активных: {len(active)}\n"
        report += f"  • Завершено на неделе: {len(completed_this_week)}\n"
        
        if active:
            avg_progress = sum(g.progress for g in active) / len(active)
            report += f"  • Средний прогресс: {avg_progress * 100:.0f}%\n"
        
        report += "\n"
        
        # Рекомендации
        report += "💡 РЕКОМЕНДАЦИИ:\n"
        if avg_mood < -0.2:
            report += "  • Настроение ниже нормы - добавь активности для восстановления\n"
        if len(recent_obs) < 7:
            report += "  • Низкая активность - давай пообщаемся чаще!\n"
        if active and avg_progress < 0.3:
            report += "  • Прогресс по целям медленный - нужен пинок?\n"
        if not active:
            report += "  • Нет активных целей - создай новую через /addgoal\n"
        
        return report


# Команды для аналитики

async def mood_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить график настроения."""
    user_id = update.effective_user.id
    
    await update.message.reply_text("📊 Генерирую график...")
    
    chart = Analytics.plot_mood_trend(user_id)
    if not chart:
        await update.message.reply_text("Недостаточно данных для графика (нужно минимум 2 наблюдения)")
        return
    
    await update.message.reply_photo(photo=chart, caption="График тренда настроения")


async def goals_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить график целей."""
    user_id = update.effective_user.id
    
    await update.message.reply_text("📊 Генерирую график...")
    
    chart = Analytics.plot_progress_breakdown(user_id)
    if not chart:
        await update.message.reply_text("Нет целей для анализа. Создай первую через /addgoal")
        return
    
    await update.message.reply_photo(photo=chart, caption="Распределение целей")


async def activity_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить тепловую карту активности."""
    user_id = update.effective_user.id
    
    await update.message.reply_text("📊 Генерирую тепловую карту...")
    
    chart = Analytics.plot_weekly_activity(user_id)
    if not chart:
        await update.message.reply_text("Недостаточно данных (нужно минимум 10 наблюдений)")
        return
    
    await update.message.reply_photo(photo=chart, caption="Тепловая карта активности")


async def weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить недельный отчёт."""
    user_id = update.effective_user.id
    
    report = Analytics.generate_weekly_report(user_id)
    await update.message.reply_text(report)
