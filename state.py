# state.py — user memory, long-term storage, and behavior scenarios.
# Responsibilities:
#   - Keep per-user conversation history for model context.
#   - Persist per-user memory (habits, goals, mistakes, mood/progress) to JSON.
#   - Maintain long-term signals (confirmed goals/habits, monthly themes, summaries).
#   - Behavior scenarios with activation/deactivation and logging.
#   - Lightweight tone/pattern detection for adaptive replies.

import json
import os
import logging
from collections import deque, Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from config import DEFAULT_MODEL, SYSTEM_PROMPT, GENERATION_CONFIG, AVRORA_PROFESSIONS, AVRORA_MAIN_GOAL

logger = logging.getLogger(__name__)

MEMORY_FILE = "user_memory.json"
LONG_TERM_FILE = "long_term.json"
MAX_HISTORY_LENGTH = 200  # cap messages to control RAM
MAX_OBSERVATIONS = 200
MAX_EVENTS = 50
MAX_DIALOG_HISTORY = 200
RESTART_TIME = datetime.utcnow()

# In-memory stores
conversation_history: Dict[int, deque] = {}
user_memory: Dict[str, Dict[str, Any]] = {}
long_term: Dict[str, Dict[str, Any]] = {}
current_model: Dict[str, str] = {"name": DEFAULT_MODEL}


# ---------------------- helpers ---------------------- #
def _now() -> str:
    return datetime.utcnow().isoformat()


def _days_ago(days: int) -> datetime:
    return datetime.utcnow() - timedelta(days=days)


def _load_json(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_json(path: str, data: dict) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------- loaders ---------------------- #
def load_memory() -> None:
    global user_memory, long_term
    user_memory = _load_json(MEMORY_FILE)
    long_term = _load_json(LONG_TERM_FILE)


def save_memory() -> None:
    _save_json(MEMORY_FILE, user_memory)


def save_long_term() -> None:
    _save_json(LONG_TERM_FILE, long_term)


# ---------------------- init ---------------------- #
def _default_scenarios() -> Dict[str, Dict[str, Any]]:
    return {
        "LowMoodSupport": {"state": "INACTIVE", "last_activation": None, "data": {}},
        "ProductivityPush": {"state": "INACTIVE", "last_activation": None, "data": {}},
        "FinancialFocus": {"state": "INACTIVE", "last_activation": None, "data": {"weekly_finance_score": 0.0, "micro_goals": []}},
        "SocialBonding": {"state": "INACTIVE", "last_activation": None, "data": {}},
    }


def _default_long_term(user_id: int) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "last_summary_at": None,
        "last_seen_at": None,
        "last_greet_at": None,
        "goal_counts": {},
        "habit_counts": {},
        "confirmed_goals": [],
        "confirmed_habits": [],
        "important_events": [],
        "monthly_theme_counts": {},
        "monthly_summaries": [],
        "weekly_finance_score": 0.0,
        "plans": [],
        "forecast": {},
        "metacognition": [],
        "tuning_history": [],
        "tuning_state": {},
        "life_map": {},
        "strategic_recommendations": {},
        "strategic_risks": [],
        "mindset_profile": {},
        "last_strategy_at": None,
        "personality_scores": {},
        "personality_history": [],
        "emotion_matrix": {"anger": 0.0, "sadness": 0.0, "calmness": 0.0, "focus": 0.0, "excitement": 0.0, "fear": 0.0},
        "emotion_history": [],
        "implicit_goals": [],
        "avoided_goals": [],
        "predicted_goals": [],
        "stalled_goals": [],
    }


def init_user(user_id: int) -> None:
    """Ensure user structures exist."""
    if user_id not in conversation_history:
        conversation_history[user_id] = deque(maxlen=MAX_HISTORY_LENGTH)
        conversation_history[user_id].append({"role": "system", "content": SYSTEM_PROMPT["content"]})

    key = str(user_id)
    if key not in user_memory:
        user_memory[key] = {
            "user_id": user_id,
            "created_at": _now(),
            "updated_at": _now(),
            "message_count": 0,
            "last_message": None,
            "last_reply": None,
            "mood_score": 0.0,        # rolling sentiment score -1..1
            "progress_score": 0.0,    # heuristic progress indicator
            "goals": [],
            "habits": [],
            "mistakes": [],
            "patterns": [],
            "custom_filters": [],
            "notes": [],
            "observations": [],
            "important_events": [],
            "behavior_scenarios": _default_scenarios(),
            "dialog_history": [],
            "pending_code_action": None,
        }
    if key not in long_term:
        long_term[key] = _default_long_term(user_id)
    # Ensure dialog history structure exists
    if "dialog_history" not in user_memory[key]:
        user_memory[key]["dialog_history"] = []
    if "pending_code_action" not in user_memory[key]:
        user_memory[key]["pending_code_action"] = None
    # Rehydrate conversation history from persisted dialog history
    convo = deque(maxlen=MAX_HISTORY_LENGTH)
    convo.append({"role": "system", "content": SYSTEM_PROMPT["content"]})
    for item in user_memory[key].get("dialog_history", []):
        convo.append(item)
    conversation_history[user_id] = convo
    save_memory()
    save_long_term()


