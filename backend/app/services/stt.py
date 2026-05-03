import json
import wave
from pathlib import Path

from ..config import STT_MODELS


class SpeechToText:
    def transcribe_wav(self, path: Path, language: str) -> str:
        model_path = Path(STT_MODELS.get(language, ""))
        if not model_path.exists():
            return ""
        try:
            from vosk import KaldiRecognizer, Model

            with wave.open(str(path), "rb") as wav:
                model = Model(str(model_path))
                recognizer = KaldiRecognizer(model, wav.getframerate())
                chunks: list[str] = []
                while True:
                    data = wav.readframes(4000)
                    if not data:
                        break
                    if recognizer.AcceptWaveform(data):
                        chunks.append(json.loads(recognizer.Result()).get("text", ""))
                chunks.append(json.loads(recognizer.FinalResult()).get("text", ""))
            return " ".join(part for part in chunks if part).strip()
        except Exception:
            return ""
