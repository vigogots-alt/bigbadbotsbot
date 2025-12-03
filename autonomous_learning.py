import json
from pathlib import Path
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


class LearningEngine:
    def __init__(self):
        self.skills_db = Path("skills_database.json")
        self.learning_log = Path("learning_log.json")
        self.skills = self._load_skills()
    
    def _load_skills(self):
        if self.skills_db.exists():
            return json.loads(self.skills_db.read_text(encoding="utf-8"))
        return {}
    
    def _save_skills(self):
        self.skills_db.write_text(
            json.dumps(self.skills, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    def has_skill(self, skill_name: str) -> bool:
        """Проверить наличие навыка"""
        return skill_name in self.skills
    
    def add_skill(self, skill_name: str, implementation: dict):
        """Добавить новый навык"""
        self.skills[skill_name] = {
            "learned_at": datetime.utcnow().isoformat(),
            "implementation": implementation,
            "usage_count": 0
        }
        self._save_skills()
        
        # Записать в лог
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "skill_learned",
            "skill": skill_name,
            "details": implementation
        }
        
        logs = []
        if self.learning_log.exists():
            logs = json.loads(self.learning_log.read_text(encoding="utf-8"))
        
        logs.append(log_entry)
        self.learning_log.write_text(
            json.dumps(logs, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        logger.info(f"New skill learned: {skill_name}")
    
    def use_skill(self, skill_name: str):
        """Использовать навык"""
        if skill_name in self.skills:
            self.skills[skill_name]["usage_count"] += 1
            self.skills[skill_name]["last_used"] = datetime.utcnow().isoformat()
            self._save_skills()
            return self.skills[skill_name]["implementation"]
        return None

    async def web_search(self, query: str):
        """Простой веб-поиск (DuckDuckGo HTML) — возвращает список dict."""
        import re
        from html import unescape
        import requests

        def _fetch():
            try:
                resp = requests.get(
                    "https://duckduckgo.com/html/",
                    params={"q": query},
                    timeout=8,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                resp.raise_for_status()
                results = []
                for match in re.finditer(r'result__a" href="([^"]+)"[^>]*>([^<]+)</a>', resp.text):
                    url = unescape(match.group(1))
                    title = unescape(match.group(2))
                    results.append({"title": title, "url": url, "snippet": ""})
                    if len(results) >= 5:
                        break
                return results
            except Exception as e:
                logger.exception("Web search error: %s", e)
                return [{"title": "search_error", "url": "", "snippet": str(e)}]

        return await asyncio.to_thread(_fetch)


# Глобальный экземпляр
learning_engine = LearningEngine()
