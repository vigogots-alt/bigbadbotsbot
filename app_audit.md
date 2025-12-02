# App Intelligence Passport (v5)

## 1. Summary
- Проект: Telegram-бот на python-telegram-bot, интеграция с Gemini API, держит краткосрочную и долгосрочную память, сценарии поведения, прогнозы, планировщик, метасознание, тюнинг.
- Основные модули: `state.py` (память, сценарии, стратегии, прогнозы, тюнинг), `handlers.py` (команды, сбор контекста, вызов Gemini), `main.py` (запуск, регистрация хендлеров).
- Сильные стороны: богата логика персонализации; есть метасознание и тюнинг; супер-контекст обогащает ответы.
- Слабые стороны: отсутствие миграций данных, конкурирующие записи JSON без блокировок, повреждённые строковые константы (кодировка), риск переполнения super-context, нет безопасной обработки старых long_term/user_memory.

## 2. High-level structure
- `config.py`: env-загрузка, системный промпт, safety, generationConfig.
- `state.py`: память, сценарии, long_term, эмоции, личность, стратегия, прогнозы, planner, goal reasoner, метасознание, тюнинг, super-context.
- `handlers.py`: команды (/start, /help, /clear, /model, /memory, /progress, /tips, /scenarios, /goals, /habits, /month, /forecast, /plan, /done, /strategy, /mindset, /personality, /goaldeep, /selfcheck, /tuning, /reboot, /status, /die), построение payload, вызов Gemini, пост-обработка (metacognition/self-tuning).
- `main.py`: логирование, построение Application, регистрация команд, run_polling.
- Данные: user_memory.json (оперативная память пользователей), long_term.json (стратегические/прогностические данные, планы и т.п.), veran_dominator.log/bot.log (логи).

## 3. Data lifecycle map
1) Сообщение → `handlers.process_message`: append_message(user), add_observation, run_autonomy (forecast/plan/strategy/personality/goals/emotions), evaluate_scenarios.
2) Сбор super-context + adaptive style → запрос в Gemini → ответ → append_message(model) → metacognition, adjust_from_metacognition, self_tuning.
3) Сохранение: user_memory/long_term через save_* в state.py (без блокировок).

## 4. Behavioral scenarios map
- LowMoodSupport: триггер mood_score<-0.4 или 3 отриц. тона; события mood_low_detected.
- ProductivityPush: ≥2 упоминаний роста за 7 дней и progress_score<0.3; событие productivity_coach_day.
- FinancialFocus: ≥3 финтриггера за 7 дней; weekly_finance_score++.
- Сценарии хранятся в behavior_scenarios (state.py), включаются в super-context.

## 5. Long-term memory model
- Файл: long_term.json, ключ на user_id.
- Поля: last_summary_at, goal_counts/habit_counts, confirmed_goals/habits, important_events, monthly_theme_counts/summaries, weekly_finance_score, plans[], forecast{}, metacognition[], tuning_history/state, life_map, strategic_recommendations/risks, mindset_profile, personality_scores/history, emotion_matrix/history, implicit/avoided/predicted/stalled goals.
- Обновление: add_observation (goals/habits/themes/summary/emotions/personality/life_strategy/goal_reasoner), run_autonomy/forecast_user/generate_plan и др.

## 6. Personality & Emotion engine
- Emotion matrix: anger/sadness/calmness/focus/excitement/fear по ключевым словам, история emotion_history.
- Personality scores: дисциплина, эмоциональная стабильность, решительность, креативность, социальная энергия, финансовая зрелость; обновление по mood/progress/паттернам/наблюдениям; история.

## 7. Forecasting engine
- forecast_user: mood_forecast (3 дня), crisis_risk (low_mood/burnout/financial), goal_prediction, theme_prediction, ts.
- forecaster вызывается в run_autonomy/add_observation.

## 8. Strategy engine
- life_strategy: life_map (направления, strengths/weaknesses), strategic_recommendations (S1-S3), strategic_risks, mindset_profile, last_strategy_at (пересчёт раз в 5 дней или при низком прогрессе).
- Связано с паттернами, mood/progress, confirmed goals/habits.