# ---------------------- conversation history ---------------------- #
def reset_history(user_id: int) -> None:
    init_user(user_id)
    conversation_history[user_id].clear()
    conversation_history[user_id].append({"role": "system", "content": SYSTEM_PROMPT["content"]})


def append_message(user_id: int, role: str, content: str) -> None:
    init_user(user_id)
    conversation_history[user_id].append(
        {"role": role, "content": content, "timestamp": _now()}
    )
    # persist to dialog_history for cross-restart memory
    key = str(user_id)
    dialog_hist = user_memory[key].get("dialog_history", [])
    dialog_hist.append({"role": role, "content": content})
    user_memory[key]["dialog_history"] = dialog_hist[-MAX_DIALOG_HISTORY:]
    save_memory()


def get_history(user_id: int) -> List[dict]:
    init_user(user_id)
    return list(conversation_history[user_id])


def set_model(model_name: str) -> None:
    current_model["name"] = model_name


def get_current_model() -> str:
    return current_model["name"]


# -------- Pattern and tone analysis --------------------------------------- #
KEYWORD_GROUPS = {
    "stress": ["стресс", "нерв", "тревог", "паник", "выгор"],
    "fatigue": ["устал", "сон", "sleep", "выспал", "засып"],
    "finance": ["деньг", "финан", "кредит", "долг", "инвест", "бюджет", "подписк"],
    "growth": ["развит", "карьер", "цель", "skill", "навык", "учусь", "учеб", "план"],
    "health": ["здоров", "спорт", "диета", "тело", "вес", "питани", "сон"],
    "relationships": ["отношен", "друз", "семь", "партнер", "любов", "конфликт"],
    "motivation": ["лень", "мотивац", "не хочу", "не могу", "апат"],
}

POSITIVE_TOKENS = ["рад", "доволен", "счаст", "класс", "ура", "отлично", "кайф", "вдохнов"]
NEGATIVE_TOKENS = ["плохо", "ужас", "груст", "злюсь", "злю", "бесит", "устал", "не хочу", "ненавиж", "страх"]


def detect_tone(text: str) -> float:
    """Very simple sentiment: returns score between -1 and 1."""
    t = text.lower()
    pos = sum(token in t for token in POSITIVE_TOKENS)
    neg = sum(token in t for token in NEGATIVE_TOKENS)
    if pos == neg == 0:
        return 0.0
    return (pos - neg) / max(pos + neg, 1)


def _update_patterns(profile: Dict[str, Any], text: str) -> Tuple[List[str], List[str], List[str]]:
    """Keyword-based detector for goals, habits, mistakes."""
    text_lower = text.lower()
    triggered = []
    for tag, tokens in KEYWORD_GROUPS.items():
        if any(token in text_lower for token in tokens):
            if tag not in profile["patterns"]:
                profile["patterns"].append(tag)
            triggered.append(tag)

    new_goals = []
    new_habits = []
    new_mistakes = []
    if "хочу" in text_lower or "цель" in text_lower:
        new_goals.append(text.strip()[:120])
    if "привыч" in text_lower:
        new_habits.append(text.strip()[:120])
    if "ошиб" in text_lower or "факап" in text_lower:
        new_mistakes.append(text.strip()[:120])

    for g in new_goals:
        if g not in profile["goals"]:
            profile["goals"].append(g)
    for h in new_habits:
        if h not in profile["habits"]:
            profile["habits"].append(h)
    for m in new_mistakes:
        if m not in profile["mistakes"]:
            profile["mistakes"].append(m)

    return new_goals, new_habits, new_mistakes


def _mark_important(profile: Dict[str, Any], text: str, tags: List[str]) -> None:
    """Mark important messages (emotionally charged or tagged)."""
    important_tokens = ["важно", "срочно", "кризис", "критич", "help", "помоги"]
    if any(tok in text.lower() for tok in important_tokens) or tags:
        profile["important_events"].append({"ts": _now(), "message": text[:200], "tags": tags})
        profile["important_events"] = profile["important_events"][-MAX_EVENTS:]


def _update_scores(profile: Dict[str, Any], tone_score: float, triggered: List[str]) -> None:
    """Update rolling mood/progress scores."""
    prev_mood = profile["mood_score"]
    prev_prog = profile["progress_score"]
    profile["mood_score"] = round((profile["mood_score"] * 0.8) + (tone_score * 0.2), 3)
    delta = 0.05 * sum(1 for t in triggered if t in {"growth", "health", "finance", "motivation"})
    delta -= 0.05 * sum(1 for t in triggered if t in {"stress", "fatigue"})
    profile["progress_score"] = round(max(-1.0, min(1.5, profile["progress_score"] + delta)), 3)
    if profile["mood_score"] != prev_mood or profile["progress_score"] != prev_prog:
        logger.info("Scores updated user=%s mood=%s->%s progress=%s->%s", profile["user_id"], prev_mood, profile["mood_score"], prev_prog, profile["progress_score"])


