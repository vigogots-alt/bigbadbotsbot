# Files Overview

| Файл | Назначение | Пример логики / что хранит |
| --- | --- | --- |
| `config.py` | Глобальные настройки: загрузка .env, токены, параметры генерации, системный промпт, профессии/цель Авроры. | `AVRORA_PROFESSIONS`, `AVRORA_MAIN_GOAL`, `SYSTEM_PROMPT`, `SAFETY_SETTINGS`, `GENERATION_CONFIG`. |
| `state.py` | Все данные и алгоритмы: краткосрочная история, user_memory, long_term, сценарии, эмоции, личность, стратегия, прогнозы, планировщик, метасознание/тюнинг, super-context, журнал pending действий. | `add_observation` (обновляет память и long_term), `evaluate_scenarios`, `forecast_user`, `generate_plan`, `update_life_strategy`, `update_personality`, `build_super_context`, `dialog_history` для продолжения диалога после рестартов. |
| `handlers.py` | Хендлеры Telegram: команды, обработка текста, сбор payload для Gemini, адаптивный стиль, handshake для изменений кода/самоулучшений, автоприветствие после рестарта. | `handle_text` (handshake → greet → process_message), `adjust_reply_style`, `build_payload`, команды `/start`, `/model`, `/memory`, `/progress`, `/tips`, `/forecast`, `/plan`, `/done`, `/strategy`, `/restart`, кодовые команды `333 Code 333 ...` + `nemesis`. |
| `main.py` | Точка входа: настройка логов, загрузка памяти, регистрация команд, запуск polling, lock-файл для единственного экземпляра, обработка Conflict. | `acquire_single_instance_lock()`, `application.run_polling(...)`, команда `/restart` регистрируется здесь. |
| `app_audit.md` | Паспорт/аудит приложения: структура, потоки данных, слабые места, предложения v5/v6. | Разделы Summary, Data lifecycle, Scenarios map, Long-term memory, Risks и улучшения. |
| `files_overview.md` | Этот файл — краткий справочник по файлам проекта. | Таблица «Файл → Назначение → Пример логики». |
| `long_term.json` | Долгосрочная память по user_id: цели/привычки, планы, прогнозы, стратегия, метасознание, тюнинг, эмоции, личность, goal reasoner, отметки времени. | `plans`, `forecast`, `life_map`, `strategic_recommendations`, `personality_scores`, `emotion_matrix`, `implicit_goals`, `last_seen_at`. |
| `user_memory.json` | Оперативная память по user_id: история сообщений (dialog_history), паттерны, теги, сценарии, временные pending действия. | `dialog_history`, `behavior_scenarios`, `pending_code_action`. |
| `requirements.txt` | Список Python-зависимостей. | `python-telegram-bot`, `requests`, `psutil`. |
| `runtime.txt` | Версия Python для деплоя. | `3.11.9`. |
| `render.yaml` | Манифест деплоя на Render (worker). | build/start команды, env vars. |