## 9. Tuning engine
- metacognition: eval качества ответа (длина, эмпатия, мотивация, сценарии) → metacognition[] → adjust_from_metacognition (temperature/topP).
- self_tuning: смотрит на “ignored” сообщения, корректирует temperature/maxTokens, ведёт tuning_history/state.
- adjust_reply_style подтягивает tuning_state при построении payload.

## 10. Слабые места (кратко)
- Нет миграций для старых user_memory/long_term (KeyError риск).
- Нет файловых блокировок при параллельной записи JSON (race/corruption).
- Повреждённые строковые константы/ключевые слова (кодировка) → паттерны/эмоции/выводы могут не работать.
- super-context чрезмерно раздувается (риск превышения токенов, задержки).
- Отсутствие токенизации/ограничения содержимого для Gemini.
- Нет нормализации входов для personality/emotion/goal reasoner (эвристики шумные).
- Планировщик/стратегия вызываются на каждое сообщение → избыточные записи long_term.
- run_autonomy без try/lock — может конфликтовать при нескольких инстансах.
- Нет health/migrations/tests.

## 11. Предложения v5
- Добавить миграции user_memory/long_term с версионным полем schema_version.
- Ввести file-lock (fasteners/portalocker) или переход на sqlite/postgres для памяти; транзакции для планов/прогнозов.
- Нормализовать строковые константы (UTF-8), заменить повреждённые списки KEYWORD_GROUPS/EMOTION_KEYWORDS/POSITIVE/NEGATIVE.
- Сжать super-context: лимит по токенам, агрегированные summary-блоки, эвристика отбора свежих данных.
- Дедупликация вызовов life_strategy/plan/forecast (schedule раз в N часов или на событие).
- Добавить health-check и retry/backoff для Gemini; валидацию респондов.
- Тесты: unit для pattern detection, scenarios, planner, metacog/tuning; интеграционный мок Gemini.
- Ввести safety-layer (фильтрация токсичных входов, контроль maxOutputTokens).

## 12. Предложения v6
- narrative_memory с авто-конденсацией и ссылками на ключевые события.
- self-correction loops: сравнение ожидания/факта по метрикам удовлетворённости.
- user modeling v2: ML-кластеризация паттернов, вероятностные профили.
- dynamic objectives: постановка/трекер целей на основе диалога и внешних сигналов.
- auto-compression: эмбеддинги + суммари для long_term/super-context.
- safety-layer: контент-фильтры, политика ответа, разделение ролей (coach/guardian).

## 13. Полный diff предложенных исправлений
- Миграции: при load_memory/load_long_term добавлять отсутствующие ключи (behavior_scenarios, life_map, personality_scores, emotion_matrix, планы и т.д.) и schema_version.
- Локинг файлов: обернуть _save_json/_load_json с блокировкой; или заменить на sqlite (refactor).
- Исправить кодировку: переписать KEYWORD_GROUPS, POSITIVE/NEGATIVE, EMOTION_KEYWORDS, строки прогресс-отчётов и планов в ASCII/UTF-8.
- Сжать super-context: выделить функцию assemble_super_context(max_tokens), суммаризация крупных полей (сводки/топ-N).
- Ограничить частоту run_autonomy/life_strategy/plan: scheduler или таймстемпы, не чаще 1 раз в N минут/часов.
- Добавить safe get/update для long_term/user_memory (dict.get + defaults) чтобы исключить KeyError на старых данных.
- Добавить флаги для отключения тяжёлых подсистем (forecast/plan/strategy) при ошибках или перегрузе.

## 14. Чек-лист улучшений
- [ ] Ввести schema_version и миграции user_memory/long_term.
- [ ] Добавить файловый lock или БД.
- [ ] Переписать списки ключевых слов/строк с нормальной кодировкой.
- [ ] Добавить ограничение размера super-context + суммари.
- [ ] Нормализовать частоту запуска life_strategy/plan/forecast.
- [ ] Добавить unit-тесты на сценарии/паттерны/эмоции/планы/метасознание.
- [ ] Добавить health-check и обработку ошибок Gemini.
- [ ] Внедрить safety-layer и лимит maxOutputTokens/temperature per-user.
- [ ] Добавить CLI/команду для миграции и сброса transient state.