# -------- long-term tracking ---------------------------------------------- #
def _bump_counter(counter: Dict[str, int], key: str) -> int:
    counter[key] = counter.get(key, 0) + 1
    return counter[key]


def detect_confirmed_goals(user_id: int, goals: List[str]) -> None:
    lt = long_term[str(user_id)]
    for g in goals:
        count = _bump_counter(lt["goal_counts"], g)
        if count >= 3 and g not in lt["confirmed_goals"]:
            lt["confirmed_goals"].append(g)
            logger.info("Confirmed goal for user %s: %s", user_id, g)
    save_long_term()


def detect_habits(user_id: int, habits: List[str]) -> None:
    lt = long_term[str(user_id)]
    for h in habits:
        count = _bump_counter(lt["habit_counts"], h)
        if count >= 5 and h not in lt["confirmed_habits"]:
            lt["confirmed_habits"].append(h)
            logger.info("Confirmed habit for user %s: %s", user_id, h)
    save_long_term()


def _ensure_plan(user_id: int) -> Dict[str, Any]:
    lt = long_term[str(user_id)]
    if lt.get("plans") is None:
        lt["plans"] = []
    if lt["plans"]:
        return lt["plans"][-1]
    plan = {
        "date": _now(),
        "short": [],
        "mid": [],
        "long": [],
        "completed_short": [],
        "completed_mid": [],
        "completed_long": [],
    }
    lt["plans"].append(plan)
    return plan


def _needs_new_plan(user_id: int) -> bool:
    lt = long_term[str(user_id)]
    if not lt.get("plans"):
        return True
    try:
        last_date = datetime.fromisoformat(lt["plans"][-1]["date"])
        return last_date < _days_ago(1)
    except Exception:
        return True


def generate_plan(user_id: int, profile: Dict[str, Any]) -> Dict[str, Any]:
    """Create or refresh a plan based on goals/progress."""
    lt = long_term[str(user_id)]
    plan = _ensure_plan(user_id)
    if not _needs_new_plan(user_id):
        return plan
    goals = profile.get("goals", []) or lt.get("confirmed_goals", [])
    goal_text = goals[0] if goals else "улучшить общее состояние"
    plan = {
        "date": _now(),
        "short": [f"Сделать 1 шаг к цели: {goal_text}", "10 минут чтения/обучения", "2 минуты планирования"],
        "mid": [f"Сформировать чек-лист на неделю по цели: {goal_text}", "Проверить прогресс через 3 дня"],
        "long": [f"Оценить результаты через месяц по цели: {goal_text}"],
        "completed_short": [],
        "completed_mid": [],
        "completed_long": [],
    }
    lt["plans"].append(plan)
    logger.info("Plan generated for user %s", user_id)
    save_long_term()
    return plan


def get_plan(user_id: int) -> Dict[str, Any]:
    lt = long_term[str(user_id)]
    if lt.get("plans"):
        return lt["plans"][-1]
    return _ensure_plan(user_id)


def mark_done(user_id: int, text: str) -> str:
    """Mark a plan item done by substring or index."""
    plan = get_plan(user_id)
    lists = [("short", "completed_short"), ("mid", "completed_mid"), ("long", "completed_long")]
    for src, dest in lists:
        items = plan.get(src, [])
        # numeric index support
        try:
            idx = int(text) - 1
            if 0 <= idx < len(items):
                item = items.pop(idx)
                plan[dest].append(item)
                save_long_term()
                return f"Отмечено выполненным: {item}"
        except ValueError:
            pass
        # substring match
        for item in list(items):
            if text.lower() in item.lower():
                items.remove(item)
                plan[dest].append(item)
                save_long_term()
                return f"Отмечено выполненным: {item}"
    save_long_term()
    return "Не нашёл такой пункт в плане."


def update_themes(user_id: int, tags: List[str]) -> None:
    lt = long_term[str(user_id)]
    for tag in tags:
        lt["monthly_theme_counts"][tag] = lt["monthly_theme_counts"].get(tag, 0) + 1


def make_monthly_summary(user_id: int) -> None:
    lt = long_term[str(user_id)]
    last = lt.get("last_summary_at")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            if last_dt > _days_ago(7):
                return
        except Exception:
            pass
    themes = sorted(lt["monthly_theme_counts"].items(), key=lambda x: x[1], reverse=True)
    top_themes = ", ".join(f"{t}×{c}" for t, c in themes[:5]) or "нет данных"
    summary = {
        "created_at": _now(),
        "top_themes": top_themes,
        "goals": lt["confirmed_goals"][-5:],
        "habits": lt["confirmed_habits"][-5:],
        "weekly_finance_score": lt.get("weekly_finance_score", 0.0),
    }
    lt["monthly_summaries"].append(summary)
    lt["last_summary_at"] = _now()
    logger.info("Monthly summary generated for user %s", user_id)
    save_long_term()


