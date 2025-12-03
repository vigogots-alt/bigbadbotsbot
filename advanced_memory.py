# advanced_memory.py - Добавить в state.py

from datetime import datetime, timedelta
from collections import defaultdict
import logging
import numpy as np
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# ========== ВЕКТОРНАЯ ПАМЯТЬ ========== #

class VectorMemory:
    """
    Семантическая память на основе эмбеддингов.
    Позволяет находить похожие разговоры и извлекать релевантный контекст.
    """
    
    def __init__(self):
        self.memories = defaultdict(list)  # user_id -> [(text, embedding, timestamp, importance)]
        self.embedding_dim = 384  # Размерность для простых эмбеддингов
        self.embedding_index = defaultdict(dict)  # user_id -> {memory_id: embedding}
    
    def _simple_embedding(self, text: str) -> list:
        """
        Упрощённый эмбеддинг (можно заменить на real embeddings от Gemini).
        """
        # TF-IDF подобное представление
        words = text.lower().split()
        word_freq = defaultdict(int)
        for word in words:
            word_freq[word] += 1
        
        # Создаём вектор из топ-слов
        vector = [0.0] * 100  # упрощённый вектор
        for i, word in enumerate(sorted(word_freq.keys())[:100]):
            if i < 100:
                vector[i] = word_freq[word] / len(words)
        
        return vector
    
    def add_memory(self, user_id: int, text: str, importance: float = 0.5):
        """???????? ????????????."""
        embedding = self._simple_embedding(text)
        memory_id = len(self.memories[user_id])

        memory = {
            "id": memory_id,
            "text": text,
            "embedding": embedding,
            "timestamp": datetime.utcnow().isoformat(),
            "importance": importance,
            "access_count": 0
        }
        
        self.memories[user_id].append(memory)
        self.embedding_index[user_id][memory_id] = embedding
        
        # ???????????? ?????? ??????
        if len(self.memories[user_id]) > 1000:
            removed_ids = [m["id"] for m in self.memories[user_id][800:]]
            for rid in removed_ids:
                if rid in self.embedding_index[user_id]:
                    del self.embedding_index[user_id][rid]
            self.memories[user_id] = self.memories[user_id][:800]

    def cosine_similarity(self, vec1: list, vec2: list) -> float:
        """Косинусное сходство между векторами."""
        if not vec1 or not vec2:
            return 0.0
        
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot / (norm1 * norm2)
    
    def search_similar(self, user_id: int, query: str, top_k: int = 5) -> list:
        """????? ??????? ????????????."""
        if user_id not in self.embedding_index:
            return []
        
        query_emb = self._simple_embedding(query)
        similarities = {}
        for mem_id, embedding in self.embedding_index[user_id].items():
            sim = self.cosine_similarity(query_emb, embedding)
            similarities[mem_id] = sim
        
        top_ids = sorted(similarities.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        results = []
        for mem_id, sim in top_ids:
            mem = self.memories[user_id][mem_id]
            results.append({
                "text": mem["text"],
                "similarity": sim,
                "timestamp": mem["timestamp"],
                "importance": mem["importance"],
            })
            mem["access_count"] += 1
        
        return results


# ========== КОНТЕКСТНАЯ ПАМЯТЬ ========== #

class ContextualMemory:
    """
    Память с контекстом: связывает события по времени, месту, эмоциям.
    """
    
    def __init__(self):
        self.contexts = defaultdict(lambda: defaultdict(list))
        # user_id -> context_type -> [memories]
    
    def add_context(self, user_id: int, context_type: str, data: dict):
        """
        Добавить контекстное воспоминание.
        context_type: "temporal", "emotional", "topical", "relational"
        """
        data["timestamp"] = datetime.utcnow().isoformat()
        self.contexts[user_id][context_type].append(data)
        
        # Ограничение размера
        if len(self.contexts[user_id][context_type]) > 500:
            self.contexts[user_id][context_type] = self.contexts[user_id][context_type][-400:]
    
    def get_temporal_context(self, user_id: int, hours_back: int = 24) -> list:
        """Получить контекст за последние N часов."""
        cutoff = datetime.utcnow() - timedelta(hours=hours_back)
        temporal = self.contexts[user_id].get("temporal", [])
        
        return [
            m for m in temporal
            if datetime.fromisoformat(m["timestamp"]) > cutoff
        ]
    
    def get_emotional_context(self, user_id: int, emotion: str) -> list:
        """Получить контекст по эмоции."""
        emotional = self.contexts[user_id].get("emotional", [])
        return [m for m in emotional if m.get("emotion") == emotion]
    
    def get_topical_context(self, user_id: int, topic: str) -> list:
        """Получить контекст по теме."""
        topical = self.contexts[user_id].get("topical", [])
        return [m for m in topical if topic in m.get("topics", [])]


# ========== ЭПИЗОДИЧЕСКАЯ ПАМЯТЬ ========== #

class EpisodicMemory:
    """
    Память о важных событиях/эпизодах в жизни пользователя.
    """
    
    def __init__(self):
        self.episodes = defaultdict(list)
    
    def create_episode(self, user_id: int, title: str, description: str, 
                      importance: float, tags: list):
        """Создать эпизод."""
        episode = {
            "id": len(self.episodes[user_id]) + 1,
            "title": title,
            "description": description,
            "importance": importance,
            "tags": tags,
            "timestamp": datetime.utcnow().isoformat(),
            "related_conversations": [],
            "reflections": []
        }
        self.episodes[user_id].append(episode)
        return episode
    
    def link_conversation(self, user_id: int, episode_id: int, conversation_snippet: str):
        """Связать разговор с эпизодом."""
        for ep in self.episodes[user_id]:
            if ep["id"] == episode_id:
                ep["related_conversations"].append({
                    "snippet": conversation_snippet,
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    def add_reflection(self, user_id: int, episode_id: int, reflection: str):
        """Добавить рефлексию к эпизоду."""
        for ep in self.episodes[user_id]:
            if ep["id"] == episode_id:
                ep["reflections"].append({
                    "text": reflection,
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    def get_important_episodes(self, user_id: int, min_importance: float = 0.7) -> list:
        """Получить важные эпизоды."""
        return [ep for ep in self.episodes[user_id] if ep["importance"] >= min_importance]


# ========== ИНТЕГРАЦИЯ ========== #

vector_memory = VectorMemory()
contextual_memory = ContextualMemory()
episodic_memory = EpisodicMemory()


def _detect_tone(text: str) -> float:
    """Лёгкая оценка тона сообщения."""
    lower = (text or "").lower()
    positive = ["great", "good", "спасибо", "thanks", "класс", "отлично", "супер"]
    negative = ["bad", "sad", "ужас", "проблема", "плохо", "злой", "angry"]
    score = 0
    for kw in positive:
        if kw in lower:
            score += 1
    for kw in negative:
        if kw in lower:
            score -= 1
    return float(max(-1.0, min(1.0, score * 0.2)))


def enhanced_add_observation(user_id: int, message_text: str, profile: dict | None = None):
    """Расширенное добавление наблюдения с продвинутой памятью."""
    try:
        if profile is None:
            try:
                from state import get_profile
                profile = get_profile(user_id)
            except Exception:
                profile = {}

        clean_text = message_text or ""
        importance = 0.5
        if any(tag in clean_text.lower() for tag in ["важно", "срочно", "помоги", "проблема"]):
            importance = 0.9

        vector_memory.add_memory(user_id, clean_text, importance)

        contextual_memory.add_context(user_id, "temporal", {
            "text": clean_text,
            "hour": datetime.utcnow().hour
        })

        tone = _detect_tone(clean_text)
        if abs(tone) > 0.3:
            emotion = "positive" if tone > 0 else "negative"
            contextual_memory.add_context(user_id, "emotional", {
                "text": clean_text,
                "emotion": emotion,
                "intensity": abs(tone)
            })

        patterns = profile.get("patterns", []) if isinstance(profile, dict) else []
        if patterns:
            contextual_memory.add_context(user_id, "topical", {
                "text": clean_text,
                "topics": patterns
            })

        if importance > 0.8:
            episodic_memory.create_episode(
                user_id,
                title=f"Важное событие {datetime.utcnow().strftime('%Y-%m-%d')}",
                description=clean_text[:200],
                importance=importance,
                tags=patterns,
            )
    except Exception:
        logger.exception("Advanced memory pipeline failed for user %s", user_id)


def build_enhanced_context(user_id: int, current_message: str) -> str:
    """Построить обогащённый контекст используя продвинутую память."""
    context_parts = []
    
    # Базовый контекст
    try:
        from state import build_super_context
        base = build_super_context(user_id)
    except Exception:
        base = ""
    if base:
        context_parts.append(f"=== БАЗОВЫЙ КОНТЕКСТ ===\n{base}")
    
    # Похожие прошлые разговоры
    similar = vector_memory.search_similar(user_id, current_message, top_k=3)
    if similar:
        context_parts.append("\n=== ПОХОЖИЕ ПРОШЛЫЕ РАЗГОВОРЫ ===")
        for i, mem in enumerate(similar, 1):
            context_parts.append(
                f"{i}. Сходство: {mem['similarity']:.2f}\n"
                f"   {mem['text'][:150]}..."
            )
    
    # Временной контекст (последние 24 часа)
    temporal = contextual_memory.get_temporal_context(user_id, hours_back=24)
    if temporal:
        context_parts.append(f"\n=== ПОСЛЕДНИЕ 24 ЧАСА ===")
        context_parts.append(f"Активность: {len(temporal)} событий")
    
    # Эмоциональный контекст
    current_tone = _detect_tone(current_message)
    if abs(current_tone) > 0.3:
        emotion = "positive" if current_tone > 0 else "negative"
        emotional = contextual_memory.get_emotional_context(user_id, emotion)
        if emotional:
            context_parts.append(
                f"\n=== ЭМОЦИОНАЛЬНЫЙ КОНТЕКСТ ({emotion}) ===\n"
                f"Похожих эмоциональных моментов: {len(emotional)}"
            )
    
    # Важные эпизоды
    episodes = episodic_memory.get_important_episodes(user_id)
    if episodes:
        context_parts.append(f"\n=== ВАЖНЫЕ ЭПИЗОДЫ ===")
        for ep in episodes[-3:]:
            context_parts.append(
                f"• {ep['title']} (важность: {ep['importance']:.2f})\n"
                f"  {ep['description'][:100]}..."
            )
    
    if not context_parts and base:
        return base
    return "\n\n".join(context_parts)


# Команды для работы с продвинутой памятью

async def search_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск в памяти по запросу."""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Использование: /search <запрос>")
        return
    
    query = " ".join(context.args)
    results = vector_memory.search_similar(user_id, query, top_k=5)
    
    if not results:
        await update.message.reply_text("Ничего не найдено в памяти.")
        return
    
    text = f"🔍 Найдено в памяти по запросу '{query}':\n\n"
    for i, res in enumerate(results, 1):
        text += (
            f"{i}. Сходство: {res['similarity']:.2f}\n"
            f"   {res['text'][:150]}...\n"
            f"   ({res['timestamp'][:10]})\n\n"
        )
    
    await update.message.reply_text(text)


async def show_episodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать важные эпизоды."""
    user_id = update.effective_user.id
    episodes = episodic_memory.get_important_episodes(user_id)
    
    if not episodes:
        await update.message.reply_text("Пока нет записанных эпизодов.")
        return
    
    text = "📖 Важные эпизоды:\n\n"
    for ep in episodes[-5:]:
        text += (
            f"• {ep['title']} (⭐ {ep['importance']:.1f})\n"
            f"  {ep['description'][:100]}...\n"
            f"  Теги: {', '.join(ep['tags'])}\n"
            f"  {ep['timestamp'][:10]}\n\n"
        )
    
    await update.message.reply_text(text)


async def create_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создать эпизод вручную."""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "Использование: /episode <заголовок> | <описание> | <важность 0-1> | <теги через запятую>"
        )
        return
    
    text = " ".join(context.args)
    parts = text.split("|")
    
    if len(parts) < 4:
        await update.message.reply_text("Недостаточно параметров. Используй | как разделитель.")
        return
    
    title = parts[0].strip()
    description = parts[1].strip()
    try:
        importance = float(parts[2].strip())
    except:
        importance = 0.5
    tags = [t.strip() for t in parts[3].split(",")]
    
    episode = episodic_memory.create_episode(user_id, title, description, importance, tags)
    
    await update.message.reply_text(
        f"✅ Эпизод создан:\n"
        f"ID: {episode['id']}\n"
        f"Заголовок: {title}\n"
        f"Важность: {importance:.2f}"
    )
