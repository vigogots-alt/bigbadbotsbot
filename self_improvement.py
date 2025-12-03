from pathlib import Path
import json
from datetime import datetime


class SelfImprover:
    def __init__(self):
        self.improvements_log = Path("improvements_log.json")
        self.code_backups = Path("code_backups")
        self.code_backups.mkdir(exist_ok=True)
    
    def analyze_own_code(self):
        """Анализ собственного кода"""
        issues = []
        
        # Проверить все .py файлы
        py_files = list(Path(".").glob("*.py"))
        
        for file in py_files:
            content = file.read_text(encoding="utf-8")
            
            # Искать анти-паттерны
            if "не могу" in content.lower():
                issues.append({
                    "file": str(file),
                    "issue": "Найдена фраза 'не могу'",
                    "severity": "high"
                })
            
            # Искать TODO
            if "TODO" in content:
                issues.append({
                    "file": str(file),
                    "issue": "Есть незавершенные TODO",
                    "severity": "medium"
                })
        
        return issues
    
    def propose_improvement(self, issue: dict) -> str:
        """Предложить улучшение"""
        proposals = {
            "Найдена фраза 'не могу'": "Заменить на конструктивное предложение решения",
            "Есть незавершенные TODO": "Реализовать или убрать TODO"
        }
        
        return proposals.get(issue["issue"], "Требуется анализ")
    
    def backup_code(self):
        """Создать бэкап перед изменениями"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.code_backups / timestamp
        backup_dir.mkdir(exist_ok=True)
        
        for py_file in Path(".").glob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            (backup_dir / py_file.name).write_text(content, encoding="utf-8")
        
        return backup_dir


self_improver = SelfImprover()