# -------- behavior scenarios ---------------------------------------------- #
def _get_scenarios(user_id: int) -> Dict[str, Dict[str, Any]]:
    init_user(user_id)
    data = user_memory[str(user_id)]
    # ensure scenarios exist and include all default keys
    if "behavior_scenarios" not in data:
        data["behavior_scenarios"] = _default_scenarios()
        save_memory()
    defaults = _default_scenarios()
    for k, v in defaults.items():
        if k not in data["behavior_scenarios"]:
            data["behavior_scenarios"][k] = v.copy()
    return data["behavior_scenarios"]


def _activate(user_id: int, name: str) -> None:
    scenarios = _get_scenarios(user_id)
    scenarios[name]["state"] = "ACTIVE"
    scenarios[name]["last_activation"] = _now()
    user_memory[str(user_id)]["important_events"].append({"ts": _now(), "event": f"{name}_activated"})
    long_term[str(user_id)]["important_events"].append({"ts": _now(), "event": f"{name}_activated"})
    logger.info("Scenario activated: %s for user %s", name, user_id)
    save_memory()
    save_long_term()


def _deactivate(user_id: int, name: str) -> None:
    scenarios = _get_scenarios(user_id)
    if scenarios[name]["state"] == "ACTIVE":
        scenarios[name]["state"] = "INACTIVE"
        logger.info("Scenario deactivated: %s for user %s", name, user_id)
        save_memory()


def evaluate_scenarios(user_id: int) -> None:
    """Check conditions and activate/deactivate scenarios."""
    init_user(user_id)
    profile = user_memory[str(user_id)]
    scenarios = _get_scenarios(user_id)
    obs = profile.get("observations", [])
    last3 = obs[-3:]
    last3_tones = [o.get("tone", 0) for o in last3]

    # LowMoodSupport
    if profile["mood_score"] < -0.4 or (last3_tones and all(t <= -0.2 for t in last3_tones)):
        if scenarios["LowMoodSupport"]["state"] != "ACTIVE":
            _activate(user_id, "LowMoodSupport")
            profile["important_events"].append({"ts": _now(), "event": "mood_low_detected"})
    else:
        _deactivate(user_id, "LowMoodSupport")

    # ProductivityPush
    recent = [o for o in obs if datetime.fromisoformat(o["ts"]) > _days_ago(7)]
    goal_mentions = sum(1 for o in recent for tag in o.get("tags", []) if tag in {"growth"})
    if goal_mentions >= 2 and profile["progress_score"] < 0.3:
        if scenarios["ProductivityPush"]["state"] != "ACTIVE":
            _activate(user_id, "ProductivityPush")
            profile["important_events"].append({"ts": _now(), "event": "productivity_coach_day"})
    else:
        _deactivate(user_id, "ProductivityPush")

    # FinancialFocus
    finance_mentions = sum(1 for o in recent for tag in o.get("tags", []) if tag == "finance")
    if finance_mentions >= 3:
        if scenarios["FinancialFocus"]["state"] != "ACTIVE":
            _activate(user_id, "FinancialFocus")
        lt = long_term[str(user_id)]
        lt["weekly_finance_score"] = min(10.0, lt.get("weekly_finance_score", 0.0) + 0.5)
        save_long_term()
    else:
        _deactivate(user_id, "FinancialFocus")

    # SocialBonding
    social_mentions = sum(1 for o in recent for tag in o.get("tags", []) if tag == "relationships")
    if social_mentions >= 2 and profile["mood_score"] > -0.3:
        _activate(user_id, "SocialBonding")
    else:
        _deactivate(user_id, "SocialBonding")


def get_scenarios_report(user_id: int) -> str:
    init_user(user_id)
    scenarios = _get_scenarios(user_id)
    lines = []
    for name, data in scenarios.items():
        lines.append(f"{name}: {data['state']} (last: {data['last_activation']})")
    return "\n".join(lines)


# -------- observations pipeline ------------------------------------------- #
def add_observation(user_id: int, message_text: str) -> None:
    """Update user memory with new message context and derived insights."""
    init_user(user_id)
    profile = user_memory[str(user_id)]
    profile["message_count"] += 1
    profile["last_message"] = message_text
    profile["updated_at"] = _now()

    tone_score = detect_tone(message_text)
    new_goals, new_habits, new_mistakes = _update_patterns(profile, message_text)
    lower_text = message_text.lower()
    custom_hits = [flt for flt in profile.get("custom_filters", []) if flt and flt in lower_text]
    triggered = [p for p in profile["patterns"] if p in lower_text] + custom_hits
    _update_scores(profile, tone_score, triggered)
    _mark_important(profile, message_text, triggered)

    profile["observations"].append(
        {"ts": _now(), "message": message_text, "tone": tone_score, "tags": triggered}
    )
    profile["observations"] = profile["observations"][-MAX_OBSERVATIONS:]

    # long-term updates
    detect_confirmed_goals(user_id, new_goals)
    detect_habits(user_id, new_habits)
    update_themes(user_id, triggered)
    make_monthly_summary(user_id)
    update_emotion_matrix(user_id, message_text)
    update_personality(user_id)
    update_goal_reasoner(user_id)
    update_life_strategy(user_id)

    save_memory()


