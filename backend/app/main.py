from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .config import AUDIO_DIR
from .db import get_db, init_db
from .security import create_token, decode_token, hash_password, verify_password
from .services.conversation import ConversationMemory
from .services.emotion import detect_emotion
from .services.rag import RagStore
from .services.stt import SpeechToText
from .services.translator import Translator
from .services.tts import TextToSpeech

app = FastAPI(title="Offline Speech-to-Speech Translation System")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stt = SpeechToText()
translator = Translator()
tts = TextToSpeech()
rag = RagStore()
memory = ConversationMemory()


class AuthPayload(BaseModel):
    username: str
    password: str


class TranslatePayload(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "ur"
    domain: str = "general"
    speak: bool = True


class DocumentPayload(BaseModel):
    name: str
    text: str


@app.on_event("startup")
def startup() -> None:
    init_db()
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def current_user(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        claims = decode_token(authorization.removeprefix("Bearer ").strip())
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token") from None
    with get_db() as conn:
        user = conn.execute("SELECT id, username FROM users WHERE username = ?", (claims["sub"],)).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)


@app.post("/auth/signup")
def signup(payload: AuthPayload) -> dict:
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (payload.username.strip().lower(), hash_password(payload.password)),
            )
    except Exception:
        raise HTTPException(status_code=409, detail="Username already exists") from None
    return {"token": create_token(payload.username.strip().lower())}


@app.post("/auth/signin")
def signin(payload: AuthPayload) -> dict:
    username = payload.username.strip().lower()
    with get_db() as conn:
        user = conn.execute("SELECT username, password_hash FROM users WHERE username = ?", (username,)).fetchone()
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(username)}


@app.post("/translate")
def translate(payload: TranslatePayload, user: dict = Depends(current_user)) -> dict:
    context = memory.get(user["username"]) + rag.retrieve(f"{payload.domain} {payload.text}")
    translated = translator.translate(payload.text, payload.source_lang, payload.target_lang, context)
    emotion = detect_emotion(payload.text)
    audio_url = tts.speak_to_file(translated, payload.target_lang, emotion) if payload.speak else None
    memory.add(user["username"], payload.text, translated)
    save_event(user["id"], payload, translated, emotion)
    return {
        "source_text": payload.text,
        "translated_text": translated,
        "emotion": emotion,
        "context_used": context[:3],
        "audio_url": audio_url,
    }


@app.post("/speech")
async def speech(
    source_lang: str = "en",
    target_lang: str = "ur",
    domain: str = "general",
    audio: UploadFile = File(...),
    user: dict = Depends(current_user),
) -> dict:
    suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = Path(tmp.name)
    source_text = stt.transcribe_wav(tmp_path, source_lang)
    tmp_path.unlink(missing_ok=True)
    if not source_text:
        raise HTTPException(status_code=422, detail="STT failed. Check WAV format and offline model path.")
    payload = TranslatePayload(text=source_text, source_lang=source_lang, target_lang=target_lang, domain=domain)
    return translate(payload, user)


@app.post("/documents")
def add_document(payload: DocumentPayload, user: dict = Depends(current_user)) -> dict:
    path = rag.add_document(payload.name, payload.text)
    return {"stored": path.name, "chunks": rag.refresh()}


@app.get("/analytics")
def analytics(user: dict = Depends(current_user)) -> dict:
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) AS count FROM events WHERE user_id = ?", (user["id"],)).fetchone()
        pairs = conn.execute(
            """
            SELECT source_lang || '→' || target_lang AS pair, COUNT(*) AS count
            FROM events WHERE user_id = ?
            GROUP BY pair ORDER BY count DESC
            """,
            (user["id"],),
        ).fetchall()
    return {"total_translations": total["count"], "language_pairs": [dict(row) for row in pairs]}


@app.get("/audio/{name}")
def audio(name: str) -> FileResponse:
    path = AUDIO_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(path, media_type="audio/wav")


@app.websocket("/ws/conversation")
async def conversation_socket(socket: WebSocket) -> None:
    await socket.accept()
    try:
        token = socket.query_params.get("token", "")
        claims = decode_token(token)
        username = claims["sub"]
        with get_db() as conn:
            user = conn.execute("SELECT id, username FROM users WHERE username = ?", (username,)).fetchone()
        if not user:
            await socket.close(code=1008)
            return
        while True:
            payload = await socket.receive_json()
            text = payload.get("text", "")
            source_lang = payload.get("source_lang", "en")
            target_lang = payload.get("target_lang", "ur")
            domain = payload.get("domain", "general")
            context = memory.get(username) + rag.retrieve(f"{domain} {text}")
            translated = translator.translate(text, source_lang, target_lang, context)
            emotion = detect_emotion(text)
            audio_url = tts.speak_to_file(translated, target_lang, emotion)
            memory.add(username, text, translated)
            save_event(
                user["id"],
                TranslatePayload(
                    text=text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    domain=domain,
                    speak=True,
                ),
                translated,
                emotion,
            )
            await socket.send_json(
                {
                    "source_text": text,
                    "translated_text": translated,
                    "emotion": emotion,
                    "audio_url": audio_url,
                }
            )
    except (WebSocketDisconnect, ValueError):
        await socket.close()


def save_event(user_id: int, payload: TranslatePayload, translated: str, emotion: str) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO events
            (user_id, source_lang, target_lang, source_text, translated_text, emotion, domain)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                payload.source_lang,
                payload.target_lang,
                payload.text,
                translated,
                emotion,
                payload.domain,
            ),
        )
