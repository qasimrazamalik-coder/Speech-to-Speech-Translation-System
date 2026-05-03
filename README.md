# Speech-to-Speech Translation System

Advanced offline-first speech-to-speech translation scaffold for English, Urdu, and additional language pairs.

## Prototype Status

This project is a prototype and proof-of-concept, not a fully functional production translation system. Some features use lightweight fallbacks or browser/device capabilities, and high-quality offline STT, translation, and TTS require downloading and configuring the proper local models and voices.

## Architecture

- `backend/`: FastAPI service for auth, STT, translation, RAG, TTS, analytics, and realtime WebSocket conversation.
- `frontend/`: React/Vite UI for sign-in, conversation mode, translation, context indexing, audio playback, and analytics.
- `backend/app/data/`: Local SQLite database, uploaded RAG documents, and generated audio files.

## Capabilities

- Offline STT adapter using Vosk model paths.
- Offline translation adapter using Hugging Face MarianMT models with local-file mode.
- Offline TTS adapter using `pyttsx3`.
- JWT sign-up/sign-in with local SQLite users.
- Conversation memory for contextual translation.
- RAG context retrieval from local `.txt` documents.
- Emotion-aware TTS rate selection.
- Lightweight fallback translation when model files are unavailable.

## Backend Setup

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Place offline Vosk models at:

```text
backend/models/vosk-en
backend/models/vosk-ur
```

For fully offline translation, download the MarianMT models once and point `.env` to local model folders.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Default backend URL:

```text
http://localhost:8000
```

Override with:

```bash
VITE_API_URL=http://localhost:8000 npm run dev
```

## API

- `POST /auth/signup`
- `POST /auth/signin`
- `POST /translate`
- `POST /speech`
- `POST /documents`
- `GET /analytics`
- `WS /ws/conversation?token=...`

## Edge Deployment Notes

- Use quantized MarianMT/T5 models where possible.
- Keep Vosk model sizes matched to the device.
- Disable TTS audio generation for low-power analytics-only deployments.
- Store only domain glossaries needed for the active workflow.