def record_reply(user_id: int, reply_text: str) -> None:
    init_user(user_id)
    profile = user_memory[str(user_id)]
    profile["last_reply"] = reply_text
    profile["updated_at"] = _now()
    save_memory()


# -------- summaries & getters --------------------------------------------- #
def get_profile_summary(user_id: int) -> str:
    init_user(user_id)
    p = user_memory[str(user_id)]
    lt = long_term[str(user_id)]
    lines = [
        f"Создано: {p['created_at']}",
        f"Сообщений: {p['message_count']}",
        f"Настроение (score): {p.get('mood_score', 0):+.2f}",
        f"Прогресс (score): {p.get('progress_score', 0):+.2f}",
        f"Цели: {', '.join(p['goals']) if p['goals'] else 'нет'}",
        f"Привычки: {', '.join(p['habits']) if p['habits'] else 'нет'}",
        f"Ошибки: {', '.join(p['mistakes']) if p['mistakes'] else 'нет'}",
        f"Темы: {', '.join(p['patterns']) if p['patterns'] else 'нет'}",
        f"Последнее сообщение: {p.get('last_message') or '—'}",
        f"Долгосрочные цели: {', '.join(lt['confirmed_goals']) if lt['confirmed_goals'] else 'нет'}",
        f"Долгосрочные привычки: {', '.join(lt['confirmed_habits']) if lt['confirmed_habits'] else 'нет'}",
    ]
    return "\n".join(lines)


def get_progress_report(user_id: int) -> str:
    init_user(user_id)
    p = user_memory[str(user_id)]
    lt = long_term[str(user_id)]
    recent = p.get("observations", [])[-10:]
    tags = Counter(tag for obs in recent for tag in obs.get("tags", []))
    top_tags = ", ".join(f"{k}×{v}" for k, v in tags.most_common()) or "нет данных"
    return (
        f"Сообщений: {p['message_count']}\n"
        f"Настроение: {p.get('mood_score', 0):+.2f}\n"
        f"Прогресс: {p.get('progress_score', 0):+.2f}\n"
        f"Темы последних сообщений: {top_tags}\n"
        f"Цели: {', '.join(p['goals']) if p['goals'] else 'нет'}\n"
        f"Привычки: {', '.join(p['habits']) if p['habits'] else 'нет'}\n"
        f"Ошибки: {', '.join(p['mistakes']) if p['mistakes'] else 'нет'}\n"
        f"Долгосрочные цели: {', '.join(lt['confirmed_goals']) if lt['confirmed_goals'] else 'нет'}\n"
        f"Долгосрочные привычки: {', '.join(lt['confirmed_habits']) if lt['confirmed_habits'] else 'нет'}"
    )


def get_month_summary(user_id: int) -> str:
    init_user(user_id)
    summaries = long_term[str(user_id)]["monthly_summaries"]
    if not summaries:
        return "Нет сводок за месяц."
    last = summaries[-1]
    return (
        f"Дата: {last['created_at']}\n"
        f"Топ темы: {last['top_themes']}\n"
        f"Цели: {', '.join(last['goals']) if last['goals'] else 'нет'}\n"
        f"Привычки: {', '.join(last['habits']) if last['habits'] else 'нет'}\n"
        f"Финансы (неделя): {last.get('weekly_finance_score', 0)}"
    )


def get_goals(user_id: int) -> List[str]:
    init_user(user_id)
    return long_term[str(user_id)]["confirmed_goals"]


def get_habits(user_id: int) -> List[str]:
    init_user(user_id)
    return long_term[str(user_id)]["confirmed_habits"]


def add_custom_filter(user_id: int, pattern: str) -> None:
    """Custom user-defined keyword to track."""
    init_user(user_id)
    p = user_memory[str(user_id)]
    if pattern and pattern not in p["custom_filters"]:
        p["custom_filters"].append(pattern)
    p["updated_at"] = _now()
    save_memory()


def get_custom_filters(user_id: int) -> List[str]:
    init_user(user_id)
    return user_memory[str(user_id)].get("custom_filters", [])


def get_profile(user_id: int) -> Dict[str, Any]:
    init_user(user_id)
    return user_memory[str(user_id)]


def get_active_scenarios(user_id: int) -> List[str]:
    init_user(user_id)
    return [name for name, data in _get_scenarios(user_id).items() if data["state"] == "ACTIVE"]


def set_last_seen(user_id: int) -> None:
    init_user(user_id)
    long_term[str(user_id)]["last_seen_at"] = _now()
    save_long_term()


def get_last_seen(user_id: int):
    init_user(user_id)
    ts = long_term[str(user_id)].get("last_seen_at")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def set_last_greet(user_id: int) -> None:
    init_user(user_id)
    long_term[str(user_id)]["last_greet_at"] = _now()
    save_long_term()


def get_last_greet(user_id: int):
    init_user(user_id)
    ts = long_term[str(user_id)].get("last_greet_at")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def set_pending_action(user_id: int, action: dict) -> None:
    init_user(user_id)
    user_memory[str(user_id)]["pending_code_action"] = action
    save_memory()


def get_pending_action(user_id: int) -> dict:
    init_user(user_id)
    return user_memory[str(user_id)].get("pending_code_action")


