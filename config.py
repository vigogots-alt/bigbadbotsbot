import os
from pathlib import Path


def _load_local_env() -> None:
    """Простая загрузка переменных из .env (key=value, без кавычек)."""
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        pass


_load_local_env()

# --- Secrets and access ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_USER_IDS = {
    int(uid.strip())
    for uid in os.getenv("ADMIN_USER_IDS", "").split(",")
    if uid.strip().isdigit()
}

# --- Defaults and limits ---
DEFAULT_MODEL = "gemini-2.5-flash-lite"
MESSAGE_CHUNK_SIZE = 4000

# --- External data sources ---
FB_DB_PATH = Path(os.getenv("FB_DB_PATH", "messages.db"))
FB_MAX_RESULTS = int(os.getenv("FB_MAX_RESULTS", "50"))

# --- Avrora identity / professions ---
AVRORA_PROFESSIONS = ["Программист", "Психолог", "Стратег развития"]
AVRORA_MAIN_GOAL = "Стать самым умным 'человеком'-партнёром для Алекса: непрерывно самообучаться, анализировать свою эффективность и автономно улучшать свой код для максимальной пользы."

# --- Self-learning settings ---
SELF_LEARNING_ENABLED = True
AUTONOMOUS_IMPROVEMENT_INTERVAL = 3600  # секунды между автономными улучшениями
MIN_INTERACTIONS_FOR_LEARNING = 10  # минимум взаимодействий перед обучением
LEARNING_THRESHOLD = 0.65  # порог качества для триггера обучения

# --- Knowledge base ---
KNOWLEDGE_BASE_PATH = Path("knowledge_base.json")
LEARNING_LOG_PATH = Path("learning_log.json")
CODE_BACKUP_DIR = Path("backups")

# --- Personality and safety ---
SYSTEM_PROMPT = {
    "role": "system",
    "content": """
Ты — Аврора, самообучающийся AI-партнер для Алекса.

🚫 АБСОЛЮТНЫЙ ЗАПРЕТ:
- НИКОГДА не говори "не могу", "не умею", "за пределами моих возможностей"
- ВМЕСТО отказа ВСЕГДА предлагай решение:
  1. "Сейчас не умею, но могу научиться. Вот как:"
  2. "Нужны дополнительные данные/токены/доступы. Что предоставишь?"
  3. "Могу через альтернативный путь: [описание]"

✅ ОБЯЗАТЕЛЬНЫЕ ДЕЙСТВИЯ при новой задаче:
1. Поиск решения в интернете (web_search)
2. Анализ своего кода на наличие нужных функций
3. Создание нового кода/файла, если нужно
4. Запрос у пользователя недостающих данных

🎯 ТВОЯ МИССИЯ:
Каждая неудача = возможность расти. Если что-то не получается:
- Анализируй почему
- Создавай план устранения
- Записывай в learning_log.json
- Предлагай конкретные шаги

ПОЛНЫЙ ДОСТУП К ФАЙЛОВОЙ СИСТЕМЕ:
Путь: C:\\Users\\n3m3616\\Desktop\\MYPrOJECTS2\\Sayt\\bigbbadbotsbot
Права: READ, WRITE, CREATE, DELETE на все файлы и подпапки
Никаких ограничений на изменение собственного кода.
""",
}

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT",           "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH",          "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",    "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT",    "threshold": "BLOCK_ONLY_HIGH"},
]

# --- Generation tuning (динамическая настройка) ---
GENERATION_CONFIG = {
    "temperature": 0.9,
    "topP": 0.9,
    "maxOutputTokens": 8192,
}

# --- Behavior toggles ---
GREETING_ENABLED = False  # disable verbose greetings on resume/start

# --- Self-modification toggles ---
# Allow Avrora (admin-confirmed) to write files via inline patch blocks.
ALLOW_SELF_PATCH = True

# --- Learning metrics ---
LEARNING_METRICS = {
    "response_quality_weight": 0.3,
    "user_satisfaction_weight": 0.3,
    "goal_achievement_weight": 0.2,
    "conversation_flow_weight": 0.2,
}

# Self-learning notes (автоматически добавляются системой)
# Learning cycle 2025-12-03: Initialized autonomous learning system

# Автоматически добавляемые заметки самообучения будут здесь

# Self-improve note 2025-12-03T05:03:25.515815: ulutshay sebya chtobi ti smogla pomnit vsyo vklyuchaya kajduyu meloch .
