from pathlib import Path
from uuid import uuid4

from ..config import AUDIO_DIR


class TextToSpeech:
    def speak_to_file(self, text: str, language: str, emotion: str = "neutral") -> str | None:
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        output = AUDIO_DIR / f"{uuid4().hex}.wav"
        try:
            import pyttsx3

            engine = pyttsx3.init()
            rate = 175
            if emotion == "sad":
                rate = 135
            elif emotion in {"excited", "urgent"}:
                rate = 205
            engine.setProperty("rate", rate)
            select_voice(engine, language)
            engine.save_to_file(text, str(output))
            engine.runAndWait()
            return f"/audio/{output.name}"
        except Exception:
            return None


def select_voice(engine, language: str) -> None:
    voices = engine.getProperty("voices")
    hints = {
        "en": ["english", "zira", "david"],
        "ur": ["urdu", "hindi", "heera"],
    }.get(language, [])
    for voice in voices:
        haystack = f"{voice.id} {getattr(voice, 'name', '')}".lower()
        if any(hint in haystack for hint in hints):
            engine.setProperty("voice", voice.id)
            return