def clear_pending_action(user_id: int) -> None:
    init_user(user_id)
    user_memory[str(user_id)]["pending_code_action"] = None
    save_memory()


# -------- metacognition --------------------------------------------------- #
def evaluate_metacognition(user_id: int, last_user: str, last_reply: str) -> Dict[str, float]:
    """Simple self-eval: length balance, scenario alignment, mood impact."""
    init_user(user_id)
    profile = user_memory[str(user_id)]
    lt = long_term[str(user_id)]
    user_len = len(last_user or "")
    reply_len = len(last_reply or "")
    length_score = 0.5 if user_len == 0 else min(1.0, (reply_len / user_len))
    length_score = 1.0 - abs(length_score - 1.0)  # closer to equal is better
    # scenario alignment (penalize if mood low but no LowMoodSupport active)
    active = get_active_scenarios(user_id)
    align = 1.0
    if profile.get("mood_score", 0) < -0.3 and "LowMoodSupport" not in active:
        align = 0.5
    empathy_score = max(0.2, min(1.0, 0.6 + profile.get("mood_score", 0) * 0.5))
    motivation_score = max(0.2, min(1.0, 0.6 + profile.get("progress_score", 0) * 0.5))
    reply_quality = round((length_score + align + empathy_score + motivation_score) / 4, 3)
    entry = {
        "ts": _now(),
        "reply_quality_score": reply_quality,
        "empathy_score": round(empathy_score, 3),
        "motivation_score": round(motivation_score, 3),
    }
    lt.setdefault("metacognition", []).append(entry)
    lt["metacognition"] = lt["metacognition"][-50:]
    logger.info("Metacog user=%s quality=%.2f empathy=%.2f motivation=%.2f", user_id, reply_quality, empathy_score, motivation_score)
    save_long_term()
    return entry


def adjust_from_metacognition(user_id: int) -> Dict[str, Any]:
    """Set simple tuning hints based on last metacog scores."""
    lt = long_term[str(user_id)]
    history = lt.get("metacognition", [])
    if not history:
        return {}
    last = history[-1]
    tuning = lt.get("tuning_state", {})
    rec_temp = tuning.get("temperature", GENERATION_CONFIG.get("temperature", 0.9))
    rec_top_p = tuning.get("topP", GENERATION_CONFIG.get("topP", 0.9))
    if last["reply_quality_score"] < 0.6:
        rec_temp = max(0.6, rec_temp - 0.1)
        rec_top_p = max(0.8, rec_top_p - 0.05)
    tuning.update({"temperature": rec_temp, "topP": rec_top_p, "last_adjusted": _now()})
    lt["tuning_state"] = tuning
    logger.info("Metacog adjust user=%s temp=%.2f topP=%.2f", user_id, rec_temp, rec_top_p)
    save_long_term()
    return tuning


# -------- forecasting ----------------------------------------------------- #
def forecast_user(user_id: int) -> Dict[str, Any]:
    """Heuristic forecasts for mood, crisis, goals, themes."""
    init_user(user_id)
    profile = user_memory[str(user_id)]
    lt = long_term[str(user_id)]
    mood = profile.get("mood_score", 0)
    progress = profile.get("progress_score", 0)
    mood_forecast = [round(max(-1.0, min(1.0, mood - 0.05 * i)), 2) for i in range(1, 4)]
    crisis_risk = {
        "low_mood": 0.7 if mood < -0.2 else 0.3,
        "burnout": 0.6 if "fatigue" in profile.get("patterns", []) else 0.2,
        "financial": 0.6 if "finance" in profile.get("patterns", []) else 0.2,
    }
    goal_pred = {
        "achieve_goal_prob": round(min(0.9, 0.4 + progress * 0.5), 2),
        "needs_push": progress < 0.35,
    }
    themes = profile.get("patterns", [])
    theme_prediction = themes[:3] if themes else []
    forecast = {
        "mood_forecast": mood_forecast,
        "crisis_risk": crisis_risk,
        "goal_prediction": goal_pred,
        "theme_prediction": theme_prediction,
        "ts": _now(),
    }
    lt["forecast"] = forecast
    save_long_term()
    return forecast


# -------- self-tuning ----------------------------------------------------- #
def self_tuning(user_id: int) -> Dict[str, Any]:
    """Analyze history to adjust generation recommendations."""
    init_user(user_id)
    lt = long_term[str(user_id)]
    profile = user_memory[str(user_id)]
    tuning = lt.get("tuning_state", {}).copy()
    observations = profile.get("observations", [])[-20:]
    ignored = sum(1 for o in observations if "!" not in o.get("message", ""))
    # simple heuristic: if many ignored messages, reduce length/temperature
    if ignored > 10:
        tuning["temperature"] = max(0.6, tuning.get("temperature", GENERATION_CONFIG.get("temperature", 0.9)) - 0.1)
        tuning["maxOutputTokens"] = 2048
    else:
        tuning["temperature"] = tuning.get("temperature", GENERATION_CONFIG.get("temperature", 0.9))
    tuning["updated_at"] = _now()
    lt.setdefault("tuning_history", []).append(tuning.copy())
    lt["tuning_history"] = lt["tuning_history"][-50:]
    lt["tuning_state"] = tuning
    logger.info("Self-tuning user=%s tuning=%s", user_id, tuning)
    save_long_term()
    return tuning


