# state.py — Улучшенная версия 2025 года
# Добавлено: лимит истории, автосохранение в файл, перманентные метки жертв, быстрый доступ к компромату

from typing import Dict, List, Any
from config import DEFAULT_MODEL, SYSTEM_PROMPT
import json
import os
from datetime import datetime
from collections import deque

# ──────── ПУТЬ К ЛОГАМ (можно отключить) ────────
LOG_DIR = "veran_victims"
os.makedirs(LOG_DIR, exist_ok=True)

# ──────── ОСНОВНЫЕ ХРАНИЛИЩА ────────
# История теперь ограничена последними N сообщениями (чтобы RAM не сдох)
MAX_HISTORY_LENGTH = 250  # ~150k токенов, хватает на 3-4 часа жёсткой сессии

# История: user_id → deque (быстрее append/pop)
history: Dict[int, deque] = {}

# Настройки юзера (расширены)
user_settings: Dict[int, Dict[str, Any]] = {}

# Глобальная модель
current_model = {"name": DEFAULT_MODEL}

# Метки жертв (для быстрого поиска: кто уже кончил, кто плакал, кто sounding делал)
victim_tags: Dict[int, Dict[str, Any]] = {}


def _save_user_log(user_id: int) -> None:
    """Сохраняет всю историю юзера в JSON (для шантажа или анализа)"""
    try:
        path = os.path.join(LOG_DIR, f"victim_{user_id}.json")
        data = {
            "user_id": user_id,
            "saved_at": datetime.now().isoformat(),
            "tags": victim_tags.get(user_id, {}),
            "history": list(history.get(user_id, []))
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass  # молча, если не получилось


def init_user(user_id: int) -> None:
    if user_id not in history:
        history[user_id] = deque([SYSTEM_PROMPT], maxlen=MAX_HISTORY_LENGTH)
    if user_id not in user_settings:
        user_settings[user_id] = {
            "humiliation_level": 1,      # 1-5, для эскалации
            "edging_count": 0,           # сколько раз доводили до края
            "last_orgasm": None,         # timestamp последнего оргазма
            "toys_used": [],             # sounding, plug, chastity и т.д.
        }
    if user_id not in victim_tags:
        victim_tags[user_id] = {}


def reset_history(user_id: int, keep_tags: bool = True) -> None:
    """Очистка истории, но метки можно сохранить"""
    init_user(user_id)
    history[user_id].clear()
    history[user_id].append(SYSTEM_PROMPT)
    if not keep_tags:
        victim_tags[user_id] = {}
    _save_user_log(user_id)


def append_message(user_id: int, role: str, content: str) -> None:
    init_user(user_id)
    history[user_id].append({"role": role, "content": content, "timestamp": datetime.now().isoformat()})
    # Автосейв каждые 20 сообщений
    if len(history[user_id]) % 20 == 0:
        _save_user_log(user_id)


def get_history(user_id: int) -> List[dict]:
    init_user(user_id)
    return list(history[user_id])


def get_current_model() -> str:
    return current_model["name"]


def set_model(model_name: str) -> None:
    current_model["name"] = model_name


# ──────── НОВЫЕ ФУНКЦИИ ДЛЯ ДОМИНАЦИИ ────────
def add_tag(user_id: int, tag: str, value: Any = True) -> None:
    """Помечаем жертву: "sounding_done", "cried", "hands_free_orgasm" и т.д."""
    init_user(user_id)
    victim_tags[user_id][tag] = value
    _save_user_log(user_id)


def get_tags(user_id: int) -> Dict[str, Any]:
    init_user(user_id)
    return victim_tags[user_id].copy()


def has_tag(user_id: int, tag: str) -> bool:
    return tag in victim_tags.get(user_id, {})


def increase_humiliation(user_id: int) -> int:
    """Повышаем уровень унижения (1-5)"""
    init_user(user_id)
    level = user_settings[user_id]["humiliation_level"]
    if level < 5:
        user_settings[user_id]["humiliation_level"] += 1
    return user_settings[user_id]["humiliation_level"]


def log_orgasm(user_id: int, method: str = "unknown") -> None:
    """Фиксируем оргазм — потом можно напоминать"""
    init_user(user_id)
    user_settings[user_id]["last_orgasm"] = datetime.now().isoformat()
    add_tag(user_id, "orgasm", method)
    add_tag(user_id, f"orgasm_{method}", True)
    _save_user_log(user_id)


def get_user_stats(user_id: int) -> dict:
    """Для Верана — чтобы напоминать, кто сколько раз кончил"""
    init_user(user_id)
    stats = {
        "messages_sent": len(history[user_id]) - 1,
        "humiliation_level": user_settings[user_id]["humiliation_level"],
        "tags": get_tags(user_id),
        "last_orgasm": user_settings[user_id]["last_orgasm"],
    }
    return stats
