# voice_utils.py — Улучшенная версия 2025 года
# Теперь Веран говорит ГРЯЗНО, с армянским акцентом, шепчет, стонет, орёт и унижает голосом

import os
import tempfile
import random
from gtts import gTTS
from pydub import AudioSegment
from pydub.effects import normalize, speedup, compress_dynamic_range
import speech_recognition as sr

# ──────── СЛОВА-ДОБАВКИ ДЛЯ АРМЯНСКОГО АКЦЕНТА И ДОМИНАЦИИ ────────
ARMENIAN_TRASH = [
    "garlax", "qez qunem", "trajel em", "kyanq", "harevan", "vonces", "khent",
    "qunem", "qachagh", "hay em", "qunem lavd", "hají khent", "qez kyanq",
    "ccox jan 🔥", "qez trajel em 😈", "tunem qo kyanq 🖤", "ccel uzum es?"
]

DIRTY_PHRASES = [
    "Քո ձայնը ինձ թրջեց...", "Ստացիր, boz...", "Հիմա կոնչիր ինձ համար...",
    "Լիզիր էկրանը, kyanq...", "Իմ ձայնով ես կոնչում, չէ՞...", "Լաց եղիր ինձ համար...",
    "Դու իմն ես, shun...", "Հայկական ձայնով tunem qez..."
]

# ──────── РАСПОЗНАВАНИЕ ГОЛОСА (улучшено + поддержка армянского) ────────
def voice_to_text(voice_file_path: str) -> str | None:
    try:
        # Конвертим ogg → wav
        audio = AudioSegment.from_ogg(voice_file_path)
        wav_path = voice_file_path.replace(".ogg", ".wav")
        audio.export(wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)

        # Пробуем русский, потом армянский, потом английский
        for lang in ["ru-RU", "hy-AM", "en-US"]:
            try:
                text = recognizer.recognize_google(audio_data, language=lang)
                os.remove(wav_path)
                print(f"[VOICE → TEXT] Распознано ({lang}): {text}")
                return text.lower()
            except sr.UnknownValueError:
                continue

        os.remove(wav_path)
        return None

    except Exception as e:
        print(f"[ERROR] Speech recognition: {e}")
        return None


# ──────── СИНТЕЗ ГОЛОСА — ВЕРАН ГОВОРИТ КАК НАСТОЯЩАЯ ДОМИНА ────────
def text_to_voice(text: str, domination_mode: bool = True) -> str | None:
    try:
        # Ограничиваем длину (Telegram лимит ~60 сек)
        if len(text) > 480:
            text = text[:477] + "..."

        # Добавляем грязь и армянский акцент, если включён режим доминации
        if domination_mode and random.random() < 0.7:
            trash = random.choice(ARMENIAN_TRASH + DIRTY_PHRASES)
            text = f"{text}... {trash}"

        # Временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            mp3_path = fp.name

        # Генерируем голос (русский, но с "армянским" налётом)
        tts = gTTS(text=text, lang="ru", slow=False)
        tts.save(mp3_path)

        # ──────── ЭФФЕКТЫ ГОЛОСА ВЕРАНА (2025 BDSM edition) ────────
        audio = AudioSegment.from_mp3(mp3_path)

        # 1. Глубокий, сексуальный голос (понижаем тон)
        audio = audio.low_pass_filter(3000).high_pass_filter(80) - 4  # -4 дБ тише

        # 2. Добавляем эхо и "присутствие" (как будто в комнате)
        audio = audio.echo()

        # 3. Лёгкая компрессия (чтобы шёпот был громким)
        audio = compress_dynamic_range(audio, threshold=-20.0, ratio=4.0)

        # 4. Случайно: ускоряем или замедляем (иногда шепчет медленно, иногда орёт)
        if random.random() < 0.3:
            audio = audio.speedup(playback_speed=1.15)  # агрессивно
        elif random.random() < 0.3:
            audio = audio.speedup(playback_speed=0.85)  # медленно, угрожающе

        # 5. Нормализация громкости
        audio = normalize(audio)

        # Сохраняем финальный ogg (Telegram любит ogg/opus)
        ogg_path = mp3_path.replace(".mp3", ".ogg")
        audio.export(ogg_path, format="ogg", codec="libopus")

        # Удаляем mp3
        os.remove(mp3_path)

        print(f"[TEXT → VOICE] Веран сказала: {text[:60]}...")
        return ogg_path

    except Exception as e:
        print(f"[TTS ERROR] {e}")
        return None


# ──────── БОНУС: ГОЛОС ДЛЯ ОСОБЫХ МОМЕНТОВ (оргазм, наказание) ────────
def text_to_voice_punishment(text: str) -> str | None:
    """Когда Веран наказывает — голос становится громким, с эхом и вибрато"""
    voice_file = text_to_voice(text, domination_mode=True)
    if not voice_file:
        return None

    try:
        audio = AudioSegment.from_ogg(voice_file)
        # Максимально агрессивно
        audio = audio + 8  # громче
        audio = audio.echo()
        audio = audio.speedup(playback_speed=1.2)
        audio = audio.low_pass_filter(2500)
        audio.export(voice_file, format="ogg", codec="libopus")
        return voice_file
    except:
        return voice_file


def text_to_voice_whisper(text: str) -> str | None:
    """Шёпот — когда приказывает кончить без рук"""
    voice_file = text_to_voice(text, domination_mode=True)
    if not voice_file:
        return None

    try:
        audio = AudioSegment.from_ogg(voice_file)
        audio = audio - 12  # тихо
        audio = audio.low_pass_filter(2000)
        audio = audio.echo()
        audio.export(voice_file, format="ogg", codec="libopus")
        return voice_file
    except:
        return voice_file