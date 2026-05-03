import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "app" / "data"
DB_PATH = DATA_DIR / "speech_translation.db"
DOCS_DIR = DATA_DIR / "documents"
AUDIO_DIR = DATA_DIR / "audio"

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_TTL_SECONDS = int(os.getenv("JWT_TTL_SECONDS", "86400"))

STT_MODELS = {
    "en": os.getenv("STT_MODEL_EN", "models/vosk-en"),
    "ur": os.getenv("STT_MODEL_UR", "models/vosk-ur"),
}

TRANSLATION_MODELS = {
    ("en", "ur"): os.getenv("TRANSLATION_MODEL_EN_UR", "Helsinki-NLP/opus-mt-en-ur"),
    ("ur", "en"): os.getenv("TRANSLATION_MODEL_UR_EN", "Helsinki-NLP/opus-mt-ur-en"),
}

OFFLINE_ONLY = os.getenv("OFFLINE_ONLY", "true").lower() == "true"