# -------- emotion matrix -------------------------------------------------- #
EMOTION_KEYWORDS = {
    "anger": ["злю", "злость", "бесит", "ярость"],
    "sadness": ["грусть", "печаль", "плохо", "одиноч"],
    "calmness": ["спокоен", "тихо", "ровно", "спокойствие"],
    "focus": ["фокус", "концентрац", "собран", "вниман"],
    "excitement": ["рад", "кайф", "вдохнов", "класс"],
    "fear": ["страх", "боюсь", "тревог", "паник"],
}


def update_emotion_matrix(user_id: int, text: str) -> Dict[str, float]:
    init_user(user_id)
    lt = long_term[str(user_id)]
    matrix = lt.get("emotion_matrix", {}).copy()
    t = text.lower()
    for emo, keys in EMOTION_KEYWORDS.items():
        if any(k in t for k in keys):
            matrix[emo] = round(min(1.0, matrix.get(emo, 0.0) + 0.1), 3)
        else:
            matrix[emo] = round(max(0.0, matrix.get(emo, 0.0) * 0.98), 3)
    lt["emotion_matrix"] = matrix
    lt.setdefault("emotion_history", []).append({"ts": _now(), "matrix": matrix})
    lt["emotion_history"] = lt["emotion_history"][-200:]
    save_long_term()
    return matrix


# -------- personality modeling ------------------------------------------- #
def update_personality(user_id: int) -> Dict[str, float]:
    init_user(user_id)
    lt = long_term[str(user_id)]
    profile = user_memory[str(user_id)]
    scores = lt.get("personality_scores", {
        "discipline": 0.5, "emotional_stability": 0.5, "decisiveness": 0.5,
        "creativity": 0.5, "social_energy": 0.5, "financial_maturity": 0.5
    })
    mood = profile.get("mood_score", 0)
    prog = profile.get("progress_score", 0)
    patterns = profile.get("patterns", [])
    obs = profile.get("observations", [])[-10:]
    mentions_goals = sum("growth" in o.get("tags", []) for o in obs)
    mentions_fin = sum("finance" in o.get("tags", []) for o in obs)
    discipline = min(1.0, max(0.0, scores["discipline"] + 0.05 * mentions_goals))
    emotional_stability = min(1.0, max(0.0, 0.6 + mood * 0.4))
    decisiveness = min(1.0, max(0.0, scores["decisiveness"] + (0.05 if prog > 0.3 else -0.02)))
    creativity = min(1.0, max(0.0, scores["creativity"] + (0.03 if "motivation" in patterns else 0)))
    social_energy = min(1.0, max(0.0, scores["social_energy"] + (0.02 if "relationships" in patterns else -0.01)))
    financial_maturity = min(1.0, max(0.0, scores["financial_maturity"] + 0.05 * mentions_fin))
    scores.update({
        "discipline": round(discipline, 3),
        "emotional_stability": round(emotional_stability, 3),
        "decisiveness": round(decisiveness, 3),
        "creativity": round(creativity, 3),
        "social_energy": round(social_energy, 3),
        "financial_maturity": round(financial_maturity, 3),
    })
    lt["personality_scores"] = scores
    lt.setdefault("personality_history", []).append({"ts": _now(), "scores": scores})
    lt["personality_history"] = lt["personality_history"][-100:]
    save_long_term()
    return scores


# -------- life strategy --------------------------------------------------- #
def update_life_strategy(user_id: int) -> None:
    init_user(user_id)
    lt = long_term[str(user_id)]
    profile = user_memory[str(user_id)]
    patterns = profile.get("patterns", [])
    mood = profile.get("mood_score", 0)
    progress = profile.get("progress_score", 0)
    last = lt.get("last_strategy_at")
    if last:
        try:
            if datetime.fromisoformat(last) > _days_ago(5) and progress > 0.4:
                return
        except Exception:
            pass
    strengths = []
    weaknesses = []
    directions = ["финансы", "карьера", "психология", "дисциплина", "отношения", "стиль жизни"]
    if "finance" in patterns:
        strengths.append("финансовая осознанность") if progress > 0.3 else weaknesses.append("финансовая гигиена")
    if "growth" in patterns:
        strengths.append("ориентация на развитие")
    if mood < -0.2:
        weaknesses.append("эмоциональная устойчивость")
    if progress < 0.2:
        weaknesses.append("дисциплина/планирование")
    life_map = {
        "directions": directions,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }
    recommendations = {
        "S1": "Выбери один навык и тренируй 15 минут в день ближайшие 3 недели.",
        "S2": "Сделай weekly review и убери лишние обязательства.",
        "S3": "Добавь короткие практики восстановления (сон/дыхание/прогулки).",
    }
    risks = []
    if mood < -0.3:
        risks.append("Потенциальное выгорание — снизить нагрузку, добавить отдых.")
    if "finance" in patterns:
        risks.append("Финансовый стресс — контроль подписок и трат.")
    mindset = {
        "thinking_style": "growth" if progress > 0 else "recover",
        "focus": "balance короткие шаги и отдых",
    }
    lt["life_map"] = life_map
    lt["strategic_recommendations"] = recommendations
    lt["strategic_risks"] = risks
    lt["mindset_profile"] = mindset
    lt["last_strategy_at"] = _now()
    save_long_term()


