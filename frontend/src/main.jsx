import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, FileText, Languages, Lock, Mic, Play, Send, Volume2 } from "lucide-react";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [authMode, setAuthMode] = useState("signin");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [sourceLang, setSourceLang] = useState("en");
  const [targetLang, setTargetLang] = useState("ur");
  const [domain, setDomain] = useState("general");
  const [text, setText] = useState("");
  const [turns, setTurns] = useState([]);
  const [docText, setDocText] = useState("");
  const [analytics, setAnalytics] = useState(null);
  const [status, setStatus] = useState("");
  const [liveState, setLiveState] = useState("offline");
  const socketRef = useRef(null);
  const recognitionRef = useRef(null);
  const pendingLiveTextRef = useRef("");

  const headers = useMemo(() => ({ Authorization: `Bearer ${token}`, "Content-Type": "application/json" }), [token]);

  useEffect(() => {
    if (token) refreshAnalytics();
    return () => stopLiveMode();
  }, [token]);

  async function refreshAnalytics() {
    fetch(`${API}/analytics`, { headers })
      .then((res) => res.json())
      .then(setAnalytics)
      .catch(() => {});
  }

  async function authenticate(event) {
    event.preventDefault();
    setStatus("Authenticating...");
    const res = await fetch(`${API}/auth/${authMode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      setStatus(data.detail || "Authentication failed");
      return;
    }
    localStorage.setItem("token", data.token);
    setToken(data.token);
    setStatus("Signed in");
  }

  async function translate() {
    if (!text.trim()) return;
    setStatus("Translating...");
    const res = await fetch(`${API}/translate`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text, source_lang: sourceLang, target_lang: targetLang, domain, speak: true }),
    });
    const data = await res.json();
    if (!res.ok) {
      setStatus(data.detail || "Translation failed");
      return;
    }
    addTurn(data);
    setText("");
    setStatus("Translated and speaking");
    refreshAnalytics();
  }

  function addTurn(turn) {
    setTurns((items) => [turn, ...items]);
    speakTurn(turn);
  }

  async function speakTurn(turn) {
    if (turn.audio_url) {
      try {
        const audio = new Audio(`${API}${turn.audio_url}`);
        await audio.play();
        return;
      } catch {
        speakInBrowser(turn.translated_text, targetLang, turn.emotion);
        return;
      }
    }
    speakInBrowser(turn.translated_text, targetLang, turn.emotion);
  }

  function speakInBrowser(value, language, emotion = "neutral") {
    if (!("speechSynthesis" in window) || !value) {
      setStatus("Speech synthesis is not available in this browser");
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(value);
    utterance.lang = language === "ur" ? "ur-PK" : "en-US";
    utterance.rate = emotion === "sad" ? 0.82 : emotion === "urgent" || emotion === "excited" ? 1.12 : 0.95;
    utterance.pitch = emotion === "sad" ? 0.85 : emotion === "excited" ? 1.12 : 1;
    const voices = window.speechSynthesis.getVoices();
    const hint = language === "ur" ? ["urdu", "hindi", "pakistan", "india"] : ["english", "zira", "david"];
    const voice = voices.find((item) => hint.some((part) => `${item.name} ${item.lang}`.toLowerCase().includes(part)));
    if (voice) utterance.voice = voice;
    window.speechSynthesis.speak(utterance);
  }

  function connectConversation() {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      startBrowserRecognition();
      setStatus("Live conversation is already connected");
      return Promise.resolve(socketRef.current);
    }
    setLiveState("connecting");
    setStatus("Connecting live conversation...");
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(`${API.replace("http", "ws")}/ws/conversation?token=${encodeURIComponent(token)}`);
      ws.onopen = () => {
        socketRef.current = ws;
        setLiveState("connected");
        setStatus("Live conversation connected. Type, send, or speak into the mic.");
        startBrowserRecognition();
        if (pendingLiveTextRef.current) {
          sendOverSocket(pendingLiveTextRef.current);
          pendingLiveTextRef.current = "";
        }
        resolve(ws);
      };
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        addTurn(data);
        setStatus("Live translation received and spoken");
        refreshAnalytics();
      };
      ws.onerror = () => {
        setLiveState("error");
        setStatus("Live connection failed");
        reject(new Error("WebSocket failed"));
      };
      ws.onclose = () => {
        socketRef.current = null;
        setLiveState("offline");
        stopRecognitionOnly();
        setStatus("Live conversation disconnected");
      };
    });
  }

  async function sendRealtime() {
    const value = text.trim();
    if (!value) {
      setStatus("Type text or use the mic before sending live");
      return;
    }
    setText("");
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      sendOverSocket(value);
      return;
    }
    pendingLiveTextRef.current = value;
    try {
      await connectConversation();
    } catch {
      pendingLiveTextRef.current = "";
    }
  }

  function sendOverSocket(value) {
    socketRef.current?.send(JSON.stringify({ text: value, source_lang: sourceLang, target_lang: targetLang, domain }));
    setStatus("Sent live text for translation...");
  }

  function startBrowserRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setStatus("Live text is connected. Browser microphone speech recognition is not supported here.");
      return;
    }
    stopRecognitionOnly();
    const recognition = new SpeechRecognition();
    recognition.lang = sourceLang === "ur" ? "ur-PK" : "en-US";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.onresult = (event) => {
      let finalText = "";
      let interimText = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const transcript = event.results[index][0].transcript.trim();
        if (event.results[index].isFinal) finalText += `${transcript} `;
        else interimText += `${transcript} `;
      }
      if (interimText) setText(interimText.trim());
      if (finalText.trim() && socketRef.current?.readyState === WebSocket.OPEN) {
        sendOverSocket(finalText.trim());
        setText("");
      }
    };
    recognition.onerror = (event) => setStatus(`Mic recognition: ${event.error}`);
    recognition.onend = () => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        try {
          recognition.start();
        } catch {}
      }
    };
    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch {
      setStatus("Mic is already listening");
    }
  }

  function stopRecognitionOnly() {
    if (recognitionRef.current) {
      recognitionRef.current.onend = null;
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
  }

  function stopLiveMode() {
    stopRecognitionOnly();
    socketRef.current?.close();
    socketRef.current = null;
    setLiveState("offline");
  }

  async function addDocument() {
    if (!docText.trim()) return;
    const res = await fetch(`${API}/documents`, {
      method: "POST",
      headers,
      body: JSON.stringify({ name: `${domain}-context`, text: docText }),
    });
    const data = await res.json();
    setStatus(res.ok ? `Context indexed: ${data.chunks} chunks` : data.detail || "Index failed");
    if (res.ok) setDocText("");
  }

  if (!token) {
    return (
      <main className="auth-shell">
        <form className="auth-panel" onSubmit={authenticate}>
          <div className="mark"><Lock size={26} /></div>
          <h1>Speech Translation</h1>
          <p>Offline-first multilingual speech-to-speech translation workspace.</p>
          <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" />
          <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" type="password" />
          <div className="segmented">
            <button type="button" className={authMode === "signin" ? "active" : ""} onClick={() => setAuthMode("signin")}>Sign in</button>
            <button type="button" className={authMode === "signup" ? "active" : ""} onClick={() => setAuthMode("signup")}>Sign up</button>
          </div>
          <button className="primary">Continue</button>
          <span className="status">{status}</span>
        </form>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside>
        <h1><Languages size={24} /> Translator</h1>
        <label>Source</label>
        <select value={sourceLang} onChange={(event) => setSourceLang(event.target.value)}>
          <option value="en">English</option>
          <option value="ur">Urdu</option>
        </select>
        <label>Target</label>
        <select value={targetLang} onChange={(event) => setTargetLang(event.target.value)}>
          <option value="ur">Urdu</option>
          <option value="en">English</option>
        </select>
        <label>Domain</label>
        <select value={domain} onChange={(event) => setDomain(event.target.value)}>
          <option>general</option>
          <option>medical</option>
          <option>legal</option>
          <option>education</option>
          <option>travel</option>
        </select>
        <button onClick={() => { stopLiveMode(); localStorage.removeItem("token"); setToken(""); }}>Sign out</button>
      </aside>

      <section className="workspace">
        <div className="composer">
          <div className={`live-badge ${liveState}`}>Live: {liveState}</div>
          <textarea value={text} onChange={(event) => setText(event.target.value)} placeholder="Type here, or press Connect and speak..." />
          <div className="actions">
            <button onClick={translate}><Send size={18} /> Translate</button>
            <button onClick={connectConversation}><Mic size={18} /> Connect</button>
            <button onClick={sendRealtime}><Activity size={18} /> Send live</button>
            <button onClick={stopLiveMode}><Volume2 size={18} /> Stop live</button>
          </div>
          <span className="status">{status}</span>
        </div>

        <div className="grid">
          <section className="panel">
            <h2>Conversation</h2>
            {turns.map((turn, index) => (
              <article className="turn" key={index}>
                <small>{turn.emotion}</small>
                <p>{turn.source_text}</p>
                <strong dir={targetLang === "ur" ? "rtl" : "ltr"}>{turn.translated_text}</strong>
                <button className="speak-button" onClick={() => speakTurn(turn)}><Volume2 size={16} /> Speak again</button>
                {turn.audio_url && <audio controls src={`${API}${turn.audio_url}`} />}
              </article>
            ))}
          </section>

          <section className="panel">
            <h2><FileText size={18} /> RAG Context</h2>
            <textarea value={docText} onChange={(event) => setDocText(event.target.value)} placeholder="Paste domain notes, glossary, policy, or medical context..." />
            <button onClick={addDocument}><Play size={18} /> Index context</button>
            <h2><Activity size={18} /> Analytics</h2>
            <p>Total translations: {analytics?.total_translations ?? 0}</p>
            {(analytics?.language_pairs || []).map((pair) => <p key={pair.pair}>{pair.pair}: {pair.count}</p>)}
          </section>
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