# -------- goal reasoner --------------------------------------------------- #
def update_goal_reasoner(user_id: int) -> None:
    init_user(user_id)
    lt = long_term[str(user_id)]
    profile = user_memory[str(user_id)]
    patterns = profile.get("patterns", [])
    goals = profile.get("goals", []) + lt.get("confirmed_goals", [])
    implicit = lt.get("implicit_goals", [])
    avoided = lt.get("avoided_goals", [])
    predicted = lt.get("predicted_goals", [])
    stalled = lt.get("stalled_goals", [])

    if "growth" in patterns and goals:
        for g in goals:
            if g not in implicit:
                implicit.append(g)
    if profile.get("progress_score", 0) < 0.2 and goals:
        for g in goals:
            if g not in stalled:
                stalled.append(g)
    if "finance" in patterns:
        if "финансовая подушка" not in predicted:
            predicted.append("финансовая подушка")
    if profile.get("mood_score", 0) < -0.3 and goals:
        avoided.append("эмоциональные запросы")

    lt["implicit_goals"] = implicit[-50:]
    lt["avoided_goals"] = avoided[-50:]
    lt["predicted_goals"] = predicted[-50:]
    lt["stalled_goals"] = stalled[-50:]
    save_long_term()


# -------- auto-step runner ----------------------------------------------- #
def run_autonomy(user_id: int, text: str) -> None:
    """Invoke forecasting/planner/life strategy/personality/goal reasoner/emotions."""
    forecast_user(user_id)
    profile = user_memory[str(user_id)]
    generate_plan(user_id, profile)
    update_life_strategy(user_id)
    update_personality(user_id)
    update_goal_reasoner(user_id)
    update_emotion_matrix(user_id, text)


# -------- super-context helpers ------------------------------------------ #
def build_super_context(user_id: int) -> str:
    """Return compact overview for Gemini: scenarios, plans, forecasts, metacog, tuning, long-term, strategy, personality, emotions, goals."""
    init_user(user_id)
    lt = long_term[str(user_id)]
    active = get_active_scenarios(user_id)
    plan = get_plan(user_id)
    forecast = lt.get("forecast", {})
    metacog = lt.get("metacognition", [])
    metacog_last = metacog[-1] if metacog else {}
    tuning = lt.get("tuning_state", {})
    life_map = lt.get("life_map", {})
    strat_rec = lt.get("strategic_recommendations", {})
    strat_risks = lt.get("strategic_risks", [])
    mindset = lt.get("mindset_profile", {})
    personality = lt.get("personality_scores", {})
    emotions = lt.get("emotion_matrix", {})
    top_emotions = sorted(emotions.items(), key=lambda x: x[1], reverse=True)[:3] if emotions else []
    goal_reason = {
        "implicit": lt.get("implicit_goals", []),
        "avoided": lt.get("avoided_goals", []),
        "predicted": lt.get("predicted_goals", []),
        "stalled": lt.get("stalled_goals", []),
    }
    summary = [
        f"Главная цель: {AVRORA_MAIN_GOAL}",
        f"Профессии Авроры: {AVRORA_PROFESSIONS}",
        f"Сценарии: {', '.join(active) if active else 'нет'}",
        f"План: short={plan.get('short', [])} mid={plan.get('mid', [])} long={plan.get('long', [])}",
        f"Прогноз: {forecast}",
        f"Самооценка: {metacog_last}" if metacog_last else "Самооценка: нет",
        f"Тюнинг: {tuning}" if tuning else "Тюнинг: нет",
        f"Долгосрочные цели: {lt.get('confirmed_goals', [])}",
        f"Долгосрочные привычки: {lt.get('confirmed_habits', [])}",
        f"Стратегическая карта: {life_map}",
        f"Стратегические рекомендации: {strat_rec}",
        f"Стратегические риски: {strat_risks}",
        f"Mindset: {mindset}",
        f"Личность: {personality}",
        f"Эмоции (топ-3): {top_emotions}",
        f"Целевой анализ: {goal_reason}",
    ]
    return "\n".join(summary)


# -------- soft reboot ----------------------------------------------------- #
def soft_reboot(user_id: int) -> None:
    """Reset transient states but keep long-term memory."""
    init_user(user_id)
    conversation_history[user_id].clear()
    conversation_history[user_id].append({"role": "system", "content": SYSTEM_PROMPT["content"]})
    user_memory[str(user_id)]["behavior_scenarios"] = _default_scenarios()
    user_memory[str(user_id)]["observations"] = []
    user_memory[str(user_id)]["important_events"] = []
    save_memory()


# Initialize memory on import
load_memory()
